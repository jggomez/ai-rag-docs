import io
import logging
from typing import Dict
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer

logger = logging.getLogger(__name__)


class PDFResponseGenerator:
    """
    Generates a formal response letter PDF using reportlab.
    Produces a clean, professional document without company branding.
    """

    def generate_response_pdf(
        self, response_text: str, metadata: Dict[str, str]
    ) -> bytes:
        """
        Generates a PDF letter with the provided response text and metadata.

        Args:
            response_text: The AI-generated response text body.
            metadata: Engineering metadata (contract_number, sender, work_front, etc.)

        Returns:
            PDF file contents as bytes.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            leftMargin=1 * inch,
            rightMargin=1 * inch,
            topMargin=1 * inch,
            bottomMargin=1 * inch,
        )

        styles = getSampleStyleSheet()

        # Custom styles for the formal letter
        header_style = ParagraphStyle(
            "LetterHeader",
            parent=styles["Normal"],
            fontSize=10,
            leading=14,
            spaceAfter=6,
        )

        body_style = ParagraphStyle(
            "LetterBody",
            parent=styles["Normal"],
            fontSize=11,
            leading=16,
            spaceAfter=8,
            alignment=4,  # Justified
        )

        subject_style = ParagraphStyle(
            "LetterSubject",
            parent=styles["Normal"],
            fontSize=11,
            leading=16,
            spaceAfter=12,
            fontName="Helvetica-Bold",
        )

        # Build the document content
        flowables = []

        # Header: metadata block
        contract_number = metadata.get("contract_number", "N/A")
        sender = metadata.get("sender", "N/A")
        work_front = metadata.get("work_front", "N/A")
        document_date = metadata.get("document_date", "N/A")
        process_name = metadata.get("process", "N/A")

        header_text = (
            f"<b>Contrato:</b> {contract_number}<br/>"
            f"<b>Destinatario:</b> {sender}<br/>"
            f"<b>Frente de Trabajo:</b> {work_front}<br/>"
            f"<b>Fecha:</b> {document_date}<br/>"
            f"<b>Proceso:</b> {process_name}"
        )
        flowables.append(Paragraph(header_text, header_style))
        flowables.append(Spacer(1, 0.3 * inch))

        # Subject line (if present in metadata)
        subject = metadata.get("subject", "")
        if subject:
            flowables.append(Paragraph(f"<b>Ref:</b> {subject}", subject_style))
            flowables.append(Spacer(1, 0.2 * inch))

        # Body: AI-generated response text, split by paragraphs
        paragraphs = response_text.split("\n")
        for paragraph in paragraphs:
            clean_text = paragraph.strip()
            if clean_text:
                flowables.append(Paragraph(clean_text, body_style))

        # Build the PDF
        doc.build(flowables)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        logger.info(f"Generated PDF response ({len(pdf_bytes)} bytes).")
        return pdf_bytes
