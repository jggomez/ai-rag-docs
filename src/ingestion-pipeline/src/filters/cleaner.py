import re
import logging
from src.filters.base import Filter
from src.domain.entities import ProcessingPayload

logger = logging.getLogger(__name__)

def document_cleaner(raw_text):
    """
    Comprehensive function to clean and segment technical engineering communications.
    Designed to:
    1. Extract Subject and Body.
    2. Remove pagination noise, tax IDs (NIT), stamps, and digital signatures.
    3. Repair OCR line breaks to improve vectorization (RAG).
    """
    
    # --- 1. KEY METADATA EXTRACTION ---
    # Extract Subject: From 'Asunto:' to formal greeting
    asunto_match = re.search(r"(?i)Asunto:\s*(.*?)(?=\n\s*(?:Estimados?\s+señore?s?|Señore?s?|Respetado\s+\w+|De\s+mi\s+consideración):|\n\s*Ref.:)", raw_text, re.DOTALL)
    asunto = asunto_match.group(1).strip() if asunto_match else "Not detected"

    # Extract Body: From greeting to closing
    body_match = re.search(
        r"(?i)(?:Estimados?\s+señore?s?|Señore?s?|Respetado\s+\w+|De\s+mi\s+consideración):\s*(.*?)(?=\n\s*(?:Atentamente|Cordialmente|Sin\s+otro\s+particular|Respetuosamente),?)",
        raw_text, re.DOTALL
    )
    body = body_match.group(1).strip() if body_match else raw_text

    # --- 2. STRUCTURAL NOISE CLEANING ---
    # Remove "Page X of Y"
    body = re.sub(r"(?i)Página\s+\d+\s+de\s+\d+", "", body)
    
    # Remove repetitive filing codes (e.g., INT-OC-CYS-1283/25)
    body = re.sub(r"INT-OC-CYS-\d+/\d+", "", body)
    
    # Remove repetitive header blocks (generic structural patterns)
    noise_patterns = [
        # Generic: lines matching address patterns (Street + Number)
        r"(?i)^\s*(?:Calle|Carrera|Avenida|Av\.)\s+\d+.*$",
        r"(?i)TEL: \d+",
        r"(?i)NIT\.? \d+\.\d+\.\d+-\d+",
        # Generic: short ALL-CAPS lines (likely entity/header names)
        r"^[A-ZÁÉÍÓÚÑ\s/\-\.]{5,60}$",
        r"(?i)INGENIEROS\s+CONSULTORES",
        r"(?i)Radicado por:.*",
        r"(?i)Radicado EPM \d+"
    ]
    for pattern in noise_patterns:
        body = re.sub(pattern, "", body, flags=re.MULTILINE)

    # Remove digital signature residuals (Timestamp and hex-like hashes)
    body = re.sub(r"\d{10,}\s\d{2}:\d+", "", body)  # Signature timestamps
    # Only strip hex-like signature hashes (e.g., "a1b2c3d4-e5f6-g7h8-i9j0")
    body = re.sub(r"\b[0-9a-f]{8,}(?:-[0-9a-f]{4,}){2,}\b", "", body, flags=re.IGNORECASE)

    # --- 3. PARAGRAPH REPAIR (OCR FIX) ---
    # Join lines broken by OCR that belong to the same paragraph
    lines = body.split('\n')
    repaired_lines = []
    current_line = ""

    for line in lines:
        line = line.strip()
        if not line: continue
            
        if current_line:
            # If the previous line doesn't end with a period/punctuation and this isn't a list
            # If the previous line doesn't end with terminal punctuation and next isn't a list item
            if not re.search(r'[.:!?;)»"…]$', current_line) and not re.match(r'^(\d+[\.)\-]|[a-z][\.)\-]|•|[-–—])', line):
                current_line += " " + line
            else:
                repaired_lines.append(current_line)
                current_line = line
        else:
            current_line = line
            
    if current_line:
        repaired_lines.append(current_line)

    clean_body = "\n".join(repaired_lines)

    # --- 4. FINAL NORMALIZATION ---
    clean_body = re.sub(r' {2,}', ' ', clean_body) # Double spaces
    clean_body = re.sub(r'\n{3,}', '\n\n', clean_body) # Triple breaks
    
    return {
        "subject": asunto,
        "body_clean": clean_body.strip()
    }

class DocumentCleaner(Filter[ProcessingPayload, ProcessingPayload]):
    """
    Filter that uses expert_rag_document_cleaner to clean raw extracted text.
    """
    def process(self, payload: ProcessingPayload) -> ProcessingPayload:
        raw_text = payload.document.metadata.get("extracted_text", "")
        if not raw_text:
            logger.warning("No extracted text found in payload to clean.")
            return payload
            
        logger.info(f"Cleaning document text for {payload.document.filename}")
        
        result = document_cleaner(raw_text)
        
        # Store results back into the document state
        payload.document.metadata["extracted_text"] = result["body_clean"]
        payload.document.metadata["document_subject"] = result["subject"]
        
        logger.info(f"Document cleaning complete. Subject: {result['subject']}")
        return payload
