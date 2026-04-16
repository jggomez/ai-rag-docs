import logging
from src.filters.base import Filter
from src.domain.entities import ProcessingPayload
from src.repositories.document_repo import DocumentRepository

logger = logging.getLogger(__name__)

class VectorSaver(Filter[ProcessingPayload, ProcessingPayload]):
    def __init__(self, document_repo: DocumentRepository):
        self.document_repo = document_repo

    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        if not payload.chunks:
            logger.warning("No chunks to save.")
            return payload
            
        logger.info(f"Saving {len(payload.chunks)} chunks to Firestore.")
        
        try:
            self.document_repo.save_chunks(payload.chunks)
            logger.info("Successfully saved all chunks.")
            return payload
        except Exception as e:
            logger.error(f"Failed to save chunks: {str(e)}")
            raise e
