# Implementation Plan: Ingest Received Document and Exclude Current Document in RAG Retrieval

**Branch**: `005-update-retrieve-ingest-received` | **Date**: 2026-06-06 | **Spec**: [spec.md](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/specs/005-update-retrieve-ingest-received/spec.md)

## Summary

Implement changes to the ingestion and retrieval services:
1. Update `POST /api/v1/retrieve` and `RetrieveAndGenerateCommand` to accept an optional `codcomunicadorecibido` parameter and filter out chunks belonging to that document from the retrieved RAG context in-memory (using a robust matching heuristic against `id_documento`, `id_borrador`, `nombre_archivo`, and `nombre_objeto`).
2. Add a new endpoint `POST /api/v1/ingestdocumentreceived` accepting a document URL and metadata (`draft_id`, `document_date`, `work_front`, `code`, `response_file_url` in English). This endpoint will trigger the Visual LLM (Gemini) ingestion strategy for the received document, and if `response_file_url` is valid, also trigger the standard text ingestion strategy for the corresponding sent document.

## Technical Context

**Language/Version**: Python 3.11  
**Primary Dependencies**: FastAPI, Pydantic, google-cloud-firestore, google-cloud-storage, google-genai, flashrank, pytest  
**Storage**: Cloud Firestore (two separate databases/collections: `docs-recibidos` and `docs-enviados`)  
**Testing**: pytest  
**Target Platform**: Google Cloud Run  
**Project Type**: Web Service  
**Performance Goals**: <200ms latency overhead for filtering out chunks from search results  
**Constraints**: Clean Architecture, SOLID, Command Pattern, Repository Pattern  
**Scale/Scope**: Ingestion pipeline codebase (`src/ingestion-pipeline`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Code Quality & Maintainability**: **PASS** - Follows strict naming conventions (e.g. `codcomunicadorecibido` parameter mapping, English parameters on the API payload).
- **Testing Standards & Automation**: **PASS** - Unit tests for the new `POST /api/v1/ingestdocumentreceived` endpoint, updated retrieve endpoint, and vector search repository will be written.
- **UX Consistency & Performance**: **PASS** - Latency for in-memory filtering is minimal (<1ms overhead). Error handling uses structured JSON.
- **SOLID & Clean Architecture**: **PASS** - Segregated use cases (`RetrieveAndGenerateCommand` and `IngestDocumentCommand`), domain routing via `RoutingFirestoreDocumentRepository`.
- **Repository & Command Patterns**: **PASS** - Vector search operations are abstracted by `FirestoreVectorSearchRepository`. No direct database client calls in business logic.
- **UI Pass Verification**: **N/A** - Backend/API only changes.

## Project Structure

### Documentation (this feature)

```text
specs/005-update-retrieve-ingest-received/
├── spec.md              # Specification file
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── checklists/
│   └── requirements.md  # Requirements verification checklist
└── tasks.md             # Phase 2 output (generated separately)
```

### Source Code (repository root)

```text
src/
└── ingestion-pipeline/
    ├── src/
    │   ├── domain/
    │   │   ├── entities.py
    │   │   └── enums.py
    │   ├── repositories/
    │   │   ├── document_repo.py
    │   │   └── vector_search_repo.py
    │   ├── usecases/
    │   │   ├── ingest_document.py
    │   │   └── retrieve_and_generate.py
    │   └── main.py
    └── tests/
        └── unit/
            ├── test_api_retrieve.py
            └── test_api_ingest_received.py
```

**Structure Decision**: Single project layout matching `src/ingestion-pipeline/src/`.

## Complexity Tracking

> *No Constitution violations.*
