# CSV Contract: Communications Metadata

## Expected Columns
The ingestion pipeline now supports the following columns in `Comunicaciones.csv`:

| Column | Required | Description |
|--------|----------|-------------|
| `Enviadas` | No | Current document ID/filename for "Sent" docs (Legacy) |
| `Recibidas` | No | Current document ID/filename for "Received" docs (Legacy) |
| `enviadas_url` | No | **[NEW]** Google Drive URL for Sent documents |
| `recibidas_url` | No | **[NEW]** Google Drive URL for Received documents |
| `Descripcion` | No | Fallback text content (Legacy) |
| `Para` | No | Sender/Recipient info |
| `Contrato` | No | Contract number |
| `Frente` | No | Work front |
| `Fecha` | No | Document date |

## Processing Priority
1. If `recibidas_url` is present → Type = RECEIVED, use LLM OCR.
2. Else if `enviadas_url` is present → Type = SENT, use Regex Path.
3. Else if `Enviadas` is present → Legacy behavior.
