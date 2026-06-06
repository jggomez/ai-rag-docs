# API Contracts: Ingest Received Document and Exclude Current Document in RAG Retrieval

This document defines the HTTP request and response contracts for the modified and new API endpoints.

## 1. POST `/api/v1/retrieve` (Updated)

Retrieves similar chunks (excluding `codcomunicadorecibido`), resolves linked sent responses, and generates a new draft response.

### Request Body

```json
{
  "url": "https://drive.google.com/file/d/1HPlEkEofIcUBbj4bjY60XEDGwdgUAe3U/view?usp=drivesdk",
  "document_type": "received",
  "filename": "CYS-CW276532-PHI-01193.pdf",
  "codcomunicadorecibido": "CYS-CW276532-PHI-01193",
  "metadata": {
    "work_front": "Descarga intermedia",
    "document_date": "26/02/2025",
    "response_file_url": "INT-OC-CYS-513/25",
    "id_borrador": "76857089"
  }
}
```

- `codcomunicadorecibido` (String, optional): The code identifying the document to exclude from the RAG chunk context during retrieval.

### Response Body (200 OK)

```json
{
  "status": "completed",
  "subject": "RE: Gestión Técnica – Descarga Intermedia...",
  "similar_count": 5,
  "sent_count": 1,
  "gcs_url": "gs://devhack-output/respuesta_Descarga_intermedia_20260606_080000_abc123.pdf"
}
```

---

## 2. POST `/api/v1/ingestdocumentreceived` (New)

Ingests a single received document PDF. If a response URL is provided, it also ingests the corresponding sent document.

### Request Body

```json
{
  "url": "https://drive.google.com/file/d/1HPlEkEofIcUBbj4bjY60XEDGwdgUAe3U/view?usp=drivesdk",
  "metadata": {
    "draft_id": "76857089",
    "document_date": "26/02/2025",
    "work_front": "Descarga intermedia",
    "code": "CYS-CW276532-PHI-01193",
    "response_file_url": "https://drive.google.com/file/d/1wX4UQTO7NKmRNC-bX4scR9PsTHHru7lp/view?usp=drivesdk"
  }
}
```

- `url` (String, required): The URL of the received document PDF.
- `metadata` (Object, required):
  - `draft_id` (String, required): Maps to `id_borrador`.
  - `document_date` (String, required): Maps to `fecha_documento`.
  - `work_front` (String, required): Maps to `frente_trabajo`.
  - `code` (String, required): Identifier used as `nombre_objeto` (received). `code + ".pdf"` is used as `nombre_archivo`.
  - `response_file_url` (String, optional): The URL of the sent response document. If valid, triggers its ingestion.

### Response Body (200 OK)

If both received and sent documents are processed:

```json
{
  "status": "completed",
  "received_document": {
    "document_id": "76857089_REC",
    "filename": "CYS-CW276532-PHI-01193.pdf",
    "document_type": "received"
  },
  "sent_document": {
    "document_id": "76857089_SEN",
    "status": "completed"
  }
}
```

If only the received document is processed:

```json
{
  "status": "completed",
  "received_document": {
    "document_id": "76857089_REC",
    "filename": "CYS-CW276532-PHI-01193.pdf",
    "document_type": "received"
  },
  "sent_document": null
}
```
