import unittest
import logging
import os
from google.cloud import firestore

# Skip if Firestore is not reachable or dummy project active
def _firestore_available():
    if os.environ.get("RUN_FIRESTORE_TESTS") != "true":
        return False
    try:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "devhack-3f0c2")
        if project_id == "dummy-project-id":
            return False
        client = firestore.Client(database="docs-recibidos", project=project_id)
        list(client.collection("documentos_chunks").limit(1).stream())
        return True
    except Exception as exc:
        print(f"\n[FIRESTORE DIAGNOSTIC] Connection error in test_api.py: {exc}")
        return False

skip_no_firestore = unittest.skipIf(
    not _firestore_available(),
    "Firestore docs-recibidos not reachable or dummy project active"
)

from fastapi.testclient import TestClient
from src.main import app, document_repo
from src.config import Settings

logger = logging.getLogger(__name__)

@skip_no_firestore
class TestRESTAPIIntegration(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)
        self.settings = Settings()
        
        # Clean up database before starting
        logger.info("Cleaning up Firestore collections for REST API test")
        for repo in [document_repo.received_repo, document_repo.sent_repo]:
            # Delete all documents in "documentos"
            for doc_snap in repo.docs_collection.stream():
                doc_snap.reference.delete()
            # Delete all chunks in "documentos_chunks"
            for chunk_snap in repo.chunks_collection.stream():
                chunk_snap.reference.delete()



    def test_ingest_received_flat_endpoint(self):
        """Tests that /api/v1/ingestdocumentreceived with flat payload ingests successfully."""
        payload = {
            "work_front": "Descarga intermedia",
            "document_date": "26/02/2025",
            "id_borrador": "76857089",
            "filename": "REC-001.pdf",
            "document_type": "received",
            "url_doc": "https://drive.google.com/file/d/1HPlEkEofIcUBbj4bjY60XEDGwdgUAe3U/view?usp=drivesdk"
        }
        
        response = self.client.post("/api/v1/ingestdocumentreceived", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["received_document"]["filename"], "REC-001.pdf")
        self.assertEqual(data["received_document"]["document_type"], "received")
        
        # Verify it exists in firestore
        doc_snap = document_repo.received_repo.docs_collection.document("76857089_REC").get()
        self.assertTrue(doc_snap.exists)
        raw_rec = doc_snap.to_dict()
        self.assertEqual(raw_rec["nombre_archivo"], "REC-001.pdf")
        self.assertEqual(raw_rec["id_borrador"], "76857089")

    def test_ingest_sent_flat_endpoint(self):
        """Tests that /api/v1/ingestdocumentsent with flat payload ingests successfully."""
        payload = {
            "work_front": "Comunicaciones",
            "document_date": "08/06/2026",
            "id_borrador": "99999999",
            "filename": "SEN-999.pdf",
            "document_type": "sent",
            "url_doc": "https://drive.google.com/file/d/1HPlEkEofIcUBbj4bjY60XEDGwdgUAe3U/view?usp=drivesdk"
        }
        
        response = self.client.post("/api/v1/ingestdocumentsent", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["sent_document"]["filename"], "SEN-999.pdf")
        self.assertEqual(data["sent_document"]["document_type"], "sent")
        
        # Verify it exists in firestore sent collection
        doc_snap = document_repo.sent_repo.docs_collection.document("99999999_SEN").get()
        self.assertTrue(doc_snap.exists)
        raw_rec = doc_snap.to_dict()
        self.assertEqual(raw_rec["nombre_archivo"], "SEN-999.pdf")
        self.assertEqual(raw_rec["id_borrador"], "99999999")
        self.assertEqual(raw_rec["url_respuesta"], payload["url_doc"])

    def test_retrieve_endpoint_flat_success(self):
        """Tests RAG retrieve endpoint with flat request."""
        # First ingest a document manually to Firestore to ensure retrieve doesn't fail
        from src.domain.entities import SourceDocument
        from src.domain.enums import DocumentStatus, DocumentType
        
        doc = SourceDocument(
            id="test-retrieve-integration-id",
            filename="REC-TEST.pdf",
            bucket="SINGLE_API",
            object_name="REC-TEST",
            content_type="application/pdf",
            size_bytes=0,
            status=DocumentStatus.COMPLETED,
            document_type=DocumentType.RECEIVED,
            source_url="https://example.com/REC-TEST.pdf",
            work_front="Descarga",
            document_date="2026-06-06",
            draft_id="12345678",
            metadata={
                "extracted_text": "Extracted text content for RAG retrieval testing.",
                "document_subject": "Integration Test Subject"
            }
        )
        document_repo.save_document(doc)
        
        # Now call retrieve endpoint with iddocumentrecibido
        response = self.client.post("/api/v1/generatedocsent", json={
            "iddocumentrecibido": "test-retrieve-integration-id"
        })
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["subject"], "Integration Test Subject")

if __name__ == "__main__":
    unittest.main()
