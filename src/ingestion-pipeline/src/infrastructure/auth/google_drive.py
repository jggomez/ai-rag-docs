"""Google Drive credential management for the ingestion pipeline."""

import logging
import os
from typing import Optional

from google.oauth2 import service_account
from google.auth import default as default_credentials

logger = logging.getLogger(__name__)

# Required OAuth scope for reading files from Drive
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"


def load_drive_credentials(
    service_account_path: Optional[str] = None,
) -> service_account.Credentials:
    """
    Load Google Drive credentials in priority order:
      1. Explicit Service Account JSON file path (parameter).
      2. DRIVE_SERVICE_ACCOUNT_PATH environment variable.
      3. Application Default Credentials (ADC) — e.g. on Cloud Run.

    Returns:
        google.oauth2.credentials.Credentials scoped for Drive read-only.

    Raises:
        RuntimeError: when no valid credentials can be resolved.
    """
    sa_path = service_account_path or os.environ.get("DRIVE_SERVICE_ACCOUNT_PATH")

    if sa_path and os.path.isfile(sa_path):
        logger.info(f"Loading Drive credentials from Service Account file: {sa_path}")
        return service_account.Credentials.from_service_account_file(
            sa_path,
            scopes=[DRIVE_READONLY_SCOPE],
        )

    # Fallback to Application Default Credentials
    try:
        credentials, _ = default_credentials(scopes=[DRIVE_READONLY_SCOPE])
        logger.info("Loaded Drive credentials via Application Default Credentials.")
        return credentials
    except Exception as exc:
        error_message = (
            "Could not resolve Google Drive credentials. "
            "Set DRIVE_SERVICE_ACCOUNT_PATH or configure ADC."
        )
        logger.error(f"{error_message} Detail: {exc}")
        raise RuntimeError(error_message) from exc
