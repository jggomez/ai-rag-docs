import unittest
import io
import urllib.error
from unittest.mock import MagicMock, patch, call
from googleapiclient.errors import HttpError
import httplib2
from src.filters.drive_downloader import DriveDownloader, extract_drive_file_id
from src.domain.entities import SourceDocument, ProcessingPayload, DocumentStatus
from src.domain.enums import DocumentType


class TestDriveDownloaderSadPaths(unittest.TestCase):
    def setUp(self):
        self.doc = SourceDocument(
            id="test",
            filename="test.pdf",
            bucket="b",
            object_name="test.pdf",
            content_type="application/pdf",
            size_bytes=0,
            status=DocumentStatus.PENDING,
            document_type=DocumentType.SENT,
            source_url="https://drive.google.com/file/d/123456789012345678901234567890/view",
            sender="S", contract_number="C", work_front="W", document_date="D", process="P"
        )
        self.payload = ProcessingPayload(document=self.doc)

    @patch.object(DriveDownloader, '_try_public_download', return_value=None)
    @patch("src.filters.drive_downloader.load_drive_credentials")
    @patch("src.filters.drive_downloader.build")
    def test_download_403_forbidden(self, mock_build, mock_creds, mock_public):
        mock_creds.return_value = MagicMock()
        mock_service = MagicMock()
        mock_files = MagicMock()
        mock_get = MagicMock()
        
        resp = httplib2.Response({"status": 403})
        mock_get.execute.side_effect = HttpError(resp, b"Forbidden")
        
        mock_files.get.return_value = mock_get
        mock_service.files.return_value = mock_files
        mock_build.return_value = mock_service

        downloader = DriveDownloader()
        
        with self.assertRaises(HttpError):
            downloader.process(self.payload)

    @patch.object(DriveDownloader, '_try_public_download', return_value=None)
    @patch("src.filters.drive_downloader.load_drive_credentials")
    @patch("src.filters.drive_downloader.build")
    def test_download_404_not_found(self, mock_build, mock_creds, mock_public):
        mock_creds.return_value = MagicMock()
        mock_service = MagicMock()
        mock_files = MagicMock()
        mock_get = MagicMock()
        
        resp = httplib2.Response({"status": 404})
        mock_get.execute.side_effect = HttpError(resp, b"Not Found")
        
        mock_files.get.return_value = mock_get
        mock_service.files.return_value = mock_files
        mock_build.return_value = mock_service

        downloader = DriveDownloader()

        with self.assertRaises(HttpError):
            downloader.process(self.payload)

    def test_invalid_drive_url(self):
        downloader = DriveDownloader()
        self.payload.document.source_url = "https://example.com/not-a-drive-url"
        
        result = downloader.process(self.payload)
        self.assertEqual(result.document.status, DocumentStatus.FAILED)
        self.assertIn("Invalid Drive URL", result.document.metadata["error"])

    # --- 1. GCS URL testing ---
    @patch("google.cloud.storage.Client")
    def test_gcs_download_gs_prefix_success(self, mock_storage_client):
        self.payload.document.source_url = "gs://my-bucket/documents/paper.pdf"
        
        mock_client = mock_storage_client.return_value
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.download_as_bytes.return_value = b"gcs-pdf-content"
        mock_blob.content_type = "application/pdf"
        
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        downloader = DriveDownloader()
        result = downloader.process(self.payload)

        self.assertEqual(result.content, b"gcs-pdf-content")
        self.assertEqual(result.document.filename, "paper.pdf")
        self.assertEqual(result.document.content_type, "application/pdf")
        self.assertEqual(result.document.status, DocumentStatus.DOWNLOADING)
        mock_client.bucket.assert_called_with("my-bucket")
        mock_bucket.blob.assert_called_with("documents/paper.pdf")

    def test_gcs_download_invalid_gs_url(self):
        self.payload.document.source_url = "gs://invalid-no-slashes"
        downloader = DriveDownloader()
        result = downloader.process(self.payload)
        self.assertEqual(result.document.status, DocumentStatus.FAILED)
        self.assertIn("Invalid GCS URL", result.document.metadata["error"])

    @patch("google.cloud.storage.Client")
    def test_gcs_download_https_pattern(self, mock_storage_client):
        self.payload.document.source_url = "https://storage.googleapis.com/my-bucket-name/folder/image.png"
        
        mock_client = mock_storage_client.return_value
        mock_bucket = MagicMock()
        mock_blob = MagicMock()
        mock_blob.download_as_bytes.return_value = b"image-content"
        mock_blob.content_type = "image/png"
        
        mock_client.bucket.return_value = mock_bucket
        mock_bucket.blob.return_value = mock_blob

        downloader = DriveDownloader()
        result = downloader.process(self.payload)

        self.assertEqual(result.content, b"image-content")
        self.assertEqual(result.document.filename, "image.png")
        self.assertEqual(result.document.content_type, "image/png")

    @patch("google.cloud.storage.Client")
    def test_gcs_download_exception(self, mock_storage_client):
        self.payload.document.source_url = "gs://my-bucket/paper.pdf"
        mock_storage_client.side_effect = Exception("Auth Failure")

        downloader = DriveDownloader()
        result = downloader.process(self.payload)
        self.assertEqual(result.document.status, DocumentStatus.FAILED)
        self.assertIn("Error downloading from GCS", result.document.metadata["error"])

    # --- 2. Public Google Drive Download ---
    @patch("urllib.request.urlopen")
    @patch("urllib.request.Request")
    def test_public_drive_download_success(self, mock_request, mock_urlopen):
        mock_response = MagicMock()
        mock_response.read.return_value = b"public-pdf-data"
        mock_response.headers = {
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="public_doc.pdf"'
        }
        mock_urlopen.return_value.__enter__.return_value = mock_response

        downloader = DriveDownloader()
        result = downloader._try_public_download(self.payload, "file_id_123")

        self.assertIsNotNone(result)
        self.assertEqual(result.content, b"public-pdf-data")
        self.assertEqual(result.document.filename, "public_doc.pdf")
        self.assertEqual(result.document.content_type, "application/pdf")

    @patch("urllib.request.urlopen")
    @patch("urllib.request.Request")
    def test_public_drive_download_virus_warning(self, mock_request, mock_urlopen):
        # First call returns the warning HTML page
        warning_response = MagicMock()
        warning_response.read.return_value = b'Google Drive - Virus scan warning. confirm=xyz_code_987'
        warning_response.headers = {"Content-Type": "text/html"}

        # Second call returns the actual file content
        file_response = MagicMock()
        file_response.read.return_value = b"real-file-bytes"
        file_response.headers = {
            "Content-Type": "application/pdf",
            "Content-Disposition": 'attachment; filename="warning_clean.pdf"'
        }

        mock_urlopen.return_value.__enter__.side_effect = [warning_response, file_response]

        downloader = DriveDownloader()
        result = downloader._try_public_download(self.payload, "file_id_123")

        self.assertIsNotNone(result)
        self.assertEqual(result.content, b"real-file-bytes")
        self.assertEqual(result.document.filename, "warning_clean.pdf")
        # Direct URL should have confirm code attached in the second request
        self.assertEqual(mock_request.call_count, 2)
        second_call_url = mock_request.call_args_list[1][0][0]
        self.assertIn("confirm=xyz_code_987", second_call_url)

    # --- 3. Private Download Client errors & Retries ---
    @patch.object(DriveDownloader, '_try_public_download', return_value=None)
    def test_private_download_service_uninitialized(self, mock_public):
        with patch("src.filters.drive_downloader.load_drive_credentials", side_effect=Exception("No Service Account File")):
            downloader = DriveDownloader()
            self.assertIsNone(downloader._service)
            
            with self.assertRaisesRegex(RuntimeError, "no authenticated Drive service"):
                downloader.process(self.payload)

    @patch.object(DriveDownloader, '_try_public_download', return_value=None)
    @patch("src.filters.drive_downloader.load_drive_credentials")
    @patch("src.filters.drive_downloader.build")
    @patch("time.sleep") # speed up tests by mocking sleep
    def test_private_download_retries_transient_failures(self, mock_sleep, mock_build, mock_creds, mock_public):
        mock_creds.return_value = MagicMock()
        mock_service = MagicMock()
        mock_files = MagicMock()
        mock_get = MagicMock()
        
        # Raise retryable HTTP 500 error
        resp = httplib2.Response({"status": 500})
        mock_get.execute.side_effect = HttpError(resp, b"Internal Server Error")
        mock_files.get.return_value = mock_get
        mock_service.files.return_value = mock_files
        mock_build.return_value = mock_service

        downloader = DriveDownloader()
        
        with self.assertRaises(HttpError):
            downloader.process(self.payload)

        # Should retry MAX_RETRIES times (3 attempts total)
        self.assertEqual(mock_get.execute.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 3)

    @patch.object(DriveDownloader, '_try_public_download', return_value=None)
    @patch("src.filters.drive_downloader.load_drive_credentials")
    @patch("src.filters.drive_downloader.build")
    @patch("src.filters.drive_downloader.MediaIoBaseDownload")
    @patch("time.sleep")
    def test_private_download_success_after_one_retry(self, mock_sleep, mock_chunk_downloader, mock_build, mock_creds, mock_public):
        mock_creds.return_value = MagicMock()
        mock_service = MagicMock()
        mock_files = MagicMock()
        mock_get = MagicMock()
        
        # First execution fails with HTTP 503, second succeeds
        resp_503 = httplib2.Response({"status": 503})
        mock_get.execute.side_effect = [
            HttpError(resp_503, b"Service Unavailable"),
            {"name": "private_doc.pdf", "mimeType": "application/pdf", "size": "100"}
        ]
        
        mock_get_media = MagicMock()
        mock_files.get.return_value = mock_get
        mock_files.get_media.return_value = mock_get_media
        mock_service.files.return_value = mock_files
        mock_build.return_value = mock_service

        # Mock the chunked downloader to complete immediately
        mock_chunk_down = mock_chunk_downloader.return_value
        mock_chunk_down.next_chunk.return_value = (None, True)

        downloader = DriveDownloader()
        result = downloader.process(self.payload)

        self.assertEqual(result.document.filename, "private_doc.pdf")
        self.assertEqual(result.document.status, DocumentStatus.DOWNLOADING)
        self.assertEqual(mock_sleep.call_count, 1) # Slept once between attempts
