"""Tools for retrieving document context from Firestore."""

import logging
from typing import List, Dict, Optional

from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google import genai
from google.adk.tools import FunctionTool
from flashrank import Ranker, RerankRequest

logger = logging.getLogger(__name__)

import os

# Re-use the existing Firestore configuration
PROJECT_ID = os.getenv("PROJECT_ID", "devhack-3f0c2")
DB_RECEIVED = os.getenv("DB_RECEIVED", "docs-recibidos")
DB_SENT = os.getenv("DB_SENT", "docs-enviados")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")

# Module-level singletons
_client_received = firestore.Client(project=PROJECT_ID, database=DB_RECEIVED)
_client_sent = firestore.Client(project=PROJECT_ID, database=DB_SENT)
_genai_client = genai.Client()

# Singleton reranker
_reranker = Ranker(
    model_name="ms-marco-MiniLM-L-12-v2", cache_dir="/tmp/flashrank_cache"
)

# Number of candidates fetched from Firestore before reranking.
_VECTOR_SEARCH_CANDIDATE_LIMIT = 20

# Final top-k returned to the LLM after reranking.
_RERANK_TOP_K = 7


def _rerank_chunks(query: str, candidates: List[dict]) -> List[dict]:
    """Reranks candidate chunks using a cross-encoder (FlashRank)."""
    passages = [
        {"id": idx, "text": chunk.get("texto", "")}
        for idx, chunk in enumerate(candidates)
    ]

    rerank_request = RerankRequest(query=query, passages=passages)
    reranked_results = _reranker.rerank(rerank_request)

    top_results = reranked_results[:_RERANK_TOP_K]

    reranked_chunks: List[dict] = []
    for result in top_results:
        original_chunk = candidates[result["id"]]
        original_chunk["rerank_score"] = result["score"]
        reranked_chunks.append(original_chunk)

    logger.info(
        f"Reranking complete: {len(candidates)} candidates → top {len(reranked_chunks)} returned."
    )
    return reranked_chunks


