# Tasks: CSV Metadata Integration & Ingestion API

Feature Branch: `002-csv-metadata-integration`
Status: IN PROGRESS

## Phase 1: Setup & Foundational
- [x] T001 [P] Ensure `SourceDocument` and `DocumentChunk` have `response_file_url` and `sent_file` fields in `src/ingestion-pipeline/src/domain/entities.py`
- [x] T002 [P] Update `IngestRequest` and `GCSEvent` schemas in `src/ingestion-pipeline/src/domain/schemas.py`
- [x] T003 Create `CSVMetadataRepository` in `src/ingestion-pipeline/src/infrastructure/repositories/csv_metadata_repository.py` for $O(1)$ lookups
- [x] T004 Implement `CSVMetadataExtractor` filter in `src/ingestion-pipeline/src/filters/csv_metadata.py`

## Phase 2: User Story 1 - Metadata-Driven Ingestion API [US1]
- [x] T005 [US1] Add `create_from_ingest_request` factory method in `src/ingestion-pipeline/src/domain/factory.py`
- [x] T006 [US1] Refactor `IngestDocumentCommand` in `src/ingestion-pipeline/src/usecases/ingest_document.py` to support `execute_manual`
- [x] T007 [US1] Update `PipelineBuilder` in `src/ingestion-pipeline/src/usecases/builder.py` to integrate `CSVMetadataExtractor` and set `EMBEDDING_MODEL`
- [x] T008 [US1] Implement `POST /ingest` endpoint in `src/ingestion-pipeline/src/main.py` (Now supports CSV batch processing)
- [x] T009 [US1] Create unit tests for `/ingest` endpoint in `tests/test_api_ingest.py`

## Phase 3: User Story 2 - Batch CSV Processing [US2]
- [x] T010 [US2] Implement `batch_ingest.py` script in `src/ingestion-pipeline/scripts/batch_ingest.py`
- [ ] T011 [US2] Create integration test for batch processing in `tests/test_batch_ingest.py`

## Phase 4: User Story 3 - Response File Traceability [US3]
- [x] T012 [US3] Update `TextChunker` in `src/ingestion-pipeline/src/filters/chunker.py` to propagate `response_file_url` to `sent_file`
- [x] T013 [US3] Update `DocumentReader` in `src/ingestion-pipeline/src/filters/reader.py` to correctly set `size_bytes`
- [x] T014 [US3] Verify metadata persistence in Firestore using a test document

## Phase 5: Polish & Cross-Cutting
- [ ] T015 Verify all tests pass with `PYTHONPATH=src uv run pytest`
- [ ] T016 Final documentation update in `README.md` and `spec.md` status
