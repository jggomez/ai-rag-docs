# Feature Specification: Restrict CSV Ingestion Columns

**Feature Branch**: `004-restrict-csv-columns`  
**Created**: 2026-06-05  
**Status**: Draft  
**Input**: User description: "ingestion pippeline solo toma del del archivo de comunicaciones solo se tendria las columas: id borrador (es el id es necesario para consultas), fecha, frente, recibidas, url recibidas, enviadas, Ubicacion filtradas (url enviadas), asunto y body del doc"

## Clarifications

### Session 2026-06-05
- Q: If a CSV row contains empty or missing values in one of the mandatory columns (Id borradores, Fecha, Frente), how should the pipeline handle it? → A: Use fallback default values (e.g. generate hash for ID, "UNKNOWN" for date, "GENERAL" for front). If "url Recibidas" or "Ubicacion filtradas" is "Sin ruta" or "Sin URL origen", set the value to "UNKNOWN" and skip the Google Drive download process.
- Q: If the PDF download is skipped because the URL is UNKNOWN, how should we handle the document's subject and body, and should we create a document or chunks? → A: Skip processing and creating the document/chunks entirely for that document. Since a single CSV row can specify both a RECEIVED document and a SENT document, if one URL is UNKNOWN and the other is valid, only process and save the valid one.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reduced CSV Schema Validation (Priority: P1)

As an ingestion system administrator, I want the pipeline to parse the communications CSV file using only the restricted set of columns, so that the pipeline does not depend on unused columns (like Contrato, Para, Proceso, Tanexos, etc.).

**Why this priority**: Core requirement to prevent pipeline failures when schema changes occur in unused columns.

**Independent Test**: Can be verified by processing a CSV file containing only the 7 columns: `Id borradores`, `Fecha`, `Frente`, `Recibidas`, `url Recibidas`, `Enviadas`, `Ubicacion filtradas`. The system must successfully parse the rows without raising missing column errors.

**Acceptance Scenarios**:

1. **Given** a CSV file with only the 7 allowed columns, **When** the batch ingestion runs, **Then** all rows are parsed successfully.
2. **Given** a CSV file containing additional columns, **When** the batch ingestion runs, **Then** the pipeline ignores the extra columns and parses the allowed columns correctly.

---

### User Story 2 - Metadata Mapping to Entities (Priority: P1)

As a search system, I want the parsed documents in the database to contain the metadata fields mapped from the restricted columns (Id borradores, Fecha, Frente) and document content (asunto, body), so that the search query works correctly.

**Why this priority**: Required to retain search capabilities on the core metadata fields.

**Independent Test**: Verify that the generated `SourceDocument` has:
- `draft_id` = value from `Id borradores`
- `document_date` = value from `Fecha`
- `work_front` = value from `Frente`
- `response_file_url` = value from `Ubicacion filtradas` (for RECEIVED type, or response URL)
- Other fields (like `sender`, `contract_number`, `process`) are set to default values (e.g., "GENERAL", "UNKNOWN", or omitted).

**Acceptance Scenarios**:

1. **Given** a parsed row from the CSV, **When** the document is created, **Then** the `draft_id`, `document_date`, and `work_front` are mapped correctly.

---

### User Story 3 - Independent Row Document Processing (Priority: P1)

As a system administrator, I want RECEIVED and SENT documents in the same CSV row to be processed independently based on their URLs, so that we only ingest valid documents and skip missing ones.

**Why this priority**: Minimizes database pollution by avoiding empty placeholder documents when only one of the two documents is available.

**Independent Test**: Provide a row where `url Recibidas` is "Sin URL origen" but `Ubicacion filtradas` is a valid Google Drive URL. Verify that only the SENT document is created in Firestore and vectorized, while no RECEIVED document is created.

**Acceptance Scenarios**:

1. **Given** a CSV row where the received document has an UNKNOWN/placeholder URL but the sent document has a valid URL, **When** the pipeline runs, **Then** only the SENT document is processed and saved, and the RECEIVED document is ignored entirely.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST support a restricted CSV schema containing exactly (or at least) the following columns:
  - `Id borradores`
  - `Fecha`
  - `Frente`
  - `Recibidas`
  - `url Recibidas`
  - `Enviadas`
  - `Ubicacion filtradas`
