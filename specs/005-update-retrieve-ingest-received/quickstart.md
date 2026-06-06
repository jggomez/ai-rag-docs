# Quickstart Guide: Ingest Received Document and Exclude Current Document in RAG Retrieval

This guide details how to run, test, and verify the changes implemented in branch `005-update-retrieve-ingest-received`.

## 1. Running the Ingestion Service Locally

Navigate to `src/ingestion-pipeline` and start the server:

```bash
cd src/ingestion-pipeline
source .venv/bin/activate
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

---

## 2. Verifying the Retrieval Endpoint with Exclusion

Send a POST request to `/api/v1/retrieve` with the `codcomunicadorecibido` parameter.

```bash
curl -X POST http://localhost:8000/api/v1/retrieve \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://drive.google.com/file/d/1HPlEkEofIcUBbj4bjY60XEDGwdgUAe3U/view?usp=drivesdk",
    "document_type": "received",
    "codcomunicadorecibido": "CYS-CW276532-PHI-01193",
    "metadata": {
      "work_front": "Descarga intermedia",
      "document_date": "26/02/2025",
      "response_file_url": "INT-OC-CYS-513/25",
      "id_borrador": "76857089"
    }
  }'
```

Verify that in the logs, the vector search returned similar chunks from other documents, but completely excluded any chunk whose parent document identifier or file/object name matched `CYS-CW276532-PHI-01193`.

---

## 3. Verifying the Ingestion Endpoint for Received Documents

Send a POST request to `/api/v1/ingestdocumentreceived` with a valid `response_file_url`.

```bash
curl -X POST http://localhost:8000/api/v1/ingestdocumentreceived \
  -H "Content-Type: application/json" \
  -d '{
    "url": "https://drive.google.com/file/d/1HPlEkEofIcUBbj4bjY60XEDGwdgUAe3U/view?usp=drivesdk",
    "metadata": {
      "draft_id": "76857089",
      "document_date": "26/02/2025",
      "work_front": "Descarga intermedia",
      "code": "CYS-CW276532-PHI-01193",
      "response_file_url": "https://drive.google.com/file/d/1wX4UQTO7NKmRNC-bX4scR9PsTHHru7lp/view?usp=drivesdk"
    }
  }'
```

Verify the JSON response confirms successful ingestion for both the RECEIVED document and the corresponding SENT response document.

---

## 4. Running the Automated Tests

Execute the unit tests to verify both endpoints:

```bash
cd src/ingestion-pipeline
pytest tests/unit/
```
