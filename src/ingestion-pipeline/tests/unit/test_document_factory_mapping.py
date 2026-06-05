import unittest
from src.domain.factory import SourceDocumentFactory

class TestDocumentFactoryMapping(unittest.TestCase):
    def test_factory_mapping_with_valid_metadata(self):
        row = {
            "Id borradores": "76857089",
            "Fecha": "26/02/2025",
            "Frente": "Descarga intermedia",
            "Recibidas": "REC_01",
            "url Recibidas": "https://drive.google.com/file/d/1/view",
            "Enviadas": "SENT_01",
            "Ubicacion filtradas": "https://drive.google.com/file/d/2/view"
        }
        docs = SourceDocumentFactory.create_documents_from_csv_row(row)
        self.assertEqual(len(docs), 2)
        
        rec_doc = next(d for d in docs if d.id.endswith("_REC"))
        self.assertEqual(rec_doc.draft_id, "76857089")
        self.assertEqual(rec_doc.document_date, "26/02/2025")
        self.assertEqual(rec_doc.work_front, "Descarga intermedia")
        self.assertEqual(rec_doc.sender, "UNKNOWN")
        self.assertEqual(rec_doc.contract_number, "UNKNOWN")
        self.assertEqual(rec_doc.process, "UNKNOWN")
        self.assertEqual(rec_doc.source_url, "https://drive.google.com/file/d/1/view")
        self.assertEqual(rec_doc.response_file_url, "SENT_01")

        sent_doc = next(d for d in docs if d.id.endswith("_SEN"))
        self.assertEqual(sent_doc.draft_id, "76857089")
        self.assertEqual(sent_doc.document_date, "26/02/2025")
        self.assertEqual(sent_doc.work_front, "Descarga intermedia")
        self.assertEqual(sent_doc.source_url, "https://drive.google.com/file/d/2/view")
        self.assertEqual(sent_doc.response_file_url, None)

    def test_factory_mapping_fallbacks_for_empty_fields(self):
        row = {
            "Id borradores": "",  # Empty ID
            "Fecha": "",          # Empty Fecha
            "Frente": "",         # Empty Frente
            "Recibidas": "REC_01",
            "url Recibidas": "https://drive.google.com/file/d/1/view",
            "Enviadas": "SENT_01",
            "Ubicacion filtradas": "https://drive.google.com/file/d/2/view"
        }
        docs = SourceDocumentFactory.create_documents_from_csv_row(row)
        self.assertEqual(len(docs), 2)

        for doc in docs:
            self.assertIsNotNone(doc.draft_id)
            self.assertNotEqual(doc.draft_id, "")
            # ID must be generated (should match the MD5 hash)
            self.assertEqual(len(doc.draft_id), 32)
            self.assertEqual(doc.document_date, "UNKNOWN")
            self.assertEqual(doc.work_front, "GENERAL")
