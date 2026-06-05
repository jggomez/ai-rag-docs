# Implementation Plan: Restrict CSV Ingestion Columns

**Branch**: `004-restrict-csv-columns` | **Date**: 2026-06-05 | **Spec**: [spec.md](file:///Users/jggomez/Documents/jggomez/consultorias/ai-doc-communications/ai-rag-docs/specs/004-restrict-csv-columns/spec.md)
**Input**: Feature specification from `/specs/004-restrict-csv-columns/spec.md`

## Summary

This feature restricts the CSV ingestion pipeline to parse only 7 core columns (`Id borradores`, `Fecha`, `Frente`, `Recibidas`, `url Recibidas`, `Enviadas`, `Ubicacion filtradas`) from the communications file, ignoring any extra columns. It also updates the pipeline to apply default fallbacks for missing mandatory columns and skip GCS/Drive processing completely for documents with `UNKNOWN` or placeholder URLs ("Sin ruta", "Sin URL origen"), validating and saving each document (RECEIVED and SENT) independently.

## Technical Context

**Language/Version**: Python >=3.12  
**Primary Dependencies**: FastAPI, Pydantic, google-cloud-firestore, google-cloud-storage, google-genai, PyMuPDF  
**Storage**: Firestore (metadata), Vector Database (chunks)  
**Testing**: pytest, pytest-asyncio  
**Target Platform**: Linux (Google Cloud Run)
**Project Type**: Web Service / Ingestion Pipeline  
**Performance Goals**: <200ms API response trigger, asynchronous batch execution  
**Constraints**: Clean Architecture, SOLID, Command Pattern, Repository Pattern  
**Scale/Scope**: Local CSV files up to 1000+ rows, Firestore DB entries  

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **I. Code Quality**: Adhere to existing patterns in `src/filters` and `src/domain`.
- **II. Testing Standards**: Unit tests for updated `SourceDocumentFactory` and `CSVMetadataRepository`. Integration tests for batch ingestion skipping logic.
- **IV. SOLID & Clean Architecture**: Decouple domain entities from CSV format; mapping logic is kept within the Factory and Repository layers.
- **V. Repository & Command Patterns**: Abstract CSV data loading through `CSVMetadataRepository`, trigger actions via `IngestDocumentCommand` use cases.

## Project Structure

### Documentation (this feature)

```text
specs/004-restrict-csv-columns/
├── spec.md              # Feature specification
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
└── contracts/
    └── csv_schema.md    # Phase 1 output
```

### Source Code (repository root)

```text
src/ingestion-pipeline/src/
├── domain/
│   ├── constants.py      # Restrict CSV column definitions
│   └── factory.py        # Update factory to parse only 7 columns, apply fallbacks, separate SENT/RECEIVED skipping
├── infrastructure/
│   └── repositories/
│       └── csv_metadata_repository.py # Update row iteration & key checks
└── usecases/
    ├── builder.py        # Double check branching logic
    └── ingest_document.py # Double check ingestion skipping logic
```

**Structure Decision**: Clean Architecture directories within `src/ingestion-pipeline/src/` will be updated to handle the new domain requirements.

## Complexity Tracking

*None (Constitution Check has no violations).*
