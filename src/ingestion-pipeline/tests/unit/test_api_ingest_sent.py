import unittest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Mock dependencies BEFORE importing app to avoid initialization errors
with patch("src.repositories.storage_repo.GCSStorageRepository"), \
     patch("src.repositories.document_repo.FirestoreDocumentRepository"), \
     patch("src.infrastructure.repositories.csv_metadata_repository.CSVMetadataRepository"), \
     patch("src.filters.embedder.genai.Client"):
    from src.main import app

class TestApiIngestSent(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("src.main.ingest_command")
    @patch("src.main.pipeline_builder")
    def test_ingest_sent_endpoint_success(self, mock_builder, mock_command):
        mock_pipeline = MagicMock()
        mock_builder.build_pipeline_for_document.return_value = mock_pipeline

        # Note: Even if we pass 'received', the endpoint should force it to 'sent'
        response = self.client.post("/api/v1/ingestdocumentsent", json={
            "work_front": "Descarga",
            "document_date": "2026-06-06",
            "id_borrador": "76857089",
            "cod_document": "SEN-001",
            "document_type": "received", 
            "url_doc": "https://drive.google.com/file/d/SEN_ID/view"
        })

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "completed")
        self.assertIsNone(result["received_document"])
        self.assertEqual(result["sent_document"]["filename"], "test.pdf")
        self.assertEqual(result["sent_document"]["document_type"], "sent")

        # Verify the builder was called with DocumentType.SENT (enum value 1)
        from src.domain.enums import DocumentType
        mock_builder.build_pipeline_for_document.assert_called_once_with(
            document_type=DocumentType.SENT,
            document_repo=unittest.mock.ANY
        )
        mock_command._run_pipeline.assert_called_once()

    @patch("src.main.ingest_command")
    @patch("src.main.pipeline_builder")
    def test_ingest_received_endpoint_forces_type(self, mock_builder, mock_command):
        mock_pipeline = MagicMock()
        mock_builder.build_pipeline_for_document.return_value = mock_pipeline

        # Passing 'sent' but the endpoint forces 'received'
        response = self.client.post("/api/v1/ingestdocumentreceived", json={
            "work_front": "Descarga",
            "document_date": "2026-06-06",
            "id_borrador": "76857089",
            "cod_document": "REC-001",
            "document_type": "sent", 
            "url_doc": "https://drive.google.com/file/d/REC_ID/view"
        })

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["received_document"]["document_type"], "received")
        self.assertIsNone(result["sent_document"])

        from src.domain.enums import DocumentType
        mock_builder.build_pipeline_for_document.assert_called_once_with(
            document_type=DocumentType.RECEIVED,
            document_repo=unittest.mock.ANY
        )

if __name__ == "__main__":
    unittest.main()
