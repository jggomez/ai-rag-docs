# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import pytest
from unittest.mock import patch, MagicMock
from app.tools import _build_filter_stages, _rerank_chunks, search_communications

def test_build_filter_stages():
    # Test with all filters
    stages = _build_filter_stages("front_a", "asunto_b", "doc_123")
    assert stages == [
        ("id_only", {"id_documento": "doc_123"}),
        ("filename_only", {"nombre_archivo": "doc_123"}),
        ("subject+metadata", {"asunto": "asunto_b", "frente_trabajo": "front_a"}),
        ("subject_only", {"asunto": "asunto_b"}),
        ("work_front", {"frente_trabajo": "front_a"}),
        ("vector_only", {})
    ]

    # Test with document_id and work_front, no subject
    stages_no_subject = _build_filter_stages("front_a", None, "doc_123")
    assert stages_no_subject == [
        ("id_only", {"id_documento": "doc_123"}),
        ("filename_only", {"nombre_archivo": "doc_123"}),
        ("work_front", {"frente_trabajo": "front_a"}),
        ("vector_only", {})
    ]

    # Test with no filters
    stages_empty = _build_filter_stages(None, None, None)
    assert stages_empty == [("vector_only", {})]


@patch("app.tools._reranker")
def test_rerank_chunks(mock_reranker):
    # Mock reranker output
    mock_reranker.rerank.return_value = [
        {"id": 1, "score": 0.95},
        {"id": 0, "score": 0.85}
    ]
    
    candidates = [
        {"texto": "candidate 0 text", "id_borrador": "draft_0"},
        {"texto": "candidate 1 text", "id_borrador": "draft_1"}
    ]
    
    reranked = _rerank_chunks("test query", candidates)
    
    assert len(reranked) == 2
    assert reranked[0]["id_borrador"] == "draft_1"
    assert reranked[0]["rerank_score"] == 0.95
    assert reranked[1]["id_borrador"] == "draft_0"
    assert reranked[1]["rerank_score"] == 0.85


@patch("app.tools._genai_client")
@patch("app.tools._client_received")
@patch("app.tools._client_sent")
@patch("app.tools._reranker")
def test_search_communications_success(mock_reranker, mock_client_sent, mock_client_received, mock_genai_client):
    # 1. Mock GenAI Embedding
    mock_embeddings_list = MagicMock()
    mock_embeddings_list.values = [0.1] * 768
    mock_genai_client.models.embed_content.return_value = MagicMock(embeddings=[mock_embeddings_list])
    
    # 2. Mock client_received find_nearest get
    mock_doc_1 = MagicMock()
    mock_doc_1.to_dict.return_value = {
        "texto": "Recibimos solicitud de diseño de viga.",
        "asunto": "Diseño de viga",
        "nombre_archivo": "REC-001.pdf",
        "fecha_documento": "10/05/2026",
        "frente_trabajo": "Descarga",
        "id_borrador": "draft_viga"
    }
    
    mock_results = [mock_doc_1]
    mock_query = mock_client_received.collection.return_value
    mock_query.where.return_value = mock_query
    mock_query.find_nearest.return_value.get.return_value = mock_results
    
    # 3. Mock Reranker
    mock_reranker.rerank.return_value = [{"id": 0, "score": 0.99}]
    
    # 4. Mock client_sent resolving response
    mock_sent_doc = MagicMock()
    mock_sent_doc.to_dict.return_value = {
        "texto_extraido": "Enviamos respuesta de diseño de viga aprobando planos."
    }
    mock_client_sent.collection.return_value.where.return_value.limit.return_value.get.return_value = [mock_sent_doc]
    
    # Run
    result = search_communications(
        query="diseño de viga",
        work_front="Descarga",
        subject="viga",
        month=5,
        year=2026
    )
    
    # Verify results
    assert "### RELEVANT RECEIVED DOCUMENTS FOUND ###" in result
    assert "Subject: Diseño de viga" in result
    assert "Document Code: REC-001.pdf" in result
    assert "Work Front: Descarga" in result
    assert "SENT RESPONSE (Draft ID: draft_viga)" in result
    assert "Enviamos respuesta de diseño de viga aprobando planos" in result


@patch("app.tools._genai_client")
@patch("app.tools._client_received")
def test_search_communications_no_candidates(mock_client_received, mock_genai_client):
    # Mock embedding
    mock_embeddings_list = MagicMock()
    mock_embeddings_list.values = [0.1] * 768
    mock_genai_client.models.embed_content.return_value = MagicMock(embeddings=[mock_embeddings_list])
    
    # Mock empty find_nearest result
    mock_client_received.collection.return_value.find_nearest.return_value.get.return_value = []
    
    result = search_communications(query="something missing")
    assert result == "No se encontró información relevante para esta consulta."


