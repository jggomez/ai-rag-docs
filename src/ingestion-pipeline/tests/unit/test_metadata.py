from src.filters.metadata import MetadataExtractor
from src.domain.entities import SourceDocument, ProcessingPayload

def test_metadata_extractor_heuristics():
    extractor = MetadataExtractor()
    doc = SourceDocument(
        id="test_id",
        filename="2023-10-27_Contract-123_Sender-XYZ_Front-A_Process-X.pdf",
        bucket="test-bucket",
        object_name="COMMUNICATION_RECEIVED/C-100/CONSTRUCTOR_A/2023-11-20_INFORME.pdf",
        content_type="application/pdf",
        size_bytes=100,
        sender="PENDING",
        contract_number="PENDING",
        work_front="PENDING",
        document_date="PENDING",
        process="PENDING"
    )
    
    payload = ProcessingPayload(document=doc)
    result = extractor.process(payload)
    
    # Path is: COMMUNICATION_RECEIVED/C-100/CONSTRUCTOR_A/2023-11-20_INFORME.pdf
    # parts: ['C-100', 'CONSTRUCTOR_A', '2023-11-20_INFORME.pdf']
    assert result.document.contract_number == "C-100"
    assert result.document.sender == "CONSTRUCTOR_A"
    assert result.document.document_date == "2023-11-20"
