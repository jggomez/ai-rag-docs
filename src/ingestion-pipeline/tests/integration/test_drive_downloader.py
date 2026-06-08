"""Integration tests for DriveDownloader filter."""

from unittest.mock import MagicMock, patch


from src.domain.entities import ProcessingPayload, SourceDocument
from src.domain.enums import DocumentStatus, DocumentType
from src.filters.drive_downloader import DriveDownloader, extract_drive_file_id


# ---------------------------------------------------------------------------
# Unit helper: URL parsing
# ---------------------------------------------------------------------------

class TestExtractDriveFileId:
    """Validate Drive URL → file-ID extraction for common formats."""

    def test_standard_view_url(self):
        url = "https://drive.google.com/file/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ012345/view?usp=sharing"
        assert extract_drive_file_id(url) == "1aBcDeFgHiJkLmNoPqRsTuVwXyZ012345"

    def test_open_id_url(self):
        url = "https://drive.google.com/open?id=1aBcDeFgHiJkLmNoPqRsTuVwXyZ012345"
        assert extract_drive_file_id(url) == "1aBcDeFgHiJkLmNoPqRsTuVwXyZ012345"

    def test_invalid_url_returns_none(self):
        assert extract_drive_file_id("https://example.com/file.pdf") is None

    def test_empty_string_returns_none(self):
        assert extract_drive_file_id("") is None


# ---------------------------------------------------------------------------
# Integration: DriveDownloader with mocked Google API
# ---------------------------------------------------------------------------

def _make_payload(source_url: str = None, doc_type: DocumentType = DocumentType.RECEIVED) -> ProcessingPayload:
    """Helper to build a minimal ProcessingPayload."""
    
    doc = SourceDocument(
        id="test-doc-001",
        filename="test.pdf",
        bucket="LOCAL_CSV",
        object_name="test-doc-001",
        content_type="application/pdf",
        size_bytes=0,
        sender="TESTS",
        contract_number="CTR-001",
        work_front="TEST",
        document_date="2026-01-01",
        process="TEST",
        document_type=doc_type,
        source_url=source_url,
    )
    return ProcessingPayload(document=doc)


class TestDriveDownloaderIntegration:
    """Tests that DriveDownloader correctly delegates to the Google API client."""

    @patch("google.cloud.storage.Client")
    @patch("src.filters.drive_downloader.MediaIoBaseDownload")
    @patch("src.filters.drive_downloader.build")
    @patch("src.infrastructure.auth.google_drive.service_account")
    def test_downloads_file_successfully(self, mock_sa, mock_build, mock_dl_cls, mock_gcs_client):
        """Given a valid Drive URL, the filter downloads the binary content."""
        # Arrange: mock GCS Storage Client
        mock_gcs = mock_gcs_client.return_value
        mock_gcs.bucket.return_value.list_blobs.return_value = []

        # Arrange: mock credentials
        mock_sa.Credentials.from_service_account_file.return_value = MagicMock()

        # Arrange: mock Drive service
        fake_content = b"%PDF-1.4 fake content"
        mock_service = MagicMock()
        mock_build.return_value = mock_service

        # Mock files().get() for metadata
        mock_service.files.return_value.get.return_value.execute.return_value = {
            "name": "downloaded.pdf",
            "mimeType": "application/pdf",
            "size": str(len(fake_content)),
        }

        # Mock files().get_media() for content download
        mock_request = MagicMock()
        mock_service.files.return_value.get_media.return_value = mock_request

        # Simulate MediaIoBaseDownload behaviour
        mock_downloader = MagicMock()
        mock_dl_cls.return_value = mock_downloader
        mock_downloader.next_chunk.return_value = (None, True)

        downloader = DriveDownloader(service_account_path="/fake/sa.json")

        payload = _make_payload(
            source_url="https://drive.google.com/file/d/1aBcDeFgHiJkLmNoPqRsTuVwXyZ012345/view"
        )

        # Act
        result = downloader.process(payload)

        # Assert
        assert result.document.filename == "downloaded"
        assert result.document.content_type == "application/pdf"

    @patch("src.filters.drive_downloader.build")
    def test_skips_when_no_source_url(self, mock_build):
        """If there is no source_url the filter is a no-op."""
        downloader = DriveDownloader.__new__(DriveDownloader)
        downloader._service = MagicMock()

        payload = _make_payload(source_url=None)
        result = downloader.process(payload)

        assert result.content is None
        mock_build.assert_not_called

    @patch("src.filters.drive_downloader.build")
    def test_fails_on_invalid_drive_url(self, mock_build):
        """An unparseable URL marks the document as FAILED."""
        downloader = DriveDownloader.__new__(DriveDownloader)
        downloader._service = MagicMock()

        payload = _make_payload(source_url="https://example.com/not-drive")
        result = downloader.process(payload)

        assert result.document.status == DocumentStatus.FAILED
        assert "Invalid Drive URL" in result.document.metadata.get("error", "")
