import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Centralized configuration for the Ingestion Pipeline.
    Uses pydantic-settings to automatically load from environment variables.
    """
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # API Keys
    gemini_api_key: Optional[str] = os.environ.get("GEMINI_API_KEY")
    
    # Models
    embedding_model: str = "gemini-embedding-2"
    ocr_model: str = "gemini-2.0-flash"
    
    # Storage
    metadata_csv_path: str = "resources/Comunicaciones.csv"
    
    # API Settings
    port: int = 8080
    log_level: str = "INFO"

# Singleton instance
settings = Settings()
