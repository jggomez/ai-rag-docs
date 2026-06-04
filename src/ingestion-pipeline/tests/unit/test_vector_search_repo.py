"""Unit tests for FirestoreVectorSearchRepository.

Tests the hybrid search fallback logic, filter stage building,
and sent document resolution. All Firestore calls are mocked.
"""

from unittest.mock import MagicMock, patch, call
import pytest

from src.repositories.vector_search_repo import FirestoreVectorSearchRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_clients():
    """Creates mock Firestore clients for received and sent databases."""
    client_received = MagicMock()
    client_sent = MagicMock()
    return client_received, client_sent


@pytest.fixture
def repo(mock_clients):
    """Creates a repo instance with mocked Firestore clients."""
    client_received, client_sent = mock_clients
    return FirestoreVectorSearchRepository(
        client_received=client_received,
        client_sent=client_sent,
    )


@pytest.fixture
def fake_vector():
    """A fake 768-dimensional query vector."""
    return [0.1] * 768


def _make_chunk_snapshot(data: dict, doc_id: str = "chunk_001"):
    """Helper to create a mock Firestore DocumentSnapshot."""
    snapshot = MagicMock()
    snapshot.to_dict.return_value = data
    snapshot.id = doc_id
    return snapshot


# ---------------------------------------------------------------------------
# _build_filter_stages
# ---------------------------------------------------------------------------

class TestBuildFilterStages:
    """Verify the progressive fallback stage construction."""

    def test_all_four_filters_present(self, repo):
        stages = repo._build_filter_stages("C-100", "Supervision", "Descarga", "CYS")
        stage_names = [s[0] for s in stages]
        assert stage_names == [
            "contrato+proceso+frente+remitente",
            "contrato+proceso+frente",
            "contrato+proceso",
            "contrato",
            "vector_only",
        ]

    def test_three_filters_no_sender(self, repo):
        stages = repo._build_filter_stages("C-100", "Supervision", "Descarga", None)
        stage_names = [s[0] for s in stages]
        assert "contrato+proceso+frente+remitente" not in stage_names
        assert stage_names[0] == "contrato+proceso+frente"

    def test_two_filters_only(self, repo):
        stages = repo._build_filter_stages("C-100", "Supervision", None, None)
        stage_names = [s[0] for s in stages]
        assert stage_names == ["contrato+proceso", "contrato", "vector_only"]

    def test_contract_only(self, repo):
        stages = repo._build_filter_stages("C-100", None, None, None)
        stage_names = [s[0] for s in stages]
        assert stage_names == ["contrato", "vector_only"]

    def test_no_filters(self, repo):
        stages = repo._build_filter_stages(None, None, None, None)
        assert len(stages) == 1
        assert stages[0][0] == "vector_only"
        assert stages[0][1] == {}

    def test_stage_filter_values_are_correct(self, repo):
        stages = repo._build_filter_stages("CTR-001", "QA", "Front-A", "ACME")
        # First stage should have all 4 filters
        _, filters = stages[0]
        assert filters == {
            "numero_contrato": "CTR-001",
            "proceso": "QA",
            "frente_trabajo": "Front-A",
            "remitente": "ACME",
        }

    def test_partial_none_skips_sender_stage(self, repo):
        """If sender is None but others present, stage 1 is skipped."""
        stages = repo._build_filter_stages("C", "P", "F", None)
        assert stages[0][0] == "contrato+proceso+frente"

    def test_empty_string_treated_as_falsy(self, repo):
        """Empty strings should be treated like None (no filter)."""
        stages = repo._build_filter_stages("", "", "", "")
        assert len(stages) == 1
        assert stages[0][0] == "vector_only"


# ---------------------------------------------------------------------------
# find_similar_chunks — fallback behavior
# ---------------------------------------------------------------------------

