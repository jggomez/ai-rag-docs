import hashlib
import os
from typing import Dict, Any
from src.domain.entities import SourceDocument
from src.domain.enums import DocumentStatus, DocumentType
from src.domain.constants import (
    CSV_COL_ID_BORRADORES, CSV_COL_URL_RECIBIDAS, CSV_COL_RECIBIDAS,
    CSV_COL_UBICACION_FILTRADAS, CSV_COL_UBICACION_ENVIADAS,
    CSV_COL_ENVIADAS, CSV_COL_PARA, CSV_COL_CONTRATO,
    CSV_COL_FRENTE, CSV_COL_FECHA, CSV_COL_PROCESO, CSV_COL_DESCRIPCION
)
from typing import List


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
        - If 'Ubicacion filtradas' (or Ubicacion Enviadas) is a valid URL, creates a SENT document with ID {Id borradores}_SEN
        """
        documents = []
        
        # Get base Id borradores
        draft_id = row.get(CSV_COL_ID_BORRADORES, "").strip()
        if not draft_id:
            # Fallback to hash if draft ID is missing
            draft_id = hashlib.md5(str(row).encode()).hexdigest()

        # Extract URLs and determine if they are valid
        recibidas_url = row.get(CSV_COL_URL_RECIBIDAS, "").strip()
        has_valid_recibidas = recibidas_url and recibidas_url.startswith("http") and "Sin" not in recibidas_url
        url_recibido = recibidas_url if has_valid_recibidas else None

        enviadas_url = (row.get(CSV_COL_UBICACION_FILTRADAS) or row.get(CSV_COL_UBICACION_ENVIADAS) or "").strip()
        has_valid_enviadas = enviadas_url and enviadas_url.startswith("http") and "Sin" not in enviadas_url
        url_enviado = enviadas_url if has_valid_enviadas else None

        # 1. RECEIVED Document processing
        if has_valid_recibidas:
            doc_id_raw = row.get(CSV_COL_RECIBIDAS, "").strip() or row.get(CSV_COL_ENVIADAS, "").strip()
            filename = doc_id_raw if doc_id_raw else f"rec-{draft_id}"
            doc_id = f"{draft_id}_REC"

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
                sender=row.get(CSV_COL_PARA, "UNKNOWN"),
                contract_number=row.get(CSV_COL_CONTRATO, "UNKNOWN"),
                work_front=row.get(CSV_COL_FRENTE, "GENERAL"),
                document_date=row.get(CSV_COL_FECHA, "UNKNOWN"),
                process=row.get(CSV_COL_PROCESO, "INBOX"),
                response_file_url=row.get(CSV_COL_ENVIADAS, "").strip(),
                draft_id=draft_id,
            )

            desc = row.get(CSV_COL_DESCRIPCION, "")
            if desc:
                doc_received.metadata["extracted_text"] = desc

            doc_received.metadata["url_recibido"] = url_recibido
            doc_received.metadata["url_enviado"] = url_enviado
            documents.append(doc_received)

        # 2. SENT Document processing (response file)
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
                sender=row.get(CSV_COL_PARA, "UNKNOWN"),
                contract_number=row.get(CSV_COL_CONTRATO, "UNKNOWN"),
                work_front=row.get(CSV_COL_FRENTE, "GENERAL"),
                document_date=row.get(CSV_COL_FECHA, "UNKNOWN"),
                process=row.get(CSV_COL_PROCESO, "INBOX"),
                response_file_url=doc_id_raw,
                draft_id=draft_id,
            )

            desc = row.get(CSV_COL_DESCRIPCION, "")
            if desc:
                doc_sent.metadata["extracted_text"] = desc

            doc_sent.metadata["url_recibido"] = url_recibido
            doc_sent.metadata["url_enviado"] = url_enviado
            documents.append(doc_sent)

        # Fallback if neither URL is present to prevent dropping row completely
        if not documents:
            doc_id_raw = row.get(CSV_COL_ENVIADAS, "").strip()
            filename = doc_id_raw if doc_id_raw else f"doc-{draft_id}"
            doc_id = f"{draft_id}_SEN"

            doc_fallback = SourceDocument(
                id=doc_id,
                filename=filename,
                bucket="LOCAL_CSV",
                object_name=doc_id,
                content_type="text/csv",
                size_bytes=0,
                status=DocumentStatus.PENDING,
                document_type=DocumentType.SENT,
                source_url=None,
                sender=row.get(CSV_COL_PARA, "UNKNOWN"),
                contract_number=row.get(CSV_COL_CONTRATO, "UNKNOWN"),
                work_front=row.get(CSV_COL_FRENTE, "GENERAL"),
                document_date=row.get(CSV_COL_FECHA, "UNKNOWN"),
                process=row.get(CSV_COL_PROCESO, "INBOX"),
                response_file_url=doc_id_raw,
                draft_id=draft_id,
            )

            desc = row.get(CSV_COL_DESCRIPCION, "")
            if desc:
                doc_fallback.metadata["extracted_text"] = desc

            doc_fallback.metadata["url_recibido"] = url_recibido
            doc_fallback.metadata["url_enviado"] = url_enviado
            documents.append(doc_fallback)

        return documents