@patch("app.tools._genai_client")
@patch("app.tools._client_received")
def test_search_communications_date_filtering(mock_client_received, mock_genai_client):
    # Mock embedding
    mock_embeddings_list = MagicMock()
    mock_embeddings_list.values = [0.1] * 768
    mock_genai_client.models.embed_content.return_value = MagicMock(embeddings=[mock_embeddings_list])
    
    # Mock documents with different dates and formats
    doc_match_slash = MagicMock()
    doc_match_slash.to_dict.return_value = {
        "texto": "Match slash date",
        "asunto": "Test subject",
        "fecha_documento": "15/05/2026"
    }
    doc_match_dash = MagicMock()
    doc_match_dash.to_dict.return_value = {
        "texto": "Match dash date",
        "asunto": "Test subject",
        "fecha_documento": "2026-05-20"
    }
    doc_mismatch_date = MagicMock()
    doc_mismatch_date.to_dict.return_value = {
        "texto": "Mismatch date",
        "asunto": "Test subject",
        "fecha_documento": "15/06/2026"
    }
    doc_invalid_date = MagicMock()
    doc_invalid_date.to_dict.return_value = {
        "texto": "Invalid date format",
        "asunto": "Test subject",
        "fecha_documento": "invalid-date-here"
    }
    doc_no_delimiter_date = MagicMock()
    doc_no_delimiter_date.to_dict.return_value = {
        "texto": "No delimiter date",
        "asunto": "Test subject",
        "fecha_documento": "2026"
    }
    doc_unknown_date = MagicMock()
    doc_unknown_date.to_dict.return_value = {
        "texto": "Unknown date",
        "asunto": "Test subject",
        "fecha_documento": "UNKNOWN"
    }
    doc_subject_mismatch = MagicMock()
    doc_subject_mismatch.to_dict.return_value = {
        "texto": "Subject mismatch",
        "asunto": "Other subject",
        "fecha_documento": "15/05/2026"
    }
    
    mock_client_received.collection.return_value.find_nearest.return_value.get.return_value = [
        doc_match_slash, doc_match_dash, doc_mismatch_date, doc_invalid_date, doc_no_delimiter_date, doc_unknown_date, doc_subject_mismatch
    ]
    
    # We also mock reranker to not perform actual ranking
    with patch("app.tools._rerank_chunks") as mock_rerank:
        mock_rerank.side_effect = lambda q, c: c
        
        # Test month and subject filtering
        result = search_communications(query="test", subject="Test subject", month=5)
        # Should match doc_match_slash and doc_match_dash (month 5 and subject matches)
        # Verify it mentions "Match slash date" and "Match dash date"
        assert "Match slash date" in result
        assert "Match dash date" in result
        assert "Mismatch date" not in result
        assert "Subject mismatch" not in result


@patch("app.tools._genai_client")
@patch("app.tools._client_received")
def test_search_communications_filter_all_out(mock_client_received, mock_genai_client):
    # Mock embedding
    mock_embeddings_list = MagicMock()
    mock_embeddings_list.values = [0.1] * 768
    mock_genai_client.models.embed_content.return_value = MagicMock(embeddings=[mock_embeddings_list])
    
    # Mock documents with dates that do not match the filter
    doc = MagicMock()
    doc.to_dict.return_value = {
        "texto": "Some doc",
        "asunto": "Test subject",
        "fecha_documento": "15/05/2026"
    }
    
    mock_client_received.collection.return_value.find_nearest.return_value.get.return_value = [doc]
    
    # Filter for month 12 (doc is month 5)
    result = search_communications(query="test", month=12)
    assert result == "No se encontraron comunicaciones para el periodo o filtros especificados."


@patch("app.tools._genai_client")
def test_search_communications_exception(mock_genai_client):
    # Mock embedding to throw exception
    mock_genai_client.models.embed_content.side_effect = Exception("Embedding connection failed")
    
    result = search_communications(query="cause exception")
    assert "Error searching the database: Embedding connection failed" in result


from datetime import datetime

def test_parse_date():
    from app.tools import _parse_date
    assert _parse_date("15/05/2026") == datetime(2026, 5, 15)
    assert _parse_date("2026-05-20") == datetime(2026, 5, 20)
    assert _parse_date("2026-05") == datetime(2026, 5, 1)
    assert _parse_date("UNKNOWN") is None
    assert _parse_date("invalid") is None
    assert _parse_date("") is None


@patch("app.tools._genai_client")
@patch("app.tools._client_received")
def test_search_communications_date_range_filtering(mock_client_received, mock_genai_client):
    # Mock embedding
    mock_embeddings_list = MagicMock()
    mock_embeddings_list.values = [0.1] * 768
    mock_genai_client.models.embed_content.return_value = MagicMock(embeddings=[mock_embeddings_list])
    
    # Mock documents with different dates
    doc1 = MagicMock()
    doc1.to_dict.return_value = {
        "texto": "Doc 1 (Jan 2026)",
        "asunto": "Test subject",
        "fecha_documento": "15/01/2026"
    }
    doc2 = MagicMock()
    doc2.to_dict.return_value = {
        "texto": "Doc 2 (Feb 2026)",
        "asunto": "Test subject",
        "fecha_documento": "15/02/2026"
    }
    doc3 = MagicMock()
    doc3.to_dict.return_value = {
        "texto": "Doc 3 (Mar 2026)",
        "asunto": "Test subject",
        "fecha_documento": "15/03/2026"
    }
    
    mock_client_received.collection.return_value.find_nearest.return_value.get.return_value = [
        doc1, doc2, doc3
    ]
    
    with patch("app.tools._rerank_chunks") as mock_rerank:
        mock_rerank.side_effect = lambda q, c: c
        
        # Test start_date only
        res = search_communications(query="test", start_date="2026-02-01")
        assert "Doc 1 (Jan 2026)" not in res
        assert "Doc 2 (Feb 2026)" in res
        assert "Doc 3 (Mar 2026)" in res
        
        # Test end_date only
        res = search_communications(query="test", end_date="2026-02-28")
        assert "Doc 1 (Jan 2026)" in res
        assert "Doc 2 (Feb 2026)" in res
        assert "Doc 3 (Mar 2026)" not in res
        
        # Test both start_date and end_date range
        res = search_communications(query="test", start_date="2026-02-01", end_date="2026-02-28")
        assert "Doc 1 (Jan 2026)" not in res
        assert "Doc 2 (Feb 2026)" in res
        assert "Doc 3 (Mar 2026)" not in res
