# Research: Ingest Received Document and Exclude Current Document in RAG Retrieval

This document logs the research and design decisions made for the implementation of branch `005-update-retrieve-ingest-received`.

## Decision 1: In-Memory Filtering for RAG Chunk Exclusion

### Recommendation
Exclude chunks matching the current document (`codcomunicadorecibido`) in-memory after fetching the initial set of candidate chunks from Firestore.

### Rationale
- **Index Simplification**: Firestore vector search queries (`find_nearest`) combined with `where` metadata filters require complex composite indexes. Adding inequality filters like `!=` on `nombre_objeto` or `id_documento` would require additional composite indexes for every work front, and Firestore has strict limitations on combining inequality filters with vector search.
- **Performance**: Chunks retrieval limit is small (20 candidate chunks). Filtering out matching chunks in-memory takes <1ms and does not impact cross-encoder reranking performance.
- **Robustness**: The in-memory filter can check multiple fields (`id_documento`, `id_borrador`, `nombre_archivo`) to ensure compatibility with both CSV-ingested documents and single-ingested documents.

### Alternatives Considered
- **Firestore Query Filtering**: Use `where("nombre_objeto", "!=", codcomunicadorecibido)` directly in the Firestore query. Rejected due to Firestore index constraints and index creation overhead.

---

## Decision 2: Sequential Ingestion for Received and Sent Documents

### Recommendation
Process the received document first, and then, if a valid `response_file_url` is provided in the metadata, process the sent document sequentially within the same API request.

### Rationale
- **Simplicity & Direct Feedback**: Executing both ingestions synchronously guarantees that both document records are created and chunked before the endpoint returns.
- **Code Reuse**: Reuses `IngestDocumentCommand._run_pipeline` directly.
- **Symmetric Schema**: Replicates the CSV batch ingestion logic where a single record (row) triggers both RECEIVED and SENT pipeline strategies.

### Alternatives Considered
- **Asynchronous/Background Ingestion**: Enqueue ingestion tasks to a task queue. Rejected because the endpoint is designed to return the completion status synchronously, similar to the existing `/api/v1/ingest` single document endpoint.
