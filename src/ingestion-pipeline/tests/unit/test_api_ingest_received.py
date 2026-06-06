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
    def test_ingest_received_with_sent_success(self, mock_builder, mock_command):
        # Mock strategy pipelines
        mock_pipeline_rec = MagicMock()
        mock_pipeline_sen = MagicMock()
        
        # Side effect to return different pipelines based on document_type
        from src.domain.enums import DocumentType
        def build_pipeline_side_effect(document_type, document_repo):
            if document_type == DocumentType.RECEIVED:
                return mock_pipeline_rec
            return mock_pipeline_sen
            
        mock_builder.build_pipeline_for_document.side_effect = build_pipeline_side_effect

        response = self.client.post("/api/v1/ingestdocumentreceived", json={
            "url": "https://drive.google.com/file/d/REC_ID/view",
            "metadata": {
                "draft_id": "76857089",
                "document_date": "2026-06-06",
                "work_front": "Descarga",
                "code": "REC-001",
                "response_file_url": "https://drive.google.com/file/d/SEN_ID/view"
            }
        })

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["received_document"]["filename"], "REC-001.pdf")
        self.assertEqual(result["received_document"]["document_type"], "received")
        self.assertEqual(result["sent_document"]["status"], "completed")

        # Verify both pipelines were built and run
        self.assertEqual(mock_builder.build_pipeline_for_document.call_count, 2)
        self.assertEqual(mock_command._run_pipeline.call_count, 2)

    @patch("src.main.ingest_command")
    @patch("src.main.pipeline_builder")
    def test_ingest_received_only_success(self, mock_builder, mock_command):
        mock_pipeline_rec = MagicMock()
        mock_builder.build_pipeline_for_document.return_value = mock_pipeline_rec

        response = self.client.post("/api/v1/ingestdocumentreceived", json={
            "url": "https://drive.google.com/file/d/REC_ID/view",
            "metadata": {
                "draft_id": "76857089",
                "document_date": "2026-06-06",
                "work_front": "Descarga",
                "code": "REC-001",
                "response_file_url": None
            }
        })

        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["received_document"]["filename"], "REC-001.pdf")
        self.assertIsNone(result["sent_document"])

        # Verify only one pipeline was built and run
        mock_builder.build_pipeline_for_document.assert_called_once()
        mock_command._run_pipeline.assert_called_once()

    def test_ingest_received_missing_fields(self):
        response = self.client.post("/api/v1/ingestdocumentreceived", json={
            "url": "https://drive.google.com/file/d/REC_ID/view"
        })
        self.assertEqual(response.status_code, 422)

if __name__ == "__main__":
    unittest.main()
