from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import document_facts
import main
import rag
from config import DOCUMENTS_DIR, INDEX_PATH, METADATA_PATH


client = TestClient(main.app)


def route(domain: str = "tenancy") -> main.domain_router.RouteDecision:
    return main.domain_router.RouteDecision(
        status="classified",
        domains=[domain],
        primary_domain=domain,
        confidence="high",
        issue_summary="Mock issue.",
        needs_clarification=False,
    )


def legal_chunk(domain: str = "tenancy") -> rag.RetrievedChunk:
    return rag.RetrievedChunk(
        chunk_id="legal_chunk_1",
        text="Section 45 concerns cutting off or withholding essential supply or service.",
        source="tenancy/delhi_rent_control_act_1958.pdf",
        document_title="The Delhi Rent Control Act, 1958",
        page=25,
        score=0.8,
        rerank_score=0.9,
        domain=domain,
        authority_level="primary",
        status="active",
        document_type="statute",
        section_number="45",
    )


def facts(document_type: str = "rent_agreement", amount: str = "Rs. 25,000", location: str = "Delhi") -> dict:
    return {
        "document_type": document_type,
        "document_summary": "User-confirmed facts from document.",
        "parties": [{"label": "tenant", "value": "Asha", "source_page": 1, "source_excerpt": "Tenant: Asha", "confidence": "high"}],
        "dates": [{"label": "agreement_date", "value": "12 July 2026", "source_page": 1, "source_excerpt": "Agreement date: 12 July 2026", "confidence": "high"}],
        "amounts": [{"label": "monthly_rent", "value": amount, "source_page": 1, "source_excerpt": f"Monthly rent: {amount}", "confidence": "high"}],
        "identifiers": [],
        "locations": [{"label": "premises", "value": location, "source_page": 1, "source_excerpt": f"Premises: {location}", "confidence": "high"}],
        "important_terms": [{"label": "notice_period", "value": "2 months", "source_page": 2, "source_excerpt": "two months notice", "confidence": "high"}],
        "events": [],
        "notices_or_demands": [],
        "other_facts": [],
        "uncertain_items": [],
        "warnings": [],
    }


def confirmed_context_id(fact_payload: dict | None = None) -> str:
    extraction_id = document_facts.store_pending_facts(fact_payload or facts())
    return document_facts.confirm_facts(extraction_id, fact_payload or facts()).confirmed_fact_context_id


def patch_supported_flow(monkeypatch, captured: dict | None = None, domain: str = "tenancy"):
    captured = captured if captured is not None else {}
    monkeypatch.setattr(main.domain_router, "route_issue", lambda text: captured.setdefault("route_text", text) and route(domain))
    monkeypatch.setattr(main.rag, "retrieve", lambda text: captured.setdefault("retrieval_text", text) and [legal_chunk(domain)])
    monkeypatch.setattr(main.claim_verifier, "verify_and_sanitize_response", lambda response, chunks: response)
    monkeypatch.setattr(main, "LLM_PROVIDER", "gemini")

    def fake_generate(**kwargs):
        captured["confirmed_case_facts"] = kwargs.get("confirmed_case_facts", [])
        return {
            "answer": {
                "issue_summary": "Mock grounded answer.",
                "what_this_may_involve": [],
                "possible_legal_position": ["The retrieved legal source may be relevant."],
                "suggested_next_steps": ["Keep the confirmed document facts available."],
                "evidence_to_preserve": [],
                "where_to_approach": [],
                "limitations": [],
                "possible_rights": ["The retrieved legal source may be relevant."],
                "next_steps": ["Keep the confirmed document facts available."],
            },
            "sources": [{"document": "The Delhi Rent Control Act, 1958", "page": 25, "section": "Section 45", "excerpt": "essential supply"}],
            "confidence": "medium",
            "insufficient_context": False,
            "disclaimer": "This is legal information, not professional legal advice.",
            "source_chunk_ids": ["legal_chunk_1"],
            "verification": {"claim_count": 1, "removed_claim_count": 0, "verified_claim_count": 1, "partially_supported_claim_count": 0},
        }

    monkeypatch.setattr(main.grounded_answer, "generate_grounded_answer", fake_generate)
    return captured


def test_confirmed_context_accepted(monkeypatch):
    context_id = confirmed_context_id()
    patch_supported_flow(monkeypatch)

    response = client.post("/api/ask", json={"question": "landlord cut electricity", "confirmed_fact_context_id": context_id})

    assert response.status_code == 200
    assert response.json()["confirmed_fact_context_id"] == context_id


def test_unconfirmed_extraction_rejected(monkeypatch):
    pending_id = document_facts.store_pending_facts(facts())
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _text: route())

    response = client.post("/api/ask", json={"question": "landlord cut electricity", "confirmed_fact_context_id": pending_id})

    assert response.status_code == 400


