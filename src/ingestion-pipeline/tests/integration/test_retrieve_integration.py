"""Integration tests for RAG Retriever with real Firestore.

These tests require:
- GOOGLE_APPLICATION_CREDENTIALS or ADC configured
- Firestore databases docs-recibidos and docs-enviados with vector indexes
- At least some documents ingested

Run with: pytest tests/integration/test_retrieve_integration.py -v
"""

import pytest
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1.base_vector_query import DistanceMeasure

from src.repositories.vector_search_repo import FirestoreVectorSearchRepository
from src.filters.pdf_generator import PDFResponseGenerator


# Skip if Firestore is not reachable
def _firestore_available():
    import os
    try:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "devhack-3f0c2")
        client = firestore.Client(database="docs-recibidos", project=project_id)
        # Use a small query to verify connectivity
        list(client.collection("documentos_chunks").limit(1).stream())
        return True
    except Exception as exc:
        print(f"Firestore not available: {exc}")
        return False

skip_no_firestore = pytest.mark.skipif(
    not _firestore_available(),
    reason="Firestore docs-recibidos not reachable"
)


@skip_no_firestore
class TestVectorSearchIntegration:
    """Real Firestore integration tests for vector search."""

    @pytest.fixture(autouse=True)
    def setup_repo(self):
        import os
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "devhack-3f0c2")
        client_received = firestore.Client(database="docs-recibidos", project=project_id)
        client_sent = firestore.Client(database="docs-enviados", project=project_id)
        self.repo = FirestoreVectorSearchRepository(
            client_received=client_received,
            client_sent=client_sent,
        )
        # Get a real vector from an existing chunk for testing
        chunks = self.repo.chunks_collection.limit(1).get()
        if chunks:
            chunk_data = chunks[0].to_dict()
            self.sample_vector = chunk_data.get("vector", [0.1] * 768)
            self.sample_contract = chunk_data.get("numero_contrato")
            self.sample_process = chunk_data.get("proceso")
            self.sample_front = chunk_data.get("frente_trabajo")
            self.sample_sender = chunk_data.get("remitente")
            self.sample_draft_id = chunk_data.get("id_borrador")
        else:
            pytest.skip("No chunks found in Firestore")

    def test_pure_vector_search_returns_results(self):
        """Vector-only search should return at least 1 result."""
        results = self.repo.find_similar_chunks(
            query_vector=self.sample_vector, limit=5
        )
        assert len(results) > 0
        assert "firestore_id" in results[0]

    def test_hybrid_search_with_contract_filter(self):
        """Search filtered by contract number should return results."""
        if not self.sample_contract:
            pytest.skip("No contract in sample chunk")
        results = self.repo.find_similar_chunks(
            query_vector=self.sample_vector,
            limit=5,
            contract_number=self.sample_contract,
        )
        assert len(results) > 0
        # Verify all results have matching contract
        for chunk in results:
            assert chunk.get("numero_contrato") == self.sample_contract

    def test_hybrid_search_fallback_on_impossible_filter(self):
        """Search with impossible filter combination falls back."""
        results = self.repo.find_similar_chunks(
            query_vector=self.sample_vector,
            limit=5,
            contract_number="NONEXISTENT-CONTRACT-XYZ",
            process="NONEXISTENT-PROCESS",
            work_front="NONEXISTENT-FRONT",
            sender="NONEXISTENT-SENDER",
        )
        # Should fall back to vector_only and still return results
        assert len(results) > 0

    def test_resolve_sent_documents_real(self):
        """Resolve sent documents from real chunk draft IDs."""
        if not self.sample_draft_id:
            pytest.skip("No draft_id in sample chunk")
        chunks = [{"id_borrador": self.sample_draft_id}]
        result = self.repo.resolve_sent_documents(chunks)
        # May or may not find a sent doc; just verify no crash
        assert isinstance(result, dict)

    def test_chunk_result_structure(self):
        """Verify chunk results contain expected fields."""
        results = self.repo.find_similar_chunks(
            query_vector=self.sample_vector, limit=1
        )
        assert len(results) > 0
        chunk = results[0]
        assert "firestore_id" in chunk
        # Chunks should have metadata fields from ingestion
        expected_fields = ["texto", "asunto"]
        has_any = any(f in chunk for f in expected_fields)
        assert has_any, f"Chunk missing expected fields. Keys: {list(chunk.keys())}"


@skip_no_firestore
class TestPDFGeneratorIntegration:
    """Real integration test: generate a PDF from actual Firestore data."""

    def test_generate_pdf_from_real_chunk_data(self):
        import os
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "devhack-3f0c2")
        client_received = firestore.Client(database="docs-recibidos", project=project_id)
        client_sent = firestore.Client(database="docs-enviados", project=project_id)
        repo = FirestoreVectorSearchRepository(
            client_received=client_received,
            client_sent=client_sent,
        )
        chunks = repo.chunks_collection.limit(1).get()
        if not chunks:
            pytest.skip("No chunks")

        chunk = chunks[0].to_dict()
        metadata = {
            "contract_number": chunk.get("numero_contrato", "N/A"),
            "sender": chunk.get("remitente", "N/A"),
            "work_front": chunk.get("frente_trabajo", "N/A"),
            "process": chunk.get("proceso", "N/A"),
            "subject": chunk.get("asunto", "Test"),
        }

        generator = PDFResponseGenerator()
        pdf = generator.generate_response_pdf(
            response_text=chunk.get("texto", "Texto de prueba"),
            metadata=metadata,
        )
        assert pdf[:5] == b"%PDF-"
        assert len(pdf) > 500
