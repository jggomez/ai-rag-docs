"""Unit tests for ResponseGenerator.

Tests the prompt formatting and Gemini API interaction.
All API calls are mocked.
"""

from unittest.mock import MagicMock, patch
import pytest

from src.usecases.response_generator import ResponseGenerator


@pytest.fixture
def generator():
    """Creates a ResponseGenerator with mocked Gemini client."""
    with patch("src.usecases.response_generator.genai.Client") as mock_client_class:
        gen = ResponseGenerator(api_key="fake-key", model_name="gemini-2.5-flash")
        mock_client = mock_client_class.return_value

        # Default mock response
        mock_response = MagicMock()
        mock_response.text = "Estimado señor, en respuesta a su comunicación..."
        mock_client.models.generate_content.return_value = mock_response

        yield gen, mock_client


class TestResponseGenerator:
    """Test the Gemini-powered response text generation."""

    def test_generates_response_text(self, generator):
        gen, mock_client = generator
        result = gen.generate_response(
            received_subject="Informe de avance",
            received_body="Se presenta el informe mensual...",
            similar_chunks=[{"texto": "Chunk similar", "id_borrador": "123"}],
            sent_texts={"123": {"texto": "Acusamos recibo de su comunicación...", "filename": "SENT-001"}},
            metadata={"contract_number": "CW-276532", "sender": "CYS"},
        )
        assert len(result) > 0
        assert "Estimado" in result
        mock_client.models.generate_content.assert_called_once()

    def test_prompt_contains_received_document_context(self, generator):
        gen, mock_client = generator
        gen.generate_response(
            received_subject="Planos de taller",
            received_body="Se adjuntan planos...",
            similar_chunks=[],
            sent_texts={},
            metadata={"contract_number": "CW-001"},
        )
        prompt = mock_client.models.generate_content.call_args.kwargs["contents"]
        assert "Planos de taller" in prompt
        assert "Se adjuntan planos" in prompt

    def test_prompt_contains_metadata(self, generator):
        gen, mock_client = generator
        gen.generate_response(
            received_subject="Test",
            received_body="Body",
            similar_chunks=[],
            sent_texts={},
            metadata={"contract_number": "CW-276532", "sender": "ACME", "work_front": "Descarga"},
        )
        prompt = mock_client.models.generate_content.call_args.kwargs["contents"]
        assert "CW-276532" in prompt
        assert "ACME" in prompt
        assert "Descarga" in prompt

    def test_uses_configured_model(self, generator):
        gen, mock_client = generator
        gen.generate_response(
            received_subject="S", received_body="B",
            similar_chunks=[], sent_texts={}, metadata={},
        )
        call_kwargs = mock_client.models.generate_content.call_args.kwargs
        assert call_kwargs["model"] == "gemini-2.5-flash"

    def test_format_similar_chunks_empty(self, generator):
        gen, _ = generator
        result = gen._format_similar_chunks([])
        assert "No similar previous communications were found." in result

    def test_format_similar_chunks_numbered(self, generator):
        gen, _ = generator
        chunks = [
            {"texto": "First chunk", "id_borrador": "A"},
            {"texto": "Second chunk", "id_borrador": "B"},
        ]
        result = gen._format_similar_chunks(chunks)
        assert "#1" in result
        assert "#2" in result
        assert "First chunk" in result

    def test_format_sent_texts_empty(self, generator):
        gen, _ = generator
        result = gen._format_sent_texts({})
        assert "No previous sent response letters were found for reference." in result

    def test_format_sent_texts_with_content(self, generator):
        gen, _ = generator
        texts = {
            "draft_1": {"texto": "Carta enviada texto", "filename": "SENT-01"},
            "draft_2": {"texto": "Otra carta", "filename": "SENT-02"}
        }
        result = gen._format_sent_texts(texts)
        assert "Carta enviada texto" in result
        assert "Otra carta" in result
        assert "SENT-01" in result
