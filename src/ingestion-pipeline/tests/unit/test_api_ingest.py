import unittest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

# Mock dependencies BEFORE importing app to avoid initialization errors
with patch("src.repositories.storage_repo.GCSStorageRepository"), \
     patch("src.repositories.document_repo.FirestoreDocumentRepository"), \
     patch("src.infrastructure.repositories.csv_metadata_repository.CSVMetadataRepository"), \
     patch("langchain_google_genai.GoogleGenerativeAIEmbeddings"):
    from src.main import app

class TestApiIngest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("src.main.ingest_command")
    def test_ingest_with_metadata_success(self, mock_command):
        # Setup mock return value
        mock_doc = MagicMock()
        mock_doc.id = "test-doc-id"
        mock_doc.filename = "test.pdf"
        mock_command.execute_manual.return_value = mock_doc

        # Request payload
        payload = {
            "bucket": "test-bucket",
            "object_name": "COMMUNICATION_RECEIVED/test.pdf",
            "sender": "Test Contractor",
            "contract_number": "CW123",
            "work_front": "Taller 1",
            "document_date": "2024-04-16",
            "process": "Ambiental",
            "response_file_url": "gs://sent-bucket/sent.pdf"
        }

        response = self.client.post("/ingest", json=payload)

        # Assertions
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "status": "accepted",
            "id": "test-doc-id",
            "file": "test.pdf"
        })
        
        # Verify command was called with right data
        mock_command.execute_manual.assert_called_once()
        args = mock_command.execute_manual.call_args[0][0]
        self.assertEqual(args["bucket"], "test-bucket")
        self.assertEqual(args["sender"], "Test Contractor")

    @patch("src.main.ingest_command")
    def test_ingest_with_metadata_error(self, mock_command):
        # Setup mock to raise error
        mock_command.execute_manual.side_effect = Exception("Processing failed")

        payload = {
            "bucket": "test-bucket",
            "object_name": "test.pdf",
            "sender": "Test",
            "contract_number": "123",
            "work_front": "A",
            "document_date": "2024",
            "process": "B",
            "response_file_url": "gs://b/f.pdf"
        }

        response = self.client.post("/ingest", json=payload)

        self.assertEqual(response.status_code, 500)
        self.assertIn("Processing failed", response.json()["detail"])

if __name__ == "__main__":
    unittest.main()
