from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
import rag


client = TestClient(main.app)


def test_health_endpoint_shape():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "knowledge_base_loaded" in data


def test_empty_question_rejected():
    response = client.post("/api/ask", json={"question": "   "})
    assert response.status_code == 400
    assert "Question is required" in response.json()["detail"]


def test_missing_vector_store_handling(monkeypatch):
    def missing_answer(_question: str):
        raise main.VectorStoreMissingError("Vector store is missing. Run `python ingest.py` inside backend first.")

    monkeypatch.setattr(main.rag, "answer", missing_answer)
    response = client.post("/api/ask", json={"question": "The seller refused a refund."})
    assert response.status_code == 503
    assert "Vector store is missing" in response.json()["detail"]


def test_configuration_error_returns_json(monkeypatch):
    def configuration_error(_question: str):
        raise main.ConfigurationError("Gemini API key is not configured.")

    monkeypatch.setattr(main.rag, "answer", configuration_error)
    response = client.post("/api/ask", json={"question": "The seller refused a refund."})
    assert response.status_code == 503
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Gemini API key is not configured."}


def test_response_json_shape(monkeypatch):
    def fake_answer(_question: str):
        return {
            "answer": {
                "issue_summary": "Mock summary",
                "possible_rights": ["Mock right"],
                "next_steps": ["Mock step"],
            },
            "sources": [{"document": "Consumer Protection Act, 2019", "page": 1, "section": None, "excerpt": "Mock excerpt"}],
            "confidence": "medium",
            "insufficient_context": False,
            "disclaimer": "This is legal information, not professional legal advice.",
        }

    monkeypatch.setattr(main.rag, "answer", fake_answer)
    response = client.post("/api/ask", json={"question": "Can I ask for refund for defective goods?"})
    assert response.status_code == 200
    data = response.json()
    assert set(data) >= {"answer", "sources", "confidence", "insufficient_context", "disclaimer"}
    assert set(data["answer"]) >= {"issue_summary", "possible_rights", "next_steps"}


def test_off_topic_question_uses_safe_fallback():
    response = client.post("/api/ask", json={"question": "Write Python code for bubble sort."})
    assert response.status_code == 200
    data = response.json()
    assert data["insufficient_context"] is True
    assert data["sources"] == []
    assert "consumer-law questions only" in data["answer"]["issue_summary"]


def test_response_normalization_removes_markdown_numbering_disclaimer_and_svg():
    parsed = {
        "answer": {
            "issue_summary": "**Possible consumer dispute** svg",
            "possible_rights": [
                "**May request repair**",
                "This is legal information, not professional legal advice.",
                "**May request repair**",
                "svg",
            ],
            "next_steps": [
                "1. **Keep the invoice**",
                "Step 2: Send a written request",
                "This is legal information, not professional legal advice.",
            ],
        },
        "confidence": "medium",
        "insufficient_context": False,
    }
    chunk = rag.RetrievedChunk(
        text="defect means any fault imperfection or shortcoming in quality",
        source="consumer_protection_act_2019.pdf",
        document_title="Consumer Protection Act, 2019",
        page=6,
        score=0.52,
    )

    normalized = rag.normalize_rag_response(parsed, [chunk])

    assert normalized["answer"]["issue_summary"] == "Possible consumer dispute"
    assert normalized["answer"]["possible_rights"] == ["May request repair"]
    assert normalized["answer"]["next_steps"] == ["Keep the invoice", "Send a written request"]
    assert normalized["disclaimer"] == "This is legal information, not professional legal advice."


def test_reranking_prefers_substantive_act_chunk_over_duplicate_rule_chunk():
    act_chunk = rag.RetrievedChunk(
        text="Section 39 Findings of District Commission replace the goods return to the complainant the price defect",
        source="consumer_protection_act_2019.pdf",
        document_title="Consumer Protection Act, 2019",
        page=22,
        score=0.48,
        section_number="39",
        section_title="Findings of District Commission",
    )
    rule_chunk = rag.RetrievedChunk(
        text="Rule 39 replace the goods return to the complainant the price defect",
        source="consumer_protection_general_rules_2020.pdf",
        document_title="Consumer Protection (General) Rules, 2020",
        page=22,
        score=0.5,
        rule_number="39",
    )

    selected = rag.select_relevant_chunks(
        [rule_chunk, act_chunk],
        question="The seller is refusing to refund a defective product.",
        top_k=2,
    )

    assert selected[0].document_title == "Consumer Protection Act, 2019"
    assert len(selected) == 1


def test_real_retrieval_returns_substantive_act_sources_for_defective_product():
    if not (Path(__file__).resolve().parents[1] / "vectorstore" / "metadata.json").exists():
        pytest.skip("Vector store has not been built.")

    rag.rag.load()
    chunks = rag.rag.retrieve("The seller is refusing to refund a defective product.")
    sections = {chunk.section_number for chunk in chunks if chunk.document_title == "Consumer Protection Act, 2019"}

    assert {"39", "83"} & sections
    assert any(chunk.document_title == "Consumer Protection Act, 2019" for chunk in chunks)
    assert len({(chunk.document_title, chunk.section_number, chunk.rule_number) for chunk in chunks}) == len(chunks)
