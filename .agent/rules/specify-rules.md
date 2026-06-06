# ai-doc-communications Development Guidelines

Auto-generated from all feature plans. Last updated: 2026-06-06

## Active Technologies
- Python 3.11+ + FastAPI (webhook entry), LangChain, google-cloud-firestore, google-cloud-storage, google-generativeai, pydantic (001-rag-document-ingestion)
- Google Cloud Storage (Source), Firestore (Vector Store) (001-rag-document-ingestion)
- Google Cloud Storage (`communications-cys/COMMUNICATION_RECEIVED/`), Firestore (Vector Store) (001-rag-document-ingestion)
- Python >=3.12 + FastAPI, Pydantic, google-cloud-firestore, google-cloud-storage, google-genai, PyMuPDF (003-drive-ingestion-llm-ocr)
- Firestore (metadata), Vector Database (chunks) (003-drive-ingestion-llm-ocr)
- Python 3.11 + FastAPI, Pydantic, google-cloud-firestore, google-cloud-storage, google-genai, flashrank, pytes (005-update-retrieve-ingest-received)
- Cloud Firestore (two separate databases/collections: `docs-recibidos` and `docs-enviados`) (005-update-retrieve-ingest-received)

- (001-rag-document-ingestion)

## Project Structure

```text
src/
tests/
```

## Commands

# Add commands for 

## Code Style

: Follow standard conventions

## Recent Changes
- 005-update-retrieve-ingest-received: Added Python 3.11 + FastAPI, Pydantic, google-cloud-firestore, google-cloud-storage, google-genai, flashrank, pytes
- 003-drive-ingestion-llm-ocr: Added Python >=3.12 + FastAPI, Pydantic, google-cloud-firestore, google-cloud-storage, google-genai, PyMuPDF
- 001-rag-document-ingestion: Added [if applicable, e.g., PostgreSQL, CoreData, files or N/A]


<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
