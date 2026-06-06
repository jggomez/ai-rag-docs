from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from src.domain.enums import DocumentStatus, DocumentType

class SourceDocument(BaseModel):
    id: str = Field(..., description="Unique ID of the document (usually hash or GCS path)")
    filename: str
    bucket: str
    object_name: str
    content_type: str
    size_bytes: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: DocumentStatus = DocumentStatus.PENDING
    document_type: DocumentType = DocumentType.SENT
    source_url: Optional[str] = None

    # Flattened engineering metadata (previously EngineeringMetadata)
    work_front: str = "GENERAL"
    document_date: str = "UNKNOWN"
    response_file_url: Optional[str] = None
    draft_id: Optional[str] = None

    metadata: Dict[str, Any] = Field(default_factory=dict)

class DocumentChunk(BaseModel):
    id: str
    document_id: str
    subject: str
    body: str
    embedding: Optional[List[float]] = None
    index: int
    sent_file: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ProcessingPayload(BaseModel):
    document: SourceDocument
    content: Optional[bytes] = None
    chunks: List[DocumentChunk] = Field(default_factory=list)


