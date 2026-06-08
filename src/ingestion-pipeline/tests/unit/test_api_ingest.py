import unittest
from unittest.mock import patch
from fastapi.testclient import TestClient

# Mock dependencies BEFORE importing app to avoid initialization errors
with patch("src.repositories.storage_repo.GCSStorageRepository"), \
     patch("src.repositories.document_repo.FirestoreDocumentRepository"), \
     patch("src.infrastructure.repositories.csv_metadata_repository.CSVMetadataRepository"), \
     patch("src.filters.embedder.genai.Client"):
    from src.main import app

class TestApiIngest(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    @patch("src.main.ingest_command")
    @patch("src.main.csv_metadata_repo")
    def test_ingest_batch_success(self, mock_repo, mock_command):
        # Setup mock command result
        mock_command.execute_batch.return_value = {
            "processed_records": 2,
            "total_records": 2
        }
        response = self.client.post("/api/v1/ingest/batch")

        # Assertions
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "completed")
        self.assertEqual(result["processed_records"], 2)
        self.assertEqual(result["total_records"], 2)
        
        # Verify execute_batch was called with the repo
        mock_command.execute_batch.assert_called_once_with(mock_repo)

    @patch("src.main.ingest_command")
    def test_ingest_batch_error(self, mock_command):
        # Setup mock command to raise error (this covers errors inside the use case)
        mock_command.execute_batch.side_effect = Exception("Batch Processing Error")

        response = self.client.post("/api/v1/ingest/batch")

        self.assertEqual(response.status_code, 500)
        self.assertIn("Batch Processing Error", response.json()["detail"])

    @patch("src.main.storage_repo")
    def test_upload_file_to_gcs_success(self, mock_storage_repo):
        # Setup mock storage repo to return a mock url
        mock_storage_repo.upload_file.return_value = "gs://communications-cys/COMMUNICATION_RECEIVED/test.pdf"
        
        # Call the API using testclient
        files = {"file": ("test.pdf", b"pdf content", "application/pdf")}
        response = self.client.post("/api/v1/upload", files=files)
        
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["gcs_url"], "gs://communications-cys/COMMUNICATION_RECEIVED/test.pdf")
        self.assertEqual(result["filename"], "test.pdf")
        
        # Verify the mock repository was called with correct bucket & prefix
        from src.config import settings
        mock_storage_repo.upload_file.assert_called_once_with(
            bucket_name=settings.gcs_communications_bucket,
            object_name=f"{settings.gcs_received_prefix}test.pdf",
            content=b"pdf content",
            content_type="application/pdf"
        )

    @patch("src.main.storage_repo")
    def test_upload_file_to_gcs_failure(self, mock_storage_repo):
        mock_storage_repo.upload_file.side_effect = Exception("GCS upload failed")
        
        files = {"file": ("test.pdf", b"pdf content", "application/pdf")}
        response = self.client.post("/api/v1/upload", files=files)
        
        self.assertEqual(response.status_code, 500)
        self.assertIn("Failed to upload file: GCS upload failed", response.json()["detail"])

if __name__ == "__main__":
    unittest.main()
