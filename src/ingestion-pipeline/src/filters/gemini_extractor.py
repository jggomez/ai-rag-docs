import logging
import os
from typing import Optional
from pydantic import BaseModel
from google import genai
from google.genai import types

from src.filters.base import Filter
from src.domain.entities import ProcessingPayload

logger = logging.getLogger(__name__)

class ExtractedContent(BaseModel):
    """Structured schema for document extraction."""
    subject: str
    body: str
    visual_tabular_data: str

OCR_EXTRACTION_PROMPT = """
Task: Act as a specialized Document Parser for technical engineering records. Extract the core content of the provided document (OCR text) for ingestion into a RAG system.

Core Extraction Rules:
1. **Subject**: Extract the text labeled as "Asunto" or "Referencia".
2. **Body**: Extract the main message from the formal greeting to the closing statement.
3. **Tables to Items**: If a table is present, convert each row into a descriptive bullet point. Format: "[Column 1 Title]: [Value] | [Column 2 Title]: [Value]".
4. **Image Descriptions**: If an image or stamp is detected, provide a brief, objective text description of its content (e.g., "Official stamp from [Entity] dated [Date]").

RAG Best Practices & Constraints:
- **Self-Contained Context**: Ensure the extracted text maintains its relationship to the project/contract mentioned.
- **Noise Removal**: Strictly exclude headers, footers, logos, signatures, and contact info.
- **Clean Output**: No conversational filler. Provide only the structured data.
"""

class GeminiExtractor(Filter[ProcessingPayload, ProcessingPayload]):
    """
    Filter that uses the Gemini generative model for OCR-based text extraction
    from scanned/received documents using Structured Output.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model_name: Optional[str] = None,
    ):
        resolved_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self.model_name = model_name or os.environ.get("GEMINI_OCR_MODEL", "gemini-2.0-flash")
        
        self.client = genai.Client(api_key=resolved_key)
        logger.info(f"GeminiExtractor initialised with model '{self.model_name}' using Structured Output.")

    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        if not payload.content:
            logger.warning("No content found in payload to extract metadata from.")
            return payload
            
        logger.info(f"Extracting structured text via Gemini OCR for {payload.document.filename}")

        try:
            # Prepare parts for the prompt
            parts = [
                types.Part.from_text(text=OCR_EXTRACTION_PROMPT),
                types.Part.from_bytes(data=payload.content, mime_type=payload.document.content_type)
            ]

            # Use generate_content with response_schema for structured output
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=parts,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=ExtractedContent,
                ),
            )
            
            extracted_data: ExtractedContent = response.parsed
            
            subject = extracted_data.subject
            body = extracted_data.body
            visual_data = extracted_data.visual_tabular_data

            # Store extracted fields for downstream filters (chunker, embedder)
            payload.document.metadata["extracted_text"] = body
            payload.document.metadata["document_subject"] = subject
            payload.document.metadata["visual_tabular_data"] = visual_data

            logger.info(f"Gemini OCR extraction successful. Subject: {subject[:80]}")
            return payload

        except Exception as exc:
            logger.error(f"Gemini OCR extraction failed: {exc}")
            raise
