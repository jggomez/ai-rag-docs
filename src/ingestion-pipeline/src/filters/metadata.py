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

        # Try to extract date from filename (YYYY-MM-DD)
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", filename)
        if date_match:
            metadata["document_date"] = date_match.group(1)

        # Update document entities ONLY if they are not already set (e.g. by manual ingestion)
        # We consider "PENDING" or "UNKNOWN" as "not set" for the purpose of heuristic extraction
        def should_update(current_val):
            return current_val in [None, "", "PENDING", "UNKNOWN"]

        if should_update(payload.document.engineering_metadata.contract_number):
            payload.document.engineering_metadata.contract_number = metadata["contract_number"]
            
        if should_update(payload.document.engineering_metadata.sender):
            payload.document.engineering_metadata.sender = metadata["sender"]
            
        if should_update(payload.document.engineering_metadata.work_front):
            payload.document.engineering_metadata.work_front = metadata["work_front"]
            
        if should_update(payload.document.engineering_metadata.document_date):
            payload.document.engineering_metadata.document_date = metadata["document_date"]
            
        if should_update(payload.document.engineering_metadata.process):
            payload.document.engineering_metadata.process = metadata["process"]
        
        logger.info(f"Metadata after extraction: {payload.document.dict()}")
        return payload
