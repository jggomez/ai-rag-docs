import fitz # PyMuPDF
import logging
import io
from src.filters.base import Filter
from src.domain.entities import ProcessingPayload
from src.domain.enums import DocumentStatus

logger = logging.getLogger(__name__)

class PDFReader(Filter[ProcessingPayload, ProcessingPayload]):
    """
    Filter that extracts text from a PDF file using PyMuPDF.
    """
    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        if not payload.content:
            logger.warning("No document content found to extract text from.")
            return payload
            
        logger.info(f"Extracting text from PDF: {payload.document.filename}")
        
        try:
            # Load PDF from memory bytes
            doc = fitz.open(stream=io.BytesIO(payload.content), filetype="pdf")
            full_text = ""
            
            # Iterate through pages and extract text
            for page in doc:
                full_text += page.get_text() + "\n\n"
            
            doc.close()
            
            # Update metadata with extracted text
            payload.document.metadata["extracted_text"] = full_text.strip()
            
            logger.info(f"Successfully extracted {len(full_text)} characters from {payload.document.filename}")
            return payload
            
        except Exception as e:
            logger.error(f"Error extracting text from PDF: {str(e)}")
            payload.document.status = DocumentStatus.FAILED
            payload.document.metadata["error"] = f"PDF text extraction failed: {str(e)}"
            raise
