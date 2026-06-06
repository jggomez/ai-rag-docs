# Implementation Plan: UI Menu Options, Retrieve API Parameters, and RAG Filtering

**Branch**: `006-ui-menu-options` | **Date**: 2026-06-06 | **Spec**: [spec.md](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/specs/006-ui-menu-options/spec.md)

## Summary

Implement UI and backend changes to enable a multi-option dashboard:
1. **Frontend Navigation Menu**: Add a three-option menu in `index.html` and `main.js`:
   - Ingestion (Form + upload file + `/api/v1/ingestdocumentreceived`).
   - Búsqueda RAG (Form + `/api/v1/retrieve` with filtering options).
   - Chat Agent (Conversational interface).
2. **Backend Retrieve API Updates**:
   - Update `RetrieveRequest` in `main.py` to accept parameters in English snake_case format (`received_communication_code`, `received_document_id`, `start_date`, `end_date`, `front`) using Pydantic aliases to preserve backwards compatibility.
   - Update `RetrieveAndGenerateCommand` to pass these new parameters to `FirestoreVectorSearchRepository`.
3. **RAG Pre-Filtering**:
   - Pre-filter vector search results in Firestore by both `front` (mapped to `frente_trabajo` in Firestore) and date range `start_date` and `end_date` (mapped to `fecha_documento` in Firestore) if provided, filtering first before performing vector similarity search.

## Technical Context

- **Language/Version**: Python 3.12, JavaScript (ES6 Modules)
- **Primary Dependencies**: FastAPI, Pydantic, google-cloud-firestore, google-cloud-storage, google-genai, flashrank, Tailwind CSS, Vite
- **Storage**: Cloud Firestore (`docs-recibidos` and `docs-enviados` databases)
- **Testing**: pytest
- **Constraints**: Follow Clean Architecture, SOLID, and Pydantic validation. Use English names for all new/updated parameters.

## Constitution Check

- **Code Quality & Maintainability**: **PASS** - New parameters use English names and snake_case format.
- **UX Consistency & Performance**: **PASS** - Form layouts match existing styles; in-memory filtering adds minimal latency.
- **SOLID & Clean Architecture**: **PASS** - Use cases remain segregated. Vector pre/post-filtering logic is encapsulated in `FirestoreVectorSearchRepository`.

## Affected Files

### 1. Ingestion Pipeline Backend (src/ingestion-pipeline/)
- [main.py](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/src/ingestion-pipeline/src/main.py):
  - Refactor `RetrieveRequest` Pydantic model to use English snake_case parameters with Pydantic aliases (`validation_alias=AliasChoices(...)`).
  - Update `retrieve_document` endpoint to extract and forward `start_date`, `end_date`, and `front` to the use case.
- [retrieve_and_generate.py](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/src/ingestion-pipeline/src/usecases/retrieve_and_generate.py):
  - Update `RetrieveAndGenerateCommand.execute` signature to accept `start_date`, `end_date`, and `front`.
  - Pass these filters to `vector_search_repo.find_similar_chunks`.
- [vector_search_repo.py](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/src/ingestion-pipeline/src/repositories/vector_search_repo.py):
  - Update `find_similar_chunks` signature to accept `start_date`, `end_date`, and `front`.
  - Update `_build_filter_stages` to construct composite query pre-filter conditions including `frente_trabajo` and `fecha_documento` (using `>=` for `start_date` and `<=` for `end_date`).
  - Execute pre-filtered vector queries using progressive fallbacks.

### 2. Backend Unit & Integration Tests (src/ingestion-pipeline/)
- [test_api_retrieve.py](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/src/ingestion-pipeline/tests/unit/test_api_retrieve.py): Update and add tests validating retrieve requests with both old and new fields, as well as date/front filters.
- [test_vector_search_repo.py](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/src/ingestion-pipeline/tests/unit/test_vector_search_repo.py): Add unit tests validating correct front pre-filtering and date-range post-filtering.
- [test_retrieve_command.py](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/src/ingestion-pipeline/tests/unit/test_retrieve_command.py): Verify command execution propagates date and front filters correctly.

### 3. Frontend UI (src/ui-ai-comunicados/)
- [index.html](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/src/ui-ai-comunicados/index.html): Add navigation buttons for "Ingesta", "Búsqueda RAG", and "Chat de Agente".
- [main.js](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/src/ui-ai-comunicados/src/main.js): Add route mappings and handle switching to the new retrieve view.
- [ApiRepository.js](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/src/ui-ai-comunicados/src/infrastructure/api/ApiRepository.js):
  - Add `ingestReceivedDocument` targeting `/api/v1/ingestdocumentreceived`.
  - Add `searchAndRetrieveDocument` targeting `/api/v1/retrieve` using new English parameters.
- [uploadView.js](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/src/ui-ai-comunicados/src/adapters/ui/uploadView.js):
  - Update submission handling to call GCS upload and then call `ingestReceivedDocument`.
  - Show success feedback (generated document ID, filename, type) without generating response text.
- [retrieveView.js](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/src/ui-ai-comunicados/src/adapters/ui/retrieveView.js) *(New File)*:
  - Implement form for RAG Retrieval view with input fields:
    - Received Communication Code (`received_communication_code`)
    - Received Document ID (`received_document_id`)
    - Start Date (`start_date`, date picker)
    - End Date (`end_date`, date picker)
    - Work Front (`front`)
  - Render search results: similar chunk count, sent document count, subject, and PDF download link.

## Implementation Steps

### Phase 1: Backend Implementation
1. **Update Pydantic Schema**: Modify `RetrieveRequest` in `main.py` using `AliasChoices` for backward-compatible snake_case parameter mapping.
2. **Update Usecase & Command**: Modify `RetrieveAndGenerateCommand` to pass new filters.
3. **Implement RAG Filtering**:
   - Update `FirestoreVectorSearchRepository.find_similar_chunks` to build stages using pre-filters for `front` (stage `frente_trabajo`) and date ranges (`fecha_documento` inequalities).
   - Execute the Firestore vector queries with the applied pre-filter conditions.
4. **Run Tests**: Execute `run_tests.sh` to verify everything is green.

### Phase 2: Frontend Implementation
1. **Update ApiRepository.js**: Add new API call methods.
2. **Create Retrieve View**: Code `retrieveView.js` with the clean form and result presentation (only showing metadata + PDF download link).
3. **Refactor Ingestion View**: Modify `uploadView.js` to trigger GCS upload followed by `/api/v1/ingestdocumentreceived`.
4. **Update Layout and Router**: Connect navigation sidebar options in `index.html` and routing in `main.js`.
5. **Verify Locally**: Build and run UI to visually verify the views.
