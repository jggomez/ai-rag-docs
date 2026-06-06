import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Mock dependencies BEFORE importing app to avoid initialization errors
with patch("src.repositories.storage_repo.GCSStorageRepository"), \
     patch("src.repositories.document_repo.FirestoreDocumentRepository"), \
     patch("src.infrastructure.repositories.csv_metadata_repository.CSVMetadataRepository"), \
     patch("src.filters.embedder.genai.Client"):
    from src.main import app

class TestApiIngestReceived(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("src.main.ingest_command")
    @patch("src.main.pipeline_builder")
    def test_ingest_received_success(self, mock_builder, mock_command):
        mock_pipeline = MagicMock()
        mock_builder.build_pipeline_for_document.return_value = mock_pipeline

        response = self.client.post("/api/v1/ingestdocumentreceived", json={
            "work_front": "Descarga",
            "document_date": "2026-06-06",
            "id_borrador": "76857089",
            "filename": "REC-001.pdf",
            "document_type": "received",
            "url_doc": "https://drive.google.com/file/d/REC_ID/view"
        })

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["received_document"]["filename"], "REC-001.pdf")
        self.assertEqual(result["received_document"]["document_type"], "received")
        self.assertIsNone(result["sent_document"])

        mock_builder.build_pipeline_for_document.assert_called_once()
        mock_command._run_pipeline.assert_called_once()

    @patch("src.main.ingest_command")
    @patch("src.main.pipeline_builder")
    def test_ingest_sent_success(self, mock_builder, mock_command):
        mock_pipeline = MagicMock()
        mock_builder.build_pipeline_for_document.return_value = mock_pipeline

        response = self.client.post("/api/v1/ingestdocumentreceived", json={
            "work_front": "Descarga",
            "document_date": "2026-06-06",
            "id_borrador": "76857089",
            "filename": "SEN-001.pdf",
            "document_type": "sent",
            "url_doc": "https://drive.google.com/file/d/SEN_ID/view"
        })

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["received_document"]["filename"], "SEN-001.pdf")
        self.assertEqual(result["received_document"]["document_type"], "sent")
        self.assertIsNone(result["sent_document"])

        mock_builder.build_pipeline_for_document.assert_called_once()
        mock_command._run_pipeline.assert_called_once()

    def test_ingest_received_invalid_type(self):
        response = self.client.post("/api/v1/ingestdocumentreceived", json={
            "work_front": "Descarga",
            "document_date": "2026-06-06",
            "id_borrador": "76857089",
            "filename": "REC-001.pdf",
            "document_type": "other",
            "url_doc": "https://drive.google.com/file/d/REC_ID/view"
        })
        self.assertEqual(response.status_code, 400)
        self.assertIn("document_type must be either 'sent' or 'received'", response.json()["detail"])

    def test_ingest_received_missing_fields(self):
        response = self.client.post("/api/v1/ingestdocumentreceived", json={
            "url_doc": "https://drive.google.com/file/d/REC_ID/view"
        })
        self.assertEqual(response.status_code, 422)

if __name__ == "__main__":
    unittest.main()
