# Research: Restrict CSV Ingestion Columns

## Python CSV Parsing Decision
* **Decision**: Continue using `csv.DictReader` for loading rows.
* **Rationale**: `csv.DictReader` exposes each row as a standard Python dictionary. If extra columns are present in the CSV file, they are loaded but can simply be ignored by not accessing their keys. If optional columns are missing entirely from the CSV, `row.get(column_name)` returns `None` safely.
* **Alternatives Considered**: Direct string parsing (rejected because it doesn't handle comma-escaping or quoted fields correctly).

## Skip & Filter Logic
* **Decision**: Perform URL validation and skip filtering at the `SourceDocumentFactory` level before `SourceDocument` instances are created.
* **Rationale**: By filtering out documents with invalid/UNKNOWN/placeholder URLs in `SourceDocumentFactory.create_documents_from_csv_row`, we prevent the downstream pipeline (downloaders, cleaners, embedding generators, and repositories) from ever receiving invalid documents.
* **Skipping Rules**:
  * Any URL containing "Sin ruta", "Sin URL origen", or not starting with "http" is classified as invalid/UNKNOWN.
  * If the RECEIVED URL is invalid, no RECEIVED `SourceDocument` is generated.
  * If the SENT URL is invalid, no SENT `SourceDocument` is generated.
  * This guarantees that ONLY valid documents are passed into the pipeline.

## Fallback Values for Mandatory Columns
* **Decision**: If core fields are missing in the row:
  * `Id borradores` -> Generate MD5 hash of the entire row dictionary to ensure a deterministic and unique ID.
  * `Fecha` -> Fallback to "UNKNOWN".
  * `Frente` -> Fallback to "GENERAL".
* **Rationale**: Ensures the parser remains robust and never crashes due to empty rows or partial input formats.
