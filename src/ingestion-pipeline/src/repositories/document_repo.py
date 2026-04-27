from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities import SourceDocument, DocumentChunk
from src.domain.enums import DocumentStatus
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector

class DocumentRepository(ABC):
    @abstractmethod
    def save_document(self, document: SourceDocument) -> None:
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[SourceDocument]:
        pass

    @abstractmethod
    def update_status(self, document_id: str, status: DocumentStatus, error: str = None) -> None:
        pass

    @abstractmethod
    def save_chunks(self, chunks: List[DocumentChunk]) -> None:
        pass


class FirestoreDocumentRepository(DocumentRepository):
    def __init__(self, database: str = "(default)", client: firestore.Client = None):
        self.client = client or firestore.Client(database=database)
        self.docs_collection = self.client.collection("source_documents")
        self.chunks_collection = self.client.collection("document_chunks")

    def save_document(self, document: SourceDocument) -> None:
        doc_ref = self.docs_collection.document(document.id)
        doc_ref.set(document.model_dump())

    def get_document(self, document_id: str) -> Optional[SourceDocument]:
        doc_ref = self.docs_collection.document(document_id)
        snapshot = doc_ref.get()
        if snapshot.exists:
            return SourceDocument(**snapshot.to_dict())
        return None

    def update_status(self, document_id: str, status: DocumentStatus, error: str = None) -> None:
        doc_ref = self.docs_collection.document(document_id)
        update_data = {"status": status.value, "updated_at": firestore.SERVER_TIMESTAMP}
        if error:
            update_data["error"] = error
        doc_ref.update(update_data)

    def save_chunks(self, chunks: List[DocumentChunk]) -> None:
        # Using batch for performance
        batch = self.client.batch()
        for chunk in chunks:
            chunk_ref = self.chunks_collection.document(chunk.id)
            data = chunk.model_dump()
            if chunk.embedding:
                data["embedding"] = Vector(chunk.embedding)
            batch.set(chunk_ref, data)
        batch.commit()
