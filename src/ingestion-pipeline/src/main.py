import logging
from fastapi import FastAPI, HTTPException
from src.config import settings
from src.domain.schemas import GCSEvent
from src.repositories.storage_repo import GCSStorageRepository
from src.repositories.document_repo import FirestoreDocumentRepository
from src.infrastructure.repositories.csv_metadata_repository import CSVMetadataRepository
from src.usecases.builder import PipelineBuilder
from src.usecases.ingest_document import IngestDocumentCommand

# Configure logging
logging.basicConfig(level=getattr(logging, settings.log_level.upper()))
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Ingestion Pipeline")

# 1. Dependency injection and wiring
storage_repo = GCSStorageRepository()
document_repo = FirestoreDocumentRepository()
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

@app.post("/ingest")
async def ingest_with_metadata():
    """
    Trigger ingestion for all records in the local communications.csv file.
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
