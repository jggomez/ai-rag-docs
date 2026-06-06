import logging
from typing import List, Dict, Optional

from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from flashrank import Ranker, RerankRequest

logger = logging.getLogger(__name__)

# Singleton: loaded once at startup — avoids re-loading the ONNX model per call.
# ms-marco-MiniLM-L-12-v2 is lightweight (~60 MB) and runs on CPU in ~50 ms.
_reranker = Ranker(model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/flashrank_cache")

# Number of candidates fetched from Firestore before reranking.
_VECTOR_SEARCH_CANDIDATE_LIMIT = 20

# Final top-k returned to the caller after reranking.
_RERANK_TOP_K = 7


class FirestoreVectorSearchRepository:
    """
    Repository dedicated to vector similarity search and cross-document linking.

    Retrieval pipeline:
      1. Hybrid vector search against Firestore (cosine KNN) fetching up to
         _VECTOR_SEARCH_CANDIDATE_LIMIT candidates.
      2. Cross-encoder reranking with FlashRank (ms-marco-MiniLM-L-12-v2) to
         reorder candidates by semantic relevance to the original query text.
      3. Return the top _RERANK_TOP_K reranked chunks.

    If query_text is not provided, the reranking step is skipped and the raw
    Firestore ordering is preserved (backwards-compatible behaviour).
    """

    def __init__(
        self,
        database_received: str = "docs-recibidos",
        database_sent: str = "docs-enviados",
        client_received: firestore.Client = None,
        client_sent: firestore.Client = None,
    ):
        self.client_received = client_received or firestore.Client(database=database_received)
        self.client_sent = client_sent or firestore.Client(database=database_sent)
        self.chunks_collection = self.client_received.collection("documentos_chunks")
        self.sent_docs_collection = self.client_sent.collection("documentos")

    def find_similar_chunks(
        self,
        query_vector: List[float],
        query_text: Optional[str] = None,
        limit: int = _VECTOR_SEARCH_CANDIDATE_LIMIT,
        work_front: Optional[str] = None,
    ) -> List[dict]:
        """
        Hybrid search: vector similarity + metadata filtering with progressive fallback,
        followed by cross-encoder reranking when query_text is supplied.

        Filter priority (most restrictive first):
          1. contrato + proceso + frente + remitente + vector
          2. contrato + proceso + frente + vector
          3. contrato + proceso + vector
          4. contrato + vector
          5. vector only (pure semantic search)

        If a level returns no results the next less restrictive level is tried.
        After retrieval, FlashRank reranks the candidates and returns the top
        _RERANK_TOP_K chunks ordered by cross-encoder score.
        """
        filter_stages = self._build_filter_stages(work_front)

        candidate_chunks: List[dict] = []
        for stage_name, filters in filter_stages:
            candidate_chunks = self._execute_vector_search(query_vector, filters, limit)
            if candidate_chunks:
                logger.info(
                    f"Hybrid search hit at stage '{stage_name}': "
                    f"{len(candidate_chunks)} candidates found."
                )
                break
            logger.info(f"Stage '{stage_name}' returned 0 results, falling back...")

        if not candidate_chunks:
            logger.warning("All search stages exhausted. No similar chunks found.")
            return []

        if query_text:
            return self._rerank_chunks(query_text, candidate_chunks)

        # No query_text supplied — return raw Firestore ordering (backwards-compatible).
        return candidate_chunks

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _rerank_chunks(self, query_text: str, candidates: List[dict]) -> List[dict]:
        """
        Reranks candidate chunks using a cross-encoder (FlashRank) and returns
        the top _RERANK_TOP_K results ordered by descending relevance score.

        Each candidate must have a 'texto' field used as the passage text.
        The original chunk dict is preserved and a 'rerank_score' key is added.
        """
        passages = [
            {"id": idx, "text": chunk.get("texto", "")}
            for idx, chunk in enumerate(candidates)
        ]

        rerank_request = RerankRequest(query=query_text, passages=passages)
        reranked_results = _reranker.rerank(rerank_request)

        # reranked_results is a list of dicts with keys: id, score, text
        top_results = reranked_results[:_RERANK_TOP_K]

        reranked_chunks: List[dict] = []
        for result in top_results:
            original_chunk = candidates[result["id"]]
            original_chunk["rerank_score"] = result["score"]
            reranked_chunks.append(original_chunk)

        logger.info(
            f"Reranking complete: {len(candidates)} candidates → top {len(reranked_chunks)} "
            f"returned. Top score: {top_results[0]['score']:.4f}"
        )
        return reranked_chunks

    def _build_filter_stages(
        self,
        work_front: Optional[str],
    ) -> List[tuple]:
        """
        Builds an ordered list of (stage_name, filters_dict) from most to least restrictive.
        Only includes stages where all required filters have values.
        """
        stages = []

        # Stage 1: Work front
        if work_front:
            stages.append((
                "frente_trabajo",
                {"frente_trabajo": work_front},
            ))

        # Stage 2: Pure vector search (always present as final fallback)
        stages.append(("vector_only", {}))

        return stages

    def _execute_vector_search(
        self, query_vector: List[float], filters: Dict[str, str], limit: int
    ) -> List[dict]:
        """Executes a vector search with optional pre-filters."""
        query_ref = self.chunks_collection

        # Apply metadata pre-filters
        for field_name, field_value in filters.items():
            query_ref = query_ref.where(field_name, "==", field_value)

        results = (
            query_ref
            .find_nearest(
                vector_field="vector",
                query_vector=Vector(query_vector),
                distance_measure=DistanceMeasure.COSINE,
                limit=limit,
            )
            .get()
        )

        similar_chunks = []
        for doc_snapshot in results:
            chunk_data = doc_snapshot.to_dict()
            chunk_data["firestore_id"] = doc_snapshot.id
            similar_chunks.append(chunk_data)

        return similar_chunks

    def resolve_sent_documents(
        self, chunk_results: List[dict]
    ) -> Dict[str, Dict[str, str]]:
        """
        For each similar chunk, extracts the draft_id (id_borrador) field
        and queries the sent documents collection to find the corresponding
        sent document text (texto_extraido) and filename (nombre_archivo).

        Returns a dict mapping {draft_id: {"texto": texto_extraido, "filename": nombre_archivo}}.
        """
        # Collect unique draft IDs from chunk results
        draft_ids = set()
        for chunk in chunk_results:
            draft_id = chunk.get("id_borrador")
            if draft_id:
                draft_ids.add(draft_id)

        if not draft_ids:
            logger.warning("No draft IDs found in similar chunks. Cannot resolve sent documents.")
            return {}

        logger.info(f"Resolving {len(draft_ids)} unique draft IDs to sent documents.")

        sent_metadata: Dict[str, Dict[str, str]] = {}
        for draft_id in draft_ids:
            query = self.sent_docs_collection.where("id_borrador", "==", draft_id).limit(1)
            results = query.get()

            for doc_snapshot in results:
                doc_data = doc_snapshot.to_dict()
                extracted_text = doc_data.get("texto_extraido", "")
                filename = doc_data.get("nombre_archivo", "N/A")
                if extracted_text:
                    sent_metadata[draft_id] = {
                        "texto": extracted_text,
                        "filename": filename
                    }
                    logger.info(f"Resolved sent text and filename for draft_id={draft_id} ({len(extracted_text)} chars, name={filename}).")
                else:
                    logger.warning(f"Sent document for draft_id={draft_id} has no texto_extraido.")

        logger.info(f"Resolved {len(sent_metadata)} sent document records out of {len(draft_ids)} draft IDs.")
        return sent_metadata
