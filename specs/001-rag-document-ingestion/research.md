# Research: RAG Document Ingestion Pipeline

## Firestore Vector Search Integration
**Decision**: Use Firestore's native `@google-cloud/firestore` (or equivalent Python SDK) with vector search capabilities.
**Rationale**: Firestore now supports vector embeddings and similarity search (k-NN) natively. This aligns with ADR 06.
**Alternatives considered**: Pinecone (external dependency), Vertex AI Vector Search (higher cost/complexity for this scale).

## LangChain + Firestore Best Practices
**Decision**: Use LangChain's `RecursiveCharacterTextSplitter` for semantic chunking and integrate with a custom Firestore vector store class if a native one isn't fully mature in the SDK.
**Rationale**: LangChain provides robust, customizable splitters. Firestore integration ensures we stay within the GCP ecosystem.

## Cloud Run Event-Driven Trigger
**Decision**: Use **Cloud Storage Triggers for Cloud Run** (Eventarc) specifically monitoring `communications-cys` bucket.
**Rationale**: Eventarc allows us to filter events by bucket and prefix. We will configure it to trigger when a `google.storage.object.v1.finalized` event is received for objects with the prefix `COMMUNICATION_RECEIVED/`. This automates the orchestration part of our Pipe & Filter pattern.

## Pipe and Filter Implementation
**Decision**: Implement as a series of asynchronous functions (Filters) orchestrated by a main Command.
**Rationale**: Matches ADR 03 and ADR 04. Each filter (e.g., `DocumentReader`, `TextChunker`, `VectorEmbedder`) is a standalone unit of logic.

## Vector DB Segmentation (Received vs Sent)
**Decision**: Use two separate Firestore collections: `received_vectors` and `sent_vectors`.
**Rationale**: Aligns with ADR 14. Separate collections allow for optimized indexing and easier management of data lifecycles while using the same database instance.

## Package Management
**Decision**: Use `uv` for dependency management and project build.
**Rationale**: `uv` is significantly faster than pip/poetry, provides reproducible environments via `uv.lock`, and simplifies the build process with a single tool.

## User Interface Requirements
**Decision**: No user interface (Web/Frontend) will be developed for this feature.
**Rationale**: This is a backend ingestion pipeline triggered automatically by storage events. Any interaction with the data will happen through existing system interfaces or developer tools.
