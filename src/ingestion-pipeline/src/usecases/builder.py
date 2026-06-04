import logging
from typing import Dict, Callable
from src.config import Settings
from src.filters.base import Pipeline
from src.filters.reader import DocumentReader
from src.filters.metadata import MetadataExtractor
from src.filters.pdf_reader import PDFReader
from src.filters.cleaner import DocumentCleaner
from src.filters.chunker import TextChunker
from src.filters.embedder import VectorEmbedder
from src.filters.saver import VectorSaver
from src.filters.drive_downloader import DriveDownloader
from src.filters.gemini_extractor import GeminiExtractor
from src.repositories.storage_repo import StorageRepository
from src.repositories.document_repo import DocumentRepository
from src.infrastructure.repositories.csv_metadata_repository import CSVMetadataRepository
from src.domain.enums import DocumentType

logger = logging.getLogger(__name__)

class PipelineBuilder:
    """
    Assembles processing pipelines based on the document's origin and type.
    Now an injectable service that respects OCP.
    """

    def __init__(self, settings: Settings):
        self.settings = settings
        # Registry for document-type specific builders (OCP)
        self._type_strategies: Dict[DocumentType, Callable[[Pipeline], None]] = {
            DocumentType.SENT: self._build_sent_strategy,
            DocumentType.RECEIVED: self._build_received_strategy
        }

    def build_ingestion_pipeline(
        self,
        storage_repo: StorageRepository, 
        document_repo: DocumentRepository,
        csv_metadata_repo: CSVMetadataRepository = None
    ) -> Pipeline:
        """Assemble the standard legacy ingestion pipeline."""
        pipeline = Pipeline()
        
        pipeline.add_filter(DocumentReader(storage_repo))
        pipeline.add_filter(MetadataExtractor())
        
        pipeline.add_filter(PDFReader())
        pipeline.add_filter(DocumentCleaner())
        pipeline.add_filter(TextChunker())
        
        self._append_embedding_and_storage(pipeline, document_repo)
        return pipeline

    def build_csv_only_pipeline(self, document_repo: DocumentRepository) -> Pipeline:
        """Build a pipeline for CSV-only processing."""
        pipeline = Pipeline()
        pipeline.add_filter(TextChunker())
        self._append_embedding_and_storage(pipeline, document_repo)
        return pipeline

    def build_pipeline_for_document(
        self,
        document_type: DocumentType,
        document_repo: DocumentRepository,
    ) -> Pipeline:
        """Build the appropriate pipeline based on the document type using strategy pattern."""
        pipeline = Pipeline()
        
        # Step 1: Common download
        pipeline.add_filter(DriveDownloader())

        # Step 2: Apply type-specific strategy
        strategy = self._type_strategies.get(document_type)
        if not strategy:
            raise ValueError(f"No pipeline strategy registered for {document_type}")
        
        strategy(pipeline)

        # Step 3: Common downstream
        pipeline.add_filter(TextChunker())
        self._append_embedding_and_storage(pipeline, document_repo)

        return pipeline

    # --- Strategy Methods ---

    def _build_sent_strategy(self, pipeline: Pipeline):
        logger.info("Applying SENT strategy: PDF → Regex cleaner path.")
        pipeline.add_filter(PDFReader())
        pipeline.add_filter(DocumentCleaner())

    def _build_received_strategy(self, pipeline: Pipeline):
        logger.info("Applying RECEIVED strategy: Gemini OCR path.")
        pipeline.add_filter(GeminiExtractor(
            api_key=self.settings.gemini_api_key,
            model_name=self.settings.ocr_model
        ))

    def _append_embedding_and_storage(self, pipeline: Pipeline, document_repo: DocumentRepository):
        """Conditionally add embedding + saver filters."""
        if self.settings.gemini_api_key:
            pipeline.add_filter(VectorEmbedder(
                api_key=self.settings.gemini_api_key, 
                model=self.settings.embedding_model
            ))

        pipeline.add_filter(VectorSaver(document_repo))
