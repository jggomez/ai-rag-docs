import logging
from src.filters.base import Filter
from src.domain.entities import ProcessingPayload
from src.repositories.storage_repo import StorageRepository

logger = logging.getLogger(__name__)

class DocumentReader(Filter[ProcessingPayload, ProcessingPayload]):
    def __init__(self, storage_repo: StorageRepository):
        self.storage_repo = storage_repo

    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        """
        Download file content from GCS.
        """
        logger.info(f"Reading document: {payload.document.object_name} from bucket: {payload.document.bucket}")
        
        try:
            content = self.storage_repo.download_file(
                payload.document.bucket, 
                payload.document.object_name
            )
            payload.content = content
            payload.document.size_bytes = len(content)
            logger.info(f"Successfully read {len(content)} bytes")
            return payload
        except Exception as e:
            logger.error(f"Error reading document from storage: {str(e)}")
            raise e
