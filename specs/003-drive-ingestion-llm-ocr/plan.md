# Implementation Plan: Drive Ingestion and LLM OCR

**Branch**: `003-drive-ingestion-llm-ocr` | **Date**: 2026-04-27 | **Spec**: [spec.md](file:///Users/jggomez/Documents/jggomez/code/ai-doc-communications/specs/003-drive-ingestion-llm-ocr/spec.md)
**Input**: Feature specification from `/specs/003-drive-ingestion-llm-ocr/spec.md`

## Summary

This feature implements a hybrid ingestion pipeline that supports downloading documents from Google Drive URLs provided in a CSV. It distinguishes between "Sent" and "Received" documents: "Sent" documents continue to use the high-precision Regex/File-reading method, while "Received" documents (often scanned) are processed using LLM OCR via the `gemini-3-flash-preview` model. The pipeline is built using Clean Architecture and the Filter/Pipeline pattern.

## Technical Context

**Language/Version**: Python 3.11
**Primary Dependencies**: 
- `google-api-python-client` (Drive API)
- `google-auth-httplib2`, `google-auth-oauthlib` (Google Auth)
- `google-generativeai` (Gemini SDK)
- `fastapi`, `pydantic` (API & Schema)
- `PyMuPDF` (fitz) (Existing PDF extraction)
**Storage**: Google Cloud Storage (for original files), Firestore (for metadata), Vector Database (for chunks)
**Testing**: pytest (Unit & Integration)
**Target Platform**: Linux (Google Cloud Run)
**Project Type**: Web Service / Ingestion Pipeline
**Performance Goals**: <200ms API response (for trigger), asynchronous batch processing for LLM OCR.
**Constraints**: Clean Architecture, SOLID, Command Pattern, Repository Pattern.
**Scale/Scope**: Handling batches of documents from CSV; LLM OCR limited by Gemini API quotas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Code Quality**: Adhere to existing naming conventions in `src/filters` and `src/domain`.
- **II. Testing**: Unit tests for new filters (`DriveDownloader`, `GeminiExtractor` updates). Integration tests for Drive download.
- **IV. SOLID & Clean Architecture**: Logic isolated in Filters; entities updated in Domain layer.
- **V. Repository & Command Patterns**: Use `IngestDocumentCommand` and `CSVMetadataRepository` updates.

## Project Structure

### Documentation (this feature)

```text
specs/003-drive-ingestion-llm-ocr/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0: SDK research and Prompt Engineering
├── data-model.md        # Phase 1: Entity updates
├── quickstart.md        # Phase 1: Setup instructions
├── contracts/           # Phase 1: CSV schema updates
└── tasks.md             # Phase 2: Implementation tasks
```

### Source Code (repository root)

```text
src/ingestion-pipeline/src/
├── domain/
│   ├── entities.py      # Update SourceDocument
│   └── enums.py         # Add DocumentType
├── filters/
│   ├── drive_downloader.py # [NEW] Native Drive API download
│   ├── gemini_extractor.py # Update to use gemini-3-flash-preview and English prompt
│   └── cleaner.py       # Keep existing Regex logic
├── infrastructure/
│   └── repositories/
│       └── csv_metadata_repository.py # Update to handle recibidas_url/enviadas_url
└── usecases/
    ├── builder.py       # Update pipeline construction logic
    └── ingest_document.py # Update batch execution logic
```

**Structure Decision**: Standard Clean Architecture structure within the `ingestion-pipeline` project.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Command Pattern | Encapsulate Use Cases | Standard in project |
| Repository Pattern | Abstract Data Access | Standard in project |
| Clean Architecture | Decoupled Persistence | Standard in project |
