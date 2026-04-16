import pytest
from unittest.mock import MagicMock, patch
from src.filters.embedder import VectorEmbedder
from src.domain.entities import SourceDocument, ProcessingPayload, DocumentChunk, DocumentStatus

@patch("src.filters.embedder.GoogleGenerativeAIEmbeddings")
def test_vector_embedder_composite_logic(mock_embeddings_class):
    # Setup mock
    mock_instance = mock_embeddings_class.return_value
    mock_instance.embed_documents.return_value = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    
    # Create payload with chunks
    doc = SourceDocument(
        id="test-doc",
        filename="test.pdf",
        bucket="test-bucket",
        object_name="test.pdf",
        content_type="application/pdf",
        size_bytes=100,
        status=DocumentStatus.PROCESSING,
        sender="Sender",
        contract_number="123",
        work_front="A",
        document_date="2024-01-01",
        process="P"
    )
    
    chunks = [
        DocumentChunk(id="c1", document_id="test-doc", subject="Subject 1", body="Body 1", index=0),
        DocumentChunk(id="c2", document_id="test-doc", subject="Subject 2", body="Body 2", index=1)
    ]
    
    payload = ProcessingPayload(document=doc, chunks=chunks)
    
    embedder = VectorEmbedder(api_key="fake-key")
    result = embedder.process(payload)
    
    # Verify embed_documents was called with composite text
    expected_texts = [
        "Subject: Subject 1\nBody: Body 1",
        "Subject: Subject 2\nBody: Body 2"
    ]
    mock_instance.embed_documents.assert_called_once_with(expected_texts)
    
    # Verify embeddings were assigned
    assert result.chunks[0].embedding == [0.1, 0.2, 0.3]
    assert result.chunks[1].embedding == [0.4, 0.5, 0.6]
