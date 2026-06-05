import unittest
from src.infrastructure.repositories.csv_metadata_repository import CSVMetadataRepository
from src.domain.factory import SourceDocumentFactory
import tempfile
import os
import csv

class TestCSVParser(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.TemporaryDirectory()
        self.csv_path = os.path.join(self.test_dir.name, "test_restricted.csv")

    def tearDown(self):
        self.test_dir.cleanup()

    def test_parse_restricted_columns_only(self):
        # Create CSV with only the 7 allowed columns
        with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "Id borradores", "Fecha", "Frente", "Recibidas", "url Recibidas", "Enviadas", "Ubicacion filtradas"
            ])
            writer.writeheader()
            writer.writerow({
                "Id borradores": "76857089",
                "Fecha": "26/02/2025",
                "Frente": "Descarga intermedia",
                "Recibidas": "REC_01",
                "url Recibidas": "https://drive.google.com/file/d/1/view",
                "Enviadas": "SENT_01",
                "Ubicacion filtradas": "https://drive.google.com/file/d/2/view"
            })

        repo = CSVMetadataRepository(self.csv_path)
        rows = repo.get_all_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        self.assertEqual(row["Id borradores"], "76857089")
        self.assertEqual(row["url Recibidas"], "https://drive.google.com/file/d/1/view")
        self.assertEqual(row["Ubicacion filtradas"], "https://drive.google.com/file/d/2/view")

    def test_parse_with_extra_ignored_columns(self):
        # Create CSV with additional columns
        with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=[
                "Id borradores", "Fecha", "Frente", "Recibidas", "url Recibidas", "Enviadas", "Ubicacion filtradas",
                "Para", "Contrato", "Proceso"
            ])
            writer.writeheader()
            writer.writerow({
                "Id borradores": "76857089",
                "Fecha": "26/02/2025",
                "Frente": "Descarga intermedia",
                "Recibidas": "REC_01",
                "url Recibidas": "https://drive.google.com/file/d/1/view",
                "Enviadas": "SENT_01",
                "Ubicacion filtradas": "https://drive.google.com/file/d/2/view",
                "Para": "CYC",
                "Contrato": "CW123",
                "Proceso": "Supervision"
            })

        repo = CSVMetadataRepository(self.csv_path)
        rows = repo.get_all_rows()
        self.assertEqual(len(rows), 1)
        row = rows[0]
        # Verify extra columns are ignored by checking that defaults are applied
        docs = SourceDocumentFactory.create_documents_from_csv_row(row)
        self.assertEqual(len(docs), 2)
        for doc in docs:
            self.assertEqual(doc.sender, "UNKNOWN")
            self.assertEqual(doc.contract_number, "UNKNOWN")
