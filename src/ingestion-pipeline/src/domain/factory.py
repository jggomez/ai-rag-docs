import hashlib
import os
from typing import Dict, Any
from src.domain.entities import SourceDocument, EngineeringMetadata
from src.domain.enums import DocumentStatus, DocumentType


class SourceDocumentFactory:
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
            document_type=DocumentType.SENT,
            engineering_metadata=EngineeringMetadata(
                sender="PENDING",
                contract_number="PENDING",
                work_front="PENDING",
                document_date="PENDING",
                process="PENDING"
            )
        )

    @staticmethod
    def create_from_csv_row(row: Dict[str, str]) -> SourceDocument:
        """
        Create a SourceDocument entity from a CSV row.
        Determines DocumentType from the URL columns:
          - recibidas_url present → RECEIVED
          - enviadas_url present  → SENT
          - fallback              → SENT (legacy behaviour)
        """
        recibidas_url = row.get("recibidas_url", "").strip()
        enviadas_url = row.get("enviadas_url", "").strip()

        # Resolve document type and source URL
        if recibidas_url:
            document_type = DocumentType.RECEIVED
            source_url = recibidas_url
        elif enviadas_url:
            document_type = DocumentType.SENT
            source_url = enviadas_url
        else:
            document_type = DocumentType.SENT
            source_url = None

        doc_id_raw = row.get("Enviadas", "").strip()
        doc_id = hashlib.md5(str(row).encode()).hexdigest()

        # Use enviadas filename or a generic label
        filename = doc_id_raw if doc_id_raw else "csv"

        doc = SourceDocument(
            id=doc_id,
            filename=filename,
            bucket="LOCAL_CSV",
            object_name=doc_id,
            content_type="text/csv",
            size_bytes=0,
            status=DocumentStatus.PENDING,
            document_type=document_type,
            source_url=source_url,
            engineering_metadata=EngineeringMetadata(
                sender=row.get("Para", "UNKNOWN"),
                contract_number=row.get("Contrato", "UNKNOWN"),
                work_front=row.get("Frente", "GENERAL"),
                document_date=row.get("Fecha", "UNKNOWN"),
                process=row.get("Proceso", "INBOX"),
                response_file_url=doc_id_raw,
            )
        )

        # Set the content directly if Descripcion exists
        # This will be used as the "source text" instead of PDF extraction
        desc = row.get("Descripcion", "")
        if desc:
            doc.metadata["extracted_text"] = desc

        return doc
