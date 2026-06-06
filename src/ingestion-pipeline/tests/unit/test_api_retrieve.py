"""Unit tests for the /api/v1/retrieve endpoint."""

from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

# Mock dependencies BEFORE importing app to avoid initialization errors
with patch("src.repositories.storage_repo.GCSStorageRepository"), \
     patch("src.repositories.document_repo.FirestoreDocumentRepository"), \
     patch("src.infrastructure.repositories.csv_metadata_repository.CSVMetadataRepository"), \
     patch("src.filters.embedder.genai.Client"):
    from src.main import app

def test_retrieve_endpoint_success():
    client = TestClient(app)

    with patch("src.main.retrieve_command") as mock_retrieve_command:
        mock_retrieve_command.execute.return_value = {
            "pdf_bytes": b"fake-pdf-content",
            "generated_text": "Response text",
            "similar_count": 5,
            "sent_count": 2,
            "subject": "Test Subject",
            "gcs_url": "gs://fake-bucket/fake.pdf"
        }

        response = client.post("/api/v1/retrieve", json={
            "codcomunicadorecibido": "REC-001",
            "iddocumentrecibido": "doc-id-123"
        })

        assert response.status_code == 200
        res_data = response.json()
        assert res_data["status"] == "completed"
        assert res_data["subject"] == "Test Subject"
        assert res_data["similar_count"] == 5
        assert res_data["sent_count"] == 2
        assert res_data["gcs_url"] == "gs://fake-bucket/fake.pdf"

        # Verify command called with correct snake_case variables and defaults
        mock_retrieve_command.execute.assert_called_once_with(
            id_documento_recibido="doc-id-123",
            cod_comunicado_recibido="REC-001",
            start_date=None,
            end_date=None,
            front=None
        )

def test_retrieve_endpoint_missing_fields():
    client = TestClient(app)

    response = client.post("/api/v1/retrieve", json={})
    assert response.status_code == 400
    assert "At least one of received_communication_code or received_document_id must be provided" in response.json()["detail"]

def test_retrieve_endpoint_value_error_handling():
    client = TestClient(app)

    with patch("src.main.retrieve_command") as mock_retrieve_command:
        mock_retrieve_command.execute.side_effect = ValueError("Document not found in DB")

        response = client.post("/api/v1/retrieve", json={
            "codcomunicadorecibido": "REC-NONEXISTENT"
        })

        assert response.status_code == 400
        assert "Document not found in DB" in response.json()["detail"]

def test_retrieve_endpoint_with_new_filters():
    client = TestClient(app)

    with patch("src.main.retrieve_command") as mock_retrieve_command:
        mock_retrieve_command.execute.return_value = {
            "pdf_bytes": b"fake-pdf-content",
            "generated_text": "Response text",
            "similar_count": 3,
            "sent_count": 1,
            "subject": "Filter Subject",
            "gcs_url": "gs://fake-bucket/fake.pdf"
        }

        response = client.post("/api/v1/retrieve", json={
            "received_communication_code": "REC-002",
            "received_document_id": "doc-id-456",
            "start_date": "2025-01-01",
            "end_date": "2025-01-31",
            "front": "Descarga"
        })

        assert response.status_code == 200
        assert response.json()["status"] == "completed"
        
        mock_retrieve_command.execute.assert_called_once_with(
            id_documento_recibido="doc-id-456",
            cod_comunicado_recibido="REC-002",
            start_date="2025-01-01",
            end_date="2025-01-31",
            front="Descarga"
        )
