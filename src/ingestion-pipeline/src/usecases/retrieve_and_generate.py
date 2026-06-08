import logging
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from google.cloud import storage
from src.domain.entities import SourceDocument, ProcessingPayload, DocumentChunk
from src.domain.enums import DocumentStatus, DocumentType
from src.filters.embedder import VectorEmbedder
from src.filters.docx_generator import DocxResponseGenerator
from src.repositories.vector_search_repo import FirestoreVectorSearchRepository
from src.usecases.response_generator import ResponseGenerator
from src.config import Settings

logger = logging.getLogger(__name__)


class RetrieveAndGenerateCommand:
    """
    Orchestrates the complete RAG retrieval and response generation pipeline:
    1. Download the received document PDF
    2. OCR extraction with Gemini (subject, body, visual data)
    3. Generate embedding vector for the extracted text
    4. Vector search for 10 similar received document chunks
    5. Resolve linked sent documents via draft_id (id_borradores)
    6. Generate response text with Gemini using triple RAG context
    7. Generate PDF with the response text
    """

    def __init__(self, settings: Settings, document_repo=None):
        self.settings = settings
        self.document_repo = document_repo

        # Embedding generator for query vector
        self.embedder = VectorEmbedder(
            api_key=settings.gemini_api_key,
            model=settings.embedding_model,
        )

        # Vector search repository
        self.vector_search_repo = FirestoreVectorSearchRepository(
            database_received=settings.firestore_database_received,
            database_sent=settings.firestore_database_sent,
        )

        # Response generator with Gemini
        self.response_generator = ResponseGenerator(
            api_key=settings.gemini_api_key,
            model_name=settings.generation_model,
        )

        # DOCX generator
        self.docx_generator = DocxResponseGenerator()

    def execute(
        self,
        id_documento_recibido: Optional[str] = None,
        cod_comunicado_recibido: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        front: Optional[str] = None,
    ) -> dict:
        """
        Executes the complete retrieve-and-generate pipeline using an already ingested document.

        Args:
            id_documento_recibido: Optional ID of the received document to retrieve.
            cod_comunicado_recibido: Optional object/file code of the received document.
            start_date: Optional start date filter (YYYY-MM-DD)
            end_date: Optional end date filter (YYYY-MM-DD)
            front: Optional work front filter

        Returns:
            Dict with keys: 'pdf_bytes', 'generated_text', 'similar_count', 'sent_count', 'subject', 'gcs_url'
        """
        logger.info(
            f"Starting RAG retrieval. id_documento_recibido={id_documento_recibido}, "
            f"cod_comunicado_recibido={cod_comunicado_recibido}, start_date={start_date}, "
            f"end_date={end_date}, front={front}"
        )

        # 1. Retrieve the document from Firestore
        document = None
        if id_documento_recibido:
            document = self.document_repo.get_document_by_draft_id(id_documento_recibido)

        if not document and cod_comunicado_recibido:
            document = self.document_repo.get_document_by_object_name(cod_comunicado_recibido)

        if not document:
            raise ValueError(
                f"No ingested received document found matching "
                f"id_documento_recibido={id_documento_recibido} or "
                f"cod_comunicado_recibido={cod_comunicado_recibido}"
            )

        # 2. Extract values directly from the stored document
        received_subject = document.metadata.get("document_subject") or "Sin asunto"
        received_body = document.metadata.get("extracted_text")

        if not received_body:
            raise ValueError(
                f"The matching document {document.id} does not contain extracted_text."
            )

        logger.info(f"Retrieved document content from DB. Subject: {received_subject[:80]}")

        # 3. Generate embedding vector for the query text
        query_text = f"{received_subject}\n{received_body}"
        query_embedding = self._generate_query_embedding(query_text)

        # 4. Hybrid vector search — filtered by work_front with fallback, excluding current document
        similar_chunks = self.vector_search_repo.find_similar_chunks(
            query_vector=query_embedding,
            query_text=query_text,
            work_front=front or document.work_front,
            start_date=start_date,
            end_date=end_date,
            exclude_draft_id=document.draft_id,
        )


        # 5. Resolve linked sent documents via draft_id
        sent_texts = self.vector_search_repo.resolve_sent_documents(similar_chunks)

        # 6. Generate response text with Gemini
        metadata_context = {
            "work_front": document.work_front,
            "document_date": document.document_date,
            "subject": received_subject,
        }

        generated_text = self.response_generator.generate_response(
            received_subject=received_subject,
            received_body=received_body,
            similar_chunks=similar_chunks,
            sent_texts=sent_texts,
            metadata=metadata_context,
        )

        # 7. Generate DOCX with the response
        docx_bytes = self.docx_generator.generate_response_docx(
            response_text=generated_text,
            metadata=metadata_context,
            similar_chunks=similar_chunks,
            sent_texts=sent_texts,
        )

        # 8. Upload DOCX to GCS
        gcs_url = self._upload_to_gcs(docx_bytes, document)

        # 9. Firestore persistence skipped per requirement

        logger.info(
            f"RAG pipeline complete. Similar chunks: {len(similar_chunks)}, "
            f"Sent texts resolved: {len(sent_texts)}, DOCX size: {len(docx_bytes)} bytes, "
            f"GCS URL: {gcs_url}"
        )

        return {
            "docx_bytes": docx_bytes,
            "generated_text": generated_text,
            "similar_count": len(similar_chunks),
            "sent_count": len(sent_texts),
            "subject": received_subject,
            "gcs_url": gcs_url,
        }

    def _generate_query_embedding(self, text: str) -> List[float]:
        """Generates a single embedding vector for the query text."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.settings.gemini_api_key)
        result = client.models.embed_content(
            model=self.settings.embedding_model,
            contents=text,
            config=types.EmbedContentConfig(
                task_type="RETRIEVAL_QUERY",
                output_dimensionality=768,
            ),
        )

        if not result.embeddings or len(result.embeddings) == 0:
            raise ValueError("Failed to generate query embedding.")

        return result.embeddings[0].values

    def _upload_to_gcs(self, docx_bytes: bytes, document: SourceDocument) -> str:
        """Uploads the generated DOCX to GCS and returns the public URL."""
        bucket_name = "communications-cys"
        prefix = "COMMUNICATIONS_SENT_TMP/"

        # Generate unique filename with work front info and timestamp
        now = datetime.utcnow()
        date_folder = now.strftime("%Y-%m-%d")
        timestamp = now.strftime("%H%M%S")
        
        safe_front = (document.work_front or "GENERAL").replace(" ", "_").replace("/", "-")
        unique_id = uuid.uuid4().hex[:6]
        
        # Folder structure: COMMUNICATIONS_SENT_TMP/YYYY-MM-DD/respuesta_FRENTE_TIMESTAMP_ID.docx
        blob_name = f"{prefix}{date_folder}/respuesta_{safe_front}_{timestamp}_{unique_id}.docx"

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(
            docx_bytes,
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )

        gcs_url = f"gs://{bucket_name}/{blob_name}"
        logger.info(f"DOCX uploaded to GCS: {gcs_url}")
        return gcs_url
