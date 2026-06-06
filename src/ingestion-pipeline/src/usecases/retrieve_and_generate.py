import logging
import uuid
from datetime import datetime
from typing import List, Dict, Optional
from google.cloud import storage
from src.domain.entities import SourceDocument, ProcessingPayload, DocumentChunk
from src.domain.enums import DocumentStatus, DocumentType
from src.filters.drive_downloader import DriveDownloader
from src.filters.gemini_extractor import GeminiExtractor
from src.filters.embedder import VectorEmbedder
from src.filters.pdf_generator import PDFResponseGenerator
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

        # OCR extractor for received documents
        self.extractor = GeminiExtractor(
            api_key=settings.gemini_api_key,
            model_name=settings.ocr_model,
        )

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

        # PDF generator
        self.pdf_generator = PDFResponseGenerator()

        # Drive downloader for fetching the PDF
        self.downloader = DriveDownloader()

    def execute(self, document: SourceDocument) -> dict:
        """
        Executes the complete retrieve-and-generate pipeline.

        Args:
            document: SourceDocument with URL and metadata of the received document.

        Returns:
            Dict with keys: 'pdf_bytes', 'generated_text', 'similar_count', 'sent_count', 'subject'
        """
        logger.info(f"Starting RAG retrieval for document: {document.source_url}")

        # Step 1: Download the PDF from Drive
        payload = ProcessingPayload(document=document)
        payload = self.downloader.process(payload)

        if document.status == DocumentStatus.FAILED:
            raise ValueError(f"Failed to download document: {document.metadata.get('error', 'Unknown error')}")

        # Step 2: OCR extraction with Gemini
        payload = self.extractor.process(payload)
        received_subject = document.metadata.get("document_subject", "Sin asunto")
        received_body = document.metadata.get("extracted_text", "")

        if not received_body:
            raise ValueError("OCR extraction produced no text content.")

        logger.info(f"OCR complete. Subject: {received_subject[:80]}")

        # Step 3: Generate embedding vector for the extracted text
        query_text = f"{received_subject}\n{received_body}"
        query_embedding = self._generate_query_embedding(query_text)

        # Step 4: Hybrid vector search — filtered by work_front with fallback
        codcomunicadorecibido = document.metadata.get("codcomunicadorecibido")
        similar_chunks = self.vector_search_repo.find_similar_chunks(
            query_vector=query_embedding,
            query_text=query_text,
            work_front=document.work_front,
            codcomunicadorecibido=codcomunicadorecibido,
        )

        # Step 5: Resolve linked sent documents via draft_id
        sent_texts = self.vector_search_repo.resolve_sent_documents(similar_chunks)

        # Step 6: Generate response text with Gemini
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

        # Step 7: Generate PDF with the response
        pdf_bytes = self.pdf_generator.generate_response_pdf(
            response_text=generated_text,
            metadata=metadata_context,
            similar_chunks=similar_chunks,
            sent_texts=sent_texts,
        )

        # Step 8: Upload PDF to GCS
        gcs_url = self._upload_to_gcs(pdf_bytes, document)

        # Step 9: Save the generated response to the database (docs-enviados)
        sent_document = SourceDocument(
            id=f"{document.id}_SEN", # Ensure it maps to sent DB if using routing repo, or just let it generate one with suffix
            filename=gcs_url.split('/')[-1],
            bucket=self.settings.gcs_output_bucket,
            object_name=gcs_url.split('/')[-1],
            content_type="application/pdf",
            size_bytes=len(pdf_bytes),
            created_at=datetime.utcnow(),
            status=DocumentStatus.COMPLETED,
            document_type=DocumentType.SENT,
            source_url=gcs_url,
            work_front=document.work_front,
            document_date=datetime.utcnow().strftime("%Y-%m-%d"),
            draft_id=document.draft_id,
            metadata={
                "created_by_rag": True,
                "extracted_text": generated_text,
                "document_subject": f"RE: {received_subject}"
            }
        )
        
        # We need the document repository to save it. We'll add it to the init.
        if hasattr(self, 'document_repo') and self.document_repo:
            self.document_repo.save_document(sent_document)
            logger.info(f"Saved generated response to database with ID: {sent_document.id}")

        logger.info(
            f"RAG pipeline complete. Similar chunks: {len(similar_chunks)}, "
            f"Sent texts resolved: {len(sent_texts)}, PDF size: {len(pdf_bytes)} bytes, "
            f"GCS URL: {gcs_url}"
        )

        return {
            "pdf_bytes": pdf_bytes,
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

    def _upload_to_gcs(self, pdf_bytes: bytes, document: SourceDocument) -> str:
        """Uploads the generated PDF to GCS and returns the public URL."""
        bucket_name = self.settings.gcs_output_bucket
        prefix = self.settings.gcs_output_prefix

        # Generate unique filename with work front info and timestamp
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        safe_front = document.work_front.replace(" ", "_").replace("/", "-")
        unique_id = uuid.uuid4().hex[:8]
        blob_name = f"{prefix}/respuesta_{safe_front}_{timestamp}_{unique_id}.pdf"

        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(blob_name)
        blob.upload_from_string(pdf_bytes, content_type="application/pdf")

        gcs_url = f"gs://{bucket_name}/{blob_name}"
        logger.info(f"PDF uploaded to GCS: {gcs_url}")
        return gcs_url
