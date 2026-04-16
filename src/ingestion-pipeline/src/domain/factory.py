import hashlib
import os
from typing import Dict, Any
from src.domain.entities import SourceDocument
from src.domain.enums import DocumentStatus

class SourceDocumentFactory:
    @staticmethod
    def create_from_ingest_request(request_data: Dict[str, Any]) -> SourceDocument:
        """
        Create a SourceDocument entity from explicit metadata received via API.
        """
        bucket = request_data.get("bucket")
        name = request_data.get("object_name")
        
        # ID generation consistent with GCS events
        doc_id = hashlib.md5(f"gs://{bucket}/{name}".encode()).hexdigest()
        
        return SourceDocument(
            id=doc_id,
            filename=os.path.basename(name),
            bucket=bucket,
            object_name=name,
            content_type="application/pdf", # Assume PDF for communications
            size_bytes=0, # Will be updated if doc is read
            status=DocumentStatus.PENDING,
            sender=request_data.get("sender"),
            contract_number=request_data.get("contract_number"),
            work_front=request_data.get("work_front"),
            document_date=request_data.get("document_date"),
            process=request_data.get("process"),
            response_file_url=request_data.get("response_file_url")
        )
    @staticmethod
    def create_from_gcs_event(event_data: Dict[str, Any]) -> SourceDocument:
        """
        Create a SourceDocument entity from a raw GCS event.
        Handles ID generation and initial status setting.
        """
        bucket = event_data.get("bucket")
        name = event_data.get("name")
        content_type = event_data.get("contentType", "application/octet-stream")
        size = int(event_data.get("size", 0))
        
        # Consistent ID generation
        doc_id = hashlib.md5(f"gs://{bucket}/{name}".encode()).hexdigest()
        
        return SourceDocument(
            id=doc_id,
            filename=os.path.basename(name),
            bucket=bucket,
            object_name=name,
            content_type=content_type,
            size_bytes=size,
            status=DocumentStatus.PENDING,
            sender="PENDING",
            contract_number="PENDING",
            work_front="PENDING",
            document_date="PENDING",
            process="PENDING"
        )
