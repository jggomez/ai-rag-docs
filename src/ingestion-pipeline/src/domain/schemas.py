from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class GCSEvent(BaseModel):
    bucket: str
    name: str
    contentType: Optional[str] = Field(None, alias="contentType")
    size: Optional[str] = None
    timeCreated: Optional[str] = None
    metageneration: Optional[str] = None
class IngestRequest(BaseModel):
    bucket: str
    object_name: str = Field(..., alias="object_name")
    sender: str
    contract_number: str
    work_front: str
    document_date: str
    process: str
    response_file_url: Optional[str] = None

    class Config:
        populate_by_name = True
