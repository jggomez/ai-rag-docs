# Feature Specification: Ingest Received Document and Exclude Current Document in RAG Retrieval

**Feature Branch**: `005-update-retrieve-ingest-received`  
**Created**: 2026-06-06  
**Status**: Draft  
**Input**: User description: "en ingestion necesitamos cambiar las api de retrieve, por que esta api reciba el campo de codcomunicadorecibido este campo es Recibidas osea en firestore nombre_objeto, con esto hacer el proceso de retrieve osea buscar docs "chunks" recibidos del RAG pero que no sean del mismo documento y seguir el proceso como esta. Otro endpoint de ingestdocumentreceived donde reciba la url del archivo ademas IngestRequestMetadata `Id borradores`, `Fecha`, `Frente`, `codigo`, `url file`, los parametros en ingles y este endpoit se encarga de guardar el doc y crear los chunks"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - RAG Retrieval Excluding Current Document (Priority: P1)

As an engineer querying the RAG system to generate a response draft for a received communication, I want the retrieval stage to exclude chunks from the current communication itself (identified by its code `codcomunicadorecibido`), so that the generated response relies on external context and references, rather than replicating the input document itself.

**Why this priority**: Core retrieval logic improvement to prevent self-referencing in generated replies.

**Independent Test**: Can be verified by executing a RAG retrieval request passing a `codcomunicadorecibido` parameter. Verify that the RAG context contains no chunks with a `nombre_objeto` field matching `codcomunicadorecibido`.

**Acceptance Scenarios**:

1. **Given** a document with code `"REC-001"` is already ingested in the RECEIVED database, **When** a retrieve request is made with `codcomunicadorecibido = "REC-001"`, **Then** the retrieval process returns candidate chunks from other documents but completely excludes any chunks belonging to `"REC-001"`.

---

### User Story 2 - Ingestion API Endpoint for Received Documents (Priority: P1)

As a pipeline user, I want a dedicated API endpoint `POST /api/v1/ingestdocumentreceived` that accepts a document download URL and its metadata in English, so that I can programmatically trigger the full ingestion flow (OCR, chunking, vector embedding, and database storage) specifically for received documents.

**Why this priority**: Required to programmatically ingest individual received documents through a clean, metadata-driven API.

**Independent Test**: Send a POST request to `/api/v1/ingestdocumentreceived` with a file URL and valid metadata, and verify that the document and its vectorized chunks are successfully saved in the RECEIVED Firestore database.

**Acceptance Scenarios**:

1. **Given** a valid document URL and metadata, **When** the request is sent to `POST /api/v1/ingestdocumentreceived`, **Then** the service downloads the file, processes it using the RECEIVED pipeline strategy (Gemini visual OCR), chunks and vectorizes it, and saves both the document record and chunk records to the RECEIVED Firestore database.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The retrieve API endpoint (`POST /api/v1/retrieve`) MUST accept `codcomunicadorecibido` as an optional string parameter in its request payload.
- **FR-002**: The retrieve API endpoint MUST map `codcomunicadorecibido` to the `nombre_objeto` field of the documents in Firestore.
- **FR-003**: The retrieval process (`RetrieveAndGenerateCommand`) MUST filter out and exclude all chunks from the search results where the chunk's `nombre_objeto` equals `codcomunicadorecibido`.
- **FR-004**: The system MUST expose a new endpoint `POST /api/v1/ingestdocumentreceived` in the ingestion pipeline service.
- **FR-005**: The request payload for `POST /api/v1/ingestdocumentreceived` MUST use the following English keys in its schema:
  - `url` (String, required): The URL of the document file (Google Drive or GCS).
  - `metadata` (Object, required) containing:
    - `draft_id` (String, required): Represents `Id borradores`.
    - `document_date` (String, required): Represents `Fecha`.
    - `work_front` (String, required): Represents `Frente`.
    - `code` (String, required): Represents `codigo` (e.g., `"REC-001"`).
    - `response_file_url` (String, optional): Represents `url file`.
- **FR-006**: When `POST /api/v1/ingestdocumentreceived` is called, the system MUST:
  - Append `.pdf` to the `code` parameter to set the `nombre_archivo` (filename).
  - Use `code` as-is (without `.pdf`) to set the `nombre_objeto` (object name).
  - Save the document under the RECEIVED collection/database.
  - Execute the pipeline strategy for received documents (using `GeminiExtractor` for visual LLM OCR, `TextChunker` for segmentation, and `VectorEmbedder` for embeddings).

### Key Entities

- **SourceDocument**: Represents the general metadata of the ingested received document. Attributes include:
  - `id`: The unique document identifier (e.g., `draft_id_REC`).
  - `filename`: Set to `code` + `.pdf`.
  - `object_name`: Set to `code` (clean, without `.pdf`).
  - `document_type`: Set to `received`.
  - `draft_id`, `document_date`, `work_front`, `source_url`, `response_file_url`.
- **DocumentChunk**: Segmented parts of the document text with associated embeddings. Attributes include:
  - `id_documento`: Refers to the parent document ID.
  - `asunto` and `texto` (composed of subject + body).
  - `nombre_archivo` and `nombre_objeto`.
  - `vector`: Embedding array (768 dimensions).

---

## Design & Performance Standards *(mandatory)*

- **UX Consistency**: Validation error messages must be returned in JSON format with clear descriptions if any of the mandatory payload fields (`url`, `draft_id`, `document_date`, `work_front`, `code`) are missing or invalid.
- **Latency Requirement**: The filter operation to exclude the current document from the retrieved chunks must execute in memory with O(1) complexity and negligible latency.

---

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Executing RAG retrieval with `codcomunicadorecibido = "REC-001"` returns a generated response based only on other documents, and no chunks from `"REC-001"` are present in the retrieval logs or generated context.
- **SC-002**: Calling `POST /api/v1/ingestdocumentreceived` successfully ingests the document and generates its chunks in Firestore under the RECEIVED database.

---

## Edge Cases

- **Missing `codcomunicadorecibido`**: If the parameter is not sent or is empty in `POST /api/v1/retrieve`, the system does not apply the exclusion filter (behaves like normal retrieve).
- **Matching document has no chunks**: If the document to exclude has no chunks in Firestore, retrieve completes normally without errors.

---

## Assumptions

- **Extension Suffix**: The parameter `code` passed to the ingestion API does not contain the `.pdf` extension. The system is responsible for appending it to `nombre_archivo`.
- **Authentication**: Drive/GCS service credentials are valid for downloading files from the provided `url`.
