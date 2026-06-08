"""Unit tests for the RetrieveAndGenerateCommand orchestrator."""

from unittest.mock import MagicMock, patch
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
        metadata={
            "extracted_text": "Body text",
            "document_subject": "Test Subject"
        }
    )
    # Merging metadata if provided in overrides
    if "metadata" in overrides:
        meta = defaults["metadata"].copy()
        meta.update(overrides.pop("metadata"))
        defaults["metadata"] = meta
        
    defaults.update(overrides)
    return SourceDocument(**defaults)


@pytest.fixture
def mock_settings():
    s = MagicMock()
    s.gemini_api_key = "fake"
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
class TestRetrieveAndGenerateCommand:

    def test_full_pipeline_success(
        self, MockEmbedder, MockResponseGen, MockVectorRepo, MockStorage, mock_settings
    ):
        doc = _make_document()

        # Mock document repo
        mock_document_repo = MagicMock()
        mock_document_repo.get_document.return_value = doc
        mock_document_repo.get_document_by_object_name.return_value = doc

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

        cmd = RetrieveAndGenerateCommand(mock_settings, mock_document_repo)
        cmd.vector_search_repo = vector_repo
        cmd.response_generator = response_gen
        cmd._generate_query_embedding = MagicMock(return_value=[0.1] * 768)

        # 1. Test execute with id_documento_recibido
        result = cmd.execute(id_documento_recibido="test-doc")

        assert "docx_bytes" in result
        assert result["similar_count"] == 1
        assert result["sent_count"] == 1
        assert result["subject"] == "Test Subject"
        assert "gcs_url" in result

        mock_document_repo.get_document.assert_called_once_with("test-doc")
        assert mock_document_repo.save_document.call_count == 0

        # 2. Test execute with cod_comunicado_recibido
        mock_document_repo.get_document.reset_mock()
        mock_document_repo.get_document.return_value = None
        mock_document_repo.save_document.reset_mock()

        result = cmd.execute(cod_comunicado_recibido="REC-001")
        mock_document_repo.get_document.assert_not_called()
        mock_document_repo.get_document_by_object_name.assert_called_once_with("REC-001")
        assert mock_document_repo.save_document.call_count == 0

    def test_fails_when_document_not_found(
        self, MockEmbedder, MockResponseGen, MockVectorRepo, MockStorage, mock_settings
    ):
        mock_document_repo = MagicMock()
        mock_document_repo.get_document.return_value = None
        mock_document_repo.get_document_by_object_name.return_value = None

        cmd = RetrieveAndGenerateCommand(mock_settings, mock_document_repo)

        with pytest.raises(ValueError, match="No ingested received document found matching"):
            cmd.execute(id_documento_recibido="nonexistent-id")

    def test_fails_when_extracted_text_missing(
        self, MockEmbedder, MockResponseGen, MockVectorRepo, MockStorage, mock_settings
    ):
        doc = _make_document(metadata={"extracted_text": None})

        mock_document_repo = MagicMock()
        mock_document_repo.get_document.return_value = doc

        cmd = RetrieveAndGenerateCommand(mock_settings, mock_document_repo)

        with pytest.raises(ValueError, match="does not contain extracted_text"):
            cmd.execute(id_documento_recibido="test-doc")

    def test_passes_work_front_to_vector_search(
        self, MockEmbedder, MockResponseGen, MockVectorRepo, MockStorage, mock_settings
    ):
        doc = _make_document(work_front="ACME Front")

        mock_document_repo = MagicMock()
        mock_document_repo.get_document.return_value = doc

        vector_repo = MockVectorRepo.return_value
        vector_repo.find_similar_chunks.return_value = []
        vector_repo.resolve_sent_documents.return_value = {}

        response_gen = MockResponseGen.return_value
        response_gen.generate_response.return_value = "Response"

        mock_gcs = MockStorage.return_value
        mock_gcs.bucket.return_value.blob.return_value = MagicMock()

        cmd = RetrieveAndGenerateCommand(mock_settings, mock_document_repo)
        cmd.vector_search_repo = vector_repo
        cmd.response_generator = response_gen
        cmd._generate_query_embedding = MagicMock(return_value=[0.1] * 768)

        cmd.execute(id_documento_recibido="test-doc")

        call_kwargs = vector_repo.find_similar_chunks.call_args.kwargs
        assert call_kwargs["work_front"] == "ACME Front"
        # Exclusion code should match document.object_name
        assert call_kwargs["codcomunicadorecibido"] == "test.pdf"
