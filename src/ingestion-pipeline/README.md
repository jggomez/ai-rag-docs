# Ingestion Pipeline

AI-powered document ingestion pipeline for processing engineering communications.

## Features

- **GCS Ingestion** — Triggered by Google Cloud Storage events (legacy).
- **CSV Batch Ingestion** — Process documents listed in a CSV file, with support for Google Drive URLs.
- **Hybrid Processing Paths**:
  - **Sent Documents** (`enviadas_url`): Downloaded from Drive → PDF text extraction → Regex-based subject/body parsing (`DocumentCleaner`).
  - **Received Documents** (`recibidas_url`): Downloaded from Drive → LLM OCR via Gemini (`GeminiExtractor`) for scanned/image documents.

## Configuration

Copy `.env.example` to `.env` and fill in the values:

```bash
cp .env.example .env
```

| Variable                    | Description                                          | Required |
|-----------------------------|------------------------------------------------------|----------|
| `GCP_PROJECT_ID`            | Google Cloud project ID                              | Yes      |
| `GCS_INGESTION_BUCKET`      | GCS bucket for incoming documents                    | Yes      |
| `GEMINI_API_KEY`            | API key for Gemini models                            | Yes      |
| `GEMINI_OCR_MODEL`          | Gemini model for OCR (default: `gemini-3-flash-preview`) | No       |
| `EMBEDDING_MODEL`           | Embedding model name (default: `models/embedding-001`) | No       |
| `DRIVE_SERVICE_ACCOUNT_PATH`| Path to Google Drive Service Account JSON file       | No*      |

> \* If not set, Application Default Credentials (ADC) are used. Required for local development with private Drive files.

## CSV Format

The CSV must contain at least one of these URL columns:

| Column          | Type      | Processing Path       |
|-----------------|-----------|-----------------------|
| `recibidas_url` | Drive URL | RECEIVED → Gemini OCR |
| `enviadas_url`  | Drive URL | SENT → Regex Cleaner  |

See [CSV Schema](../../specs/003-drive-ingestion-llm-ocr/contracts/csv_schema.md) for full column reference.

## Running Tests

```bash
cd src/ingestion-pipeline
uv run pytest tests/ -v
```

## Architecture

The pipeline uses a **Filter/Pipeline** pattern with Clean Architecture:

```
DriveDownloader → [PDFReader + DocumentCleaner] OR [GeminiExtractor] → TextChunker → VectorEmbedder → VectorSaver
```

Branch selection is handled by `PipelineBuilder.build_pipeline_for_document()` based on `DocumentType` (SENT/RECEIVED).
