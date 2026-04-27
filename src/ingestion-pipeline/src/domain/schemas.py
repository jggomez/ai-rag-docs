from pydantic import BaseModel, Field
from typing import Optional

class GCSEvent(BaseModel):
    bucket: str
    name: str
    contentType: Optional[str] = Field(None, alias="contentType")
    size: Optional[str] = None
    timeCreated: Optional[str] = None
    metageneration: Optional[str] = None
