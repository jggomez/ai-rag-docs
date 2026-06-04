import fitz
from src.filters.pdf_reader import PDFReader
from src.domain.entities import SourceDocument, ProcessingPayload, DocumentStatus

def create_dummy_pdf(text: str) -> bytes:
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), text)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes

def test_pdf_reader_extraction():
    test_text = "Hello world from PyMuPDF"
    pdf_content = create_dummy_pdf(test_text)
    
    doc = SourceDocument(
        id="test-1",
        filename="test.pdf",
        bucket="test-bucket",
        object_name="test.pdf",
        content_type="application/pdf",
        size_bytes=len(pdf_content),
        status=DocumentStatus.PROCESSING,
        sender="Test Sender",
        contract_number="123",
        work_front="Front A",
        document_date="2024-01-01",
        process="Extraction"
    )
    payload = ProcessingPayload(document=doc, content=pdf_content)
    
    reader = PDFReader()
    result = reader.process(payload)
    
    assert test_text in result.document.metadata["extracted_text"]
    assert len(result.document.metadata["extracted_text"]) > 0
