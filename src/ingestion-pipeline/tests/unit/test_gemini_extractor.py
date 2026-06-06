from unittest.mock import MagicMock, patch
from src.filters.gemini_extractor import GeminiExtractor, ExtractedContent
from src.domain.entities import SourceDocument, ProcessingPayload, DocumentStatus, DocumentType

@patch("src.filters.gemini_extractor.genai.Client")
def test_gemini_extractor_structured_output(mock_client_class):
    # Setup mock client
    mock_client = mock_client_class.return_value
    
    # Create mock parsed response
    mock_parsed = ExtractedContent(
        subject="Test Subject", 
        body="Test Body Content",
        visual_tabular_data="Test Tabular Data"
    )
    
    mock_response = MagicMock()
    mock_response.parsed = mock_parsed
    
    mock_client.models.generate_content.return_value = mock_response
    
    # Create payload
    doc = SourceDocument(
        id="test-doc",
        filename="scanned.pdf",
        bucket="test-bucket",
        object_name="scanned.pdf",
        content_type="application/pdf",
        size_bytes=100,
        status=DocumentStatus.PROCESSING,
        document_type=DocumentType.RECEIVED,
        work_front="A",
        document_date="2024-01-01",
    )
    
    payload = ProcessingPayload(document=doc, content=b"fake-pdf-content")
    
    extractor = GeminiExtractor(api_key="fake-key", model_name="gemini-3-flash-preview")
    result = extractor.process(payload)
    
    # Verify SDK calls
    mock_client.models.generate_content.assert_called_once()
    args, kwargs = mock_client.models.generate_content.call_args
    
    assert kwargs['model'] == "gemini-3-flash-preview"
    assert kwargs['config'].response_schema == ExtractedContent
    
    # Verify metadata updates
    assert result.document.metadata["extracted_text"] == "Test Body Content\n\n---\n\nTest Tabular Data"
    assert result.document.metadata["document_subject"] == "Test Subject"
    assert result.document.metadata["visual_tabular_data"] == "Test Tabular Data"