def test_corrected_facts_override_original_extraction(monkeypatch):
    corrected = facts(amount="Rs. 45,000")
    context_id = confirmed_context_id(corrected)
    captured = patch_supported_flow(monkeypatch)

    client.post("/api/ask", json={"question": "landlord cut electricity", "confirmed_fact_context_id": context_id})

    joined = " ".join(captured["confirmed_case_facts"])
    assert "Rs. 45,000" in joined
    assert "Rs. 50,000" not in joined


def test_confirmed_facts_contribute_to_fact_sufficiency():
    context = main.fact_sufficiency.new_case_context(
        "Can I get it back?",
        route("tenancy"),
        document_fact_lines=["security deposit: Rs. 50,000", "Document type confirmed by user: rent agreement"],
    )

    result = main.fact_sufficiency.assess_fact_sufficiency(context)

    assert result.status == "sufficient"


def test_router_can_use_document_context_without_blind_document_type(monkeypatch):
    context_id = confirmed_context_id()
    captured = patch_supported_flow(monkeypatch)

    client.post("/api/ask", json={"question": "Can they do this?", "confirmed_fact_context_id": context_id})

    assert "CONFIRMED DOCUMENT FACTS" in captured["route_text"]
    assert "rent agreement" in captured["route_text"]


def test_document_facts_do_not_enter_faiss(monkeypatch):
    context_id = confirmed_context_id()
    tracked_paths = [DOCUMENTS_DIR / "corpus_manifest.json", INDEX_PATH, METADATA_PATH]
    before = {path: path.stat().st_mtime_ns for path in tracked_paths if path.exists()}
    patch_supported_flow(monkeypatch)

    client.post("/api/ask", json={"question": "landlord cut electricity", "confirmed_fact_context_id": context_id})

    after = {path: path.stat().st_mtime_ns for path in tracked_paths if path.exists()}
    assert after == before


def test_document_facts_never_appear_in_legal_sources(monkeypatch):
    context_id = confirmed_context_id()
    patch_supported_flow(monkeypatch)

    response = client.post("/api/ask", json={"question": "landlord cut electricity", "confirmed_fact_context_id": context_id})
    data = response.json()

    assert data["sources"][0]["document"] == "The Delhi Rent Control Act, 1958"
    assert data["document_evidence_used"]
    assert all(item.get("source") == "user_document" for item in data["document_evidence_used"])


def test_legal_claims_still_verified_against_legal_chunks_only(monkeypatch):
    context_id = confirmed_context_id()
    captured = {}
    patch_supported_flow(monkeypatch)

    def verifier(response, chunks):
        captured["chunk_titles"] = [chunk.document_title for chunk in chunks]
        return response

    monkeypatch.setattr(main.claim_verifier, "verify_and_sanitize_response", verifier)
    client.post("/api/ask", json={"question": "landlord cut electricity", "confirmed_fact_context_id": context_id})

    assert captured["chunk_titles"] == ["The Delhi Rent Control Act, 1958"]


def test_corpus_gap_still_blocks_unsupported_jurisdiction(monkeypatch):
    context_id = confirmed_context_id(facts(location="Mumbai"))
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _text: route("tenancy"))
    monkeypatch.setattr(main.rag, "retrieve", lambda _text: [legal_chunk("tenancy")])

    response = client.post("/api/ask", json={"question": "landlord cut electricity", "confirmed_fact_context_id": context_id})
    data = response.json()

    assert data["corpus_status"] == "insufficient"
    assert "jurisdiction_not_covered" in data["corpus_gap"]["reason_codes"]


def test_conflicting_typed_and_document_fact_triggers_clarification(monkeypatch):
    context_id = confirmed_context_id(facts(amount="Rs. 25,000"))

    response = client.post("/api/ask", json={"question": "rent is Rs. 20,000, can landlord do this?", "confirmed_fact_context_id": context_id})
    data = response.json()

    assert data["clarification"]["type"] == "document_fact_conflict"
    assert "Which amount should I use" in data["clarification"]["question"]


def test_no_document_ask_flow_unchanged(monkeypatch):
    captured = patch_supported_flow(monkeypatch)

    response = client.post("/api/ask", json={"question": "landlord cut electricity"})
    data = response.json()

    assert response.status_code == 200
    assert "document_evidence_used" not in data
    assert "CONFIRMED DOCUMENT FACTS" not in captured["route_text"]


def test_document_context_can_be_detached():
    context_id = confirmed_context_id()

    assert document_facts.detach_confirmed_context(context_id) is True
    assert document_facts.get_confirmed_context(context_id) is None
