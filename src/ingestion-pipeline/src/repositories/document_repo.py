import logging
from abc import ABC, abstractmethod
from typing import List, Optional
from src.domain.entities import SourceDocument, DocumentChunk
from src.domain.enums import DocumentStatus, DocumentType
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector

logger = logging.getLogger(__name__)


class DocumentRepository(ABC):
    @abstractmethod
    def save_document(self, document: SourceDocument) -> None:
        pass

    @abstractmethod
    def get_document(self, document_id: str) -> Optional[SourceDocument]:
        pass

    @abstractmethod
    def update_status(
        self, document_id: str, status: DocumentStatus, error: str = None
    ) -> None:
        pass

    @abstractmethod
    def save_chunks(self, chunks: List[DocumentChunk]) -> None:
        pass


class FirestoreDocumentRepository(DocumentRepository):
    def __init__(self, database: str = "(default)", client: firestore.Client = None):
        self.client = client or firestore.Client(database=database)
        self.docs_collection = self.client.collection("documentos")
        self.chunks_collection = self.client.collection("documentos_chunks")

    def save_document(self, document: SourceDocument) -> None:
        is_temp_id = document.id.endswith("_REC") or document.id.endswith("_SEN") or document.id.isdigit()
        if is_temp_id:
            doc_ref = self.docs_collection.document()
            document.id = doc_ref.id
        else:
            doc_ref = self.docs_collection.document(document.id)

        spanish_data = self._to_spanish_dict(document)
        doc_ref.set(spanish_data)

    def get_document(self, document_id: str) -> Optional[SourceDocument]:
        doc_ref = self.docs_collection.document(document_id)
        snapshot = doc_ref.get()
        if snapshot.exists:
            spanish_data = snapshot.to_dict()
            return self._to_english_document(spanish_data)
        return None

    def update_status(
        self, document_id: str, status: DocumentStatus, error: str = None
    ) -> None:
        doc_ref = self.docs_collection.document(document_id)

        status_map = {
            DocumentStatus.PENDING: "PENDIENTE",
            DocumentStatus.PROCESSING: "PROCESANDO",
            DocumentStatus.COMPLETED: "COMPLETADO",
            DocumentStatus.FAILED: "FALLIDO",
        }
        status_es = status_map.get(status, "PENDIENTE")

        update_data = {"estado": status_es}

        if error:
            update_data["error"] = error
        doc_ref.update(update_data)

    def save_chunks(self, chunks: List[DocumentChunk]) -> None:
        if not chunks:
            return

        # Get parent document to retrieve engineering metadata and URLs
        first_chunk = chunks[0]
        parent_doc = self.get_document(first_chunk.document_id)
        if parent_doc:
            spanish_parent = self._to_spanish_dict(parent_doc)
            spanish_meta = {
                "frente_trabajo": spanish_parent.get("frente_trabajo"),
                "fecha_documento": spanish_parent.get("fecha_documento"),
                "id_borrador": spanish_parent.get("id_borrador"),
                "nombre_archivo": spanish_parent.get("nombre_archivo"),
                "url_archivo_respuesta": spanish_parent.get("url_archivo_respuesta"),
            }
            url_origen = spanish_parent.get("url_origen")
            url_recibido = spanish_parent.get("url_recibido")
        else:
            spanish_meta = {}
            url_origen = None
            url_recibido = None

        # Using batch for performance
        batch = self.client.batch()
        for chunk in chunks:
            chunk_ref = self.chunks_collection.document()  # Let Firestore generate the ID
            chunk.id = chunk_ref.id  # Update chunk in-memory ID

            # Flatten chunk.metadata properties directly to the root in Spanish
            flattened_meta = {}
            for k, v in chunk.metadata.items():
                translated_key = {
                    "work_front": "frente_trabajo",
                    "chunk_index": "indice_chunk",
                }.get(k, k)
                flattened_meta[translated_key] = v

            spanish_chunk = {
                "id": chunk.id,
                "id_documento": chunk.document_id,
                "asunto": chunk.subject,
                "texto": f"{chunk.subject}\n{chunk.body}",  # mix of subject and body
                "url_origen": url_origen,
                "url_recibido": url_recibido,
                **spanish_meta,
                **flattened_meta,
            }
            # Save embedding vector
            if chunk.embedding:
                spanish_chunk["vector"] = Vector(chunk.embedding)

            batch.set(chunk_ref, spanish_chunk)
        batch.commit()

    def _to_spanish_dict(self, document: SourceDocument) -> dict:
        spanish_meta = {
            "frente_trabajo": document.work_front,
            "fecha_documento": document.document_date,
            "url_archivo_respuesta": document.response_file_url,
            "id_borrador": document.draft_id,
        }

        status_map = {
            DocumentStatus.PENDING: "PENDIENTE",
            DocumentStatus.PROCESSING: "PROCESANDO",
            DocumentStatus.COMPLETED: "COMPLETADO",
            DocumentStatus.FAILED: "FALLIDO",
        }
        status_es = status_map.get(document.status, "PENDIENTE")

        type_map = {DocumentType.RECEIVED: "RECIBIDO", DocumentType.SENT: "ENVIADO"}
        type_es = type_map.get(document.document_type, "ENVIADO")

        url_recibido = document.metadata.get("url_recibido")

        spanish_data = {
            "id": document.id,
            "nombre_archivo": document.filename,
            "nombre_objeto": document.object_name[:-4] if document.object_name.lower().endswith(".pdf") else document.object_name,
            "tipo_contenido": document.content_type,
            "tamano_bytes": document.size_bytes,
            "creado_en": document.created_at,
            "estado": status_es,
            "tipo_documento": type_es,
            "url_origen": document.source_url,
            "url_recibido": url_recibido,
            **spanish_meta,
        }

        # Translate metadata keys to Spanish and flatten directly in the root
        for k, v in document.metadata.items():
            if k in ["url_recibido", "url_enviado"]:
                continue
            translated_key = {
                "extracted_text": "texto_extraido",
                "document_subject": "asunto_documento",
                "visual_tabular_data": "datos_tabulares_visuales",
                "error": "error",
            }.get(k, k)
            spanish_data[translated_key] = v

        return spanish_data

    def _to_english_document(self, spanish_data: dict) -> SourceDocument:
        status_map = {
            "PENDIENTE": DocumentStatus.PENDING,
            "PROCESANDO": DocumentStatus.PROCESSING,
            "COMPLETADO": DocumentStatus.COMPLETED,
            "FALLIDO": DocumentStatus.FAILED,
        }
        status_en = status_map.get(spanish_data.get("estado"), DocumentStatus.PENDING)

        type_map = {"RECIBIDO": DocumentType.RECEIVED, "ENVIADO": DocumentType.SENT}
        type_en = type_map.get(spanish_data.get("tipo_documento"), DocumentType.SENT)

        standard_keys = {
            "id", "nombre_archivo", "nombre_objeto", "tipo_contenido", "tamano_bytes",
            "creado_en", "estado", "tipo_documento", "url_origen", "url_recibido",
            "frente_trabajo", "fecha_documento",
            "url_archivo_respuesta", "id_borrador"
        }

        metadata = {}
        for k, v in spanish_data.items():
            if k in standard_keys:
                continue
            # Translate back to English
            english_key = {
                "texto_extraido": "extracted_text",
                "asunto_documento": "document_subject",
                "datos_tabulares_visuales": "visual_tabular_data",
                "error": "error",
            }.get(k, k)
            metadata[english_key] = v

        # Maintain url_recibido in metadata dict if present
        if "url_recibido" in spanish_data:
            metadata["url_recibido"] = spanish_data["url_recibido"]

        return SourceDocument(
            id=spanish_data.get("id"),
            filename=spanish_data.get("nombre_archivo"),
            bucket=spanish_data.get("bucket", "docs-enviados"),
            object_name=spanish_data.get("nombre_objeto"),
            content_type=spanish_data.get("tipo_contenido"),
            size_bytes=spanish_data.get("tamano_bytes", 0),
            created_at=spanish_data.get("creado_en"),
            status=status_en,
            document_type=type_en,
            source_url=spanish_data.get("url_origen"),
            work_front=spanish_data.get("frente_trabajo", "GENERAL"),
            document_date=spanish_data.get("fecha_documento", "UNKNOWN"),
            response_file_url=spanish_data.get("url_archivo_respuesta"),
            draft_id=spanish_data.get("id_borrador"),
            metadata=metadata,
        )


