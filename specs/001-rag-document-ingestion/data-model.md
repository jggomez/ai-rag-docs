# Data Model: RAG Document Ingestion

## Entities

### SourceDocument (Firestore Document)
Represents the metadata of the original file stored in GCS.
- `id`: UUID / Hash of file path
- `contract_number`: string (extracted from document content or metadata)
- `work_front`: string
- `sender`: string (contracting entity)
- `document_date`: timestamp
- `process`: string
- `response_file_url`: string (GCS URI for the response document)
- `file_path`: string (GCS URI)
- `fileName`: string
- `type`: string (e.g., "COMMUNICATION_RECEIVED", "COMMUNICATION_SENT")
- `status`: enum ("PENDING", "PROCESSING", "COMPLETED", "FAILED")
- `version`: integer
- `createdAt`: timestamp
- `updatedAt`: timestamp

### DocumentChunk (Firestore Document - in specific instance)
The atomic unit of information for the RAG system.
- `id`: UUID
- `sourceId`: Reference to SourceDocument
- `subject`: string (Heading or context of the chunk)
- `body`: string (The actual text content)
- `embedding`: Vector (Gemini Embedding SOTA)
- `metadata`: object
  - `pageNumber`: integer
  - `chunkIndex`: integer
  - `contractNumber`: string
  - `workFront`: string
  - `sender`: string
- `createdAt`: timestamp

## Relationships
- **SourceDocument** (1) ---- (N) **DocumentChunk**

## State Transitions
- Ingestion Triggered → `SourceDocument.status = PENDING`
- Pipeline Start → `SourceDocument.status = PROCESSING`
- Successfully Stored → `SourceDocument.status = COMPLETED`
- Failure at any step → `SourceDocument.status = FAILED`
