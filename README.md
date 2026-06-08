# AI RAG Communications — Engineering Ingestion System

An AI-powered Retrieval-Augmented Generation (RAG) system for processing and querying technical engineering communications. It leverages Clean Architecture, the Pipe & Filter pattern, and the Google Gemini API to extract, embed, and store documents in a Firestore vector database.

---

## 🏗 System Architecture

The system is composed of four independent services that work together:

```mermaid
graph LR
    subgraph Frontend
        UI[UI Frontend - Vite/JS]
    end

    subgraph Backend Services
        IP[Ingestion Pipeline - FastAPI]
        AC[Agent Communications - ADK]
    end

    subgraph Infrastructure
        GCS[(Google Cloud Storage)]
        FS[(Firestore Vector DB)]
        ML[MLflow Tracking]
    end

    UI -->|Upload & Ingest| IP
    UI -->|Chat & Query| AC
    IP -->|Save Vectors| FS
    IP -->|Store Files| GCS
    AC -->|Search| FS
    AC -->|Trace| ML
    IP -->|Log| ML
```

---

## 🚀 Key Processes

### 1. Document Ingestion (Received & Sent)
The system differentiates between scanned received documents (OCR needed) and native digital sent documents (PDF Reader).

```mermaid
sequenceDiagram
    participant User as UI/User
    participant API as Ingestion API
    participant GCS as Cloud Storage
    participant Gemini as Gemini 2.5 Flash
    participant DB as Firestore (docs-recibidos/enviados)

    User->>API: POST /api/v1/upload (File + Metadata)
    API->>GCS: Upload to COMMUNICATIONS_[TYPE]/YYYY-MM-DD/
    GCS-->>API: GCS URL
    API-->>User: 200 OK (GCS URL)

    User->>API: POST /api/v1/ingestdocument[type]
    API->>API: Selection of Strategy (OCR vs PDF Reader)
    API->>Gemini: Text Extraction & Cleaning
    API->>Gemini: Vector Embedding (768d)
    API->>DB: Save Document & Chunks (Linked by id_borrador)
    API-->>User: 200 OK (Ingest Complete)
```

### 2. RAG Retrieval & DOCX Generation
Retrieves similar historical context to generate a draft response.

```mermaid
graph TD
    A[UI: Request RAG] --> B[API: Find Source Document]
    B --> C[Extract Text & Vectorize]
    C --> D{Hybrid Search}
    D -- Stage 1 --> E[Front + Dates]
    D -- Stage 2 --> F[Front Only]
    D -- Stage 3 --> G[Dates Only]
    D -- Stage 4 --> H[Global Vector]
    E & F & G & H --> I[Filter: Exclude Source id_borrador]
    I --> J{Results > 0?}
    J -- No --> D
    J -- Yes --> K[TinyBERT Reranking]
    K --> L[Resolve Sent Documents via id_borrador]
    L --> M[Gemini: Generate Response Text]
    M --> N[Generate DOCX & Upload to GCS]
    N --> O[Return DOCX URL to UI]
```

---

## 🆔 Document Identification & Linking

| Identifier | Purpose | Firestore Field |
|---|---|---|
| **Draft ID** | Technical link between Received and Sent pairs. | `id_borrador` |
| **Official Code** | User-facing identifier (e.g. REC-001). | `nombre_objeto` |
| **Filename** | Physical file name in storage. | `nombre_archivo` |

- **RAG Exclusion:** When generating a response for `ID: 1111`, the system retrieves chunks from **other** documents, strictly excluding chunks where `id_borrador == 1111`.
- **Response Resolution:** For every similar chunk found, the system queries the `docs-enviados` collection by `id_borrador` to find the actual historical response.

---

## 🛠 API Reference (Core Endpoints)

### Ingestion Pipeline (:8080)

| Endpoint | Method | Description |
|---|---|---|
| `/api/v1/upload` | `POST` | Uploads file to date-partitioned GCS folder. Returns `gcs_url`. |
| `/api/v1/ingestdocumentreceived` | `POST` | Ingests a received doc. Uses Gemini OCR. |
| `/api/v1/ingestdocumentsent` | `POST` | Ingests a sent doc. Uses PDF Reader. |
| `/api/v1/ingest/batch` | `POST` | Ingests from `Comunicaciones.csv`. Supports `?limit=N`. |
| `/api/v1/generatedocsent` | `POST` | Executes RAG cycle and returns DOCX URL. |

### Agent Communications (:8000)

| Endpoint | Method | Description |
|---|---|---|
| `/run` | `POST` | Main ADK endpoint for chat interactions. |
| `/health` | `GET` | Health status. |

---

## 🧪 Reranker & Models

- **Embedding:** `models/embedding-001` (768 dimensions).
- **Reranker:** `ms-marco-TinyBERT-L-2-v2` via **FlashRank** (Unified across Agent and Pipeline).
- **OCR/Extraction:** `gemini-2.5-flash`.
- **Generation:** `gemini-2.5-flash` (with specific engineering context instructions).

---

## 📖 Setup & Development

See the specific READMEs for detailed installation steps:
- [Ingestion Pipeline Documentation](src/ingestion-pipeline/README.md)
- [Agent Communications Documentation](src/agent-communications/README.md)
- [UI Frontend Documentation](src/ui-ai-comunicados/README.md)
