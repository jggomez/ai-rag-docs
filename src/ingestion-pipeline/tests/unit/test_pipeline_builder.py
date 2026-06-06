from unittest.mock import patch, MagicMock
import pytest
from src.domain.enums import DocumentType
from src.usecases.builder import PipelineBuilder
from src.config import Settings

@pytest.fixture
def mock_settings():
    settings = MagicMock(spec=Settings)
    settings.gemini_api_key = "test_key"
    settings.ocr_model = "gemini-3-flash-preview"
    settings.embedding_model = "gemini-embedding-2"
    return settings

@pytest.fixture
def builder(mock_settings):
    return PipelineBuilder(settings=mock_settings)

class TestBuildPipelineForDocument:
    """Verify that build_pipeline_for_document produces the correct filter chain."""

    @patch("src.usecases.builder.GeminiExtractor")
    @patch("src.usecases.builder.DriveDownloader")
    def test_sent_pipeline_contains_pdf_and_cleaner(self, mock_dd, mock_ge, builder):
        """SENT documents must go through PDFReader → DocumentCleaner (no GeminiExtractor)."""
        mock_dd.return_value = MagicMock()
        mock_repo = MagicMock()

        pipeline = builder.build_pipeline_for_document(
            document_type=DocumentType.SENT,
            document_repo=mock_repo,
        )

        filter_types = [type(f).__name__ for f in pipeline._filters]

        assert "PDFReader" in filter_types, "SENT pipeline must include PDFReader"
        assert "DocumentCleaner" in filter_types, "SENT pipeline must include DocumentCleaner"
        mock_ge.assert_not_called()

    @patch("src.usecases.builder.GeminiExtractor")
    @patch("src.usecases.builder.DriveDownloader")
    def test_received_pipeline_contains_gemini_extractor(self, mock_dd, mock_ge, builder):
        """RECEIVED documents must go through GeminiExtractor (no PDFReader or DocumentCleaner)."""
        mock_dd.return_value = MagicMock()
        mock_ge.return_value = MagicMock()
        mock_repo = MagicMock()

        pipeline = builder.build_pipeline_for_document(
            document_type=DocumentType.RECEIVED,
            document_repo=mock_repo,
        )

        filter_types = [type(f).__name__ for f in pipeline._filters]

        mock_ge.assert_called_once()
        assert "PDFReader" not in filter_types, "RECEIVED pipeline must NOT include PDFReader"
        assert "DocumentCleaner" not in filter_types, "RECEIVED pipeline must NOT include DocumentCleaner"

    @patch("src.usecases.builder.GeminiExtractor")
    @patch("src.usecases.builder.DriveDownloader")
    def test_both_pipelines_start_with_drive_downloader(self, mock_dd, mock_ge, builder):
        """Both SENT and RECEIVED pipelines should start with DriveDownloader."""
        mock_dd.return_value = MagicMock()
        mock_ge.return_value = MagicMock()
        mock_repo = MagicMock()

        for doc_type in (DocumentType.SENT, DocumentType.RECEIVED):
            pipeline = builder.build_pipeline_for_document(
                document_type=doc_type,
                document_repo=mock_repo,
            )
            mock_dd.assert_called()
