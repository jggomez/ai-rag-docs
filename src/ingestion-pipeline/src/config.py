import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Centralized configuration for the Ingestion Pipeline.
    Uses pydantic-settings to automatically load from environment variables.
    """
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parent.parent / ".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # API Keys
    gemini_api_key: Optional[str] = os.environ.get("GEMINI_API_KEY")
    
    # Models
    embedding_model: str = "gemini-embedding-2"
    ocr_model: str = "gemini-3-flash-preview"
    generation_model: str = "gemini-3-flash-preview"
    
    # Storage
    metadata_csv_path: str = "resources/Comunicaciones_100.csv"
    
    # API Settings
    port: int = 8080
    log_level: str = "INFO"

    # Firestore Database instances
    firestore_database_received: str = "docs-recibidos"
    firestore_database_sent: str = "docs-enviados"

    # GCS Output for generated response PDFs
    gcs_output_bucket: str = "communications-cys"
    gcs_output_prefix: str = "COMMUNICATIONS_SENT"

    # GCS Ingestion for communications (unifies GCS buckets)
    gcs_communications_bucket: str = "communications-cys"

    # GCS Ingestion for received communications prefix
    gcs_received_prefix: str = "COMMUNICATIONS_RECEIVED/"

    # GCS Ingestion for sent communications prefix
    gcs_sent_prefix: str = "COMMUNICATIONS_SENT/"

# Singleton instance
settings = Settings()