class RoutingFirestoreDocumentRepository(DocumentRepository):
    def __init__(
        self,
        database_received: str = "docs-recibidos",
        database_sent: str = "docs-enviados",
        client_received: firestore.Client = None,
        client_sent: firestore.Client = None,
    ):
        self.received_repo = FirestoreDocumentRepository(
            database=database_received, client=client_received
        )
        self.sent_repo = FirestoreDocumentRepository(
            database=database_sent, client=client_sent
        )

    def _get_repo_for_id(self, document_id: str) -> FirestoreDocumentRepository:
        # Check received database first
        if document_id.endswith("_REC"):
            return self.received_repo
        elif document_id.endswith("_SEN"):
            return self.sent_repo

        # For Firestore generated IDs, check if exists in received docs-collection
        if self.received_repo.docs_collection.document(document_id).get().exists:
            return self.received_repo
        return self.sent_repo

    def save_document(self, document: SourceDocument) -> None:
        if document.document_type == DocumentType.RECEIVED:
            repo = self.received_repo
        else:
            repo = self.sent_repo
        repo.save_document(document)

    def get_document(self, document_id: str) -> Optional[SourceDocument]:
        if document_id.endswith("_REC"):
            return self.received_repo.get_document(document_id)
        elif document_id.endswith("_SEN"):
            return self.sent_repo.get_document(document_id)

        # For generated IDs, search received first, then sent
        doc = self.received_repo.get_document(document_id)
        if doc:
            return doc
        return self.sent_repo.get_document(document_id)

    def update_status(
        self, document_id: str, status: DocumentStatus, error: str = None
    ) -> None:
        if document_id.endswith("_REC"):
            self.received_repo.update_status(document_id, status, error)
            return
        elif document_id.endswith("_SEN"):
            self.sent_repo.update_status(document_id, status, error)
            return

        # For generated IDs
        if self.received_repo.docs_collection.document(document_id).get().exists:
            self.received_repo.update_status(document_id, status, error)
        else:
            self.sent_repo.update_status(document_id, status, error)

    def save_chunks(self, chunks: List[DocumentChunk]) -> None:
        if not chunks:
            return
        # Group chunks by document_id to route correctly
        by_doc = {}
        for chunk in chunks:
            by_doc.setdefault(chunk.document_id, []).append(chunk)

        for doc_id, doc_chunks in by_doc.items():
            if doc_id.endswith("_REC"):
                self.received_repo.save_chunks(doc_chunks)
            elif doc_id.endswith("_SEN"):
                self.sent_repo.save_chunks(doc_chunks)
            else:
                if self.received_repo.docs_collection.document(doc_id).get().exists:
                    self.received_repo.save_chunks(doc_chunks)
                else:
                    self.sent_repo.save_chunks(doc_chunks)
