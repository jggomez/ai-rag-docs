"""Functional tests for LLM OCR layout preservation.

These tests mock the Gemini API to verify that the GeminiExtractor
correctly stores table/image-descriptive text into the payload metadata.
"""

import json
from unittest.mock import MagicMock, patch


from src.domain.entities import ProcessingPayload, SourceDocument, EngineeringMetadata
from src.domain.enums import DocumentType
from src.filters.gemini_extractor import GeminiExtractor


def _make_received_payload(content: bytes = b"fake-image-bytes") -> ProcessingPayload:
    """Helper to create a RECEIVED document payload."""
    doc = SourceDocument(
        id="func-test-001",
        filename="scanned_letter.pdf",
        bucket="LOCAL_CSV",
        object_name="func-test-001",
        content_type="application/pdf",
        size_bytes=len(content),
        engineering_metadata=EngineeringMetadata(
            sender="External Corp",
            contract_number="CTR-FUNC",
            work_front="TESTING",
            document_date="2026-04-01",
            process="QA",
        ),
        document_type=DocumentType.RECEIVED,
        source_url="https://drive.google.com/file/d/FAKE_ID/view",
    )
    return ProcessingPayload(document=doc, content=content)


class TestLLMOCRLayoutPreservation:
    """Verify that Gemini OCR output is correctly parsed and stored."""

    @patch("src.filters.gemini_extractor.genai.Client")
    def test_tables_rendered_as_list_items(self, mock_client_class):
        """Tables in the scanned doc should appear as list items in visual_tabular_data."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        gemini_response = json.dumps({
            "subject": "Monthly Progress Report",
            "body": "Dear Team, see details below.",
            "visual_tabular_data": (
                "- Item 1: Foundation work — 95% complete\n"
                "- Item 2: Electrical installation — 60% complete\n"
                "- Item 3: Plumbing — 30% complete"
            )
        })
        
        # Mock the response object to have a 'parsed' attribute if needed, 
        # but the current GeminiExtractor implementation might expect a string if not using Pydantic output.
        # Actually, in structured output, result.parsed contains the object.
        mock_response = MagicMock()
        mock_response.parsed = MagicMock(
            subject="Monthly Progress Report",
            body="Dear Team, see details below.",
            visual_tabular_data="- Item 1: Foundation work — 95% complete\n- Item 2: Electrical installation — 60% complete\n- Item 3: Plumbing — 30% complete"
        )
        mock_client.models.generate_content.return_value = mock_response

        extractor = GeminiExtractor(api_key="test-key", model_name="gemini-2.0-flash")

        payload = _make_received_payload()
        result = extractor.process(payload)

        tabular = result.document.metadata.get("visual_tabular_data", "")
        assert "- Item 1:" in tabular
        assert result.document.metadata["document_subject"] == "Monthly Progress Report"

    @patch("src.filters.gemini_extractor.genai.Client")
    def test_images_described_in_body(self, mock_client_class):
        """Images in scanned documents should be described in visual_tabular_data."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        
        mock_response = MagicMock()
        mock_response.parsed = MagicMock(
            subject="Site Inspection Report",
            body="The inspection concluded with no major findings.",
            visual_tabular_data="Photo 1: Aerial view of the construction site."
        )
        mock_client.models.generate_content.return_value = mock_response

        extractor = GeminiExtractor(api_key="test-key", model_name="gemini-2.0-flash")

        payload = _make_received_payload()
        result = extractor.process(payload)

        tabular = result.document.metadata.get("visual_tabular_data", "")
        assert "Aerial view" in tabular
        assert "Site Inspection Report" == result.document.metadata["document_subject"]

    @patch("src.filters.gemini_extractor.genai.Client")
    def test_empty_content_is_noop(self, mock_client_class):
        """If there is no binary content the extractor should return the payload unchanged."""
        extractor = GeminiExtractor(api_key="test-key", model_name="gemini-2.0-flash")

        payload = _make_received_payload(content=b"")
        payload.content = None

        result = extractor.process(payload)
        assert result.document.metadata.get("visual_tabular_data") is None
