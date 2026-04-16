import os
from src.filters.base import Pipeline
from src.filters.reader import DocumentReader
from src.filters.metadata import MetadataExtractor
from src.filters.pdf_reader import PDFReader
from src.filters.cleaner import DocumentCleaner
from src.filters.chunker import TextChunker
from src.filters.embedder import VectorEmbedder
from src.filters.saver import VectorSaver
from src.repositories.storage_repo import StorageRepository
from src.repositories.document_repo import DocumentRepository
from src.infrastructure.repositories.csv_metadata_repository import CSVMetadataRepository
from src.filters.csv_metadata import CSVMetadataExtractor

class PipelineBuilder:
    @staticmethod
    def build_ingestion_pipeline(
        storage_repo: StorageRepository, 
        document_repo: DocumentRepository,
        csv_metadata_repo: CSVMetadataRepository = None
    ) -> Pipeline:
        """
        Assemble the ingestion pipeline with all necessary filters.
        Handles environment-based configuration for the embedding model.
        """
        pipeline = Pipeline()
        
        # 1. Base Document Loading
        pipeline.add_filter(DocumentReader(storage_repo))
        pipeline.add_filter(MetadataExtractor())
        
        # 1b. CSV Enrichment (if repo provided)
        if csv_metadata_repo:
            pipeline.add_filter(CSVMetadataExtractor(csv_metadata_repo))
        
        # 2. Text Extraction from PDF (Local)
        pipeline.add_filter(PDFReader())
        
        # 3. Document Cleaning and Segmentation
        pipeline.add_filter(DocumentCleaner())
        
        # 4. Text Processing (Semantic Chunking)
        pipeline.add_filter(TextChunker())
        
        # 5. Embedding and Storage
        gemini_api_key = os.environ.get("GEMINI_API_KEY")
        embedding_model = os.environ.get("EMBEDDING_MODEL", "models/embedding-001")
        
        if gemini_api_key:
            pipeline.add_filter(VectorEmbedder(api_key=gemini_api_key, model=embedding_model))
            
        pipeline.add_filter(VectorSaver(document_repo))
        
        return pipeline
