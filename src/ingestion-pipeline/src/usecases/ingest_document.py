import logging
from typing import Dict, Any, Optional, List
from src.domain.entities import SourceDocument, ProcessingPayload
from src.domain.factory import SourceDocumentFactory
from src.domain.enums import DocumentStatus
from src.repositories.document_repo import DocumentRepository
from src.filters.base import Pipeline
from src.infrastructure.repositories.csv_metadata_repository import CSVMetadataRepository
from src.usecases.builder import PipelineBuilder

logger = logging.getLogger(__name__)

class IngestDocumentCommand:
    """
    Orchestrator for the document ingestion process.
    Now strictly follows DIP by receiving all dependencies.
    """
    def __init__(
        self, 
        document_repo: DocumentRepository,
        pipeline_builder: PipelineBuilder,
        default_pipeline: Optional[Pipeline] = None
    ):
        self.document_repo = document_repo
        self.pipeline_builder = pipeline_builder
        self.default_pipeline = default_pipeline

    def execute(self, event_data: Dict[str, Any]) -> SourceDocument:
        """Orchestrate ingestion from a GCS event."""
        doc = SourceDocumentFactory.create_from_gcs_event(event_data)
        return self._run_pipeline(doc)

    def execute_batch(self, csv_metadata_repo: CSVMetadataRepository) -> Dict[str, Any]:
        """Orchestrate batch ingestion from CSV."""
        logger.info("Starting batch ingestion from CSV repository")
        
        rows = csv_metadata_repo.get_all_rows()
        processed_count = 0
        failed_count = 0
        
        for index, row in enumerate(rows):
            row_label = row.get("Enviadas", "").strip() or f"row-{index}"

            try:
                logger.info(f"Processing CSV row: {row_label}")
                docs = SourceDocumentFactory.create_documents_from_csv_row(row)

                for doc in docs:
                    logger.info(f"Ingesting document {doc.id} ({doc.document_type.value})")
                    # Use the injected builder to get the right pipeline
                    selected_pipeline = self.pipeline_builder.build_pipeline_for_document(
                        document_type=doc.document_type,
                        document_repo=self.document_repo,
                    )
                    self._run_pipeline(doc, pipeline=selected_pipeline)
                    processed_count += 1
            except Exception as row_error:
                logger.error(f"Error processing row {row_label}: {row_error}")
                failed_count += 1
                continue
                
        return {
            "processed_records": processed_count,
            "failed_records": failed_count,
            "total_records": len(rows),
        }

    def execute_csv_row(self, row_data: Dict[str, Any], csv_pipeline: Pipeline) -> List[SourceDocument]:
        """Orchestrate ingestion from a single CSV row, returning all processed documents."""
        docs = SourceDocumentFactory.create_documents_from_csv_row(row_data)
        processed_docs = []
        for doc in docs:
            processed_docs.append(self._run_pipeline(doc, pipeline=csv_pipeline))
        return processed_docs

    def _run_pipeline(self, doc: SourceDocument, pipeline: Optional[Pipeline] = None) -> SourceDocument:
        """Common execution and persistence logic."""
        exec_pipeline = pipeline or self.default_pipeline
        if not exec_pipeline:
            # Fallback for GCS events if no default provided
            exec_pipeline = self.pipeline_builder.build_ingestion_pipeline(
                storage_repo=None, # This might need fixing if GCS path is used
                document_repo=self.document_repo
            )
        
        self.document_repo.save_document(doc)
        self.document_repo.update_status(doc.id, DocumentStatus.PROCESSING)
        
        try:
            payload = ProcessingPayload(document=doc)
            result_payload = exec_pipeline.execute(payload)
            
            processed_doc = result_payload.document
            self.document_repo.save_document(processed_doc)
            self.document_repo.update_status(processed_doc.id, DocumentStatus.COMPLETED)
            
            logger.info(f"Document {processed_doc.id} processed successfully.")
            return processed_doc

        except Exception as e:
            logger.error(f"Failed to ingest document {doc.id}: {str(e)}")
            self.document_repo.update_status(doc.id, DocumentStatus.FAILED, error=str(e))
            raise e
