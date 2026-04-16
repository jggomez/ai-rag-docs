import os
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
from fastapi import FastAPI, HTTPException
from src.domain.schemas import GCSEvent, IngestRequest
from src.repositories.storage_repo import GCSStorageRepository
from src.repositories.document_repo import FirestoreDocumentRepository
from src.infrastructure.repositories.csv_metadata_repository import CSVMetadataRepository
from src.usecases.builder import PipelineBuilder
from src.usecases.ingest_document import IngestDocumentCommand

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="RAG Ingestion Pipeline")

# Dependency injection and wiring
storage_repo = GCSStorageRepository()
document_repo = FirestoreDocumentRepository()

# Initialize optional CSV Metadata Repository
csv_path = os.environ.get("METADATA_CSV_PATH", "resources/Comunicaciones.csv")
csv_metadata_repo = CSVMetadataRepository(csv_path)

# Use the builder to construct the ingestion pipeline
pipeline = PipelineBuilder.build_ingestion_pipeline(
    storage_repo, 
    document_repo,
    csv_metadata_repo=csv_metadata_repo
)

# Inject document_repo and the pipeline into the command
ingest_command = IngestDocumentCommand(document_repo, pipeline)

@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.post("/ingest")
async def ingest_with_metadata(request: IngestRequest):
    """
    Trigger ingestion with explicit metadata.
    """
    try:
        logger.info(f"Received manual ingestion request for: gs://{request.bucket}/{request.object_name}")
        
        doc = ingest_command.execute_manual(request.dict(by_alias=True))
        
        return {"status": "accepted", "id": doc.id, "file": doc.filename}
    except Exception as e:
        logger.error(f"Error in manual ingestion: {str(e)}")
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
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
