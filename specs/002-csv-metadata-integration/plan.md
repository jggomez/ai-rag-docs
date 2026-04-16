# Implementation Plan: CSV Metadata Integration & Ingestion API

**Branch**: `002-csv-metadata-integration` | **Date**: 2026-04-16 | **Spec**: [spec.md](file:///Users/jggomez/Documents/jggomez/code/ai-doc-communications/specs/002-csv-metadata-integration/spec.md)
**Input**: Feature specification from `/specs/002-csv-metadata-integration/spec.md`

## Summary

This feature adds a new `POST /ingest` API to the `ingestion-pipeline` to allow triggering ingestion with external metadata. It also includes a batch script to process a local CSV file by iterating over its rows and executing the pipeline for each communication record, ensuring `response_file_url` is correctly persisted in both `SourceDocument` and `DocumentChunk`.

## Technical Context

- **Language/Version**: Python 3.12 (uv)
- **Primary Dependencies**: `FastAPI`, `pymupdf`, `pydantic`, `vertexai`, `python-dotenv`
- **Storage**: Firestore (metadata & vectors), GCS (raw documents)

## Detailed Execution Plan

### 1. Domain Layer
- Ensure `SourceDocument` and `DocumentChunk` in `src/domain/entities.py` have `response_file_url` and `sent_file` respectively.

### 2. Pipeline Adjustment
- Create `ManualMetadataProvider` filter that accepts metadata from the API/Caller.
- Update `PipelineBuilder` to support "Manual Mode" ingestion.

### 3. API Entry Point
- Update `src/main.py`:
    - Add `POST /ingest` endpoint.
    - Define Pydantic request model for metadata.
    - Instantiate the pipeline and trigger `process_document`.

### 4. Batch Script
- Create `src/ingestion-pipeline/scripts/batch_ingest.py`:
    - Read local CSV using `csv.DictReader`.
    - Format metadata according to requirements.
    - Call the `IngestDocument` usecase directly or via API request.

### 5. Verification
- `tests/unit/test_api.py`: Test the new endpoint with mock pipeline.
- `tests/integration/test_batch_processing.py`: Verify CSV parsing and pipeline triggering.
