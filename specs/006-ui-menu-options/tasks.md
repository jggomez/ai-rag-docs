# Tasks: UI Menu Options, Retrieve API Parameters, and RAG Filtering

**Input**: Design documents from `/specs/006-ui-menu-options/`
**Prerequisites**: [plan.md](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/specs/006-ui-menu-options/plan.md) (required), [spec.md](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/specs/006-ui-menu-options/spec.md) (required)

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3, US4)
- Includes exact file paths in descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verification of local setup and dependencies before coding

- [x] T001 Verify existing ingestion pipeline unit tests run successfully using `src/ingestion-pipeline/run_tests.sh`
- [x] T002 Verify existing agent communications unit tests run successfully using `src/agent-communications/run_tests.sh`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared backend API parameter definition and vector search repo modifications

**⚠️ CRITICAL**: Setup of Pydantic schemas and repository pre-filters must complete before testing or frontend integration can begin

- [x] T003 Refactor `RetrieveRequest` Pydantic model in `src/ingestion-pipeline/src/main.py` to support `received_communication_code`, `received_document_id`, `start_date`, `end_date`, and `front` with backward-compatible Spanish aliases
- [x] T004 Update `RetrieveAndGenerateCommand.execute` in `src/ingestion-pipeline/src/usecases/retrieve_and_generate.py` to accept and forward `start_date`, `end_date`, and `front` parameters
- [x] T005 Update `FirestoreVectorSearchRepository._build_filter_stages` in `src/ingestion-pipeline/src/repositories/vector_search_repo.py` to build pre-filtering stages containing `frente_trabajo` (using `front`) and date ranges (using `start_date` `>=` and `end_date` `<=`) on the `fecha_documento` field
- [x] T006 Update `FirestoreVectorSearchRepository.find_similar_chunks` in `src/ingestion-pipeline/src/repositories/vector_search_repo.py` to accept the new optional parameters and execute the query with the constructed pre-filters

**Checkpoint**: Foundation ready - backend retrieval changes are fully implemented and ready for unit testing.

---

## Phase 3: User Story 1 - Multi-Option Navigation Menu (Priority: P1)

**Goal**: Provide side navigation in the frontend UI to switch views

**Independent Test**: Load the dashboard UI in a browser, click each nav button, and verify that the container rendering responds immediately and displays the matching header/layout.

- [x] T007 [US1] Update `src/ui-ai-comunicados/index.html` to add the "Búsqueda RAG" navigation button alongside "Upload Received" (Ingesta) and "AI Agent"
- [x] T008 [US1] Register the new navigation route in `src/ui-ai-comunicados/src/main.js` mapping the `retrieve` route to the `retrieveView` component

---

## Phase 4: User Story 2 - Upload and Ingest Received Document (Priority: P1)

**Goal**: Enable uploading files and submitting them to the visual RAG ingestion pipeline

**Independent Test**: Submit the Ingestion form with metadata and a test PDF, and verify it successfully hits GCS upload and saves the document metadata and chunks in Firestore.

- [x] T009 [P] [US2] Create the `ingestReceivedDocument` client method in `src/ui-ai-comunicados/src/infrastructure/api/ApiRepository.js` to call the `/api/v1/ingestdocumentreceived` endpoint
- [x] T010 [US2] Update `src/ui-ai-comunicados/src/adapters/ui/uploadView.js` to trigger `ingestReceivedDocument` upon successful GCS upload and display the final ingested document ID without generating a response text

---

## Phase 5: User Story 3 - RAG Retrieval with ID/Code and Pre-filtering (Priority: P1)

**Goal**: Retrieve response drafts with pre-filtering by front and date range

**Independent Test**: Query retrieval in the UI with a code and optional pre-filters, verifying that it correctly limits/pre-filters search candidates in Firestore and displays the PDF link and metadata on screen.

- [x] T011 [P] [US3] Create the `searchAndRetrieveDocument` client method in `src/ui-ai-comunicados/src/infrastructure/api/ApiRepository.js` to trigger the `/api/v1/retrieve` API with English snake_case query fields
- [x] T012 [US3] Implement the retrieve view component in `src/ui-ai-comunicados/src/adapters/ui/retrieveView.js` including inputs for code, ID, start/end dates, and front, and rendering search result metadata and the PDF download link
- [x] T013 [P] [US3] Add unit tests in `src/ingestion-pipeline/tests/unit/test_api_retrieve.py` to verify that `POST /api/v1/retrieve` supports both the old/new parameter names and processes date/front filters
- [x] T014 [P] [US3] Add unit tests in `src/ingestion-pipeline/tests/unit/test_vector_search_repo.py` to assert that `_build_filter_stages` correctly builds pre-filtering lists for `frente_trabajo` and `fecha_documento`

---

## Phase 6: User Story 4 - Conversational Chat Agent View (Priority: P1)

**Goal**: Preserve the interactive conversational chat agent view in the dashboard

**Independent Test**: Switch to the "AI Agent" view, send a question, and verify the ADK agent receives and answers the message correctly.

- [x] T015 [US4] Verify that the navigation in `src/ui-ai-comunicados/src/main.js` correctly renders `agentChatView` and preserves chat history/state

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Optimization, cleanup, and validation

- [x] T016 Verify that all tests pass by executing `run_tests.sh` in both the agent and ingestion directories
- [x] T017 Run a local server build of the UI using Vite and verify full end-to-end functionality of all three menu views
- [x] T018 Run the `speckit-analyze` analysis tool to verify that all design, specification, and implementation artifacts are complete and consistent

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS US1, US2, and US3 implementation
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User Story 1 (US1) builds the layout skeleton (sidebar options)
  - User Story 2 (US2) enables ingestion of received documents via the UI
  - User Story 3 (US3) adds retrieve endpoint search with pre-filters
  - User Story 4 (US4) integrates the conversational agent
- **Polish (Phase 7)**: Depends on all user stories being completed

### Parallel Opportunities

- Ingestion API call code (`T009`) and retrieval API call code (`T011`) can be coded in parallel in `ApiRepository.js`
- Backend test additions (`T013`, `T014`) can be written in parallel
- UI changes for the retrieve view (`T012`) can be designed and coded independently from backend test cases once Phase 2 (Foundational) is completed

---

## Implementation Strategy

### MVP First (User Story 1 + 2 + 3)

1. Complete Phase 1: Setup and Phase 2: Foundational.
2. Implement UI layout updates (Phase 3: US1).
3. Complete Phase 4: US2 and verify ingestion uploads.
4. Complete Phase 5: US3 and verify retrieval pre-filtering.
5. Validate all functionality in a local dashboard session.
