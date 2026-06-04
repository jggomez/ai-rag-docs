import logging
import os
import mlflow
from typing import Optional, Union
from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from src.config import settings
from src.domain.schemas import GCSEvent
from src.domain.enums import DocumentStatus, DocumentType
from src.domain.entities import SourceDocument
from src.repositories.storage_repo import GCSStorageRepository
from src.repositories.document_repo import RoutingFirestoreDocumentRepository
from src.infrastructure.repositories.csv_metadata_repository import CSVMetadataRepository
from src.usecases.builder import PipelineBuilder
from src.usecases.ingest_document import IngestDocumentCommand
from src.usecases.retrieve_and_generate import RetrieveAndGenerateCommand

# Configure MLflow Tracing for LLMs
try:
    # Force local tracking URI
    tracking_uri = os.environ.get("MLFLOW_TRACKING_URI", "http://localhost:5001")
    mlflow.set_tracking_uri(tracking_uri)
    
    # Set or create experiment
    experiment_name = "ingestion-pipeline"
    mlflow.set_experiment(experiment_name)

    # Enable automatic tracing for LangChain
    mlflow.langchain.autolog()
    # Enable automatic tracing for Google GenAI SDK (Gemini)
    mlflow.gemini.autolog()
    
    logger_mlflow = logging.getLogger("mlflow")
    logger_mlflow.info(f"MLflow LLM autologging enabled at {tracking_uri} [Exp: {experiment_name}]")
except Exception as e:
    print(f"Warning: Could not initialize MLflow autologging: {e}")

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Ingestion Pipeline")

# Enable CORS for frontend integration
allow_origins_str = os.environ.get("ALLOW_ORIGINS", "*")
if allow_origins_str == "*":
    allow_origins = ["*"]
    allow_credentials = False
else:
    allow_origins = [origin.strip() for origin in allow_origins_str.split(",") if origin.strip()]
    allow_credentials = True

app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic Schemas for single ingest
class IngestRequestMetadata(BaseModel):
    sender: str
    contract_number: str
    work_front: str
    document_date: str
    process: str
    response_file_url: Optional[str] = None
    id_borrador: Optional[str] = None
    
    model_config = {
        "extra": "allow"
    }

class SingleIngestRequest(BaseModel):
    url: str = Field(..., description="The Drive or GCS file URL")
    document_type: str = Field(..., description="Must be either 'sent' or 'received'")
    filename: Optional[str] = Field(None, description="Optional custom filename/identifier")
    metadata: IngestRequestMetadata

# 1. Dependency injection and wiring
storage_repo = GCSStorageRepository()
document_repo = RoutingFirestoreDocumentRepository(
    database_received=settings.firestore_database_received,
    database_sent=settings.firestore_database_sent
)
csv_metadata_repo = CSVMetadataRepository(settings.metadata_csv_path)

# 2. Initialize the Builder service with settings
pipeline_builder = PipelineBuilder(settings)

# 3. Construct the default ingestion pipeline (legacy/GCS)
default_pipeline = pipeline_builder.build_ingestion_pipeline(
    storage_repo, 
    document_repo,
    csv_metadata_repo=csv_metadata_repo
)

# 4. Inject document_repo and the builder into the command
ingest_command = IngestDocumentCommand(
    document_repo=document_repo, 
    pipeline_builder=pipeline_builder,
    default_pipeline=default_pipeline
)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/api/v1/upload")
async def upload_file_to_gcs(file: UploadFile = File(...)):
    """
    Upload a communication file directly to GCS in the ingestion bucket/prefix.
    """
    try:
        content = await file.read()
        object_name = f"{settings.gcs_ingestion_prefix}{file.filename}"
        logger.info(f"Uploading file {file.filename} to GCS bucket {settings.gcs_ingestion_bucket} as {object_name}...")
        
        gcs_url = storage_repo.upload_file(
            bucket_name=settings.gcs_ingestion_bucket,
            object_name=object_name,
            content=content,
            content_type=file.content_type
        )
        
        logger.info(f"File uploaded successfully. GCS URL: {gcs_url}")
        return {
            "status": "success",
            "gcs_url": gcs_url,
            "filename": file.filename
        }
    except Exception as e:
        logger.error(f"Error uploading file to GCS: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to upload file: {str(e)}")

