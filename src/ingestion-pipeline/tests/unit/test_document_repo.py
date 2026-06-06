import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from src.repositories.document_repo import (
    FirestoreDocumentRepository,
    RoutingFirestoreDocumentRepository,
)
from src.domain.entities import SourceDocument, DocumentChunk
from src.domain.enums import DocumentStatus, DocumentType
from google.cloud.firestore_v1.vector import Vector


class TestFirestoreDocumentRepository(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock()
        self.repo = FirestoreDocumentRepository(database="test-db", client=self.mock_client)

    def test_save_document_new_with_temp_id(self):
        # Temp ID ending with _REC should generate a new firestore document ID
        doc = SourceDocument(
            id="123_REC",
            filename="test.pdf",
            bucket="b",
            object_name="obj",
            content_type="application/pdf",
            size_bytes=100,
            status=DocumentStatus.PENDING,
            document_type=DocumentType.RECEIVED,
            work_front="A",
            document_date="2024-01-01",
        )
        mock_ref = MagicMock()
        mock_ref.id = "generated_firestore_id"
        self.mock_client.collection.return_value.document.return_value = mock_ref

        self.repo.save_document(doc)

        self.assertEqual(doc.id, "generated_firestore_id")
        self.mock_client.collection.assert_any_call("documentos")
        mock_ref.set.assert_called_once()
        saved_data = mock_ref.set.call_args[0][0]
        self.assertEqual(saved_data["id"], "generated_firestore_id")
        self.assertEqual(saved_data["nombre_archivo"], "test.pdf")
        self.assertEqual(saved_data["estado"], "PENDIENTE")

    def test_save_document_existing_id(self):
        # Existing ID not matching temp patterns should be preserved
        doc = SourceDocument(
            id="permanent-id-999",
            filename="test.pdf",
            bucket="b",
            object_name="obj",
            content_type="application/pdf",
            size_bytes=100,
            status=DocumentStatus.COMPLETED,
            document_type=DocumentType.SENT,
            work_front="A",
            document_date="2024-01-01",
        )
        mock_ref = MagicMock()
        self.mock_client.collection.return_value.document.return_value = mock_ref

        self.repo.save_document(doc)

        self.assertEqual(doc.id, "permanent-id-999")
        self.mock_client.collection.return_value.document.assert_called_with("permanent-id-999")
        mock_ref.set.assert_called_once()

    def test_get_document_exists(self):
        mock_ref = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.exists = True
        mock_snapshot.to_dict.return_value = {
            "id": "doc123",
            "nombre_archivo": "file.pdf",
            "nombre_objeto": "file.pdf",
            "tipo_contenido": "application/pdf",
            "creado_en": datetime.now(),
            "estado": "COMPLETADO",
            "tipo_documento": "RECIBIDO",
            "remitente": "ACME",
            "numero_contrato": "C1",
            "frente_trabajo": "F1",
            "fecha_documento": "2026-06-05",
            "proceso": "P1",
            "texto_extraido": "body text",
            "asunto_documento": "subject text"
        }
        mock_ref.get.return_value = mock_snapshot
        self.mock_client.collection.return_value.document.return_value = mock_ref

        doc = self.repo.get_document("doc123")

        self.assertIsNotNone(doc)
        self.assertEqual(doc.id, "doc123")
        self.assertEqual(doc.status, DocumentStatus.COMPLETED)
        self.assertEqual(doc.document_type, DocumentType.RECEIVED)
        self.assertEqual(doc.metadata["extracted_text"], "body text")
        self.assertEqual(doc.metadata["document_subject"], "subject text")

    def test_get_document_not_exists(self):
        mock_ref = MagicMock()
        mock_snapshot = MagicMock()
        mock_snapshot.exists = False
        mock_ref.get.return_value = mock_snapshot
        self.mock_client.collection.return_value.document.return_value = mock_ref

        doc = self.repo.get_document("missing123")
        self.assertIsNone(doc)

    def test_update_status(self):
        mock_ref = MagicMock()
        self.mock_client.collection.return_value.document.return_value = mock_ref

        self.repo.update_status("doc123", DocumentStatus.FAILED, error="Timeout error")

        mock_ref.update.assert_called_once_with({"estado": "FALLIDO", "error": "Timeout error"})

    def test_save_chunks_empty(self):
        self.repo.save_chunks([])
        self.mock_client.batch.assert_not_called()

    def test_save_chunks_with_parent(self):
        # Mock parent document
        parent_doc = SourceDocument(
            id="parent123",
            filename="parent.pdf",
            bucket="b",
            object_name="obj",
            content_type="pdf",
            size_bytes=1000,
            status=DocumentStatus.COMPLETED,
            document_type=DocumentType.RECEIVED,
            work_front="GENERAL",
            document_date="2026-01-01",
            source_url="https://drive.google.com/view"
        )
        
        with patch.object(self.repo, "get_document", return_value=parent_doc):
            mock_batch = MagicMock()
            self.mock_client.batch.return_value = mock_batch
            
            mock_chunk_ref = MagicMock()
            mock_chunk_ref.id = "chunk_id_generated"
            self.mock_client.collection.return_value.document.return_value = mock_chunk_ref

            chunks = [
                DocumentChunk(
                    id="c1",
                    document_id="parent123",
                    subject="Chunk Subject",
                    body="Chunk Body",
                    index=0,
                    embedding=[0.1, 0.2, 0.3],
                    metadata={"chunk_index": 0}
                )
            ]

            self.repo.save_chunks(chunks)

            self.mock_client.batch.assert_called_once()
            mock_batch.set.assert_called_once()
            mock_batch.commit.assert_called_once()
            
            saved_data = mock_batch.set.call_args[0][1]
            self.assertEqual(saved_data["id"], "chunk_id_generated")
            self.assertEqual(saved_data["id_documento"], "parent123")
            self.assertEqual(saved_data["texto"], "Chunk Subject\nChunk Body")
            self.assertEqual(saved_data["url_origen"], "https://drive.google.com/view")
            self.assertTrue(isinstance(saved_data["vector"], Vector))


class TestRoutingFirestoreDocumentRepository(unittest.TestCase):
    def setUp(self):
        self.mock_client_rec = MagicMock()
        self.mock_client_sent = MagicMock()
        self.repo = RoutingFirestoreDocumentRepository(
            client_received=self.mock_client_rec,
            client_sent=self.mock_client_sent,
        )

    def test_save_document_routing(self):
        # RECEIVED goes to received_repo
        doc_rec = SourceDocument(
            id="doc_rec", filename="f.pdf", bucket="b", object_name="obj",
            content_type="pdf", size_bytes=0, status=DocumentStatus.PENDING,
            document_type=DocumentType.RECEIVED,
            work_front="W", document_date="2026"
        )
        with patch.object(self.repo.received_repo, "save_document") as mock_save:
            self.repo.save_document(doc_rec)
            mock_save.assert_called_once_with(doc_rec)

        # SENT goes to sent_repo
        doc_sen = SourceDocument(
            id="doc_sen", filename="f.pdf", bucket="b", object_name="obj",
            content_type="pdf", size_bytes=0, status=DocumentStatus.PENDING,
            document_type=DocumentType.SENT,
            work_front="W", document_date="2026"
        )
        with patch.object(self.repo.sent_repo, "save_document") as mock_save:
            self.repo.save_document(doc_sen)
            mock_save.assert_called_once_with(doc_sen)

    def test_get_document_by_id_suffix(self):
        # Ends with _REC
        with patch.object(self.repo.received_repo, "get_document") as mock_get:
            self.repo.get_document("123_REC")
            mock_get.assert_called_once_with("123_REC")

        # Ends with _SEN
        with patch.object(self.repo.sent_repo, "get_document") as mock_get:
            self.repo.get_document("123_SEN")
            mock_get.assert_called_once_with("123_SEN")

    def test_get_document_routing_fallback(self):
        # Test routing fallback for generated Firestore IDs
        mock_doc_ref = MagicMock()
        mock_snap = MagicMock()
        mock_snap.exists = True
        mock_doc_ref.get.return_value = mock_snap
        self.mock_client_rec.collection.return_value.document.return_value = mock_doc_ref

        with patch.object(self.repo.received_repo, "get_document", return_value="received_doc"):
            doc = self.repo.get_document("random_generated_id")
            self.assertEqual(doc, "received_doc")
