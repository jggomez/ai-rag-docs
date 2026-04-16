# Feature Specification: RAG Document Ingestion Pipeline

**Feature Branch**: `001-rag-document-ingestion`  
**Created**: 2026-04-15  
**Status**: Draft  
**Input**: User description: "Crear un RAG que permita de un storage obtener el archivo y hacer el prepocesamiento de leer el doc, luego hacer el chunking, convertir a embeddings y guardar los vectores en una Base de datos, con metadatos"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Automated Document Ingestion (Priority: P1)

As a system administrator, I want files uploaded to storage to be automatically processed into searchable vectors so that the assistant can answer questions based on the new content.

**Why this priority**: Core functionality of the RAG system. Without ingestion, there is no data to retrieve.

**Independent Test**: Upload a PDF to the source storage and verify its presence as vector chunks in the database with correct metadata.

**Acceptance Scenarios**:

1. **Given** a PDF file is uploaded to the designated storage bucket, **When** the ingestion job is triggered, **Then** the file should be chunked and stored in the vector database within 30 seconds.
2. **Given** a corrupted file is uploaded, **When** the ingestion job runs, **Then** a descriptive error should be logged and the system should remain stable.

---

### User Story 2 - Ingestion Status Monitoring (Priority: P2)

As a developer, I want to see the status of a document's ingestion (pending, processing, completed, failed) so I can verify the pipeline's health.

**Why this priority**: Essential for observability and adherence to the UI Pass principle.

**Independent Test**: Invoke the ingestion command for a list of documents and check the status tracking view/API for correct state transitions.

**Acceptance Scenarios**:

1. **Given** an ingestion process is started, **When** querying the status, **Then** it should show "Processing".
2. **Given** an ingestion process completes, **When** querying the status, **Then** it should show "Completed" with a timestamp.

---

### Edge Cases

- **Large Files**: Documents exceeding 50MB should be rejected with a clear user-facing error message.
- **Empty Files**: Files with no extractable text should be logged as warnings but skip vector generation.
- **Duplicate Uploads**: The system must detect if an identical file version has already been processed to avoid redundant vectors.
- **Unsupported Formats**: Any file type other than PDF/TXT/MD must be caught and reported as an unsupported format error.

---

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST retrieve files from configured Cloud Storage buckets.
- **FR-002**: System MUST extract text from PDF, Markdown, and TXT files.
- **FR-003**: System MUST split extracted text into semantic chunks with appropriate context overlap to ensure retrieval quality.
- **FR-004**: System MUST generate vector embeddings for each chunk using an embedding model.
- **FR-005**: System MUST store vectors alongside metadata (source_id, chunk_index, original_text, timestamp) in a Vector Database.
- **FR-006**: System MUST prevent duplicate ingestion of the same file version.

### Key Entities *(include if feature involves data)*

- **IngestionJob**: Represents the lifecycle of a single document processing task.
- **DocumentChunk**: The atomic unit of text, embedding, and metadata stored in the vector DB.
- **SourceDocument**: Reference to the original file in storage with its metadata.

## Design & Performance Standards *(mandatory)*

- **UX Consistency**: Ingestion status indicators must follow the project's standard loading and state transition tokens.
- **Latency Requirement**: The API call to trigger or check ingestion status must respond in <200ms.
- **UI Verification**: A "Processing Dashboard" or similar UI pass must exist to visualize the ingestion queue.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid documents (PDF/TXT/MD) successfully converted to searchable vectors.
- **SC-002**: Average ingestion time (storage to vector DB) under 2 seconds per page ($PAGE_SIZE approx 2k chars).
- **SC-003**: All User Stories have a verified UI flow passing the Constitution UI Pass check.
- **SC-004**: System handles concurrent uploads without exceeding 200ms interaction latency for the status UI.

## Assumptions

- Source files are primarily textual and do not require OCR in the initial version.
- The Vector Database and Embedding API are pre-configured in the environment.
- Files do not exceed 50MB in size for MVP.
