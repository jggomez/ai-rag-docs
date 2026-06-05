import hashlib
import os
from typing import Dict, Any, List
from src.domain.entities import SourceDocument
from src.domain.enums import DocumentStatus, DocumentType
from src.domain.constants import (
    CSV_COL_ID_BORRADORES, CSV_COL_URL_RECIBIDAS, CSV_COL_RECIBIDAS,
    CSV_COL_UBICACION_FILTRADAS, CSV_COL_ENVIADAS, CSV_COL_FRENTE, CSV_COL_FECHA
)


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
            sender="PENDING",
            contract_number="PENDING",
            work_front="PENDING",
            document_date="PENDING",
            process="PENDING",
        )

    @staticmethod
    def create_documents_from_csv_row(row: Dict[str, str]) -> List[SourceDocument]:
        """
        Create one or two SourceDocument entities from a single CSV row.
        - If 'url Recibidas' is a valid URL, creates a RECEIVED document with ID {Id borradores}_REC
        - If 'Ubicacion filtradas' is a valid URL, creates a SENT document with ID {Id borradores}_SEN
        - If a URL is invalid/UNKNOWN (e.g. "Sin ruta", "Sin URL origen"), it is skipped.
        """
        documents = []
        
        # Get base Id borradores with fallback MD5 hash if missing
        draft_id = row.get(CSV_COL_ID_BORRADORES, "").strip()
        if not draft_id:
            # Consistent hash generation from row data
            row_str = "".join(sorted(f"{k}:{v}" for k, v in row.items()))
            draft_id = hashlib.md5(row_str.encode()).hexdigest()

        # Get core metadata with fallbacks
        fecha_val = row.get(CSV_COL_FECHA, "").strip()
        document_date = fecha_val if fecha_val else "UNKNOWN"

        frente_val = row.get(CSV_COL_FRENTE, "").strip()
        work_front = frente_val if frente_val else "GENERAL"

        # Extract URLs
        recibidas_url = row.get(CSV_COL_URL_RECIBIDAS, "").strip()
        enviadas_url = row.get(CSV_COL_UBICACION_FILTRADAS, "").strip()

        # Helper function to check valid URL
        def is_valid_url(url: str) -> bool:
            if not url:
                return False
            url_clean = url.lower()
            return url_clean.startswith("http") and "sin" not in url_clean

        has_valid_recibidas = is_valid_url(recibidas_url)
        has_valid_enviadas = is_valid_url(enviadas_url)

        # 1. RECEIVED Document processing
        if has_valid_recibidas:
            doc_id_raw = row.get(CSV_COL_RECIBIDAS, "").strip()
            filename = doc_id_raw if doc_id_raw else f"rec-{draft_id}"
            doc_id = f"{draft_id}_REC"

            # response file URL mapping
            response_val = row.get(CSV_COL_ENVIADAS, "").strip()
            response_file_url = response_val if response_val else (enviadas_url if has_valid_enviadas else None)

            doc_received = SourceDocument(
                id=doc_id,
                filename=filename,
                bucket="LOCAL_CSV",
                object_name=doc_id,
                content_type="application/pdf",
                size_bytes=0,
                status=DocumentStatus.PENDING,
                document_type=DocumentType.RECEIVED,
                source_url=recibidas_url,
                sender="UNKNOWN",
                contract_number="UNKNOWN",
                work_front=work_front,
                document_date=document_date,
                process="UNKNOWN",
                response_file_url=response_file_url,
                draft_id=draft_id,
            )

            doc_received.metadata["url_recibido"] = recibidas_url
            doc_received.metadata["url_enviado"] = enviadas_url if has_valid_enviadas else None
            documents.append(doc_received)

        # 2. SENT Document processing
        if has_valid_enviadas:
            doc_id_raw = row.get(CSV_COL_ENVIADAS, "").strip()
            filename = doc_id_raw if doc_id_raw else f"sen-{draft_id}"
            doc_id = f"{draft_id}_SEN"

            doc_sent = SourceDocument(
                id=doc_id,
                filename=filename,
                bucket="LOCAL_CSV",
                object_name=doc_id,
                content_type="application/pdf",
                size_bytes=0,
                status=DocumentStatus.PENDING,
                document_type=DocumentType.SENT,
                source_url=enviadas_url,
                sender="UNKNOWN",
                contract_number="UNKNOWN",
                work_front=work_front,
                document_date=document_date,
                process="UNKNOWN",
                response_file_url=None,
                draft_id=draft_id,
            )

            doc_sent.metadata["url_recibido"] = recibidas_url if has_valid_recibidas else None
            doc_sent.metadata["url_enviado"] = enviadas_url
            documents.append(doc_sent)

        return documents
