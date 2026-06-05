import unittest
import os
import logging
from google.cloud import firestore

# Skip if Firestore is not reachable or dummy project active
def _firestore_available():
    try:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "devhack-3f0c2")
        if project_id == "dummy-project-id":
            return False
        client = firestore.Client(database="docs-recibidos", project=project_id)
        list(client.collection("documentos_chunks").limit(1).stream())
        return True
    except Exception:
        return False

skip_no_firestore = unittest.skipIf(
    not _firestore_available(),
    "Firestore docs-recibidos not reachable or dummy project active"
)

from src.config import Settings
from src.repositories.document_repo import RoutingFirestoreDocumentRepository
from src.infrastructure.repositories.csv_metadata_repository import (
    CSVMetadataRepository,
)
from src.usecases.builder import PipelineBuilder
from src.usecases.ingest_document import IngestDocumentCommand

logger = logging.getLogger(__name__)

@skip_no_firestore
class TestLiveIngestionIntegration(unittest.TestCase):
    def setUp(self):
        # Determine the CSV path relative to this file
        self.test_csv_path = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__), "../../resources/Comunicaciones_Test.csv"
            )
        )
        self.assertTrue(
            os.path.exists(self.test_csv_path),
            f"Test CSV not found at {self.test_csv_path}",
        )

        self.settings = Settings()
        self.settings.metadata_csv_path = self.test_csv_path

        self.document_repo = RoutingFirestoreDocumentRepository(
            database_received=self.settings.firestore_database_received,
            database_sent=self.settings.firestore_database_sent,
        )
        self.pipeline_builder = PipelineBuilder(self.settings)
        self.csv_repo = CSVMetadataRepository(self.test_csv_path)

    def test_live_batch_ingestion_and_routing(self):
        """
        Runs the complete live batch ingestion process on real GCP Firestore and Gemini API
        and asserts Spanish schemas, document status, dual URLs and correct routing database.
        """
        # Clean up all documents and chunks from previous test runs to avoid stale data
        logger.info("Cleaning up all documents and chunks from previous test runs")
        for repo in [self.document_repo.received_repo, self.document_repo.sent_repo]:
            # Delete all documents in "documentos"
            docs_query = repo.docs_collection.stream()
            for doc_snap in docs_query:
                doc_snap.reference.delete()
            
            # Delete all chunks in "documentos_chunks"
            chunks_query = repo.chunks_collection.stream()
            for chunk_snap in chunks_query:
                chunk_snap.reference.delete()

        logger.info("Starting live batch ingestion from test CSV")
        ingest_command = IngestDocumentCommand(
            document_repo=self.document_repo, pipeline_builder=self.pipeline_builder
        )

        # 1. Run live ingestion
        result = ingest_command.execute_batch(self.csv_repo)
        self.assertEqual(
            result["failed_records"], 0, f"Some records failed ingestion: {result}"
        )
        self.assertEqual(
            result["processed_records"],
            6,
            f"Expected 6 documents to be processed, got {result['processed_records']}",
        )

        # 2. Assert and verify saved documents inside real Firestore instances
        received_docs = [d.to_dict() for d in self.document_repo.received_repo.docs_collection.stream()]
        sent_docs = [d.to_dict() for d in self.document_repo.sent_repo.docs_collection.stream()]
        all_docs = received_docs + sent_docs

        self.assertEqual(len(all_docs), 6, f"Expected 6 documents in total, found {len(all_docs)}")

        for raw_dict in all_docs:
            doc_id = raw_dict.get("id")
            self.assertIsNotNone(doc_id, "Document must have an ID")
            # Verify Firestore generated ID has no custom suffix like _REC or _SEN in the Firestore ID itself
            self.assertFalse(doc_id.endswith("_REC") or doc_id.endswith("_SEN"), f"ID {doc_id} should be Firestore-generated and not contain legacy suffix")

            # Spanish Main Schema Keys
            self.assertIn("nombre_archivo", raw_dict, "Missing Spanish key: nombre_archivo")
            self.assertIn("creado_en", raw_dict, "Missing Spanish key: creado_en")
            self.assertIn("estado", raw_dict, "Missing Spanish key: estado")
            self.assertEqual(
                raw_dict["estado"],
                "COMPLETADO",
                f"Status should be COMPLETADO, got {raw_dict['estado']}",
            )

            # Assert complete omission of nested dictionaries and unsought properties
            self.assertNotIn("metadatos_ingenieria", raw_dict)
            self.assertNotIn("metadatos", raw_dict)
            self.assertNotIn("bucket", raw_dict)
            self.assertNotIn("url_enviado", raw_dict)
            self.assertNotIn("actualizado_en", raw_dict)

            # Spanish Engineering Metadata Keys flat at the root
            es_meta_keys = [
                "remitente",
                "numero_contrato",
                "frente_trabajo",
                "fecha_documento",
                "proceso",
                "url_archivo_respuesta",
            ]
            for key in es_meta_keys:
                self.assertIn(key, raw_dict, f"Missing flat Spanish key: {key}")
                self.assertIsNotNone(raw_dict.get(key), f"Value for {key} should not be None")

            # Spanish Custom/Gemini Metadata Keys flat at the root
            self.assertIn("texto_extraido", raw_dict, "Missing flat Spanish key: texto_extraido")
            self.assertIsNotNone(raw_dict.get("texto_extraido"), "texto_extraido should not be None")

            # Assert Dual URLs are present in Spanish
            self.assertIn("url_recibido", raw_dict, "Missing Spanish key: url_recibido")
            self.assertIn("url_origen", raw_dict, "Missing Spanish key: url_origen")

            # Determine routing database
            is_received = raw_dict.get("tipo_documento") == "RECIBIDO"
            inner_repo = self.document_repo.received_repo if is_received else self.document_repo.sent_repo
            expected_db = (
                self.settings.firestore_database_received
                if is_received
                else self.settings.firestore_database_sent
            )
            self.assertEqual(
                inner_repo.client._database,
                expected_db,
                f"Document routed to wrong database: expected {expected_db}",
            )

            # Verify saved chunks inside the correct database
            chunks_query = inner_repo.chunks_collection.where(
                "id_documento", "==", doc_id
            ).stream()
            chunks_list = [c.to_dict() for c in chunks_query]

            # Since we downloaded files successfully, we should have generated chunks
            self.assertGreater(
                len(chunks_list), 0, f"No chunks were saved for document {doc_id}"
            )

            for chunk_dict in chunks_list:
                self.assertIn("id", chunk_dict)
                self.assertIn("id_documento", chunk_dict)
                self.assertEqual(chunk_dict["id_documento"], doc_id)
                self.assertIn("texto", chunk_dict)

                # Check unified text properties - should not contain old keys
                self.assertNotIn("asunto", chunk_dict)
                self.assertNotIn("contenido", chunk_dict)

                # Verify that redundant index 'indice' does not exist in the chunk
                self.assertNotIn("indice", chunk_dict)
                self.assertIn("archivo_enviado", chunk_dict)

                # Verify that metadatos_ingenieria does not exist in the chunk (it is flattened to the root)
                self.assertNotIn("metadatos_ingenieria", chunk_dict)
                
                # Verify that all parent engineering metadata fields are flat on the root
                for k in es_meta_keys:
                    self.assertIn(k, chunk_dict)
                    self.assertEqual(chunk_dict[k], raw_dict[k])
                
                # Verify that the flat index 'indice_chunk' is present on the root
                self.assertIn("indice_chunk", chunk_dict)

                # Dual URLs in chunks
                self.assertIn("url_origen", chunk_dict)
                self.assertIn("url_recibido", chunk_dict)
                self.assertEqual(chunk_dict["url_origen"], raw_dict["url_origen"])
                self.assertEqual(chunk_dict["url_recibido"], raw_dict["url_recibido"])

                # Embedding vector presence
                self.assertIn("vector", chunk_dict)


if __name__ == "__main__":
    unittest.main()
