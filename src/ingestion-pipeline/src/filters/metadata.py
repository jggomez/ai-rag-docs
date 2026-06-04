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
        
        # Default metadata if parsing fails
        metadata = {
            "contract_number": "UNKNOWN",
            "sender": "UNKNOWN",
            "work_front": "GENERAL",
            "document_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "process": "INBOX",
        }
        
        # Example heuristic: if path is contract/sender/file
        if len(parts) >= 3:
            metadata["contract_number"] = parts[0]
            metadata["sender"] = parts[1]
            filename = parts[-1]
        elif len(parts) == 2:
            metadata["contract_number"] = parts[0]
            filename = parts[1]
        else:
            filename = parts[0]

        # Try to extract date from filename (supports multiple formats)\n        date_patterns = [\n            (r"(\d{4}-\d{2}-\d{2})", "%Y-%m-%d"),     # 2025-03-11\n            (r"(\d{8})", "%Y%m%d"),                    # 20250311\n            (r"(\d{2}-\d{2}-\d{4})", "%d-%m-%Y"),      # 11-03-2025\n        ]\n        for pattern, date_fmt in date_patterns:\n            date_match = re.search(pattern, filename)\n            if date_match:\n                try:\n                    parsed_date = datetime.strptime(date_match.group(1), date_fmt)\n                    metadata["document_date"] = parsed_date.strftime("%Y-%m-%d")\n                    break\n                except ValueError:\n                    continue

        # Update document entities ONLY if they are not already set (e.g. by manual ingestion)
        # We consider "PENDING" or "UNKNOWN" as "not set" for the purpose of heuristic extraction
        def should_update(current_val):
            return current_val in [None, "", "PENDING", "UNKNOWN"]

        if should_update(payload.document.contract_number):
            payload.document.contract_number = metadata["contract_number"]
            
        if should_update(payload.document.sender):
            payload.document.sender = metadata["sender"]
            
        if should_update(payload.document.work_front):
            payload.document.work_front = metadata["work_front"]
            
        if should_update(payload.document.document_date):
            payload.document.document_date = metadata["document_date"]
            
        if should_update(payload.document.process):
            payload.document.process = metadata["process"]
        
        logger.info(f"Metadata after extraction: {payload.document.model_dump()}")
        return payload
