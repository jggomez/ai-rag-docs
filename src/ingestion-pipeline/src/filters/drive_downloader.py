import io
import logging
import re
import time
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaIoBaseDownload

from src.filters.base import Filter
from src.domain.entities import ProcessingPayload
from src.domain.enums import DocumentStatus
from src.infrastructure.auth.google_drive import load_drive_credentials

logger = logging.getLogger(__name__)

# Regex to extract a Google Drive file ID from common URL formats
DRIVE_FILE_ID_PATTERN = re.compile(
    r"(?:/d/|id=|open\?id=)([a-zA-Z0-9_-]{25,})"
)

# Retry configuration
MAX_RETRIES = 3
RETRY_BACKOFF_SECONDS = 2


def extract_drive_file_id(url: str) -> Optional[str]:
    """Extract the file ID from a Google Drive URL."""
    match = DRIVE_FILE_ID_PATTERN.search(url)
    return match.group(1) if match else None


class DriveDownloader(Filter[ProcessingPayload, ProcessingPayload]):
    """
    Filter that downloads a document from Google Drive using the
    official google-api-python-client with centralised Service Account auth.

    Includes automatic retries with exponential back-off for transient errors
    and clear error reporting for 404 / permission-denied responses.
    """

    def __init__(self, service_account_path: Optional[str] = None):
        credentials = load_drive_credentials(service_account_path)
        self._service = build("drive", "v3", credentials=credentials)
        logger.info("DriveDownloader initialised successfully.")

    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        source_url = payload.document.source_url
        if not source_url:
            logger.debug(f"No source_url on {payload.document.filename}; skipping Drive download.")
            return payload

        file_id = extract_drive_file_id(source_url)
        if not file_id:
            logger.error(f"Could not extract Drive file ID from URL: {source_url}")
            payload.document.status = DocumentStatus.FAILED
            payload.document.metadata["error"] = f"Invalid Drive URL: {source_url}"
            return payload

        logger.info(f"Downloading Drive file {file_id} for document {payload.document.id}")
        payload.document.status = DocumentStatus.DOWNLOADING

        return self._download_with_retries(payload, file_id)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _download_with_retries(
        self, payload: ProcessingPayload, file_id: str
    ) -> ProcessingPayload:
        """Attempt file download with exponential back-off for transient errors."""
        last_error: Optional[Exception] = None

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                return self._execute_download(payload, file_id)
            except HttpError as http_err:
                status_code = http_err.resp.status if http_err.resp else 0

                # Non-retryable client errors
                if status_code == 404:
                    logger.error(f"Drive file not found (404): {file_id}")
                    payload.document.status = DocumentStatus.FAILED
                    payload.document.metadata["error"] = f"Drive file not found: {file_id}"
                    return payload
                if status_code == 403:
                    logger.error(f"Permission denied (403) for Drive file: {file_id}")
                    payload.document.status = DocumentStatus.FAILED
                    payload.document.metadata["error"] = f"Permission denied for Drive file: {file_id}"
                    return payload

                # Retryable server / rate-limit errors
                last_error = http_err
                wait = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    f"Drive download attempt {attempt}/{MAX_RETRIES} failed "
                    f"(HTTP {status_code}). Retrying in {wait}s…"
                )
                time.sleep(wait)

            except Exception as exc:
                last_error = exc
                wait = RETRY_BACKOFF_SECONDS * (2 ** (attempt - 1))
                logger.warning(
                    f"Drive download attempt {attempt}/{MAX_RETRIES} failed: {exc}. "
                    f"Retrying in {wait}s…"
                )
                time.sleep(wait)

        # All retries exhausted
        logger.error(f"Drive download failed after {MAX_RETRIES} attempts for {file_id}")
        payload.document.status = DocumentStatus.FAILED
        payload.document.metadata["error"] = f"Drive download error after retries: {last_error}"
        raise last_error  # type: ignore[misc]

    def _execute_download(
        self, payload: ProcessingPayload, file_id: str
    ) -> ProcessingPayload:
        """Single download attempt — fetch metadata then stream binary content."""
        # Fetch file metadata to determine MIME type
        file_metadata = (
            self._service.files()
            .get(fileId=file_id, fields="name,mimeType,size")
            .execute()
        )
        mime_type = file_metadata.get("mimeType", "application/octet-stream")
        payload.document.content_type = mime_type
        payload.document.filename = file_metadata.get("name", payload.document.filename)
        payload.document.size_bytes = int(file_metadata.get("size", 0))

        # Download file content
        request = self._service.files().get_media(fileId=file_id)
        buffer = io.BytesIO()
        downloader = MediaIoBaseDownload(buffer, request)

        done = False
        while not done:
            _, done = downloader.next_chunk()

        payload.content = buffer.getvalue()
        logger.info(
            f"Downloaded {len(payload.content)} bytes for {payload.document.filename}"
        )
        return payload
