import unittest
from unittest.mock import MagicMock, patch
from src.filters.embedder import VectorEmbedder
from src.domain.entities import SourceDocument, ProcessingPayload, DocumentChunk, DocumentStatus
from src.domain.enums import DocumentType


class TestVectorEmbedder(unittest.TestCase):
    def setUp(self):
        self.doc = SourceDocument(
            id="test-doc",
            filename="test.pdf",
            bucket="test-bucket",
            object_name="test.pdf",
            content_type="application/pdf",
            size_bytes=100,
            status=DocumentStatus.PROCESSING,
            document_type=DocumentType.RECEIVED,
            sender="Sender",
            contract_number="123",
            work_front="A",
            document_date="2024-01-01",
            process="P"
        )
        self.chunks = [
            DocumentChunk(id="c1", document_id="test-doc", subject="Subject 1", body="Body 1", index=0),
            DocumentChunk(id="c2", document_id="test-doc", subject="Subject 2", body="Body 2", index=1)
        ]
        self.payload = ProcessingPayload(document=self.doc, chunks=self.chunks)

    @patch("src.filters.embedder.genai.Client")
    def test_vector_embedder_composite_logic(self, mock_client_class):
        mock_client = mock_client_class.return_value
        
        # Create mock embedding objects
        mock_result1 = MagicMock()
        mock_emb1 = MagicMock()
        mock_emb1.values = [0.1, 0.2, 0.3]
        mock_result1.embeddings = [mock_emb1]

        mock_result2 = MagicMock()
        mock_emb2 = MagicMock()
        mock_emb2.values = [0.4, 0.5, 0.6]
        mock_result2.embeddings = [mock_emb2]
        
        mock_client.models.embed_content.side_effect = [mock_result1, mock_result2]
        
        embedder = VectorEmbedder(api_key="fake-key", model="gemini-embedding-2")
        result = embedder.process(self.payload)
        
        self.assertEqual(mock_client.models.embed_content.call_count, 2)
        self.assertEqual(result.chunks[0].embedding, [0.1, 0.2, 0.3])
        self.assertEqual(result.chunks[1].embedding, [0.4, 0.5, 0.6])

    @patch("src.filters.embedder.genai.Client")
    def test_vector_embedder_empty_chunks(self, mock_client_class):
        mock_client = mock_client_class.return_value
        payload = ProcessingPayload(document=self.doc, chunks=[])
        
        embedder = VectorEmbedder(api_key="fake-key", model="gemini-embedding-2")
        result = embedder.process(payload)
        
        # Should exit early and not call embed_content
        mock_client.models.embed_content.assert_not_called()
        self.assertEqual(result.chunks, [])

    @patch("src.filters.embedder.genai.Client")
    @patch("time.sleep")
    def test_vector_embedder_rate_limit_retry_success(self, mock_sleep, mock_client_class):
        mock_client = mock_client_class.return_value
        
        # 1st call: Rate limit exception
        # 2nd call: Success
        mock_result = MagicMock()
        mock_emb = MagicMock()
        mock_emb.values = [0.9, 0.8, 0.7]
        mock_result.embeddings = [mock_emb]
        
        mock_client.models.embed_content.side_effect = [
            Exception("RESOURCE_EXHAUSTED: Rate limit exceeded 429"),
            mock_result
        ]
        
        # Test only with 1 chunk to simplify tracking side_effect calls
        payload = ProcessingPayload(document=self.doc, chunks=[self.chunks[0]])
        embedder = VectorEmbedder(api_key="fake-key", model="gemini-embedding-2")
        
        result = embedder.process(payload)
        
        self.assertEqual(mock_client.models.embed_content.call_count, 2)
        self.assertEqual(result.chunks[0].embedding, [0.9, 0.8, 0.7])
        mock_sleep.assert_called_once()

    @patch("src.filters.embedder.genai.Client")
    def test_vector_embedder_non_rate_limit_error_fails(self, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client.models.embed_content.side_effect = Exception("403 Forbidden: Invalid API Key")
        
        payload = ProcessingPayload(document=self.doc, chunks=[self.chunks[0]])
        embedder = VectorEmbedder(api_key="fake-key", model="gemini-embedding-2")
        
        with self.assertRaises(Exception):
            embedder.process(payload)

    @patch("src.filters.embedder.genai.Client")
    @patch("time.sleep")
    def test_vector_embedder_rate_limit_exhausted(self, mock_sleep, mock_client_class):
        mock_client = mock_client_class.return_value
        mock_client.models.embed_content.side_effect = Exception("RESOURCE_EXHAUSTED: Rate limit exceeded 429")
        
        payload = ProcessingPayload(document=self.doc, chunks=[self.chunks[0]])
        embedder = VectorEmbedder(api_key="fake-key", model="gemini-embedding-2")
        
        with self.assertRaises(Exception):
            embedder.process(payload)
            
        # Should attempt 5 times (max_retries) and sleep 4 times
        self.assertEqual(mock_client.models.embed_content.call_count, 5)
        self.assertEqual(mock_sleep.call_count, 4)
