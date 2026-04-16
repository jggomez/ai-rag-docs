# Research: CSV Metadata Integration

## Decisions

### 1. CSV Processing Strategy
- **Decision**: Use the standard `csv` module with a dictionary-based lookup.
- **Rationale**: For the expected scale of communications (thousands, not millions), loading the CSV into a dictionary indexed by `filename` provides $O(1)$ lookup time per document with minimal memory overhead. Avoids the external dependency of `pandas`.

### CSV Structure Analysis
The sample file `src/resources/Comunicaciones.csv` (actual path: `./src/ingestion-pipeline/resources/Comunicaciones.csv`) has the following headers:
`Id borradores, Fecha, Para, Contrato, Proceso, Frente, Descripcion, Responde a com, Recibidas, Tanexos, Fecha Com, Enviadas`

### Column Specification
- **Remitente**: Mapped from `Para` (e.g., "CYS")
- **Numero de contrato**: Mapped from `Contrato` (e.g., "Contrato CW 276532")
- **Frente de obra**: Mapped from `Frente` (e.g., "Casa de máquinas y obras anexas")
- **Fecha**: Mapped from `Fecha`
- **Proceso**: Mapped from `Proceso`
- **url_archivo_respuesta**: Mapped from `Enviadas` (e.g., "INT-OC-CYS-291/25")

### Filename Resolution
The system will assume the PDF filename in GCS corresponds to the `Enviadas` ID with a `.pdf` extension, potentially replacing forward slashes with underscores if required by the storage bucket conventions.

### 2. CSV Connectivity
- **Decision**: Pass the CSV path via environment variable `METADATA_CSV_PATH`.
- **Rationale**: Follows the existing `python-dotenv` pattern and makes it easy to switch between local development and Cloud Run (using a mounted volume or GCS path).

### 3. Firestore Schema
- **Decision**: Add `sent_file` as an optional top-level field in the `DocumentChunk` document.
- **Rationale**: While it could go in a metadata map, having it as a top-level field allows for easier filtering and indexing in Firestore if needed later.

| CSV Column / API Field | Entity Property | Sample Value |
|-------------------------|-----------------|--------------|
| Para                    | `sender`        | CYS          |
| Contrato                | `contract_number` | Contrato CW 276532 |
| Frente                  | `work_front`    | Casa de máquinas |
| Fecha                   | `document_date` | 26/02/2025   |
| Proceso                 | `process`       | Supervisión técnica |
| Enviadas                | `response_file_url` & `sent_file` | INT-OC-CYS-291/25 |

## Best Practices
- **Validation**: Validate that the CSV contains a header with at least `filename` and `sent_file` columns.
- **Error Handling**: Documents with missing CSV entries should be logged as errors but not halt the entire pipeline execution (graceful degradation).
