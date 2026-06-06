import logging
import re
from datetime import datetime
from src.filters.base import Filter
from src.domain.entities import ProcessingPayload

logger = logging.getLogger(__name__)

class MetadataExtractor(Filter[ProcessingPayload, ProcessingPayload]):
    """
    Extracts metadata from the GCS path or object metadata.
    Expected path pattern (tentative): COMMUNICATION_RECEIVED/{contract_number}/{sender}/{date}_{process}_{filename}
    Or filename pattern: {date}_{contract}_{sender}_{process}_...
    """
    
    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        logger.info(f"Extracting metadata for: {payload.document.object_name}")
        
        obj_name = payload.document.object_name
        # Remove prefix
        clean_path = obj_name.replace("COMMUNICATION_RECEIVED/", "")
        parts = clean_path.split("/")
        filename = parts[-1]
        
        # Default metadata if parsing fails
        metadata = {
            "work_front": "GENERAL",
            "document_date": datetime.utcnow().strftime("%Y-%m-%d"),
        }
        
        # Try to extract date from filename (supports multiple formats)
        date_patterns = [
            (r"(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),     # 2025-03-11
            (r"(\d{8})", "%Y%m%d"),                    # 20250311
            (r"(\d{2}-\d{2}-\d{4})", "%d-%m-%Y"),      # 11-03-2025
        ]
        for pattern, date_fmt in date_patterns:
            date_match = re.search(pattern, filename)
            if date_match:
                try:
                    parsed_date = datetime.strptime(date_match.group(1), date_fmt)
                    metadata["document_date"] = parsed_date.strftime("%Y-%m-%d")
                    break
                except ValueError:
                    continue

        # Update document entities ONLY if they are not already set (e.g. by manual ingestion)
        # We consider "PENDING" or "UNKNOWN" as "not set" for the purpose of heuristic extraction
        def should_update(current_val):
            return current_val in [None, "", "PENDING", "UNKNOWN"]
            
        if should_update(payload.document.work_front):
            payload.document.work_front = metadata["work_front"]
            
        if should_update(payload.document.document_date):
            payload.document.document_date = metadata["document_date"]
        
        logger.info(f"Metadata after extraction: {payload.document.model_dump()}")
        return payload
