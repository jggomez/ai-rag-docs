# Tasks: Ingest Received Document and Exclude Current Document in RAG Retrieval

**Input**: Design documents from `/specs/005-update-retrieve-ingest-received/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/api.md

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2)
- Exact file paths are included in the descriptions

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Basic verification of existing setup

- [x] T001 Verify active virtual environment and ensure Firestore credentials are set

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Expose the chunk exclusion logic in the vector search repository

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T002 Implement in-memory chunk filtering by `codcomunicadorecibido` in `find_similar_chunks` in `src/ingestion-pipeline/src/repositories/vector_search_repo.py`

---

## Phase 3: User Story 1 - RAG Retrieval Excluding Current Document (Priority: P1)

**Goal**: Exclude chunks from the current document during retrieve-and-generate RAG search

**Independent Test**: Verify that the generated context in `/api/v1/retrieve` contains no chunks matching `codcomunicadorecibido`

- [x] T003 [P] [US1] Create unit tests in `src/ingestion-pipeline/tests/unit/test_api_retrieve.py` to verify that `POST /api/v1/retrieve` accepts `codcomunicadorecibido` and filters out its chunks
- [x] T004 [US1] Add `codcomunicadorecibido` to `RetrieveRequest` schema and build/map it in `src/ingestion-pipeline/src/main.py`
- [x] T005 [US1] Update `RetrieveAndGenerateCommand` to pass `codcomunicadorecibido` to `find_similar_chunks` in `src/ingestion-pipeline/src/usecases/retrieve_and_generate.py`

**Checkpoint**: At this point, retrieve endpoint works with chunk exclusion and is fully testable

---

## Phase 4: User Story 2 - Ingestion API Endpoint for Received Documents (Priority: P1)

**Goal**: Ingest a single received document and optionally the corresponding sent document if response URL is provided

**Independent Test**: Verify that sending a payload to `/api/v1/ingestdocumentreceived` ingests both files and creates chunks in the respective Firestore collections

- [x] T006 [P] [US2] Create unit tests for the received ingestion endpoint in `src/ingestion-pipeline/tests/unit/test_api_ingest_received.py`
- [x] T007 [US2] Add `IngestReceivedRequest` and `IngestReceivedMetadata` schemas in `src/ingestion-pipeline/src/main.py`
- [x] T008 [US2] Implement the endpoint `POST /api/v1/ingestdocumentreceived` in `src/ingestion-pipeline/src/main.py` to download, process, and save both received and sent documents

**Checkpoint**: Ingestion endpoint is fully functional and unit tests pass

---

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Verification and final cleanup

- [x] T009 Run `run_tests.sh` script to execute all unit tests and verify code correctness
- [x] T010 Run `quickstart.md` curl requests to verify local endpoints

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Can start immediately.
- **Foundational (Phase 2)**: Depends on Setup completion. Blocks US1 and US2.
- **User Story 1 (Phase 3)**: Depends on Phase 2.
- **User Story 2 (Phase 4)**: Depends on Phase 2. Can be implemented in parallel with US1.
- **Polish (Phase 5)**: Depends on Phase 3 and Phase 4 completion.

### Parallel Opportunities

- T003 (US1 tests) and T006 (US2 tests) can be written in parallel.
- US1 (Phase 3) and US2 (Phase 4) can be developed in parallel since they touch different parts of `main.py` and different use cases.

---

## Parallel Example: User Story 1 & 2 Tests

```bash
# Developer A starts US1 tests:
pytest src/ingestion-pipeline/tests/unit/test_api_retrieve.py

# Developer B starts US2 tests:
pytest src/ingestion-pipeline/tests/unit/test_api_ingest_received.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)
1. Complete Setup + Foundational chunk exclusion filter.
2. Complete User Story 1 (RAG retrieve exclusion).
3. Validate US1 unit tests.

### Incremental Delivery
1. Deliver US1 (RAG retrieve exclusion) first.
2. Deliver US2 (new ingestion endpoint) second.
