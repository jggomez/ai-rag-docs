from unittest.mock import MagicMock, patch
from src.filters.embedder import VectorEmbedder
from src.domain.entities import SourceDocument, ProcessingPayload, DocumentChunk, DocumentStatus

@patch("src.filters.embedder.genai.Client")
def test_vector_embedder_composite_logic(mock_client_class):
    # Setup mock client and response
    mock_client = mock_client_class.return_value
    
    # Create mock embedding objects with .values attribute
    mock_result1 = MagicMock()
    mock_emb1 = MagicMock()
    mock_emb1.values = [0.1, 0.2, 0.3]
    mock_result1.embeddings = [mock_emb1]

    mock_result2 = MagicMock()
    mock_emb2 = MagicMock()
    mock_emb2.values = [0.4, 0.5, 0.6]
    mock_result2.embeddings = [mock_emb2]
    
    # Return mock1 for first call, mock2 for second call
    mock_client.models.embed_content.side_effect = [mock_result1, mock_result2]
    
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
    
    embedder = VectorEmbedder(api_key="fake-key", model="gemini-embedding-2")
    result = embedder.process(payload)
    
    # Check that embed_content was called on the models attribute of the client twice (once per chunk)
    assert mock_client.models.embed_content.call_count == 2
    
    # Verify embeddings were assigned
    assert result.chunks[0].embedding == [0.1, 0.2, 0.3]
    assert result.chunks[1].embedding == [0.4, 0.5, 0.6]
