# Tasks: Restrict CSV Ingestion Columns

**Input**: Design documents from `/specs/004-restrict-csv-columns/`
**Prerequisites**: plan.md (required), spec.md (required for user stories), research.md, data-model.md, contracts/csv_schema.md

**Tests**: Tests are included to satisfy the project constitution's verification standards.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Paths assume single project within `src/ingestion-pipeline/` - paths are relative to the repository root.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Project initialization and validation of environment configurations.

- [x] T001 Verify local environment variables and test configurations in `src/ingestion-pipeline/.env`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core model updates that must be complete before any user story can be implemented.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [x] T002 Update CSV column constant definitions in `src/ingestion-pipeline/src/domain/constants.py` to deprecate unused fields
- [x] T003 [P] Update default parameters in `SourceDocument` entity in `src/ingestion-pipeline/src/domain/entities.py`

**Checkpoint**: Foundation ready - user story implementation can now begin.

---

## Phase 3: User Story 1 - Reduced CSV Schema Validation (Priority: P1) 🎯 MVP

**Goal**: Parse communications CSV containing only the 7 allowed columns.

**Independent Test**: Verify that a CSV with only the 7 allowed columns is parsed successfully without raising missing column errors.

### Tests for User Story 1
- [x] T004 [P] [US1] Create unit tests in `src/ingestion-pipeline/tests/unit/test_csv_parser.py` to verify parsing with only 7 columns

### Implementation for User Story 1
- [x] T005 [US1] Update `CSVMetadataRepository` in `src/ingestion-pipeline/src/infrastructure/repositories/csv_metadata_repository.py` to only access the restricted columns
- [x] T006 [US1] Update `SourceDocumentFactory` in `src/ingestion-pipeline/src/domain/factory.py` to parse only the allowed columns

**Checkpoint**: At this point, User Story 1 should be fully functional and testable independently.

---

## Phase 4: User Story 2 - Metadata Mapping to Entities (Priority: P1)

**Goal**: Ensure parsed documents have metadata mapped correctly and unmapped fields default to "UNKNOWN".

**Independent Test**: Check that Firestore entries contain `draft_id`, `document_date`, `work_front`, and default unmapped fields.

### Tests for User Story 2
- [x] T007 [P] [US2] Create unit tests in `src/ingestion-pipeline/tests/unit/test_document_factory_mapping.py` to verify mapping of fallback defaults when CSV fields are empty

### Implementation for User Story 2
- [x] T008 [US2] Implement fallback defaults in `SourceDocumentFactory.create_documents_from_csv_row` in `src/ingestion-pipeline/src/domain/factory.py` for empty mandatory columns

**Checkpoint**: At this point, User Stories 1 and 2 should both work independently.

---

## Phase 5: User Story 3 - Independent Row Document Processing (Priority: P1)

**Goal**: Process RECEIVED and SENT documents from the same CSV row independently and skip UNKNOWN/placeholder URLs.

**Independent Test**: Ingest a row with one valid and one UNKNOWN URL, verify only the valid document is created in Firestore and chunks generated.

### Tests for User Story 3
- [x] T009 [P] [US3] Create integration tests in `src/ingestion-pipeline/tests/integration/test_skipping_logic.py` to verify independent processing and skipping of placeholder URLs

### Implementation for User Story 3
- [x] T010 [US3] Implement URL validation and skip filtering in `SourceDocumentFactory.create_documents_from_csv_row` in `src/ingestion-pipeline/src/domain/factory.py` to skip documents with placeholder URLs
- [x] T011 [US3] Update use case logic in `src/ingestion-pipeline/src/usecases/ingest_document.py` to ensure skipped documents do not trigger downloads or database writes

**Checkpoint**: All user stories should now be independently functional.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Final cleanups, verification, and verification script testing.

- [x] T012 Update sample CSV file in `src/ingestion-pipeline/resources/Comunicaciones_Test.csv` to match the 7-column schema
- [x] T013 Run all tests in `src/ingestion-pipeline/tests/` to check for regressions
- [x] T014 Run validation steps documented in `specs/004-restrict-csv-columns/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies - can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion - BLOCKS all user stories
- **User Stories (Phase 3+)**: All depend on Foundational phase completion
  - User stories can then proceed in parallel or sequentially in priority order (P1 → P2 → P3)
- **Polish (Final Phase)**: Depends on all user stories being complete

### Parallel Opportunities

- Foundational tasks marked [P] can run in parallel (T003)
- Tests marked [P] can run in parallel with each other (T004, T007, T009)
- Once Phase 2 is complete, US1, US2, and US3 can be worked on in parallel by different developers

---

## Parallel Example: User Story 1

```bash
# Launch test and implementation tasks together:
Task: "Create unit tests in src/ingestion-pipeline/tests/unit/test_csv_parser.py"
Task: "Update SourceDocumentFactory in src/ingestion-pipeline/src/domain/factory.py to parse only the allowed columns"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: Verify User Story 1 independently

### Incremental Delivery

1. Complete Setup + Foundational → Foundation ready
2. Add User Story 1 → Test independently (MVP!)
3. Add User Story 2 → Test independently
4. Add User Story 3 → Test independently
5. Complete Polish phase
