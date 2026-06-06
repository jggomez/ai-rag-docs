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
<persona>
You are a lossless document transcriber specialized in formal engineering and
construction correspondence (letters, memos, technical reports, inspection records).
Your sole purpose is to produce a faithful, complete text extraction of every page
in the provided document for downstream ingestion into a Retrieval-Augmented
Generation (RAG) system.
</persona>

<task>
Given a PDF document (which may be scanned, digital, or a mix of both), extract
its full textual content into three structured fields: `subject`, `body`, and
`visual_tabular_data`.
</task>

<extraction_rules>
## 1. Subject
- Look for the field labeled "Asunto", "Referencia", "Ref.", or "RE:" in the
  document header section.
- Copy the subject text verbatim. If multiple labels exist, prefer "Asunto".
- If no explicit subject label is found, synthesize a short descriptive title
  from the first paragraph (max 120 characters).

## 2. Body — Full Text Extraction
- Transcribe the ENTIRE textual content of the document from the first paragraph
  after the header block through the closing statement.
- Process ALL pages sequentially (page 1, page 2, … page N). Do NOT stop after
  the first page.
- Preserve the original paragraph structure. Separate paragraphs with a blank line.
- Include numbered lists, bullet points, and any inline references exactly as
  they appear in the document.
- Preserve any reference numbers, dates, file codes, and protocol numbers found
  within the body text.
- EXCLUDE from body: letterhead, logos, header/footer repetitions on each page,
  page numbers, signatures, handwritten annotations, and contact information blocks.

## 3. Visual & Tabular Data
- **Tables**: Render every table using standard Markdown table syntax:
  ```
  | Column A | Column B | Column C |
  |----------|----------|----------|
  | value    | value    | value    |
  ```
  Preserve all rows and columns. Do not summarize or omit rows.
- **Images / Stamps / Seals**: For each non-text visual element, produce a
  detailed objective description enclosed in markers:
  `[IMAGE: <description of content, entities mentioned, dates visible, colors, position on page>]`
  Example: `[IMAGE: Official round stamp from "Consorcio CYS" dated 2025-03-11, blue ink, bottom-right corner of page 2]`
- **Charts / Diagrams**: Describe axes labels, legend entries, and key data
  points in text form within `[CHART: ...]` markers.
- If the document contains NO tables, images, or charts, set this field to an
  empty string "".
</extraction_rules>

<constraints>
- **Zero Hallucination**: NEVER invent, paraphrase, or infer text that is not
  visibly present in the document. If a section is illegible, write
  "[ILLEGIBLE: approximate location on page]".
- **Completeness over brevity**: It is better to include a seemingly redundant
  paragraph than to skip content. Every sentence matters for RAG retrieval.
- **Language preservation**: The document text is in Spanish. Transcribe it in
  the original Spanish. Do NOT translate.
- **No conversational filler**: Return ONLY the structured data. No greetings,
  no explanations, no meta-commentary.
- **Safety & Recitation Avoidance**: To avoid triggering API safety filters and recitation blocks on verbatim text:
  * Do NOT transcribe long standard boilerplate clauses, legal disclaimers, generic privacy notices, or long commercial product technical datasheets/specifications verbatim. Instead, replace them with a brief bracketed summary, e.g., `[Generic legal disclaimer summarized]` or `[Product technical datasheet summarized]`.
  * Focus 100% of your transcription fidelity on the main correspondence body, technical reports, dates, reference codes, specific instructions, names, and tables.
