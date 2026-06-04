# Data Model: Drive Ingestion and LLM OCR

## Updated Entities

### SourceDocument (`src/domain/entities.py`)
| Field | Type | Description |
|-------|------|-------------|
| `document_type` | `DocumentType` | Enum: SENT or RECEIVED |
| `source_url` | `Optional[str]` | The Google Drive URL used for download |

### DocumentType (`src/domain/enums.py`) [NEW]
| Value | Description |
|-------|-------------|
| `SENT` | Documents sent by the organization (Digital-native PDFs) |
| `RECEIVED` | Documents received from external parties (Often scanned images) |

## State Transitions
1. **PENDING**: Initial state after CSV row parsing.
2. **DOWNLOADING**: (Optional) While fetching from Drive.
3. **PROCESSING**: Running the pipeline (either Regex or LLM path).
4. **COMPLETED / FAILED**: Final states.

## Validations
- `source_url` must be a valid Google Drive URL if present.
- `document_type` must be inferred correctly from the CSV column used.
