import unittest
from unittest.mock import patch, MagicMock
import os
import csv
import tempfile
from scripts.batch_ingest import batch_ingest

class TestBatchIngest(unittest.TestCase):
    def setUp(self):
        # Create a temporary CSV file
        self.test_dir = tempfile.TemporaryDirectory()
        self.csv_path = os.path.join(self.test_dir.name, "test_comunicaciones.csv")
        
        with open(self.csv_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=["Para", "Contrato", "Frente", "Fecha", "Proceso", "Enviadas"])
            writer.writeheader()
            writer.writerow({
                "Para": "Sender 1",
                "Contrato": "CW1",
                "Frente": "F1",
                "Fecha": "2024-01-01",
                "Proceso": "P1",
                "Enviadas": "SENT_001"
            })
            writer.writerow({
                "Para": "Sender 2",
                "Contrato": "CW2",
                "Frente": "F2",
                "Fecha": "2024-01-02",
                "Proceso": "P2",
                "Enviadas": "SENT_002"
            })

    def tearDown(self):
        self.test_dir.cleanup()

    @patch("scripts.batch_ingest.requests.post")
    def test_batch_ingest_success(self, mock_post):
        # Mock successful response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_post.return_value = mock_response

        batch_ingest(self.csv_path, "test-bucket")

        # Verify post was called twice
        self.assertEqual(mock_post.call_count, 2)
        
        # Verify first call data
        args, kwargs = mock_post.call_args_list[0]
        payload = kwargs["json"]
        self.assertEqual(payload["sender"], "Sender 1")
        self.assertEqual(payload["object_name"], "COMMUNICATION_RECEIVED/SENT_001.pdf")
        self.assertEqual(payload["response_file_url"], "SENT_001")

    @patch("scripts.batch_ingest.requests.post")
    def test_batch_ingest_with_errors(self, mock_post):
        # Mock failed response
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_response.text = "Internal error"
        mock_post.return_value = mock_response

        # This should not raise exception but log errors
        batch_ingest(self.csv_path, "test-bucket")
        
        self.assertEqual(mock_post.call_count, 2)

if __name__ == "__main__":
    unittest.main()
