"""Unit tests for the RetrieveAndGenerateCommand orchestrator."""

from unittest.mock import MagicMock, patch, PropertyMock
import pytest
from src.usecases.retrieve_and_generate import RetrieveAndGenerateCommand
from src.domain.entities import SourceDocument
from src.domain.enums import DocumentStatus, DocumentType


def _make_document(**overrides):
    defaults = dict(
        id="test-doc", filename="test.pdf", bucket="B",
        object_name="test.pdf", content_type="application/pdf",
        size_bytes=0, status=DocumentStatus.PENDING,
        document_type=DocumentType.RECEIVED,
        source_url="https://drive.google.com/file/d/FAKE/view",
        work_front="Descarga", document_date="2025-02-26",
        draft_id="76857089",
    )
    defaults.update(overrides)
    return SourceDocument(**defaults)


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.gemini_api_key = "fake"
    s.ocr_model = "gemini-3-flash-preview"
    s.embedding_model = "gemini-embedding-2"
    s.generation_model = "gemini-3-flash-preview"
    s.firestore_database_received = "docs-recibidos"
    s.firestore_database_sent = "docs-enviados"
    s.gcs_output_bucket = "test-bucket"
    s.gcs_output_prefix = "output"
    return s


@patch("src.usecases.retrieve_and_generate.storage.Client")
@patch("src.usecases.retrieve_and_generate.FirestoreVectorSearchRepository")
@patch("src.usecases.retrieve_and_generate.ResponseGenerator")
@patch("src.usecases.retrieve_and_generate.VectorEmbedder")
@patch("src.usecases.retrieve_and_generate.GeminiExtractor")
@patch("src.usecases.retrieve_and_generate.DriveDownloader")
class TestRetrieveAndGenerateCommand:

    def test_full_pipeline_success(
        self, MockDownloader, MockExtractor, MockEmbedder,
        MockResponseGen, MockVectorRepo, MockStorage, mock_settings
    ):
        doc = _make_document()

        # Mock downloader
        downloader = MockDownloader.return_value
        def download_side_effect(payload):
            payload.document.metadata["extracted_text"] = "Body text"
            payload.document.metadata["document_subject"] = "Test Subject"
            payload.content = b"pdf-bytes"
            return payload
        downloader.process.side_effect = download_side_effect

        # Mock extractor
        extractor = MockExtractor.return_value
        extractor.process.side_effect = lambda p: p  # No-op, already set by downloader

        # Mock vector repo
        vector_repo = MockVectorRepo.return_value
        vector_repo.find_similar_chunks.return_value = [
            {"texto": "Similar chunk", "id_borrador": "76857089"}
        ]
        vector_repo.resolve_sent_documents.return_value = {
            "76857089": {"texto": "Sent doc text", "filename": "SENT-001"}
        }

        # Mock response generator
        response_gen = MockResponseGen.return_value
        response_gen.generate_response.return_value = "Generated response text"

        # Mock GCS upload
        mock_gcs = MockStorage.return_value
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_gcs.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        cmd = RetrieveAndGenerateCommand(mock_settings)
        cmd.downloader = downloader
        cmd.extractor = extractor
        cmd.vector_search_repo = vector_repo
        cmd.response_generator = response_gen
        cmd._generate_query_embedding = MagicMock(return_value=[0.1] * 768)

        result = cmd.execute(doc)

        assert "pdf_bytes" in result
        assert result["similar_count"] == 1
        assert result["sent_count"] == 1
        assert result["subject"] == "Test Subject"
        assert "gcs_url" in result

    def test_fails_on_download_error(
        self, MockDownloader, MockExtractor, MockEmbedder,
        MockResponseGen, MockVectorRepo, MockStorage, mock_settings
    ):
        doc = _make_document()

        downloader = MockDownloader.return_value
        def fail_download(payload):
            payload.document.status = DocumentStatus.FAILED
            payload.document.metadata["error"] = "403 Forbidden"
            return payload
        downloader.process.side_effect = fail_download

        cmd = RetrieveAndGenerateCommand(mock_settings)
        cmd.downloader = downloader

        with pytest.raises(ValueError, match="Failed to download"):
            cmd.execute(doc)

    def test_fails_on_empty_ocr(
        self, MockDownloader, MockExtractor, MockEmbedder,
        MockResponseGen, MockVectorRepo, MockStorage, mock_settings
    ):
        doc = _make_document()

        downloader = MockDownloader.return_value
        downloader.process.side_effect = lambda p: p  # No metadata set
        extractor = MockExtractor.return_value
        extractor.process.side_effect = lambda p: p

        cmd = RetrieveAndGenerateCommand(mock_settings)
        cmd.downloader = downloader
        cmd.extractor = extractor

        with pytest.raises(ValueError, match="no text content"):
            cmd.execute(doc)

    def test_passes_work_front_to_vector_search(
        self, MockDownloader, MockExtractor, MockEmbedder,
        MockResponseGen, MockVectorRepo, MockStorage, mock_settings
    ):
        doc = _make_document(work_front="ACME Front")

        downloader = MockDownloader.return_value
        def setup_payload(payload):
            payload.document.metadata["extracted_text"] = "Text"
            payload.document.metadata["document_subject"] = "Sub"
            return payload
        downloader.process.side_effect = setup_payload
        extractor = MockExtractor.return_value
        extractor.process.side_effect = lambda p: p

        vector_repo = MockVectorRepo.return_value
        vector_repo.find_similar_chunks.return_value = []
        vector_repo.resolve_sent_documents.return_value = {}

        response_gen = MockResponseGen.return_value
        response_gen.generate_response.return_value = "Response"

        mock_gcs = MockStorage.return_value
        mock_gcs.bucket.return_value.blob.return_value = MagicMock()

        cmd = RetrieveAndGenerateCommand(mock_settings)
        cmd.downloader = downloader
        cmd.extractor = extractor
        cmd.vector_search_repo = vector_repo
        cmd.response_generator = response_gen
        cmd._generate_query_embedding = MagicMock(return_value=[0.1] * 768)

        cmd.execute(doc)

        call_kwargs = vector_repo.find_similar_chunks.call_args.kwargs
        assert call_kwargs["work_front"] == "ACME Front"