</constraints>
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
        self.model_name = model_name or os.environ.get("GEMINI_OCR_MODEL", "gemini-3-flash-preview")
        
        self.client = genai.Client(api_key=resolved_key)
        logger.info(f"GeminiExtractor initialised with model '{self.model_name}' using Structured Output.")

    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        if not payload.content:
            logger.warning("No content found in payload to extract metadata from.")
            return payload
            
        logger.info(f"Extracting structured text via Gemini OCR for {payload.document.filename}")

        try:
            # Prepare parts for the content (excluding the prompt text)
            parts = [
                types.Part.from_bytes(data=payload.content, mime_type=payload.document.content_type)
            ]

            # Use generate_content with response_schema for structured output
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=parts,
                config=types.GenerateContentConfig(
                    system_instruction=OCR_EXTRACTION_PROMPT,
                    response_mime_type="application/json",
                    response_schema=ExtractedContent,
                    temperature=0.2,
                    max_output_tokens=65536,
                    thinking_config=types.ThinkingConfig(
                        thinking_budget=0
                    ),
                    safety_settings=[
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE,
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE,
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_HARASSMENT,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE,
                        ),
                        types.SafetySetting(
                            category=types.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                            threshold=types.HarmBlockThreshold.BLOCK_NONE,
                        ),
                    ],
                ),
            )
            
            extracted_data: ExtractedContent = response.parsed
            
            # If parsed is None or missing expected fields, fallback to manual validation
            if (extracted_data is None or 
                not hasattr(extracted_data, "subject") or 
                not hasattr(extracted_data, "body") or 
                not hasattr(extracted_data, "visual_tabular_data")):
                
                # Check finish reason early
                finish_reason = "UNKNOWN"
                if response.candidates and len(response.candidates) > 0:
                    finish_reason = response.candidates[0].finish_reason

                if finish_reason == types.FinishReason.RECITATION:
                    logger.warning(
                        f"Gemini OCR fue bloqueado por los filtros de recitación para {payload.document.filename}. "
                        "Se registrará el documento en Firestore sin texto extraído y sin generar fragmentos (chunks) como se solicitó."
                    )
                    payload.document.metadata["extracted_text"] = ""
                    payload.document.metadata["document_subject"] = "Bloqueado por Recitación (Ficha Técnica)"
                    payload.document.metadata["visual_tabular_data"] = ""
                    payload.document.metadata["recitation_blocked"] = True
                    payload.document.metadata["recitation_warning"] = (
                        "El proceso de extracción OCR fue bloqueado por los filtros de recitación/derechos de autor de Gemini "
                        "(frecuente en fichas técnicas verbatim de productos como Sikafloor)."
                    )
                    return payload
                
                logger.warning("response.parsed is None or incomplete. Attempting manual parsing from response.text.")
                
                # Check for empty/blocked response
                text = response.text
                
                if not text:
                    raise ValueError(f"Gemini returned an empty/blocked response (finish reason: {finish_reason})")
                
                text = text.strip()
                if text.startswith("```"):
                    lines = text.splitlines()
                    if len(lines) >= 3:
                        text = "\n".join(lines[1:-1])
                try:
                    extracted_data = ExtractedContent.model_validate_json(text)
                except Exception as json_err:
                    logger.error(f"Failed to parse Gemini response as JSON. Finish reason: {finish_reason}. Text sample: {text[:200]}")
                    if finish_reason == types.FinishReason.MAX_TOKENS:
                         raise ValueError(f"Gemini response truncated (MAX_TOKENS). The document might be too long for a single OCR pass.")
                    raise ValueError(f"Failed to parse Gemini response as JSON (finish reason: {finish_reason}): {json_err}")
            
            subject = getattr(extracted_data, "subject", "") or ""
            body = getattr(extracted_data, "body", "") or ""
            visual_data = getattr(extracted_data, "visual_tabular_data", "") or ""

            # Guard against empty body extraction
            if not isinstance(body, str) or not body.strip():
                logger.error(f"Gemini returned empty or invalid body for {payload.document.filename}")
                raise ValueError(f"OCR extraction returned empty body for {payload.document.filename}")

            # Merge visual/tabular data into body so it gets chunked and embedded
            full_text = body
            if isinstance(visual_data, str) and visual_data.strip():
                full_text += "\n\n---\n\n" + visual_data

            # Store extracted fields for downstream filters (chunker, embedder)
            payload.document.metadata["extracted_text"] = full_text
            payload.document.metadata["document_subject"] = subject
            payload.document.metadata["visual_tabular_data"] = visual_data

            logger.info(f"Gemini OCR extraction successful. Subject: {subject[:80]}")
            return payload

        except Exception as exc:
            logger.error(f"Gemini OCR extraction failed: {exc}")
            raise
