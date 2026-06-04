import logging
from typing import List, Dict, Optional
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

logger = logging.getLogger(__name__)


class FirestoreVectorSearchRepository:
    """
    Repository dedicated to vector similarity search and cross-document linking.
    Uses Firestore's native find_nearest for KNN vector search with COSINE distance.
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
        limit: int = 10,
        contract_number: Optional[str] = None,
        process: Optional[str] = None,
        work_front: Optional[str] = None,
        sender: Optional[str] = None,
    ) -> List[dict]:
        """
        Hybrid search: vector similarity + metadata filtering with progressive fallback.

        Filter priority (most restrictive first):
          1. contrato + proceso + frente + remitente + vector
          2. contrato + proceso + frente + vector
          3. contrato + proceso + vector
          4. contrato + vector
          5. vector only (pure semantic search)

        If a level returns no results, the next less restrictive level is tried.
        """
        filter_stages = self._build_filter_stages(contract_number, process, work_front, sender)

        for stage_name, filters in filter_stages:
            results = self._execute_vector_search(query_vector, filters, limit)
            if results:
                logger.info(
                    f"Hybrid search hit at stage '{stage_name}': {len(results)} chunks found."
                )
                return results
            logger.info(f"Stage '{stage_name}' returned 0 results, falling back...")

        logger.warning("All search stages exhausted. No similar chunks found.")
        return []

    def _build_filter_stages(
        self,
        contract_number: Optional[str],
        process: Optional[str],
        work_front: Optional[str],
        sender: Optional[str],
    ) -> List[tuple]:
        """
        Builds an ordered list of (stage_name, filters_dict) from most to least restrictive.
        Only includes stages where all required filters have values.
        """
        stages = []

        # Stage 1: All four filters
        if contract_number and process and work_front and sender:
            stages.append((
                "contrato+proceso+frente+remitente",
                {
                    "numero_contrato": contract_number,
                    "proceso": process,
                    "frente_trabajo": work_front,
                    "remitente": sender,
                },
            ))

        # Stage 2: Contract + process + work front
        if contract_number and process and work_front:
            stages.append((
                "contrato+proceso+frente",
                {"numero_contrato": contract_number, "proceso": process, "frente_trabajo": work_front},
            ))

        # Stage 3: Contract + process
        if contract_number and process:
            stages.append((
                "contrato+proceso",
                {"numero_contrato": contract_number, "proceso": process},
            ))

        # Stage 4: Contract only
        if contract_number:
            stages.append((
                "contrato",
                {"numero_contrato": contract_number},
            ))

        # Stage 5: Pure vector search (always present as final fallback)
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
    ) -> Dict[str, str]:
        """
        For each similar chunk, extracts the draft_id (id_borrador) field
        and queries the sent documents collection to find the corresponding
        sent document text (texto_extraido).

        Returns a dict mapping {draft_id: texto_extraido}.
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

        sent_texts: Dict[str, str] = {}
        for draft_id in draft_ids:
            # Query sent documents where id_borrador matches the draft_id
            query = self.sent_docs_collection.where("id_borrador", "==", draft_id).limit(1)
            results = query.get()

            for doc_snapshot in results:
                doc_data = doc_snapshot.to_dict()
                extracted_text = doc_data.get("texto_extraido", "")
                if extracted_text:
                    sent_texts[draft_id] = extracted_text
                    logger.info(f"Resolved sent text for draft_id={draft_id} ({len(extracted_text)} chars).")
                else:
                    logger.warning(f"Sent document for draft_id={draft_id} has no texto_extraido.")

        logger.info(f"Resolved {len(sent_texts)} sent document texts out of {len(draft_ids)} draft IDs.")
        return sent_texts