@app.post("/api/v1/ingest/batch")
async def ingest_batch_csv():
    """
    Trigger batch ingestion for all records in the local communications.csv file.
    This uses the strategy-based pipeline selection inside the command.
    """
    try:
        logger.info(f"Starting batch ingestion from local CSV: {settings.metadata_csv_path}")
        
        result = ingest_command.execute_batch(csv_metadata_repo)
        
        return {
            "status": "completed", 
            "processed_records": result["processed_records"],
            "total_records": result["total_records"]
        }
    except Exception as e:
        logger.error(f"Error in CSV batch ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

def _sanitize_header_value(val: str) -> str:
    """Sanitize header values to be ASCII compatible by converting accented characters
    and replacing common non-ASCII symbols.
    """
    if not val:
        return ""
    import unicodedata
    replacements = {
        "\u2013": "-",  # en dash
        "\u2014": "-",  # em dash
        "\u2018": "'",  # left single quote
        "\u2019": "'",  # right single quote
        "\u201c": '"',  # left double quote
        "\u201d": '"',  # right double quote
    }
    for char, repl in replacements.items():
        val = val.replace(char, repl)
        
    normalized = unicodedata.normalize('NFKD', val)
    return normalized.encode('ascii', errors='ignore').decode('ascii')


def _build_document_from_request(request: Union[SingleIngestRequest, "RetrieveRequest"]) -> SourceDocument:
    """Builder method to construct a SourceDocument from an HTTP request."""
    # Resolve doc type & ID
    doc_type_str = request.document_type.lower().strip()
    doc_type = DocumentType.RECEIVED if doc_type_str == "received" else DocumentType.SENT
    temp_id = f"single_ingest_{'REC' if doc_type == DocumentType.RECEIVED else 'SEN'}"

    # Extract clean filename
    req_filename = getattr(request, "filename", None)
    if req_filename:
        filename = req_filename.strip()
    else:
        clean_url = request.url.split("?")[0]
        filename = os.path.basename(clean_url) or "document.pdf"
        
    if not filename.lower().endswith(".pdf"):
        filename = f"{filename}.pdf"

    # Optimize Extra Meta parsing natively in Pydantic O(1)
    extra_meta = request.metadata.model_dump(
        exclude={"sender", "contract_number", "work_front", "document_date", "process", "response_file_url", "id_borrador"},
        exclude_none=True
    )

    # Apply symmetric URL cross-mapping
    if doc_type == DocumentType.RECEIVED:
        extra_meta["url_recibido"] = request.url
        if request.metadata.response_file_url:
            extra_meta["url_enviado"] = request.metadata.response_file_url
    else:
        extra_meta["url_enviado"] = request.url
        if request.metadata.response_file_url:
            extra_meta["url_recibido"] = request.metadata.response_file_url

    # Ensure draft_id is not null
    draft_id = request.metadata.id_borrador
    if not draft_id:
        import uuid
        draft_id = f"single_ingest_{uuid.uuid4().hex[:8]}"

    # Return constructed domain entity
    return SourceDocument(
        id=temp_id,
        filename=filename,
        bucket="SINGLE_API",
        object_name=filename,
        content_type="application/pdf",
        size_bytes=0,
        status=DocumentStatus.PENDING,
        document_type=doc_type,
        source_url=request.url,
        sender=request.metadata.sender,
        contract_number=request.metadata.contract_number,
        work_front=request.metadata.work_front,
        document_date=request.metadata.document_date,
        process=request.metadata.process,
        response_file_url=request.metadata.response_file_url,
        draft_id=draft_id,
        metadata=extra_meta
    )


@app.post("/api/v1/ingest")
async def ingest_single_document(request: SingleIngestRequest):
    """
    Trigger ingestion for a single document URL with its metadata.
    Automatically handles routing, URL cross-referencing and strategy selection.
    """
    try:
        # Validate early
        if request.document_type.lower().strip() not in ("sent", "received"):
            raise HTTPException(
                status_code=400, 
                detail="document_type must be either 'sent' or 'received'"
            )

        # Delegate document construction (SRP)
        doc = _build_document_from_request(request)

        # Delegate strategy selection
        selected_pipeline = pipeline_builder.build_pipeline_for_document(
            document_type=doc.document_type,
            document_repo=document_repo,
        )

        # Execute pipeline
        logger.info(f"Running pipeline strategy for single document: {doc.filename} ({doc.document_type.value})")
        ingest_command._run_pipeline(doc, pipeline=selected_pipeline)

        return {
            "status": "completed",
            "document_id": doc.id,
            "filename": doc.filename,
            "document_type": request.document_type
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in single document ingestion: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

# 5. Initialize the retrieve-and-generate command
retrieve_command = RetrieveAndGenerateCommand(settings, document_repo)


class RetrieveRequest(BaseModel):
    url: str = Field(..., description="URL of the received document to analyze")
    document_type: str = Field(default="received", description="Always 'received'")
    filename: Optional[str] = Field(None, description="Optional custom filename/identifier")
    metadata: IngestRequestMetadata


@app.post("/api/v1/retrieve")
async def retrieve_document(request: RetrieveRequest):
    """
    RAG Retriever endpoint: receives a document URL, extracts its content,
    searches for similar communications, resolves linked sent documents,
    generates a response letter with Gemini, and returns a PDF.
    """
    try:
        # Validate document type
        if request.document_type.lower().strip() != "received":
            raise HTTPException(
                status_code=400,
                detail="document_type must be 'received' for the retrieve endpoint"
            )

        # Build the document entity
        doc = _build_document_from_request(request)

        # Add custom tags to MLflow trace for better observability
        if mlflow.active_run():
            mlflow.set_tags({
                "contract_number": doc.contract_number,
                "process": doc.process,
                "work_front": doc.work_front,
                "sender": doc.sender,
                "document_type": "rag_retrieval"
            })

        # Execute the RAG pipeline
        result = retrieve_command.execute(doc)

        # Return RAG metadata as JSON response
        return {
            "status": "completed",
            "subject": result.get("subject", ""),
            "similar_count": result.get("similar_count", 0),
            "sent_count": result.get("sent_count", 0),
            "gcs_url": result.get("gcs_url", ""),
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in RAG retrieval: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/")
async def handle_event(event: GCSEvent):
    """
    Handle Eventarc events from Cloud Storage.
    The payload is a CloudEvent sent via HTTP POST.
    """
    try:
        # Log the event for debugging
        logger.info(f"Received event for: gs://{event.bucket}/{event.name}")
        
        # Check if it's in our target directory
        if not event.name.startswith("COMMUNICATION_RECEIVED/"):
            logger.info(f"Ignoring file: {event.name} (outside target directory)")
            return {"status": "ignored", "reason": "wrong_prefix"}

        # 1. Trigger IngestDocumentCommand
        doc = ingest_command.execute(event.dict(by_alias=True))
        
        return {"status": "accepted", "id": doc.id, "file": doc.filename}

    except Exception as e:
        logger.error(f"Error processing event: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=settings.port)