- **FR-002**: System MUST ignore all other columns if present in the CSV file.
- **FR-003**: System MUST map CSV columns as follows:
  - `Id borradores` -> `draft_id` (used as identifier for queries)
  - `Fecha` -> `document_date`
  - `Frente` -> `work_front`
- **FR-004**: System MUST map `url Recibidas` as the source URL for RECEIVED documents, and `Ubicacion filtradas` as the source URL for SENT documents.
- **FR-005**: For RECEIVED documents, `response_file_url` MUST be mapped to the `Enviadas` value (if present) or `Ubicacion filtradas`.
- **FR-006**: System MUST extract the subject and body of the document from the downloaded file content using `DocumentCleaner` (Regex) for SENT documents, and `GeminiExtractor` (LLM OCR) for RECEIVED documents.
- **FR-007**: Any legacy columns not present in the restricted schema (e.g. `Para`, `Contrato`, `Proceso`, `Descripcion`, `Resonde a com`, `Ubicacion Recibidas`, `Tanexos`, `Fecha Com`, `Ubicacion Enviadas`) MUST NOT be required by the CSV parser or factory logic.
- **FR-008**: System MUST apply fallback default values for missing/empty mandatory metadata in the CSV row:
  - If `Id borradores` is empty, generate an MD5 hash of the row content as `draft_id`.
  - If `Fecha` is empty, set `document_date` to "UNKNOWN".
  - If `Frente` is empty, set `work_front` to "GENERAL".
- **FR-009**: If the `url Recibidas` or `Ubicacion filtradas` column value is empty or represents a placeholder (e.g., "Sin ruta", "Sin URL origen", "Sin URL origen"), the corresponding document (RECEIVED or SENT) MUST NOT be downloaded, processed, or saved to the database. No Firestore or search database records are created for it.
- **FR-010**: System MUST evaluate RECEIVED and SENT documents from the same CSV row independently. If one has an UNKNOWN/placeholder URL and the other has a valid URL, the pipeline processes and saves the valid document and ignores the other.

### Key Entities

- **SourceDocument**: Updated to reflect the restricted CSV schema (e.g., mapping only `draft_id`, `document_date`, `work_front`, `source_url`, and `response_file_url`). Unmapped attributes like `sender`, `contract_number`, and `process` should either use secure defaults ("UNKNOWN", "GENERAL") or be marked as optional/deprecated.
- **DocumentChunk**: Stores the extracted `subject` (asunto) and `body` of the document chunk.

## Design & Performance Standards *(mandatory)*

- **UX Consistency**: Validation logs and error messages must clearly specify if any of the mandatory restricted columns are missing from the input CSV.
- **Latency Requirement**: Column filtering must not introduce any performance overhead during parsing.
- **UI Verification**: Not applicable (Backend service).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Ingesting a CSV containing ONLY the 7 restricted columns completes without errors.
- **SC-002**: Database records (Firestore) for ingested documents have `draft_id`, `document_date`, and `work_front` populated correctly.
- **SC-003**: All `DocumentChunk` records have non-empty `subject` and `body` fields populated from the parsed/extracted PDF content.

## Edge Cases

- **"Sin ruta" / "Sin URL origen" handling**: If a row contains these values for the URL, the system logs the record but skips the Drive download.
- **Empty Mandatory Fields**: If a row is missing values, defaults are applied instead of throwing errors.

## Assumptions

- **CSV Header Naming**: Assumes standard Spanish headers are used (`Id borradores`, `Fecha`, `Frente`, `Recibidas`, `url Recibidas`, `Enviadas`, `Ubicacion filtradas`).
- **Missing Columns**: If any of these 7 columns are completely absent, the CSV parsing should fail with a clear schema validation error.
- **Default Values**: Fields like `sender`, `contract_number`, and `process` are no longer extracted from the CSV and will default to standard values.
