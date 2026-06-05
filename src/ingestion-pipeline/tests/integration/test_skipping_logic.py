import unittest
from src.domain.factory import SourceDocumentFactory

class TestSkippingLogic(unittest.TestCase):
    def test_skip_received_url_only(self):
        row = {
            "Id borradores": "76857089",
            "Fecha": "26/02/2025",
            "Frente": "Descarga intermedia",
            "Recibidas": "REC_01",
            "url Recibidas": "Sin URL origen",  # Invalid
            "Enviadas": "SENT_01",
            "Ubicacion filtradas": "https://drive.google.com/file/d/2/view"  # Valid
        }
        docs = SourceDocumentFactory.create_documents_from_csv_row(row)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].id, "76857089_SEN")
        self.assertEqual(docs[0].document_type.value, "SENT")

    def test_skip_sent_url_only(self):
        row = {
            "Id borradores": "76857089",
            "Fecha": "26/02/2025",
            "Frente": "Descarga intermedia",
            "Recibidas": "REC_01",
            "url Recibidas": "https://drive.google.com/file/d/1/view",  # Valid
            "Enviadas": "SENT_01",
            "Ubicacion filtradas": "Sin ruta"  # Invalid
        }
        docs = SourceDocumentFactory.create_documents_from_csv_row(row)
        self.assertEqual(len(docs), 1)
        self.assertEqual(docs[0].id, "76857089_REC")
        self.assertEqual(docs[0].document_type.value, "RECEIVED")

    def test_skip_both_urls(self):
        row = {
            "Id borradores": "76857089",
            "Fecha": "26/02/2025",
            "Frente": "Descarga intermedia",
            "Recibidas": "REC_01",
            "url Recibidas": "Sin URL origen",  # Invalid
            "Enviadas": "SENT_01",
            "Ubicacion filtradas": "Sin ruta"  # Invalid
        }
        docs = SourceDocumentFactory.create_documents_from_csv_row(row)
        self.assertEqual(len(docs), 0)
