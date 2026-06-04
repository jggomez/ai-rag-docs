import csv
import logging
import os
from typing import Dict, List, Optional
from src.domain.constants import CSV_COL_ENVIADAS

logger = logging.getLogger(__name__)

class CSVMetadataRepository:
    """
    Repository for accessing document metadata stored in a CSV file.
    Supports both legacy single-key lookup (by 'Enviadas') and
    dual-URL iteration for Drive-based ingestion.
    Provides O(1) lookup after initial load.
    """

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._data: Dict[str, Dict[str, str]] = {}
        self._rows: List[Dict[str, str]] = []
        self._is_loaded = False

    def _load_data(self):
        """Loads CSV data into an in-memory dictionary and row list."""
        if not os.path.exists(self.csv_path):
            logger.error(f"Metadata CSV not found at: {self.csv_path}")
            return

        try:
            with open(self.csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self._rows.append(row)

                    # Keyed index by 'Enviadas' column using constant
                    key = row.get(CSV_COL_ENVIADAS, "").strip()
                    if key:
                        self._data[key] = row
            
            self._is_loaded = True
            logger.info(f"Successfully loaded {len(self._rows)} rows ({len(self._data)} keyed records) from {self.csv_path}")
        except Exception as e:
            logger.error(f"Error loading metadata CSV: {str(e)}")

    def get_metadata(self, document_id: str) -> Optional[Dict[str, str]]:
        """
        Retrieves metadata for a specific document ID.
        The document_id should match the value in the 'Enviadas' column.
        """
        if not self._is_loaded:
            self._load_data()
        
        # Normalize document_id for lookup (remove .pdf if present)
        clean_id = document_id.replace(".pdf", "").strip()
        
        # Also try replacing slash with underscore if the input filename uses underscores
        metadata = self._data.get(clean_id)
        if not metadata:
            # Try alternate slash/underscore normalization if needed
            alt_id = clean_id.replace("_", "/")
            metadata = self._data.get(alt_id)
            
        return metadata

    def get_all_records(self) -> Dict[str, Dict[str, str]]:
        """
        Returns all keyed metadata records from the CSV (legacy).
        Useful for batch ingestion of 'Enviadas' documents.
        """
        if not self._is_loaded:
            self._load_data()
        return self._data

    def get_all_rows(self) -> List[Dict[str, str]]:
        """
        Returns every row from the CSV as a list of dicts.
        Supports iteration over both recibidas_url and enviadas_url rows.
        """
        if not self._is_loaded:
            self._load_data()
        return self._rows
