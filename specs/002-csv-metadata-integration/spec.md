# Feature Specification: CSV Metadata Integration & Ingestion API

**Feature Branch**: `002-csv-metadata-integration`  
**Created**: 2026-04-16
**Status**: Draft  
**Input**: User description: "Reuse previous pipeline service and take a CSV file where all communications are, taking columns for metadata and adding the 'sent file' property to the DocumentChunk in Firestore. READ each row and get respective data from a new API POST in main.py."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Metadata-Driven Ingestion API (Priority: P1)

As a system, I want to trigger a document ingestion via a POST API by providing all necessary metadata, so that the pipeline can process the PDF from Storage without needing to "guess" metadata.

**Acceptance Scenarios**:
1. **Given** a valid JSON payload with `Remitente`, `Numero de contrato`, `Frente de obra`, `Fecha`, `Proceso`, and `url_archivo_respuesta`, **When** the `/ingest` endpoint is called, **Then** the pipeline should fetch the PDF from GCS and process it using the provided metadata.

---

### User Story 2 - Batch CSV Processing (Priority: P1)

As a developer, I want a tool to read each row of a local CSV and trigger the ingestion pipeline for every communication record (calling the Ingest API), so that I can perform bulk ingestion easily.

**Acceptance Scenarios**:
1. **Given** a local CSV file, **When** the batch script runs, **Then** it should iterate through all rows and successfully trigger the ingestion for each referenced PDF.

---

### User Story 3 - Response File Traceability (Priority: P1)

As an auditor, I want to see the `url_archivo_respuesta` (sent file) both in the `SourceDocument` and on every `DocumentChunk` in Firestore.

**Acceptance Scenarios**:
1. **Given** a document processed with a `url_archivo_respuesta`, **When** I check Firestore, **Then** both the parent `SourceDocument` and all its `DocumentChunk` children must contain the URL.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Implement `POST /ingest` in `src/main.py` using FastAPI.
- **FR-002**: Pipeline MUST accept external metadata as input, bypassing heuristic extraction.
- **FR-003**: Implement a batch processing script to read local CSV and invoke ingestion.
- **FR-004**: System MUST persist `url_archivo_respuesta` in both `SourceDocument` and `DocumentChunk`.
- **FR-005**: Maintain existing PDF reading, cleaning, and embedding logic.

### Key Entities

- **SourceDocument**: Updated to ensure `response_file_url` (mapped from `url_archivo_respuesta`) is mandatory when available.
- **DocumentChunk**: Updated with `sent_file` field (mapped from `url_archivo_respuesta`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: API returns 200 OK and valid job ID for valid metadata payloads.
- **SC-002**: Firestore documents perfectly reflect the fields provided via API/CSV.
- **SC-003**: All rows in a test CSV can be processed sequentially.