def search_communications(
    query: str,
    contract_number: Optional[str] = None,
    process: Optional[str] = None,
    work_front: Optional[str] = None,
    sender: Optional[str] = None,
    subject: Optional[str] = None,
    month: Optional[int] = None,
    year: Optional[int] = None,
    document_id: Optional[str] = None,
) -> str:
    """Searches the documents database and returns the most relevant chunks.

    Args:
        query: The query or topic you want to search for in the communications.
        contract_number: Contract number (e.g., 'CW-276532') if known.
        process: Process or area (e.g., 'Supervisión técnica') if known.
        work_front: Work front (e.g., 'Descarga intermedia') if known.
        sender: Sender of the communication if known.
        subject: Specific subject to filter by (e.g., 'Viga') if known.
        month: Month number (1-12) to filter by.
        year: Year (e.g. 2025) to filter by.
        document_id: Specific document ID or code (e.g., 'CYS-CW276532-PHI-03362').
    """
    try:
        # 1. Generate embedding for query
        response = _genai_client.models.embed_content(
            model=EMBEDDING_MODEL, contents=query, config={"output_dimensionality": 768}
        )
        query_vector = response.embeddings[0].values

        # 2. Search Firestore using hybrid fallback approach
        chunks_collection = _client_received.collection("documentos_chunks")
        stages = _build_filter_stages(
            contract_number, process, work_front, sender, subject, document_id
        )

        candidate_chunks = []
        for stage_name, filters in stages:
            query_ref = chunks_collection
            for field_name, field_value in filters.items():
                query_ref = query_ref.where(field_name, "==", field_value)

            results = query_ref.find_nearest(
                vector_field="vector",
                query_vector=Vector(query_vector),
                distance_measure=DistanceMeasure.COSINE,
                limit=_VECTOR_SEARCH_CANDIDATE_LIMIT,
            ).get()

            for doc_snap in results:
                candidate_chunks.append(doc_snap.to_dict())

            if candidate_chunks:
                logger.info(
                    f"Hybrid search hit at stage '{stage_name}' with {len(candidate_chunks)} candidates"
                )
                break

        if not candidate_chunks:
            return "No se encontró información relevante para esta consulta."

        # 3. Post-filtering by month/year and subject (contains) if provided
        if month or year or subject:
            filtered_candidates = []
            for chunk in candidate_chunks:
                # Subject filter (case-insensitive contains)
                if subject:
                    d_subject = chunk.get("asunto", "").lower()
                    if subject.lower() not in d_subject:
                        continue

                # Date filter
                if month or year:
                    date_str = chunk.get("fecha_documento", "")
                    try:
                        if not date_str or date_str == "UNKNOWN":
                            continue

                        if "/" in date_str:
                            parts = date_str.split("/")
                            d_month = int(parts[1])
                            d_year = int(parts[2])
                        elif "-" in date_str:
                            parts = date_str.split("-")
                            d_year = int(parts[0])
                            d_month = int(parts[1])
                        else:
                            continue

                        match_month = month is None or d_month == month
                        match_year = year is None or d_year == year

                        if not (match_month and match_year):
                            continue
                    except (ValueError, IndexError):
                        continue

                filtered_candidates.append(chunk)
            candidate_chunks = filtered_candidates

        if not candidate_chunks:
            return "No se encontraron comunicaciones para el periodo o filtros especificados."

        # 4. Rerank candidates
        similar_chunks = _rerank_chunks(query, candidate_chunks)

        # 5. Resolve responses
        draft_ids = {
            c.get("id_borrador") for c in similar_chunks if c.get("id_borrador")
        }
        sent_texts = {}
        for draft_id in draft_ids:
            sent_results = (
                _client_sent.collection("documentos")
                .where("id_borrador", "==", draft_id)
                .limit(1)
                .get()
            )
            for s in sent_results:
                txt = s.to_dict().get("texto_extraido", "")
                if txt:
                    sent_texts[draft_id] = txt

        # 6. Format context
        context = ["### RELEVANT RECEIVED DOCUMENTS FOUND ###"]
        for i, chunk in enumerate(similar_chunks, 1):
            context.append(f"\n--- Document #{i} ---")
            context.append(f"Subject: {chunk.get('asunto', 'N/A')}")
            context.append(f"Document Code: {chunk.get('nombre_archivo', 'N/A')}")
            context.append(f"Date: {chunk.get('fecha_documento', 'N/A')}")
            context.append(f"Contract: {chunk.get('numero_contrato', 'N/A')} | Process: {chunk.get('proceso', 'N/A')}")
            context.append(f"Sender: {chunk.get('remitente', 'N/A')} | Work Front: {chunk.get('frente_trabajo', 'N/A')}")
            context.append(f"Draft ID: {chunk.get('id_borrador', 'N/A')}")
            context.append(f"Extracted text: {chunk.get('texto', 'N/A')}")


            draft_id = chunk.get("id_borrador")
            if draft_id and draft_id in sent_texts:
                context.append(f"\n*** SENT RESPONSE (Draft ID: {draft_id}) ***")
                context.append(sent_texts[draft_id][:1500] + "...(truncated)")

        return "\n".join(context)

    except Exception as e:
        logger.error(f"Error searching documents: {e}")
        return f"Error searching the database: {e}"


def _build_filter_stages(
    contract_number: Optional[str],
    process: Optional[str],
    work_front: Optional[str],
    sender: Optional[str],
    subject: Optional[str] = None,
    document_id: Optional[str] = None,
) -> List[tuple]:
    """Builds an ordered list of (stage_name, filters_dict) from most to least restrictive."""
    stages = []

    def build_filters(**kwargs):
        return {k: v for k, v in kwargs.items() if v is not None}

    if document_id:
        stages.append(("id_only", {"id_documento": document_id}))
        stages.append(("filename_only", {"nombre_archivo": document_id}))

    if subject:
        stages.append(
            (
                "subject+metadata",
                build_filters(
                    asunto=subject,
                    numero_contrato=contract_number,
                    proceso=process,
                    frente_trabajo=work_front,
                    remitente=sender,
                ),
            )
        )
        stages.append(("subject_only", {"asunto": subject}))

    if contract_number and process and work_front and sender:
        stages.append(
            (
                "contract+process+work_front+sender",
                {
                    "numero_contrato": contract_number,
                    "proceso": process,
                    "frente_trabajo": work_front,
                    "remitente": sender,
                },
            )
        )

    if contract_number and process and work_front:
        stages.append(
            (
                "contract+process+work_front",
                {
                    "numero_contrato": contract_number,
                    "proceso": process,
                    "frente_trabajo": work_front,
                },
            )
        )

    if contract_number and process:
        stages.append(
            (
                "contract+process",
                {"numero_contrato": contract_number, "proceso": process},
            )
        )

    if contract_number:
        stages.append(("contract", {"numero_contrato": contract_number}))

    stages.append(("vector_only", {}))
    return stages


vector_search_tool = FunctionTool(func=search_communications)
