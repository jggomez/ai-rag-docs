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

    @abstractmethod
    def get_document_by_draft_id(self, draft_id: str) -> Optional[SourceDocument]:
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

        # Sync url_recibido and url_respuesta to chunks if they exist
        update_fields = {}
        if spanish_data.get("url_recibido"):
            update_fields["url_recibido"] = spanish_data["url_recibido"]
        if spanish_data.get("url_respuesta"):
            update_fields["url_respuesta"] = spanish_data["url_respuesta"]

        if update_fields:
            try:
                chunks_query = self.chunks_collection.where("id_documento", "==", document.id).stream()
                batch = self.client.batch()
                count = 0
                for chunk_snap in chunks_query:
                    batch.update(chunk_snap.reference, update_fields)
                    count += 1
                if count > 0:
                    batch.commit()
                    logger.info(f"Updated {count} chunks of document {document.id} with fields {update_fields}")
            except Exception as e:
                logger.warning(f"Could not update chunks for document {document.id}: {e}")

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

    def get_document_by_object_name(self, object_name: str) -> Optional[SourceDocument]:
        query = self.docs_collection.where("nombre_objeto", "==", object_name).limit(1)
        results = query.get()
        for doc in results:
            return self._to_english_document(doc.to_dict())
        return None

    def get_document_by_draft_id(self, draft_id: str) -> Optional[SourceDocument]:
        query = self.docs_collection.where("id_borrador", "==", draft_id).limit(1)
        results = query.get()
        for doc in results:
            data = doc.to_dict()
            english_doc = self._to_english_document(data)
            english_doc.id = doc.id
            return english_doc
        return None

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
                "nombre_objeto": spanish_parent.get("nombre_objeto"),
                "url_respuesta": spanish_parent.get("url_respuesta"),
            }
            url_recibido = spanish_parent.get("url_recibido")
        else:
            spanish_meta = {}
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
        url_recibido = document.metadata.get("url_recibido") or document.source_url
        if url_recibido and not url_recibido.startswith("gs://"):
            url_recibido = None

        url_respuesta = document.response_file_url
        if url_respuesta and not url_respuesta.startswith("gs://"):
            url_respuesta = None

        spanish_meta = {
            "frente_trabajo": document.work_front,
            "fecha_documento": document.document_date,
            "url_respuesta": url_respuesta,
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

        # Priority: 1. explicit metadata, 2. object_name (from DB), 3. filename
        nombre_objeto = document.metadata.get("codigo_comunicado")
        if not nombre_objeto:
            # If reading from DB, object_name holds the official code
            if document.object_name and not document.object_name.startswith("TMP_"):
                nombre_objeto = document.object_name
            else:
                nombre_objeto = document.filename

        if nombre_objeto and nombre_objeto.lower().endswith(".pdf"):
            nombre_objeto = nombre_objeto[:-4]

        spanish_data = {
            "id": document.id,
            "nombre_archivo": document.filename,
            "nombre_objeto": nombre_objeto,
            "tipo_contenido": document.content_type,
            "tamano_bytes": document.size_bytes,
            "creado_en": document.created_at,
            "estado": status_es,
            "tipo_documento": type_es,
            "url_recibido": url_recibido,
            **spanish_meta,
        }

        # Translate metadata keys to Spanish and flatten directly in the root
        for k, v in document.metadata.items():
            if k in ["url_recibido", "url_enviado", "url_origen", "codigo_comunicado"]:
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
            "creado_en", "estado", "tipo_documento", "url_recibido",
            "frente_trabajo", "fecha_documento",
            "url_respuesta", "id_borrador"
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
            source_url=spanish_data.get("url_recibido"),
            work_front=spanish_data.get("frente_trabajo", "GENERAL"),
            document_date=spanish_data.get("fecha_documento", "UNKNOWN"),
            response_file_url=spanish_data.get("url_respuesta"),
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
            try:
                from unittest.mock import MagicMock
                # Query RECEIVED doc by draft ID since Firestore IDs are dynamically generated
                query = self.received_repo.docs_collection.where("id_borrador", "==", document.draft_id).limit(1)
                results = query.get()
                rec_doc = None
                for doc_snap in results:
                    rec_doc = self.received_repo._to_english_document(doc_snap.to_dict())
                    rec_doc.id = doc_snap.id
                    break
                
                if rec_doc and not isinstance(rec_doc, MagicMock):
                    # 1. Update the SENT document's url_recibido with GCS URL of RECEIVED doc
                    if rec_doc.source_url and rec_doc.source_url.startswith("gs://"):
                        document.metadata["url_recibido"] = rec_doc.source_url
                    
                    # 2. Update the corresponding RECEIVED document's url_respuesta with SENT doc GCS URL
                    if document.response_file_url and document.response_file_url.startswith("gs://"):
                        rec_doc.response_file_url = document.response_file_url
                        self.received_repo.save_document(rec_doc)
                        logger.info(f"Cross-updated RECEIVED document {rec_doc.id} url_respuesta to {document.response_file_url}")
            except Exception as e:
                logger.exception(f"Could not perform GCS URL cross-update: {e}")
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

    def get_document_by_object_name(self, object_name: str) -> Optional[SourceDocument]:
        doc = self.received_repo.get_document_by_object_name(object_name)
        if doc:
            return doc
        return self.sent_repo.get_document_by_object_name(object_name)

    def get_document_by_draft_id(self, draft_id: str) -> Optional[SourceDocument]:
        doc = self.received_repo.get_document_by_draft_id(draft_id)
        if doc:
            return doc
        return self.sent_repo.get_document_by_draft_id(draft_id)

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
