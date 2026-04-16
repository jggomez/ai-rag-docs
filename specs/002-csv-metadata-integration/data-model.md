# Data Model: CSV Metadata Integration & Ingestion API

## Updated Entities

### SourceDocument (Domain)
- `filename`: str (Join key for CSV/API)
- `sender`: str (from `Remitente`)
- `contract_number`: str (from `Numero de contrato`)
- `work_front`: str (from `Frente de obra`)
- `document_date`: str (from `Fecha`)
- `process`: str (from `Proceso`)
- `response_file_url`: Optional[str] (from `url_archivo_respuesta`)
- `metadata`: Dict[str, Any]

### DocumentChunk (Domain)
- `sent_file`: Optional[str] (Mapped from `url_archivo_respuesta`)
- [Existing fields: id, document_id, subject, body, embedding, index]

## Firestore Collection: `DocumentChunk`

| Field | Type | Description |
|-------|------|-------------|
| document_id | String | Reference to parent document |
| subject | String | Cleaned subject |
| body | String | Cleaned body |
| embedding | Vector | 768-dim vector (Google Gemini) |
| index | Number | Chunk index |
| sent_file | String | **(New)** Path to the original sent file (`url_archivo_respuesta`) |
| metadata | Map | Additional document metadata |

## Mappings

| CSV Column / API Field | Entity Property |
|-------------------------|-----------------|
| Remitente | `sender` |
| Numero de contrato | `contract_number` |
| Frente de obra | `work_front` |
| Fecha | `document_date` |
| Proceso | `process` |
| url_archivo_respuesta | `response_file_url` & `sent_file` |
