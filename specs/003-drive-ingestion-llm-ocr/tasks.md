# Tasks: Drive Ingestion and LLM OCR

**Feature**: Drive Ingestion and LLM OCR
**Plan**: [plan.md](file:///Users/jggomez/Documents/jggomez/code/ai-doc-communications/specs/003-drive-ingestion-llm-ocr/plan.md)
**Spec**: [spec.md](file:///Users/jggomez/Documents/jggomez/code/ai-doc-communications/specs/003-drive-ingestion-llm-ocr/spec.md)

## Implementation Strategy
We will follow an incremental delivery approach, starting with the core data model and repository updates, followed by the Drive downloader infrastructure. Finally, we will implement the hybrid pipeline logic to enable both Regex and LLM OCR paths.

## Phase 1: Setup
- [X] T001 Initialize research and configuration documentation for Drive and Gemini
- [X] T002 Configure environment variables: `DRIVE_SERVICE_ACCOUNT`, `GEMINI_API_KEY`, `GEMINI_MODEL`

## Phase 2: Foundational (Blocking)
- [X] T003 [P] Add `DocumentType` (SENT, RECEIVED) to `src/ingestion-pipeline/src/domain/enums.py`
- [X] T004 [P] Update `SourceDocument` entity with `document_type` and `source_url` in `src/ingestion-pipeline/src/domain/entities.py`
- [X] T005 [P] Update `CSVMetadataRepository` to support `enviadas_url` and `recibidas_url` columns in `src/ingestion-pipeline/src/infrastructure/repositories/csv_metadata_repository.py`
- [X] T006 [P] Update `DocumentFactory` to assign `DocumentType` based on CSV metadata in `src/ingestion-pipeline/src/domain/factory.py`

## Phase 3: User Story 1 - Batch Ingestion with Drive URLs (Priority: P1)
**Goal**: Trigger batch ingestion from a CSV that contains Google Drive URLs.
**Test Criteria**: Verify files are downloaded from Drive and records created in the document repository.

- [X] T007 [P] [US1] Implement `DriveDownloader` filter using `google-api-python-client` in `src/ingestion-pipeline/src/filters/drive_downloader.py`
- [X] T008 [US1] Integrate `DriveDownloader` into `IngestDocumentCommand` sequence in `src/ingestion-pipeline/src/usecases/ingest_document.py`
- [X] T009 [US1] Create integration test for `DriveDownloader` with mock API in `src/ingestion-pipeline/tests/integration/test_drive_downloader.py`

## Phase 4: User Story 2 - Hybrid Processing Paths (Priority: P1)
**Goal**: Process "Sent" docs with Regex and "Received" docs with LLM OCR.
**Test Criteria**: Verify extraction logic branches correctly based on `DocumentType`.

- [X] T010 [P] [US2] Update `GeminiExtractor` to use `gemini-3-flash-preview` and new English prompt in `src/ingestion-pipeline/src/filters/gemini_extractor.py`
- [X] T011 [US2] Update `PipelineBuilder` logic to branch based on `DocumentType` in `src/ingestion-pipeline/src/usecases/builder.py`
- [X] T012 [US2] Create unit test for `PipelineBuilder` branching logic in `src/ingestion-pipeline/tests/unit/test_pipeline_builder.py`

## Phase 5: User Story 3 - Drive Authentication (Priority: P2)
**Goal**: Securely authenticate with Google Drive for private documents.
**Test Criteria**: Successfully download a non-public file from an authorized Drive folder.

- [X] T013 [US3] Implement Service Account credential loader in `src/ingestion-pipeline/src/infrastructure/auth/google_drive.py`
- [X] T014 [US3] Add authentication error handling and retries in `src/ingestion-pipeline/src/filters/drive_downloader.py`

## Phase 6: User Story 4 - Document Layout Preservation (Priority: P2)
**Goal**: Preserve tables and images as descriptive text in OCR output.
**Test Criteria**: Verify `extracted_text` contains list-based tables and image descriptions.

- [X] T015 [US4] Refine `GeminiExtractor` prompt for table-to-text and image description in `src/ingestion-pipeline/src/filters/gemini_extractor.py`
- [X] T016 [US4] Create functional test with sample scanned document containing tables in `src/ingestion-pipeline/tests/functional/test_llm_ocr_preservation.py`

## Final Phase: Polish & Cross-cutting
- [X] T017 Update pipeline logging to include the chosen processing path (Regex vs LLM)
- [X] T018 Implement 404/Permission handling for Drive URLs with status update to FAILED
- [X] T019 Update `README.md` with Drive ingestion and Gemini OCR configuration steps

## Dependencies
- US1 depends on Phase 2
- US2 depends on US1
- US3 depends on US1
- US4 depends on US2

## Parallel Execution Examples
- [P] T003, T004, T005, T006 can be done in parallel (Domain/Repo updates)
- [P] T007 (Downloader) and T010 (LLM OCR) can be done in parallel
