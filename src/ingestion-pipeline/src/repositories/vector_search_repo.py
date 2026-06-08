import logging
from typing import List, Dict, Optional, Union

from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from flashrank import Ranker, RerankRequest

logger = logging.getLogger(__name__)

# Singleton: loaded once at startup — avoids re-loading the ONNX model per call.
# ms-marco-TinyBERT-L-2-v2 is lightweight and offers better cross-platform compatibility.
_reranker = Ranker(
    model_name="ms-marco-TinyBERT-L-2-v2", cache_dir="/tmp/flashrank_cache_v2"
)

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
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        exclude_draft_id: Optional[str] = None,
    ) -> List[dict]:
        """
        Robust hybrid search with automatic fallback stages:
          1. work_front + date_range
          2. work_front only
          3. date_range only
          4. vector only (Global)

        In each stage, it filters out chunks belonging to 'exclude_draft_id'.
        If a stage results in 0 chunks, it automatically moves to the next fallback.
        """
        # Build prioritized stages
        stages = self._build_robust_fallback_stages(work_front, start_date, end_date)
        
        final_candidates: List[dict] = []
        
        for stage_name, filters in stages:
            raw_results = self._execute_vector_search(query_vector, filters, limit)
            
            if not raw_results:
                logger.info(f"Stage '{stage_name}' returned 0 raw results, falling back...")
                continue
                
            # Filter results to exclude the source document's chunks
            filtered = []
            for chunk in raw_results:
                chunk_draft_id = str(chunk.get("id_borrador", "")).strip()
                if exclude_draft_id and chunk_draft_id == str(exclude_draft_id).strip():
                    logger.debug(f"Excluding chunk from source document draft_id={exclude_draft_id}")
                    continue
                filtered.append(chunk)
                
            if filtered:
                logger.info(f"RAG search hit at stage '{stage_name}': {len(filtered)} usable chunks found.")
                final_candidates = filtered
                break
            else:
                logger.info(f"Stage '{stage_name}' had results but all were excluded. Falling back...")

        if not final_candidates:
            logger.warning("RAG fallback chain exhausted. No similar chunks found from other documents.")
            return []

        # Apply reranking if text was provided
        if query_text:
            return self._rerank_chunks(query_text, final_candidates)

        return final_candidates

    def _build_robust_fallback_stages(
        self,
        work_front: Optional[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> List[tuple]:
        """
        Builds the ordered fallback stages for robust retrieval.
        """
        stages = []
        front_cond = ("frente_trabajo", "==", work_front) if work_front else None
        
        date_conds = []
        if start_date:
            date_conds.append(("fecha_documento", ">=", start_date))
        if end_date:
            date_conds.append(("fecha_documento", "<=", end_date))

        # 1. Front + Dates
        if front_cond and date_conds:
            stages.append(("front_and_date", [front_cond] + date_conds))

        # 2. Front Only
        if front_cond:
            stages.append(("front_only", [front_cond]))

        # 3. Dates Only
        if date_conds:
            stages.append(("date_only", date_conds))

        # 4. Global fallback
        stages.append(("global_vector", []))
        
        return stages

    def _execute_vector_search(
        self,
        query_vector: List[float],
        filters: Union[Dict[str, str], List[tuple]],
        limit: int,
    ) -> List[dict]:
        """Executes a vector search with optional pre-filters."""
        query_ref = self.chunks_collection

        # Apply metadata pre-filters
        if isinstance(filters, dict):
            for field_name, field_value in filters.items():
                query_ref = query_ref.where(field_name, "==", field_value)
        else:
            for cond in filters:
                if len(cond) == 3:
                    field_name, op, field_value = cond
                    query_ref = query_ref.where(field_name, op, field_value)
                elif len(cond) == 2:
                    field_name, field_value = cond
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

    def _rerank_chunks(self, query_text: str, candidates: List[dict]) -> List[dict]:
        """
        Reranks candidate chunks using a cross-encoder (FlashRank) and returns
        the top _RERANK_TOP_K results ordered by descending relevance score.

        Each candidate must have a 'texto' field used as the passage text.
        The original chunk dict is preserved and a 'rerank_score' key is added.
        """
        try:
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
        except Exception as e:
            logger.error(f"Reranking failed: {e}. Falling back to vector search order.")
            # Fallback: just return the top-k from original candidates
            return candidates[:_RERANK_TOP_K]
