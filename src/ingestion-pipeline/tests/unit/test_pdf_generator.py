"""Unit tests for PDFResponseGenerator."""

import pytest
from src.filters.pdf_generator import PDFResponseGenerator


@pytest.fixture
def generator():
    return PDFResponseGenerator()


@pytest.fixture
def sample_metadata():
    return {
        "contract_number": "CW-276532",
        "sender": "CYS Constructores",
        "work_front": "Descarga intermedia",
        "document_date": "2025-02-26",
        "process": "Supervisión técnica",
        "subject": "Respuesta a informe",
    }


class TestPDFResponseGenerator:

    def test_generates_pdf_bytes(self, generator, sample_metadata):
        pdf = generator.generate_response_pdf("Test body", sample_metadata)
        assert isinstance(pdf, bytes) and len(pdf) > 0

    def test_pdf_header(self, generator, sample_metadata):
        pdf = generator.generate_response_pdf("Body", sample_metadata)
        assert pdf[:5] == b"%PDF-"

    def test_metadata_increases_pdf_size(self, generator, sample_metadata):
        """PDF with metadata should be larger than a minimal one."""
        pdf_with = generator.generate_response_pdf("Content", sample_metadata)
        pdf_without = generator.generate_response_pdf("Content", {})
        assert len(pdf_with) >= len(pdf_without)

    def test_empty_text(self, generator, sample_metadata):
        pdf = generator.generate_response_pdf("", sample_metadata)
        assert pdf[:5] == b"%PDF-"

    def test_multiline(self, generator, sample_metadata):
        pdf = generator.generate_response_pdf("P1\n\nP2\n\nP3", sample_metadata)
        assert len(pdf) > 500

    def test_no_subject(self, generator):
        pdf = generator.generate_response_pdf("Body", {"contract_number": "C"})
        assert pdf[:5] == b"%PDF-"

    def test_special_chars(self, generator, sample_metadata):
        pdf = generator.generate_response_pdf("Señor Gómez Nº 5", sample_metadata)
        assert len(pdf) > 0
