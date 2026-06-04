# Feature Specification: Drive Ingestion and LLM OCR

**Feature Branch**: `003-drive-ingestion-llm-ocr`  
**Created**: 2026-04-27  
**Status**: Draft  
**Input**: User description: "Del endpoint y pipeline que toma un csv y procesa cada fila hay una columna con nombre recibidas_url, el cual es una url del doc en drive se debe descargar y procesar por el pipeline. Tambien hacer lo mismo con la columna enviadas_url. Cambiar del pipeline tanto del csv como el otro que los docs enviados se debe procesar como esta actual que es es usando regex y leyendo el archivo, pero los docs de recibidos son imagenes escaneadas la cual se usara una LLM para el OCR"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Batch Ingestion with Drive URLs (Priority: P1)

As a system administrator, I want to trigger a batch ingestion from a CSV that contains Google Drive URLs so that documents can be automatically downloaded and processed without manual upload to GCS.

**Why this priority**: This is the core requirement for automating the ingestion of documents stored in Drive.

**Independent Test**: Can be fully tested by providing a CSV with `recibidas_url` and `enviadas_url` columns and verifying that files are downloaded and records are created in the document repository.

**Acceptance Scenarios**:

1. **Given** a CSV with a `recibidas_url`, **When** the `/ingest` endpoint is called, **Then** the system downloads the file from Drive and proceeds with the "Received" processing path.
2. **Given** a CSV with an `enviadas_url`, **When** the `/ingest` endpoint is called, **Then** the system downloads the file from Drive and proceeds with the "Sent" processing path.

---

### User Story 2 - Hybrid Processing Paths (Priority: P1)

As a data analyst, I want "Sent" documents to be processed with high-precision Regex and "Received" documents (scanned) to be processed via LLM OCR so that metadata extraction is optimized for each document type.

**Why this priority**: "Received" documents are often scanned images where standard PDF extraction fails, necessitating LLM OCR. "Sent" documents follow a rigid format where Regex is more efficient and consistent.

**Independent Test**: Can be tested by verifying that a "Sent" document metadata is extracted via `DocumentCleaner` and a "Received" document metadata is extracted via `GeminiExtractor`.

**Acceptance Scenarios**:

1. **Given** a document identified as "Sent", **When** processed through the pipeline, **Then** the `DocumentCleaner` (Regex) logic is applied to extract the Subject and Body.
2. **Given** a document identified as "Received", **When** processed through the pipeline, **Then** the `GeminiExtractor` (LLM) is used to perform OCR and extract metadata.

---

### User Story 3 - Drive Authentication (Priority: P2)

As a developer, I want the system to securely authenticate with Google Drive to download private documents.

**Why this priority**: Most corporate documents in Drive will not be public.

**Independent Test**: Successfully download a non-public file from a authorized Drive folder using service account credentials.

**Acceptance Scenarios**:

1. **Given** a private Drive URL and valid credentials, **When** the downloader is triggered, **Then** the file is successfully retrieved.

---

### Edge Cases

- **Broken Drive Links**: How does the system handle 404 or permission denied errors for a Drive URL? (Should mark record as FAILED with specific error).
- **Non-PDF/Image Files**: What if the Drive URL points to a Google Doc or a Spreadsheet? (Should probably only support PDF and Image formats initially).
- **Empty URLs**: How to handle rows where both URL columns are empty? (Fallback to current `Enviadas` filename lookup or skip).
- **Rate Limiting**: Handling Google Drive and Gemini API rate limits during large batch ingestions.

## Clarifications

### Session 2026-04-27
- **Q: Authentication for Google Drive** → **A: Use native Google libraries (Service Account recommended)**.
- **Q: LLM OCR Prompt** → **A: English prompt focusing on 'subject' and 'body'. Tables as text items, images as text descriptions.**
- **Q: Model Selection** → **A: Use `gemini-3-flash-preview` via native Python SDK.**
- **Q: Extracted Fields** → **A: Only 'subject' and 'body' are required for LLM OCR path.**

---

### User Story 4 - Document Layout Preservation (Priority: P2)

As a consumer of the processed text, I want tables and images to be converted into descriptive text so that the semantic meaning is preserved in the RAG system.

**Why this priority**: Scanned documents often contain tables and diagrams that are critical for understanding but difficult to represent as raw text.

**Independent Test**: Verify that a document with a table results in `extracted_text` containing a markdown-style or list-based representation of the table.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support two new CSV columns: `recibidas_url` and `enviadas_url`.
- **FR-002**: System MUST download document content from Google Drive URLs using native Google Python libraries (e.g., `google-api-python-client`).
- **FR-003**: System MUST identify if a document is "Sent" or "Received" to determine the processing path.
- **FR-004**: "Sent" documents MUST be processed using the existing `PDFReader` and `DocumentCleaner` (Regex) filters.
- **FR-005**: "Received" documents MUST be processed using the `GeminiExtractor` filter with the `gemini-3-flash-preview` model.
- **FR-006**: The LLM prompt MUST be in English and instructed to extract only `subject` and `body`.
- **FR-007**: The LLM MUST be instructed to represent tables as text items and describe images in text.

### Key Entities

- **SourceDocument**: Updated to include `document_type` (Enum: SENT, RECEIVED) and `source_url`.
- **ProcessingPayload**: Carriers the document and its binary content through the branched pipeline.

## Design & Performance Standards *(mandatory)*

- **UX Consistency**: Ingestion logs should clearly state which processing path was chosen for each document.
- **Latency Requirement**: LLM OCR via Gemini-3 may take several seconds per document; batch processing must handle this asynchronously or with appropriate timeouts.
- **UI Verification**: Not applicable (Backend service), but CLI/API responses must reflect the hybrid status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid Drive URLs in a batch are successfully downloaded.
- **SC-002**: "Received" documents have `subject` and `body` populated via LLM OCR.
- **SC-003**: Tables in "Received" documents are correctly represented as text lists/items.
- **SC-004**: Zero regressions in the current GCS-based ingestion flow.

## Assumptions

- **Drive URL Format**: Assumed to be standard `https://drive.google.com/file/d/ID/view` or similar.
- **Authentication**: A Google Service Account with appropriate permissions to the Drive folders will be provided.
- **Model Selection**: `gemini-3-flash-preview` is the target model.
- **PDF Nature**: "Sent" documents are assumed to be digital PDFs with extractable text, while "Received" are assumed to be scans requiring OCR.
- **CSV Identity**: The `Enviadas` column (or a new ID column) will remain the primary key for the record.
- [NEEDS CLARIFICATION]: Should the system handle rows that have BOTH `recibidas_url` and `enviadas_url`?
- [NEEDS CLARIFICATION]: If both URLs are absent, should we fallback to GCS or skip?
