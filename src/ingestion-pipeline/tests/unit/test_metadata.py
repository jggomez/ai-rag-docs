from src.filters.metadata import MetadataExtractor
from src.domain.entities import SourceDocument, ProcessingPayload

def test_metadata_extractor_heuristics():
    extractor = MetadataExtractor()
    doc = SourceDocument(
        id="test_id",
        filename="2023-10-27_Front-A.pdf",
        bucket="test-bucket",
        object_name="COMMUNICATION_RECEIVED/2023-11-20_INFORME.pdf",
        content_type="application/pdf",
        size_bytes=100,
        work_front="PENDING",
        document_date="PENDING",
    )
    
    payload = ProcessingPayload(document=doc)
    result = extractor.process(payload)
    
    assert result.document.document_date == "2023-11-20"
