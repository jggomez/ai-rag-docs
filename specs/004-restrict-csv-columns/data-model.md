# Data Model: Restrict CSV Ingestion Columns

## Entity Mapping & Default Values

Since the CSV schema is restricted to 7 columns, certain fields in the `SourceDocument` (`src/domain/entities.py`) will no longer receive values from the CSV. They will be initialized with the following defaults:

| Field | Source Column | Default Value |
|-------|---------------|---------------|
| `draft_id` | `Id borradores` | MD5 hash of row (if empty) |
| `document_date` | `Fecha` | `"UNKNOWN"` (if empty) |
| `work_front` | `Frente` | `"GENERAL"` (if empty) |
| `sender` | *None (Omitted)* | `"UNKNOWN"` |
| `contract_number` | *None (Omitted)* | `"UNKNOWN"` |
| `process` | *None (Omitted)* | `"UNKNOWN"` |
| `source_url` | `url Recibidas` (RECEIVED) / `Ubicacion filtradas` (SENT) | `None` (if skipped/UNKNOWN) |
| `response_file_url` | `Enviadas` (RECEIVED) / `Ubicacion filtradas` (SENT) | `None` (if skipped/UNKNOWN) |

## State Rules for Skipping Ingestion

A document is only created and processed if its source URL is valid. The following decision tree determines which entities are instantiated and processed:

1. **`url Recibidas` starts with "http"**:
   * Instantiate RECEIVED `SourceDocument` with `id = "{draft_id}_REC"`.
   * Proceed to download from Google Drive and ingest.
2. **`Ubicacion filtradas` starts with "http"**:
   * Instantiate SENT `SourceDocument` with `id = "{draft_id}_SEN"`.
   * Proceed to download from Google Drive and ingest.
3. **If a URL does not start with "http" or matches "Sin ruta" / "Sin URL origen"**:
   * Skip entity creation. No record is created in Firestore or vector database.
