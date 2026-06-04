# Research: Drive Ingestion and LLM OCR

## Decision: Google Drive API (Native SDK)
**Rationale**: Using `google-api-python-client` is the officially supported way to interact with Google Drive. It handles authentication securely via Service Accounts and provides robust methods for downloading file content.
**Alternatives Considered**: 
- `requests` with public links: Rejected because most documents will be private.
- `gdown`: Rejected as it's a wrapper and less stable for production server-side tasks than the official SDK.

## Decision: Gemini 3 Flash Preview
**Rationale**: `gemini-3-flash-preview` offers high-speed multimodal capabilities (OCR) at a lower cost than Pro models, while maintaining enough intelligence to handle complex document layouts (tables, images) as requested.
**Alternatives Considered**:
- `gemini-1.5-pro`: Better but more expensive and slower.
- `tesseract`: Traditional OCR, but lacks the layout understanding and table-to-text conversion intelligence of LLMs.

## Prompt Engineering for OCR
**Prompt Design**:
```text
Extract the content of this document with high precision.
Focus specifically on the following sections:
1. SUBJECT (Asunto): The formal subject line of the communication.
2. BODY (Texto): The main message content.

Guidelines:
- If you find TABLES, represent them as a list of items or a markdown table.
- If you find IMAGES, describe their content and any text within them in the BODY section.
- Output the result in English.
- Return the result in a structured JSON format with 'subject' and 'body' fields.
```

## Entity Updates
**SourceDocument**:
- Add `document_type: DocumentType` (SENT, RECEIVED).
- Add `source_url: Optional[str]`.
- Logic:
    - If `enviadas_url` exists → `DocumentType.SENT`.
    - If `recibidas_url` exists → `DocumentType.RECEIVED`.
    - Fallback: Current logic.

## Pipeline Branching
**Logic**:
```python
if payload.document.document_type == DocumentType.SENT:
    # Path: Reader -> PDFReader -> DocumentCleaner (Regex)
else:
    # Path: Reader -> GeminiExtractor (OCR)
```
Note: `DocumentCleaner` might still be useful for LLM output if we want further normalization, but Gemini can handle most of it via the prompt.
