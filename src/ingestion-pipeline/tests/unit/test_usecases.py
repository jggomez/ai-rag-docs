import unittest
from unittest.mock import MagicMock, patch
from src.usecases.ingest_document import IngestDocumentCommand
from src.domain.enums import DocumentType

class TestIngestDocumentCommand(unittest.TestCase):
    def setUp(self):
        self.doc_repo = MagicMock()
        self.builder = MagicMock()
        self.command = IngestDocumentCommand(self.doc_repo, self.builder)

    @patch("src.usecases.ingest_document.SourceDocumentFactory")
    def test_execute_batch(self, mock_factory):
        # Setup mock repo
        mock_repo = MagicMock()
        mock_repo.get_all_rows.return_value = [
            {"Enviadas": "File1", "Para": "User1"},
            {"recibidas_url": "Url2", "Para": "User2"}
        ]
        
        # Setup mock factory to return documents with types
        doc1 = MagicMock()
        doc1.document_type = DocumentType.SENT
        doc1.id = "ID1"
        
        doc2 = MagicMock()
        doc2.document_type = DocumentType.RECEIVED
        doc2.id = "ID2"
        
        mock_factory.create_documents_from_csv_row.side_effect = [[doc1], [doc2]]
        
        # Setup mock builder (already in self.builder)
        mock_pipeline = MagicMock()
        self.builder.build_pipeline_for_document.return_value = mock_pipeline
        
        # Execute
        with patch.object(self.command, "_run_pipeline") as mock_run:
            result = self.command.execute_batch(mock_repo)
            
            # Assertions
            self.assertEqual(result["processed_records"], 2)
            self.assertEqual(result["total_records"], 2)
            self.assertEqual(mock_run.call_count, 2)
            
            # Verify factory calls
            self.assertEqual(mock_factory.create_documents_from_csv_row.call_count, 2)
            
            # Verify builder was called for each type
            self.builder.build_pipeline_for_document.assert_any_call(
                document_type=DocumentType.SENT,
                document_repo=self.doc_repo
            )
            self.builder.build_pipeline_for_document.assert_any_call(
                document_type=DocumentType.RECEIVED,
                document_repo=self.doc_repo
            )

    def test_execute_csv_row(self):
        # Setup
        row_data = {"Para": "User", "Descripcion": "Test", "Enviadas": "File"}
        mock_pipeline = MagicMock()
        
        # Configure the mock pipeline to return the payload it receives
        def mock_execute(payload):
            return payload
        mock_pipeline.execute.side_effect = mock_execute
        
        # Execute
        docs = self.command.execute_csv_row(row_data, mock_pipeline)
        
        # Assertions
        self.assertIsNotNone(docs)
        self.assertEqual(len(docs), 1)
        doc = docs[0]
        self.assertEqual(doc.filename, "File")
        mock_pipeline.execute.assert_called_once()

if __name__ == "__main__":
    unittest.main()
