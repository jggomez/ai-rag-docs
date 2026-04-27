from src.filters.chunker import TextChunker
from src.domain.entities import SourceDocument, ProcessingPayload, EngineeringMetadata

def test_text_chunker():
    chunker = TextChunker(chunk_size=50, chunk_overlap=10)
    doc = SourceDocument(
        id="doc_123",
        filename="test.pdf",
        bucket="b",
        object_name="o",
        content_type="c",
        size_bytes=0,
        engineering_metadata=EngineeringMetadata(
            sender="s",
            contract_number="cn",
            work_front="wf",
            document_date="d",
            process="p"
        )
    )
    doc.metadata["extracted_text"] = "This is a long text that should be chunked into multiple pieces for testing."
    
    payload = ProcessingPayload(document=doc)
    result = chunker.process(payload)
    
    assert len(result.chunks) > 1
    assert result.chunks[0].document_id == "doc_123"
    assert result.chunks[0].subject != ""
    assert result.chunks[0].body != ""
    assert result.chunks[0].metadata["contract_number"] == "cn"
