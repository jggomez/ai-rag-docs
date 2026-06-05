import unittest
import tempfile
import os
from src.infrastructure.repositories.csv_metadata_repository import CSVMetadataRepository


class TestCSVMetadataRepository(unittest.TestCase):
    def setUp(self):
        # Create a temporary CSV file with test data
        self.temp_dir = tempfile.TemporaryDirectory()
        self.csv_path = os.path.join(self.temp_dir.name, "test_metadata.csv")
        
        # Write mock headers and data
        with open(self.csv_path, "w", encoding="utf-8") as f:
            f.write("Id borradores,Fecha,Frente,Recibidas,url Recibidas,Enviadas,Ubicacion filtradas\n")
            f.write("76857089,26/02/2025,Frente 1,REC-001,https://drive.google.com/1,INT/OC/CYS/513,https://drive.google.com/2\n")
            f.write("3e674e6a,04/03/2025,Frente 2,REC-002,https://drive.google.com/3,INT_OC_CYS_339,https://drive.google.com/4\n")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_load_non_existent_csv(self):
        repo = CSVMetadataRepository("/non/existent/path.csv")
        rows = repo.get_all_rows()
        self.assertEqual(len(rows), 0)
        self.assertFalse(repo._is_loaded)

    def test_get_metadata_by_exact_key(self):
        repo = CSVMetadataRepository(self.csv_path)
        metadata = repo.get_metadata("INT/OC/CYS/513")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["Id borradores"], "76857089")
        self.assertEqual(metadata["Frente"], "Frente 1")

    def test_get_metadata_normalized_with_pdf_extension(self):
        repo = CSVMetadataRepository(self.csv_path)
        metadata = repo.get_metadata("INT/OC/CYS/513.pdf")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["Id borradores"], "76857089")

    def test_get_metadata_slash_underscore_fallback(self):
        # If lookup uses underscores, e.g. "INT_OC_CYS_513", alt_id cleans slash/underscore
        repo = CSVMetadataRepository(self.csv_path)
        
        # Look up "INT_OC_CYS_513" -> should alternate to "INT/OC/CYS/513"
        metadata = repo.get_metadata("INT_OC_CYS_513")
        self.assertIsNotNone(metadata)
        self.assertEqual(metadata["Id borradores"], "76857089")

    def test_get_all_records(self):
        repo = CSVMetadataRepository(self.csv_path)
        records = repo.get_all_records()
        self.assertEqual(len(records), 2)
        self.assertIn("INT/OC/CYS/513", records)
        self.assertIn("INT_OC_CYS_339", records)

    def test_get_all_rows(self):
        repo = CSVMetadataRepository(self.csv_path)
        rows = repo.get_all_rows()
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["Enviadas"], "INT/OC/CYS/513")
        self.assertEqual(rows[1]["Enviadas"], "INT_OC_CYS_339")
