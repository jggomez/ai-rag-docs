# Plan: Fix Unit Tests and Update Coverage

## Objective
Fix the 12 failing unit tests in the Ingestion Pipeline caused by recent API schema changes, method signature updates (like `exclude_draft_id` and `limit`), and GCS folder organization.

## Key Files & Context
- `tests/unit/test_api_ingest.py`: Fix `execute_batch` mock assertion and GCS `object_name` path.
- `tests/unit/test_retrieve_command.py`: Fix mocked document metadata extraction and ensure `_generate_query_embedding` is mocked across all tests to avoid Gemini API key errors.
- `tests/unit/test_vector_search_repo.py`: Update `_build_filter_stages` to `_build_robust_fallback_stages` and replace `codcomunicadorecibido` with `exclude_draft_id`.

## Implementation Steps
1.  **test_api_ingest.py**: Update `assert_called_once_with` to include `limit=None` and update `object_name` string in the upload test to include the date folder.
2.  **test_retrieve_command.py**: Add missing `_generate_query_embedding` mocks to `test_fails_when_document_not_found` and `test_fails_when_extracted_text_missing`. Update assertions to check `metadata.get("document_subject")` and `work_front` on the mock.
3.  **test_vector_search_repo.py**: Rename method calls to `_build_robust_fallback_stages` and update the `find_similar_chunks` call to use `exclude_draft_id`.
4.  **Coverage**: Re-run tests to ensure 100% pass rate and update the coverage metrics in the READMEs.

## Verification
- Run `pytest --cov=src tests/unit`.
- All 108 tests must pass.