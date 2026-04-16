import csv
import logging
import os
from typing import Dict, Optional, Any

logger = logging.getLogger(__name__)

class CSVMetadataRepository:
    """
    Repository for accessing document metadata stored in a CSV file.
    Provides O(1) lookup after initial load.
    """

    def __init__(self, csv_path: str):
        self.csv_path = csv_path
        self._data: Dict[str, Dict[str, str]] = {}
        self._is_loaded = False

    def _load_data(self):
        """Loads CSV data into an in-memory dictionary."""
        if not os.path.exists(self.csv_path):
            logger.error(f"Metadata CSV not found at: {self.csv_path}")
            return

        try:
            with open(self.csv_path, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    # 'Enviadas' contains the document ID/filename (e.g., INT-OC-CYS-291/25)
                    key = row.get("Enviadas", "").strip()
                    if key:
                        self._data[key] = row
            
            self._is_loaded = True
            logger.info(f"Successfully loaded {len(self._data)} metadata records from {self.csv_path}")
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
