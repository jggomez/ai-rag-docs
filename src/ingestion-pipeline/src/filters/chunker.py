import logging
from typing import List, Dict, Any
from langchain_text_splitters import RecursiveCharacterTextSplitter
from src.filters.base import Filter
from src.domain.entities import ProcessingPayload, DocumentChunk

logger = logging.getLogger(__name__)

class TextChunker(Filter[ProcessingPayload, ProcessingPayload]):
    def __init__(self, chunk_size: int = 1000, chunk_overlap: int = 200):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )

    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        text = payload.document.metadata.get("extracted_text", "")
        if not text:
            # Fallback to empty if no text found
            logger.warning("No extracted text found for chunking.")
            return payload
            
        logger.info(f"Chunking text of length {len(text)}")
        
        chunks_text = self.splitter.split_text(text)
        
        # Base metadata for all chunks
        base_metadata = {
            "contract_number": payload.document.contract_number,
            "sender": payload.document.sender,
            "work_front": payload.document.work_front
        }
        
        for i, chunk_content in enumerate(chunks_text):
            # Check if we have a cleaner-extracted subject
            subject = payload.document.metadata.get("document_subject")
            
            if not subject or subject == "Not detected":
                # Heuristic fallback for subject: First line or first 100 chars
                lines = [l for l in chunk_content.split("\n") if l.strip()]
                subject = lines[0][:100] if lines else chunk_content[:100]
            
            chunk = DocumentChunk(
                id=f"{payload.document.id}_{i}",
                document_id=payload.document.id,
                subject=subject,
                body=chunk_content,
                index=i,
                sent_file=payload.document.response_file_url,
                metadata={**base_metadata, "chunk_index": i}
            )
            payload.chunks.append(chunk)
            
        logger.info(f"Generated {len(payload.chunks)} chunks.")
        return payload
