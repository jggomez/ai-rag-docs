import io
import logging
from typing import Dict, List
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    PageBreak,
    Table,
    TableStyle,
    HRFlowable,
)

logger = logging.getLogger(__name__)

# ── Colour palette ────────────────────────────────────────────────────────────
_BLUE_DARK = colors.HexColor("#1a3a5c")
_BLUE_MID = colors.HexColor("#2c6fad")
_BLUE_LIGHT = colors.HexColor("#ddeeff")
_GREY_ROW = colors.HexColor("#f5f7fa")
_GREY_BORDER = colors.HexColor("#cccccc")
_TEXT_DARK = colors.HexColor("#1a1a2e")
_GREEN_SENT = colors.HexColor("#e6f4ea")
_GREEN_DARK = colors.HexColor("#1e6e42")

# Maximum characters to show per sent-document excerpt in the references page.
_SENT_TEXT_EXCERPT_CHARS = 600


class PDFResponseGenerator:
    """
    Generates a formal response letter PDF using reportlab.

    The PDF is composed of two parts:
      1. Response letter page(s) – the AI-generated reply.
      2. References page        – a structured summary of every context
                                  document (received chunks + resolved sent
                                  responses) that was used to produce the reply.
    """

    # ── Public API ─────────────────────────────────────────────────────────────

    def generate_response_pdf(
        self,
        response_text: str,
        metadata: Dict[str, str],
        similar_chunks: List[dict] = None,
        sent_texts: Dict[str, Dict[str, str]] = None,
    ) -> bytes:
        """
        Generates a PDF letter with the provided response text, metadata, and
        an optional references page listing all context documents used.

        Args:
            response_text:  The AI-generated response text body.
            metadata:       Engineering metadata (contract_number, sender, …).
            similar_chunks: Reranked received-document chunks used as RAG context.
            sent_texts:     Dict mapping {id_borrador: {texto, filename}} of resolved
                            sent responses used as RAG context.

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

        styles = self._build_styles()
        flowables = []

        # ── Page 1+: Response letter ──────────────────────────────────────────
        flowables.extend(self._build_letter_section(response_text, metadata, styles))

        # ── References page (only when context docs are available) ────────────
        if similar_chunks:
            flowables.append(PageBreak())
            flowables.extend(
                self._build_references_section(
                    similar_chunks,
                    sent_texts or {},
                    styles,
                )
            )

        doc.build(flowables)
        pdf_bytes = buffer.getvalue()
        buffer.close()

        logger.info(
            f"Generated PDF response ({len(pdf_bytes)} bytes, "
            f"{len(similar_chunks or [])} context docs referenced)."
        )
        return pdf_bytes

    # ── Letter section ─────────────────────────────────────────────────────────

    def _build_letter_section(
        self, response_text: str, metadata: Dict[str, str], styles: dict
    ) -> list:
        """Builds the main response-letter flowables."""
        flowables = []

        subject = metadata.get("subject", "")
        if subject:
            flowables.append(Paragraph(f"<b>Ref:</b> {subject}", styles["subject"]))
            flowables.append(Spacer(1, 0.2 * inch))

        for paragraph in response_text.split("\n"):
            clean = paragraph.strip()
            if clean:
                flowables.append(Paragraph(clean, styles["body"]))

        return flowables

    # ── References section ─────────────────────────────────────────────────────

    def _build_references_section(
        self,
        similar_chunks: List[dict],
        sent_texts: Dict[str, Dict[str, str]],
        styles: dict,
    ) -> list:
        """
        Builds the references page with two sub-sections:
          • Documentos Recibidos — one row per retrieved chunk.
          • Respuestas Enviadas   — excerpt of each resolved sent document.
        """
        flowables = []

        # ── Section header ────────────────────────────────────────────────────
        flowables.append(
            Paragraph("Documentos de Contexto Utilizados", styles["page_title"])
        )
        flowables.append(Spacer(1, 0.08 * inch))
        flowables.append(
            Paragraph(
                "La siguiente página presenta los documentos de referencia que el sistema "
                "utilizó como contexto para generar la respuesta anterior.",
                styles["caption"],
            )
        )
        flowables.append(Spacer(1, 0.25 * inch))

        # ── Sub-section 1: Received documents ────────────────────────────────
        flowables.append(
            Paragraph("Documentos Recibidos (contexto de recuperación)", styles["section_title"])
        )
        flowables.append(Spacer(1, 0.1 * inch))
        flowables.extend(self._build_received_table(similar_chunks, styles))
        flowables.append(Spacer(1, 0.3 * inch))

        # ── Sub-section 2: Sent responses ────────────────────────────────────
        # Collect unique (id_borrador → sent text) pairs from the chunks
        seen_draft_ids: set = set()
        ordered_sent: list = []
        for chunk in similar_chunks:
            draft_id = chunk.get("id_borrador")
            if draft_id and draft_id in sent_texts and draft_id not in seen_draft_ids:
                seen_draft_ids.add(draft_id)
                data = sent_texts[draft_id]
                ordered_sent.append(
                    {
                        "filename": data.get("filename", draft_id),
                        "texto": data.get("texto", ""),
                        "asunto": chunk.get("asunto", "—"),
                    }
                )

        if ordered_sent:
            flowables.append(HRFlowable(width="100%", color=_GREY_BORDER))
            flowables.append(Spacer(1, 0.15 * inch))
            flowables.append(
                Paragraph("Respuestas Enviadas (contexto de generación)", styles["section_title"])
            )
            flowables.append(Spacer(1, 0.1 * inch))
            flowables.extend(self._build_sent_section(ordered_sent, styles))

        return flowables

    def _build_received_table(self, chunks: List[dict], styles: dict) -> list:
        """Renders the received-documents table with one row per chunk."""
        col_headers = ["#", "Asunto", "Contrato", "Documento", "Relevancia"]

        table_data = [col_headers]
        for idx, chunk in enumerate(chunks, 1):
            rerank_score = chunk.get("rerank_score")
            score_cell = f"{rerank_score:.3f}" if rerank_score is not None else "—"

            # Truncate long text to keep rows compact
            asunto = self._truncate(chunk.get("asunto", "—"), 80)
            contrato = chunk.get("numero_contrato", "—")
            documento = chunk.get("nombre_archivo", "—")

            table_data.append([
                str(idx),
                Paragraph(asunto, styles["table_cell"]),
                Paragraph(contrato, styles["table_cell"]),
                Paragraph(documento, styles["table_cell"]),
                score_cell,
            ])

        # Column widths that fit letter page (6.5" usable width)
        col_widths = [0.3 * inch, 2.8 * inch, 1.2 * inch, 1.5 * inch, 0.7 * inch]

        table = Table(table_data, colWidths=col_widths, repeatRows=1)
        table.setStyle(self._received_table_style())

        return [table]

    def _build_sent_section(self, ordered_sent: list, styles: dict) -> list:
        """Renders one card per resolved sent document showing an excerpt."""
        flowables = []
        for entry in ordered_sent:
            filename = entry["filename"]
            asunto = entry["asunto"]
            texto = entry["texto"]

            excerpt = texto[:_SENT_TEXT_EXCERPT_CHARS].strip()
            if len(texto) > _SENT_TEXT_EXCERPT_CHARS:
                excerpt += "…"

            # Card header
            flowables.append(
                Paragraph(
                    f"<b>Documento:</b> {filename} &nbsp;|&nbsp; <b>Asunto:</b> {asunto}",
                    styles["sent_header"],
                )
            )
            # Excerpt body
            flowables.append(
                Paragraph(excerpt.replace("\n", "<br/>"), styles["sent_body"])
            )
            flowables.append(Spacer(1, 0.15 * inch))

        return flowables

    # ── Styles ─────────────────────────────────────────────────────────────────

    def _build_styles(self) -> dict:
        base = getSampleStyleSheet()
        return {
            "body": ParagraphStyle(
                "LetterBody",
                parent=base["Normal"],
                fontSize=11,
                leading=16,
                spaceAfter=8,
                alignment=4,  # Justified
                textColor=_TEXT_DARK,
            ),
            "subject": ParagraphStyle(
                "LetterSubject",
                parent=base["Normal"],
                fontSize=11,
                leading=16,
                spaceAfter=12,
                fontName="Helvetica-Bold",
                textColor=_TEXT_DARK,
            ),
            "page_title": ParagraphStyle(
                "PageTitle",
                parent=base["Normal"],
                fontSize=14,
                leading=18,
                fontName="Helvetica-Bold",
                textColor=_BLUE_DARK,
                spaceAfter=4,
            ),
            "section_title": ParagraphStyle(
                "SectionTitle",
                parent=base["Normal"],
                fontSize=11,
                leading=14,
                fontName="Helvetica-Bold",
                textColor=_BLUE_MID,
                spaceAfter=4,
            ),
            "caption": ParagraphStyle(
                "Caption",
                parent=base["Normal"],
                fontSize=9,
                leading=12,
                textColor=colors.HexColor("#555555"),
            ),
            "table_cell": ParagraphStyle(
                "TableCell",
                parent=base["Normal"],
                fontSize=8,
                leading=10,
                textColor=_TEXT_DARK,
            ),
            "sent_header": ParagraphStyle(
                "SentHeader",
                parent=base["Normal"],
                fontSize=9,
                leading=12,
                fontName="Helvetica-Bold",
                textColor=_GREEN_DARK,
                backColor=_GREEN_SENT,
                spaceAfter=2,
                borderPad=4,
            ),
            "sent_body": ParagraphStyle(
                "SentBody",
                parent=base["Normal"],
                fontSize=9,
                leading=13,
                textColor=_TEXT_DARK,
                backColor=colors.HexColor("#fafffe"),
                spaceAfter=4,
                leftIndent=6,
            ),
        }

    def _received_table_style(self) -> TableStyle:
        return TableStyle([
            # Header row
            ("BACKGROUND", (0, 0), (-1, 0), _BLUE_DARK),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 8),
            ("ALIGN", (0, 0), (-1, 0), "CENTER"),
            ("VALIGN", (0, 0), (-1, 0), "MIDDLE"),
            ("BOTTOMPADDING", (0, 0), (-1, 0), 7),
            ("TOPPADDING", (0, 0), (-1, 0), 7),
            # Data rows — alternating background
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, _GREY_ROW]),
            ("FONTSIZE", (0, 1), (-1, -1), 8),
            ("VALIGN", (0, 1), (-1, -1), "TOP"),
            ("TOPPADDING", (0, 1), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 1), (-1, -1), 5),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            # Index column centred
            ("ALIGN", (0, 1), (0, -1), "CENTER"),
            # Relevancia column centred
            ("ALIGN", (6, 1), (6, -1), "CENTER"),
            # Grid
            ("GRID", (0, 0), (-1, -1), 0.4, _GREY_BORDER),
            ("LINEBELOW", (0, 0), (-1, 0), 1.5, _BLUE_MID),
            # Rounded-feel top corners via thick top border
            ("LINEABOVE", (0, 0), (-1, 0), 1.5, _BLUE_DARK),
        ])

    # ── Utilities ──────────────────────────────────────────────────────────────

    @staticmethod
    def _truncate(text: str, max_chars: int) -> str:
        """Truncates text to max_chars adding ellipsis if needed."""
        if not text:
            return "—"
        return text if len(text) <= max_chars else text[:max_chars - 1] + "…"
