# CSV Contract: Restricted Communications Metadata

## Expected Columns
The updated ingestion pipeline only reads the following 7 columns in `Comunicaciones.csv`. All other columns are ignored.

| Column | Required | Description |
|--------|----------|-------------|
| `Id borradores` | Yes | Unique ID of the draft (used for database queries) |
| `Fecha` | Yes | Document date (supports fallback to "UNKNOWN") |
| `Frente` | Yes | Project work front (supports fallback to "GENERAL") |
| `Recibidas` | No | Received document identifier/filename |
| `url Recibidas` | No | Google Drive URL for RECEIVED documents |
| `Enviadas` | No | Sent document identifier/filename |
| `Ubicacion filtradas` | No | Google Drive URL for SENT documents |

## Processing & Skipping Contract
1. **RECEIVED Document**: Processed and saved only if `url Recibidas` contains a valid URL starting with `http`. If it contains `"Sin URL origen"`, `"Sin ruta"`, or is empty, the RECEIVED document is skipped.
2. **SENT Document**: Processed and saved only if `Ubicacion filtradas` contains a valid URL starting with `http`. If it contains `"Sin URL origen"`, `"Sin ruta"`, or is empty, the SENT document is skipped.
3. If both URLs in a row are invalid or empty, the entire row's documents are skipped.
