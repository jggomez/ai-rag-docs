import logging
from typing import Dict, Any
from src.domain.entities import SourceDocument, ProcessingPayload
from src.domain.factory import SourceDocumentFactory
from src.domain.enums import DocumentStatus
from src.repositories.document_repo import DocumentRepository
from src.filters.base import Pipeline

logger = logging.getLogger(__name__)

class IngestDocumentCommand:
    """
    Orchestrator for the document ingestion process.
    Following SRP, it only handles the high-level flow and persistence coordination.
    Following DIP, it receives its pipeline of operations as a dependency.
    """
    def __init__(
        self, 
        document_repo: DocumentRepository,
        pipeline: Pipeline
    ):
        self.document_repo = document_repo
        self.pipeline = pipeline

    def execute(self, event_data: Dict[str, Any]) -> SourceDocument:
        """
        Orchestrate the ingestion of a document from a raw GCS event.
        """
        # 1. Create initial SourceDocument entity using Factory
        doc = SourceDocumentFactory.create_from_gcs_event(event_data)
        return self._run_pipeline(doc)

    def execute_manual(self, request_data: Dict[str, Any]) -> SourceDocument:
        """
        Orchestrate the ingestion of a document with explicit metadata.
        """
        # 1. Create initial SourceDocument entity using Factory
        doc = SourceDocumentFactory.create_from_ingest_request(request_data)
        return self._run_pipeline(doc)

    def _run_pipeline(self, doc: SourceDocument) -> SourceDocument:
        """
        Common logic for running the processing pipeline and persistence.
        """
        # 2. Save initial record and update status
        self.document_repo.save_document(doc)
        self.document_repo.update_status(doc.id, DocumentStatus.PROCESSING)
        
        try:
            # 3. Run the processing Pipeline
            payload = ProcessingPayload(document=doc)
            result_payload = self.pipeline.execute(payload)
            
            # 4. Update with final metadata and mark as COMPLETED
            processed_doc = result_payload.document
            self.document_repo.save_document(processed_doc)
            self.document_repo.update_status(processed_doc.id, DocumentStatus.COMPLETED)
            
            logger.info(f"Document {processed_doc.id} processed successfully.")
            return processed_doc

        except Exception as e:
            logger.error(f"Failed to ingest document {doc.id}: {str(e)}")
            self.document_repo.update_status(doc.id, DocumentStatus.FAILED, error=str(e))
            raise e
