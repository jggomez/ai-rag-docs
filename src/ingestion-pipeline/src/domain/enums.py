from enum import Enum

class DocumentStatus(str, Enum):
    PENDING = "PENDING"
    DOWNLOADING = "DOWNLOADING"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class DocumentType(str, Enum):
    """Identifies the document origin to determine the processing path."""
    SENT = "SENT"
    RECEIVED = "RECEIVED"
