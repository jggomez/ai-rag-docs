import unittest
from unittest.mock import MagicMock, patch
from googleapiclient.errors import HttpError
import httplib2
from src.filters.drive_downloader import DriveDownloader
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
        
        # Mock API to raise HttpError 403
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
        
        # Mock API to raise HttpError 404
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
