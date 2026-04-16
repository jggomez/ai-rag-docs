import logging
from typing import Optional
from src.filters.base import Filter
from src.domain.entities import ProcessingPayload
from src.infrastructure.repositories.csv_metadata_repository import CSVMetadataRepository

logger = logging.getLogger(__name__)

class CSVMetadataExtractor(Filter[ProcessingPayload, ProcessingPayload]):
    """
    Extends metadata extraction by looking up document information in a CSV file.
    If metadata is already present in the payload (e.g., from API), it preserves it.
    """

    def __init__(self, repository: CSVMetadataRepository):
        self.repository = repository

    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        doc = payload.document
        logger.info(f"Refining metadata for: {doc.filename}")

        # Check if we already have metadata (e.g. from API injection)
        # We consider it "present" if contract_number is not the default "UNKNOWN"
        # or if it was explicitly set by the ingestion endpoint.
        is_already_populated = (
            doc.contract_number and doc.contract_number != "UNKNOWN" and
            doc.sender and doc.sender != "UNKNOWN"
        )

        if is_already_populated:
            logger.info(f"Metadata already present for {doc.filename}, skipping CSV lookup.")
            return payload

        # lookup in CSV using the filename/object name
        # We try both the full filename and the object_name
        csv_row = self.repository.get_metadata(doc.filename)
        if not csv_row:
            csv_row = self.repository.get_metadata(doc.object_name)

        if csv_row:
            logger.info(f"Found CSV metadata for {doc.filename}")
            # Mapping based on CSV structure:
            # Para -> sender
            # Contrato -> contract_number
            # Frente -> work_front
            # Fecha -> document_date
            # Proceso -> process
            # Enviadas -> response_file_url
            
            doc.sender = csv_row.get("Para", doc.sender or "UNKNOWN")
            doc.contract_number = csv_row.get("Contrato", doc.contract_number or "UNKNOWN")
            doc.work_front = csv_row.get("Frente", doc.work_front or "GENERAL")
            doc.document_date = csv_row.get("Fecha", doc.document_date or "UNKNOWN")
            doc.process = csv_row.get("Proceso", doc.process or "INBOX")
            doc.response_file_url = csv_row.get("Enviadas", doc.response_file_url)
            
            logger.info(f"Metadata updated from CSV for {doc.filename}")
        else:
            logger.warning(f"No CSV metadata found for {doc.filename}. Keeping existing metadata.")

        return payload