class TestFindSimilarChunks:
    """Test the hybrid search with progressive fallback."""

    def test_returns_results_from_first_matching_stage(self, repo, fake_vector):
        """If stage 1 returns results, no fallback happens."""
        chunk_data = {"texto": "test text", "id_borrador": "123"}
        mock_snapshot = _make_chunk_snapshot(chunk_data)

        # Mock the chain: collection.where().where()...find_nearest().get()
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.find_nearest.return_value.get.return_value = [mock_snapshot]
        repo.chunks_collection = mock_query

        results = repo.find_similar_chunks(
            query_vector=fake_vector,
            contract_number="C-100",
            process="QA",
            work_front="Front-A",
            sender="CYS",
        )

        assert len(results) == 1
        assert results[0]["texto"] == "test text"
        assert results[0]["firestore_id"] == "chunk_001"

    def test_falls_back_when_first_stage_empty(self, repo, fake_vector):
        """If restrictive stage returns empty, falls back to less restrictive."""
        chunk_data = {"texto": "fallback result"}
        mock_snapshot = _make_chunk_snapshot(chunk_data, doc_id="fb_001")

        call_count = 0
        def mock_get_side_effect():
            nonlocal call_count
            call_count += 1
            # First 4 calls return empty (stages 1-4), 5th returns results
            if call_count < 5:
                return []
            return [mock_snapshot]

        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.find_nearest.return_value.get = mock_get_side_effect
        repo.chunks_collection = mock_query

        results = repo.find_similar_chunks(
            query_vector=fake_vector,
            contract_number="C-100",
            process="QA",
            work_front="Front-A",
            sender="CYS",
        )

        assert len(results) == 1
        assert results[0]["firestore_id"] == "fb_001"
        assert call_count == 5  # All 5 stages tried

    def test_returns_empty_when_all_stages_fail(self, repo, fake_vector):
        """If all stages return empty, returns empty list."""
        mock_query = MagicMock()
        mock_query.where.return_value = mock_query
        mock_query.find_nearest.return_value.get.return_value = []
        repo.chunks_collection = mock_query

        results = repo.find_similar_chunks(
            query_vector=fake_vector,
            contract_number="C-100",
        )

        assert results == []

    def test_vector_only_search_no_filters(self, repo, fake_vector):
        """With no metadata filters, only vector_only stage runs."""
        chunk_data = {"texto": "pure vector"}
        mock_snapshot = _make_chunk_snapshot(chunk_data)

        mock_query = MagicMock()
        mock_query.find_nearest.return_value.get.return_value = [mock_snapshot]
        repo.chunks_collection = mock_query

        results = repo.find_similar_chunks(query_vector=fake_vector)

        assert len(results) == 1
        # where() should NOT be called since no filters
        mock_query.where.assert_not_called()

    def test_respects_limit_parameter(self, repo, fake_vector):
        """The limit parameter is passed through to find_nearest."""
        mock_query = MagicMock()
        mock_query.find_nearest.return_value.get.return_value = []
        repo.chunks_collection = mock_query

        repo.find_similar_chunks(query_vector=fake_vector, limit=5)

        # Check find_nearest was called with limit=5
        find_nearest_call = mock_query.find_nearest.call_args
        assert find_nearest_call.kwargs["limit"] == 5


# ---------------------------------------------------------------------------
# resolve_sent_documents
# ---------------------------------------------------------------------------

class TestResolveSentDocuments:
    """Test the draft_id → sent document text resolution."""

    def test_resolves_unique_draft_ids(self, repo):
        chunks = [
            {"id_borrador": "draft_A", "texto": "chunk 1"},
            {"id_borrador": "draft_B", "texto": "chunk 2"},
            {"id_borrador": "draft_A", "texto": "chunk 3 (duplicate)"},
        ]

        # Mock sent collection queries
        sent_doc_a = MagicMock()
        sent_doc_a.to_dict.return_value = {"texto_extraido": "Sent text A"}
        sent_doc_b = MagicMock()
        sent_doc_b.to_dict.return_value = {"texto_extraido": "Sent text B"}

        def mock_where(field, op, value):
            mock_q = MagicMock()
            mock_q.limit.return_value = mock_q
            if value == "draft_A":
                mock_q.get.return_value = [sent_doc_a]
            elif value == "draft_B":
                mock_q.get.return_value = [sent_doc_b]
            return mock_q

        repo.sent_docs_collection.where = mock_where

        result = repo.resolve_sent_documents(chunks)

        assert len(result) == 2
        assert result["draft_A"] == "Sent text A"
        assert result["draft_B"] == "Sent text B"

    def test_empty_chunks_returns_empty(self, repo):
        result = repo.resolve_sent_documents([])
        assert result == {}

    def test_chunks_without_draft_id_returns_empty(self, repo):
        chunks = [{"texto": "no draft id here"}]
        result = repo.resolve_sent_documents(chunks)
        assert result == {}

    def test_no_sent_document_found(self, repo):
        chunks = [{"id_borrador": "draft_missing"}]

        mock_q = MagicMock()
        mock_q.limit.return_value = mock_q
        mock_q.get.return_value = []
        repo.sent_docs_collection.where = MagicMock(return_value=mock_q)

        result = repo.resolve_sent_documents(chunks)
        assert result == {}

    def test_sent_document_without_texto_extraido(self, repo):
        chunks = [{"id_borrador": "draft_empty"}]

        sent_doc = MagicMock()
        sent_doc.to_dict.return_value = {"remitente": "CYS"}  # No texto_extraido

        mock_q = MagicMock()
        mock_q.limit.return_value = mock_q
        mock_q.get.return_value = [sent_doc]
        repo.sent_docs_collection.where = MagicMock(return_value=mock_q)

        result = repo.resolve_sent_documents(chunks)
        assert result == {}
