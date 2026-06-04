"""Tools for retrieving document context from Firestore."""

import logging
from typing import List, Dict, Optional
from pydantic import Field

from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure
from google import genai
from google.adk.tools import FunctionTool

logger = logging.getLogger(__name__)

import os

# Re-use the existing Firestore configuration
PROJECT_ID = os.getenv("PROJECT_ID", "devhack-3f0c2")
DB_RECEIVED = os.getenv("DB_RECEIVED", "docs-recibidos")
DB_SENT = os.getenv("DB_SENT", "docs-enviados")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "gemini-embedding-2")

# Module-level singletons: instantiated once at startup so mlflow.gemini.autolog()
# does not re-patch the SDK on every tool call, and traces always land in the
# agent-communications experiment rather than triggering a foreign one.
_client_received = firestore.Client(project=PROJECT_ID, database=DB_RECEIVED)
_client_sent = firestore.Client(project=PROJECT_ID, database=DB_SENT)
_genai_client = genai.Client()


def search_communications(
    query: str,
    contract_number: Optional[str] = None,
    process: Optional[str] = None,
    work_front: Optional[str] = None,
    sender: Optional[str] = None,
) -> str:
    """Searches the received documents database and returns the most relevant chunks and their sent responses.

    Args:
        query: The query or topic you want to search for in the communications.
        contract_number: Contract number (e.g., 'CW-276532') if known, otherwise None.
        process: Process or area (e.g., 'Supervisión técnica') if known, otherwise None.
        work_front: Work front (e.g., 'Descarga intermedia') if known, otherwise None.
        sender: Sender of the communication (the 'Para' or 'From' field) if known, otherwise None.
    """
    try:
        # 1. Generate embedding for query
        response = _genai_client.models.embed_content(
            model=EMBEDDING_MODEL, contents=query, config={"output_dimensionality": 768}
        )
        query_vector = response.embeddings[0].values

        # 3. Search Firestore using hybrid fallback approach
        chunks_collection = _client_received.collection("documentos_chunks")
        stages = _build_filter_stages(contract_number, process, work_front, sender)

        similar_chunks = []
        for stage_name, filters in stages:
            query_ref = chunks_collection
            for field_name, field_value in filters.items():
                query_ref = query_ref.where(field_name, "==", field_value)

            results = query_ref.find_nearest(
                vector_field="vector",
                query_vector=Vector(query_vector),
                distance_measure=DistanceMeasure.COSINE,
                limit=5,
            ).get()

            for doc_snap in results:
                similar_chunks.append(doc_snap.to_dict())

            if similar_chunks:
                logger.info(f"Hybrid search hit at stage '{stage_name}'")
                break

        if not similar_chunks:
            return "No relevant documents were found for the query."

        # 4. Resolve sent documents (responses)
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

        # 5. Format the context for the LLM
        context = []
        context.append("### RELEVANT RECEIVED DOCUMENTS FOUND ###")
        for i, chunk in enumerate(similar_chunks, 1):
            context.append(f"\n--- Document #{i} ---")
            context.append(f"Subject: {chunk.get('asunto', 'N/A')}")
            context.append(
                f"Contract: {chunk.get('numero_contrato', 'N/A')} | Process: {chunk.get('proceso', 'N/A')}"
            )
            context.append(
                f"Sender: {chunk.get('remitente', 'N/A')} | Work Front: {chunk.get('frente_trabajo', 'N/A')}"
            )
            context.append(
                f"Draft ID (response link): {chunk.get('id_borrador', 'N/A')}"
            )
            context.append(f"Extracted text: {chunk.get('texto', 'N/A')}")

            draft_id = chunk.get("id_borrador")
            if draft_id and draft_id in sent_texts:
                context.append(
                    f"\n*** SENT RESPONSE TO THIS DOCUMENT (Draft ID: {draft_id}) ***"
                )
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
) -> List[tuple]:
    """Builds an ordered list of (stage_name, filters_dict) from most to least restrictive."""
    stages = []

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
        stages.append(
            (
                "contract",
                {"numero_contrato": contract_number},
            )
        )

    # Always fallback to pure vector search
    stages.append(("vector_only", {}))

    return stages


# Create the ADK FunctionTool wrapper
vector_search_tool = FunctionTool(func=search_communications)
