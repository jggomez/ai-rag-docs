import logging
import json
import google.generativeai as genai
from typing import Optional
from src.filters.base import Filter
from src.domain.entities import ProcessingPayload

logger = logging.getLogger(__name__)

class GeminiExtractor(Filter[ProcessingPayload, ProcessingPayload]):
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model_name)

    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        if not payload.content:
            logger.warning("No content found in payload to extract metadata from.")
            return payload
            
        logger.info(f"Extracting text and metadata using Gemini for {payload.document.filename}")
        
        prompt = """
        Extract the following information from this document. 
        If a field is not found, use 'UNKNOWN'.
        
        Fields:
        - sender: The entity or company sending the document (entidad contratista).
        - contract_number: The specific contract number mentioned.
        - work_front: The project area or work front (frente de obra).
        - document_date: The date specified in the document (YYYY-MM-DD).
        - process: The specific process or department (e.g., Legal, Technical, HR).
        - response_file_url: If the document mentions a response file or related document URL.
        - full_text: The entire text content of the document.

        Return strictly a JSON object.
        """

        try:
            # Upload content as part of the request
            # For brevity in MVP, we send bytes directly if small or use file API if needed.
            # Here we use the part API for bytes.
            response = self.model.generate_content(
                [
                    prompt, 
                    {"mime_type": payload.document.content_type, "data": payload.content}
                ],
                generation_config={"response_mime_type": "application/json"}
            )
            
            data = json.loads(response.text)
            
            # Update metadata if not already set by path heuristics (or overwrite if found better)
            if data.get("sender") != "UNKNOWN":
                payload.document.sender = data["sender"]
            if data.get("contract_number") != "UNKNOWN":
                payload.document.contract_number = data["contract_number"]
            if data.get("work_front") != "UNKNOWN":
                payload.document.work_front = data["work_front"]
            if data.get("document_date") != "UNKNOWN":
                payload.document.document_date = data["document_date"]
            if data.get("process") != "UNKNOWN":
                payload.document.process = data["process"]
                
            # Store full text in metadata for the chunking step
            payload.document.metadata["extracted_text"] = data.get("full_text", "")
            
            logger.info("Gemini extraction successful.")
            return payload

        except Exception as e:
            logger.error(f"Gemini extraction failed: {str(e)}")
            # We don't necessarily want to fail the whole pipe if Gemini fails OCR, 
            # but for this MVP, let's treat it as a step.
            raise e
