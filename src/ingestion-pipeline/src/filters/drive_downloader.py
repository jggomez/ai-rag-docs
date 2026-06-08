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
from src.domain.enums import DocumentStatus, DocumentType
from src.infrastructure.auth.google_drive import load_drive_credentials

logger = logging.getLogger(__name__)

# Regex to extract a Google Drive file ID from common URL formats
DRIVE_FILE_ID_PATTERN = re.compile(
    r"(?:/d/|id=|open\?id=)([a-zA-Z0-9_-]{20,})"
)

# Regex to extract bucket and blob from HTTPS GCS URLs
GCS_HTTPS_PATTERN = re.compile(
    r"https://storage\.(?:googleapis\.com|cloud\.google\.com)/([^/]+)/(.+)"
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
        try:
            credentials = load_drive_credentials(service_account_path)
            self._service = build("drive", "v3", credentials=credentials)
            logger.info("DriveDownloader initialised successfully with authenticated service client.")
        except Exception as e:
            logger.warning(
                f"Could not load Google Drive credentials for authenticated downloads: {e}. "
                "Only public downloads will be supported."
            )
            self._service = None

    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        source_url = payload.document.source_url
        if not source_url:
            logger.debug(f"No source_url on {payload.document.filename}; skipping Drive download.")
            return payload

        # 1. Handle Native GCS URLs (gs:// or storage.googleapis.com)
        gcs_match = GCS_HTTPS_PATTERN.search(source_url)
        if source_url.startswith("gs://") or gcs_match:
            if gcs_match:
                bucket_name = gcs_match.group(1)
                blob_name = gcs_match.group(2)
            else:
                parts = source_url[5:].split("/", 1)
                if len(parts) != 2:
                    err_msg = f"Invalid GCS URL: {source_url}"
                    logger.error(err_msg)
                    payload.document.status = DocumentStatus.FAILED
                    payload.document.metadata["error"] = err_msg
                    return payload
                bucket_name, blob_name = parts[0], parts[1]
            
            return self._download_from_gcs(payload, bucket_name, blob_name)

        # 2. Handle Google Drive URLs
        file_id = extract_drive_file_id(source_url)
        if not file_id:
            logger.error(f"Could not extract Drive file ID from URL: {source_url}")
            payload.document.status = DocumentStatus.FAILED
            payload.document.metadata["error"] = f"Invalid Drive URL: {source_url}"
            return payload

        logger.info(f"Attempting public download for Drive file {file_id}...")
        public_payload = self._try_public_download(payload, file_id)
        if public_payload:
            return self._upload_to_gcs_and_update(public_payload)

        # Fallback to official API client
        logger.info(f"Public download failed or not accessible for file {file_id}. Falling back to authenticated client...")
        if not self._service:
            err_msg = f"Cannot download private file {file_id} because no authenticated Drive service was initialized."
            logger.error(err_msg)
            payload.document.status = DocumentStatus.FAILED
            payload.document.metadata["error"] = err_msg
            raise RuntimeError(err_msg)

        payload.document.status = DocumentStatus.DOWNLOADING
        result_payload = self._download_with_retries(payload, file_id)
        return self._upload_to_gcs_and_update(result_payload)

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _download_from_gcs(self, payload: ProcessingPayload, bucket_name: str, blob_name: str) -> ProcessingPayload:
        """Helper to download a file directly from Google Cloud Storage."""
        logger.info(f"Downloading from GCS: bucket={bucket_name}, blob={blob_name}...")
        try:
            from google.cloud import storage
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(blob_name)
            content = blob.download_as_bytes()
            
            # Set payload details
            payload.content = content
            payload.document.size_bytes = len(content)
            payload.document.status = DocumentStatus.DOWNLOADING
            
            # Guess filename and content_type
            filename = blob_name.split("/")[-1]
            if not payload.document.filename or payload.document.filename == "test.pdf":
                payload.document.filename = filename
            
            # If content_type is not already set or is generic, set it based on suffix
            if filename.lower().endswith(".pdf"):
                payload.document.content_type = "application/pdf"
            else:
                payload.document.content_type = blob.content_type or "application/octet-stream"
                
            logger.info(f"Successfully downloaded {filename} ({len(content)} bytes) from GCS.")
            return payload
        except Exception as e:
            err_msg = f"Error downloading from GCS (bucket={bucket_name}, blob={blob_name}): {e}"
            logger.error(err_msg)
            payload.document.status = DocumentStatus.FAILED
            payload.document.metadata["error"] = err_msg
            return payload

    def _upload_to_gcs_and_update(self, payload: ProcessingPayload) -> ProcessingPayload:
        """Upload downloaded content to GCS landing zone and update document properties."""
        if not payload.content:
            logger.warning("No content downloaded to upload to GCS.")
            return payload

        from datetime import datetime
        from google.cloud import storage
        from src.config import settings

        bucket_name = settings.gcs_communications_bucket

        # Select prefix based on document type (SENT vs RECEIVED)
        if payload.document.document_type == DocumentType.SENT:
            prefix = settings.gcs_sent_prefix
        else:
            prefix = settings.gcs_received_prefix

        # Determine yyyy-mm-dd directory name using document_date or current date
        doc_date = payload.document.document_date
        # Normalise date if possible (supporting YYYY-MM-DD or DD/MM/YYYY)
        if doc_date and "/" in doc_date:
            parts = doc_date.split("/")
            if len(parts) == 3:
                # Assuming DD/MM/YYYY -> YYYY-MM-DD
                date_str = f"{parts[2]}-{parts[1]}-{parts[0]}"
            else:
                date_str = datetime.now().strftime("%Y-%m-%d")
        elif doc_date and len(doc_date) == 10 and doc_date[4] == '-' and doc_date[7] == '-':
            date_str = doc_date
        else:
            date_str = datetime.now().strftime("%Y-%m-%d")

        folder_prefix = f"{prefix}{date_str}/"
        gcs_filename = payload.document.filename
        if not gcs_filename.lower().endswith(".pdf"):
            gcs_filename = f"{gcs_filename}.pdf"
        # Replace forward slashes to avoid nested folders in GCS
        gcs_filename = gcs_filename.replace("/", "-")
        object_name = f"{folder_prefix}{gcs_filename}"

        logger.info(f"Uploading downloaded file {payload.document.filename} to GCS bucket {bucket_name} folder {folder_prefix}...")

        try:
            client = storage.Client()
            bucket = client.bucket(bucket_name)

            # Check if the folder exists (has any files) in GCS flat namespace.
            # If not, create a 0-byte folder placeholder.
            blobs = list(bucket.list_blobs(prefix=folder_prefix, max_results=1))
            if not blobs:
                logger.info(f"GCS Folder placeholder {folder_prefix} does not exist. Creating...")
                folder_blob = bucket.blob(folder_prefix)
                folder_blob.upload_from_string(b"", content_type="application/x-directory")
            else:
                logger.info(f"GCS Folder {folder_prefix} already exists.")

            # Save the actual file
            blob = bucket.blob(object_name)
            content_type = payload.document.content_type or "application/pdf"
            blob.upload_from_string(payload.content, content_type=content_type)
            logger.info(f"Successfully uploaded {payload.document.filename} to GCS: gs://{bucket_name}/{object_name}")

            # Update document to reflect the new GCS location
            payload.document.bucket = bucket_name
            payload.document.object_name = object_name
            
            gcs_url = f"gs://{bucket_name}/{object_name}"
            if payload.document.document_type == DocumentType.RECEIVED:
                payload.document.metadata["url_recibido"] = gcs_url
            else:
                payload.document.response_file_url = gcs_url
            
        except Exception as e:
            logger.error(f"Failed to upload document to GCS: {str(e)}")
            raise e

        return payload


    def _try_public_download(self, payload: ProcessingPayload, file_id: str) -> Optional[ProcessingPayload]:
        """Try to download a file from Google Drive publicly without authentication."""
        import urllib.request
        import urllib.error
        
        direct_url = f"https://docs.google.com/uc?export=download&id={file_id}"
        try:
            req = urllib.request.Request(
                direct_url, 
                headers={'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)'}
            )
            with urllib.request.urlopen(req) as response:
                content = response.read()
                
                # Check if we hit a virus warning page (Google Drive returns HTML for larger files)
                if b"confirm=" in content or b"Google Drive - Virus scan warning" in content:
                    logger.info("Encountered virus scan warning page, attempting to extract confirmation code...")
                    html = content.decode('utf-8', errors='ignore')
                    confirm_match = re.search(r'confirm=([a-zA-Z0-9_]+)', html)
                    if confirm_match:
                        confirm_code = confirm_match.group(1)
                        direct_url += f"&confirm={confirm_code}"
                        req = urllib.request.Request(direct_url, headers={'User-Agent': 'Mozilla/5.0'})
                        with urllib.request.urlopen(req) as response2:
                            content = response2.read()
                            response = response2
                
                # Detect MIME type and headers
                content_type = response.headers.get("Content-Type", "application/octet-stream")
                content_disposition = response.headers.get("Content-Disposition", "")
                
                filename_match = None
                content_disposition_filename = None
                if content_disposition:
                    filename_match = re.search(r'filename="([^"]+)"', content_disposition)
                    if filename_match:
                        content_disposition_filename = filename_match.group(1)
                
                filename = None
                if content_disposition_filename and content_disposition_filename not in ["test.pdf", "document.pdf", "test", "document"]:
                    filename = content_disposition_filename
                elif payload.document.filename:
                    filename = payload.document.filename
                else:
                    filename = content_disposition_filename or "document"
                
                # Check for PDF extension before stripping it
                is_pdf = (
                    filename.lower().endswith(".pdf") or 
                    (content_disposition_filename and content_disposition_filename.lower().endswith(".pdf")) or
                    (payload.document.filename and payload.document.filename.lower().endswith(".pdf")) or
                    content_type == "application/pdf"
                )
                if is_pdf:
                    content_type = "application/pdf"
                
                # Strip .pdf extension
                if filename.lower().endswith(".pdf"):
                    filename = filename[:-4]
                
                payload.content = content
                payload.document.content_type = content_type
                payload.document.filename = filename
                payload.document.size_bytes = len(content)
                payload.document.status = DocumentStatus.DOWNLOADING
                
                logger.info(f"Successfully downloaded public file {filename} ({len(content)} bytes) as {content_type}")
                return payload
        except Exception as e:
            logger.warning(f"Direct public download attempt failed for file ID {file_id}: {e}")
            return None

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
                    raise http_err
                if status_code == 403:
                    logger.error(f"Permission denied (403) for Drive file: {file_id}")
                    payload.document.status = DocumentStatus.FAILED
                    payload.document.metadata["error"] = f"Permission denied for Drive file: {file_id}"
                    raise http_err

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
        original_filename = payload.document.filename
        gdrive_metadata_name = file_metadata.get("name")
        
        if gdrive_metadata_name and gdrive_metadata_name not in ["test.pdf", "document.pdf", "test", "document"]:
            downloaded_filename = gdrive_metadata_name
        elif original_filename:
            downloaded_filename = original_filename
        else:
            downloaded_filename = gdrive_metadata_name or "document"

        is_pdf = (
            downloaded_filename.lower().endswith(".pdf") or
            (original_filename and original_filename.lower().endswith(".pdf")) or
            mime_type == "application/pdf"
        )
        if is_pdf:
            mime_type = "application/pdf"
            
        payload.document.content_type = mime_type

        if downloaded_filename.lower().endswith(".pdf"):
            downloaded_filename = downloaded_filename[:-4]

        payload.document.filename = downloaded_filename
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
