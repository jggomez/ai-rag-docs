# Plan: Implement Ingest Sent Document Endpoint

## Objective
Create a new endpoint `/api/v1/ingestdocumentsent` to explicitly handle the ingestion (chunking and indexing) of sent documents and store them in the `docs-enviados` collection, mirroring the existing ingestion process but targeting the correct collection and pipeline strategy.

## Key Files & Context
- `src/ingestion-pipeline/src/main.py`: Will contain the new endpoint definition and schema updates.
- `src/ingestion-pipeline/src/domain/entities.py`: `SourceDocument` schema (already supports `response_file_url`).
- `src/ui-ai-comunicados/src/infrastructure/api/ApiRepository.js`: (Optional, but good if the UI needs to call it later).
- `src/ingestion-pipeline/tests/unit/test_api.py` or similar: (We need to add tests for the new endpoint).

## Implementation Steps

1.  **Refactor Request Schema in `main.py`**:
    - Rename `IngestReceivedRequest` to `IngestDocumentRequest` to reflect its general use for both received and sent documents.

2.  **Refactor Document Builder in `main.py`**:
    - Rename `_build_received_document` to `_build_source_document`.
    - Update the logic so that if the document is `SENT`, it correctly maps `request.url_doc` to `response_file_url` initially (though `DriveDownloader` will ultimately update it after re-uploading to the correct GCS prefix).

3.  **Implement the New Endpoint in `main.py`**:
    - Create `@app.post("/api/v1/ingestdocumentsent")`.
    - The endpoint will accept `IngestDocumentRequest`.
    - It will explicitly force `request.document_type = "sent"` to guarantee the correct pipeline strategy (`_build_sent_strategy`: PDF Reader -> Cleaner) and Firestore destination (`docs-enviados`).
    - It will execute the pipeline using `ingest_command._run_pipeline`.

4.  **Update Existing Endpoint in `main.py`**:
    - Ensure `/api/v1/ingestdocumentreceived` explicitly forces `request.document_type = "received"` to prevent cross-contamination.

5.  **Testing**:
    - Add unit tests in `src/ingestion-pipeline/tests/unit/test_api.py` to verify the new endpoint correctly sets the type to `SENT` and processes the request successfully.

## Verification & Testing
- Send a request to `/api/v1/ingestdocumentsent` with a test PDF.
- Verify that the API returns a 200 OK.
- Verify that the document is correctly processed using the SENT strategy (PDF Reader vs Gemini OCR).