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

    def _build_payload(self, url: str, doc_type: str, response_url: str) -> dict:
        """Helper to construct the standard ingestion API payload."""
        return {
            "url": url,
            "document_type": doc_type,
            "metadata": {
                "work_front": "Descarga intermedia",
                "document_date": "26/02/2025",
                "response_file_url": response_url,
                "custom_project_tag": "Ingenieria-Rest-Test"
            }
        }

    def _assert_common_firestore_schema(self, raw_doc: dict):
        """Helper to assert the unified flat Spanish schema is respected."""
        self.assertNotIn("metadatos_ingenieria", raw_doc)
        self.assertNotIn("metadatos", raw_doc)
        self.assertNotIn("bucket", raw_doc)
        self.assertNotIn("url_enviado", raw_doc) # Should be completely unified/omitted!
        self.assertIn("nombre_archivo", raw_doc)
        self.assertEqual(raw_doc["estado"], "COMPLETADO")

        # Flat Engineering Metadata
        self.assertEqual(raw_doc["frente_trabajo"], "Descarga intermedia")
        self.assertEqual(raw_doc["fecha_documento"], "26/02/2025")
        self.assertEqual(raw_doc["custom_project_tag"], "Ingenieria-Rest-Test")

    def test_received_document_creates_cross_urls(self):
        """Tests that RECEIVED documents execute OCR and map URLs symmetrically."""
        received_url = "https://drive.google.com/file/d/1HPlEkEofIcUBbj4bjY60XEDGwdgUAe3U/view?usp=drivesdk"
        sent_response_url = "https://drive.google.com/file/d/1wX4UQTO7NKmRNC-bX4scR9PsTHHru7lp/view?usp=drivesdk"

        payload = self._build_payload(received_url, "received", sent_response_url)

        logger.info("Sending RECEIVED document single ingest request")
        response = self.client.post("/api/v1/ingest", json=payload)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["document_type"], "received")

        # Capture generated Firestore ID
        doc_id = data["document_id"]
        self.assertIsNotNone(doc_id)
        self.assertFalse(doc_id.endswith("_REC") or doc_id.endswith("_SEN"))

        # Verify exact Spanish storage structure in Firestore (docs-recibidos)
        doc_snap = document_repo.received_repo.docs_collection.document(doc_id).get()
        self.assertTrue(doc_snap.exists)
        raw_rec = doc_snap.to_dict()

        self._assert_common_firestore_schema(raw_rec)

        # Cross-mapping URL Assertions for RECEIVED:
        self.assertEqual(raw_rec["url_recibido"], received_url)
        self.assertEqual(raw_rec["url_origen"], received_url)

        # Received specific: OCR text extraction
        self.assertIn("texto_extraido", raw_rec)
        self.assertIsNotNone(raw_rec["texto_extraido"])

        # Check generated chunks
        chunks_query = document_repo.received_repo.chunks_collection.where(
            "id_documento", "==", doc_id
        ).stream()
        chunks_list = [c.to_dict() for c in chunks_query]
        self.assertGreater(len(chunks_list), 0)

        for chunk in chunks_list:
            self.assertFalse(chunk["id"].endswith("_0") or chunk["id"].endswith("_1"))
            self.assertEqual(chunk["id_documento"], doc_id)
            self.assertEqual(chunk["url_recibido"], received_url)
            self.assertIn("indice_chunk", chunk)

    def test_sent_document_creates_cross_urls(self):
        """Tests that SENT documents map URLs symmetrically and skip OCR cleanly."""
        sent_url = "https://drive.google.com/file/d/1wX4UQTO7NKmRNC-bX4scR9PsTHHru7lp/view?usp=drivesdk"
        received_origin_url = "https://drive.google.com/file/d/1HPlEkEofIcUBbj4bjY60XEDGwdgUAe3U/view?usp=drivesdk"

        payload = self._build_payload(sent_url, "sent", received_origin_url)

        logger.info("Sending SENT document single ingest request")
        response = self.client.post("/api/v1/ingest", json=payload)
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "completed")
        self.assertEqual(data["document_type"], "sent")

        # Capture generated Firestore ID
        doc_id = data["document_id"]
        self.assertIsNotNone(doc_id)
        self.assertFalse(doc_id.endswith("_REC") or doc_id.endswith("_SEN"))

        # Verify exact Spanish storage structure in Firestore (docs-enviados)
        doc_snap = document_repo.sent_repo.docs_collection.document(doc_id).get()
        self.assertTrue(doc_snap.exists)
        raw_sen = doc_snap.to_dict()

        self._assert_common_firestore_schema(raw_sen)

        # Cross-mapping URL Assertions for SENT:
        self.assertEqual(raw_sen["url_origen"], sent_url)
        self.assertEqual(raw_sen["url_recibido"], received_origin_url)

        # Check generated chunks
        chunks_query = document_repo.sent_repo.chunks_collection.where(
            "id_documento", "==", doc_id
        ).stream()
        chunks_list = [c.to_dict() for c in chunks_query]
        self.assertGreater(len(chunks_list), 0)

        for chunk in chunks_list:
            self.assertFalse(chunk["id"].endswith("_0") or chunk["id"].endswith("_1"))
            self.assertEqual(chunk["id_documento"], doc_id)
            self.assertEqual(chunk["url_recibido"], received_origin_url)
            self.assertEqual(chunk["url_origen"], sent_url)
            self.assertIn("indice_chunk", chunk)

if __name__ == "__main__":
    unittest.main()
