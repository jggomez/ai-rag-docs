from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from src.domain.enums import DocumentStatus

class SourceDocument(BaseModel):
    id: str = Field(..., description="Unique ID of the document (usually hash or GCS path)")
    filename: str
    bucket: str
    object_name: str
    content_type: str
    size_bytes: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
    status: DocumentStatus = DocumentStatus.PENDING
    
    # Metadata extracted from GCS path/properties
    sender: str
    contract_number: str
    work_front: str
    document_date: str
    process: str
    response_file_url: Optional[str] = None
    
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
