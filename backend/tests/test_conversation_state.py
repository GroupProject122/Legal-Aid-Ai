from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import conversation_state
import domain_router
import main
import rag


client = TestClient(main.app)


def route(domain: str = "tenancy") -> domain_router.RouteDecision:
    return domain_router.RouteDecision(
        status="classified",
        domains=[domain],
        primary_domain=domain,
        confidence="high",
        issue_summary=f"Mock {domain} issue.",
        needs_clarification=False,
    )


def legal_chunk(domain: str = "tenancy") -> rag.RetrievedChunk:
    return rag.RetrievedChunk(
        chunk_id="legal_chunk_1",
        text="Section 45 concerns cutting off or withholding essential supply or service.",
        source=f"{domain}/source.pdf",
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


def patch_answer_flow(monkeypatch, captured: dict | None = None, domain: str = "tenancy"):
    captured = captured if captured is not None else {}
    monkeypatch.setattr(main.conversation_state, "GEMINI_API_KEY", "")

    def fake_route(text):
        captured["route_text"] = text
        return route(domain)

    def fake_retrieve(text):
        captured["retrieval_text"] = text
        return [legal_chunk(domain)]

    monkeypatch.setattr(main.domain_router, "route_issue", fake_route)
    monkeypatch.setattr(main.rag, "retrieve", fake_retrieve)
    monkeypatch.setattr(main.claim_verifier, "verify_and_sanitize_response", lambda response, chunks: response)
    monkeypatch.setattr(main, "LLM_PROVIDER", "gemini")

    def fake_generate(**kwargs):
        captured["original_message"] = kwargs.get("original_message")
        captured["normalized_case_summary"] = kwargs.get("normalized_case_summary")
        return {
            "answer": {
                "issue_summary": "Mock grounded answer.",
                "what_this_may_involve": [],
                "possible_legal_position": ["The retrieved source may be relevant."],
                "suggested_next_steps": ["Keep useful records."],
                "evidence_to_preserve": [],
                "where_to_approach": [],
                "limitations": [],
                "possible_rights": ["The retrieved source may be relevant."],
                "next_steps": ["Keep useful records."],
            },
            "sources": [{"document": "The Delhi Rent Control Act, 1958", "page": 25, "section": "Section 45", "excerpt": "essential supply"}],
            "confidence": "medium",
            "insufficient_context": False,
            "disclaimer": "This is legal information, not professional legal advice.",
            "source_chunk_ids": ["legal_chunk_1"],
        }

    monkeypatch.setattr(main.grounded_answer, "generate_grounded_answer", fake_generate)
    return captured


def test_conversation_state_creation():
    state = conversation_state.create_state(
        domains=["tenancy"],
        primary_domain="tenancy",
        case_summary="Delhi landlord disconnected electricity.",
        known_facts=["Delhi rented premises", "electricity disconnected"],
    )

    assert conversation_state.get_state(state.conversation_state_id) is state
    assert state.domains == ["tenancy"]
    assert "electricity" in state.case_summary


def test_follow_up_pipeline_uses_previous_case_context(monkeypatch):
    captured = patch_answer_flow(monkeypatch)
    first = client.post("/api/ask", json={"question": "My landlord in Delhi disconnected electricity. What can I do?"}).json()
    state_id = first["conversation_state_id"]

    client.post(
        "/api/ask",
        json={"question": "What if he says I have not paid rent for two months?", "conversation_state_id": state_id},
    )

    assert "landlord" in captured["route_text"].lower()
    assert "electricity" in captured["route_text"].lower()
    assert "rent for two months" in captured["route_text"].lower()


def test_additional_fact_is_acknowledged_without_retrieval(monkeypatch):
    state = conversation_state.create_state(["consumer"], "consumer", "Seller refused refund.", ["Seller refused refund."])
    called = {"retrieve": False}
    monkeypatch.setattr(main.rag, "retrieve", lambda _text: called.update(retrieve=True) or [])

    response = client.post("/api/ask", json={"question": "I paid by UPI.", "conversation_state_id": state.conversation_state_id})
    data = response.json()

    assert response.status_code == 200
    assert called["retrieve"] is False
    assert data["conversation_state_id"] == state.conversation_state_id
    assert "UPI" in " ".join(conversation_state.get_state(state.conversation_state_id).known_facts)


def test_correction_replaces_prior_amount():
    state = conversation_state.create_state(["consumer"], "consumer", "Payment dispute.", ["I paid Rs. 50,000."])
    classification = conversation_state.classify_turn("Sorry, it was Rs. 45,000.", state)

    conversation_state.apply_turn_to_state(state, "Sorry, it was Rs. 45,000.", classification)

    facts = " ".join(state.known_facts)
    assert "45,000" in facts
    assert "50,000" not in facts


def test_small_talk_bypasses_legal_pipeline(monkeypatch):
    state = conversation_state.create_state(["tenancy"], "tenancy", "Landlord electricity dispute.", ["landlord cut electricity"])
    called = {"route": False, "retrieve": False}
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _text: called.update(route=True) or route())
    monkeypatch.setattr(main.rag, "retrieve", lambda _text: called.update(retrieve=True) or [])

    response = client.post("/api/ask", json={"question": "thanks", "conversation_state_id": state.conversation_state_id})
    data = response.json()

    assert response.status_code == 200
    assert called == {"route": False, "retrieve": False}
    assert data["conversation_state_id"] == state.conversation_state_id


def test_new_unrelated_issue_resets_active_case(monkeypatch):
    state = conversation_state.create_state(["tenancy"], "tenancy", "Landlord electricity dispute.", ["landlord cut electricity"])
    captured = patch_answer_flow(monkeypatch, domain="consumer")

    response = client.post(
        "/api/ask",
        json={"question": "My online order was never delivered. What can I do?", "conversation_state_id": state.conversation_state_id},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["conversation_state_id"] != state.conversation_state_id
    assert conversation_state.get_state(state.conversation_state_id) is None
    assert "electricity" not in captured["route_text"].lower()


def test_acknowledgement_response_has_no_legal_sources():
    state = conversation_state.create_state(["tenancy"], "tenancy", "Landlord electricity dispute.")
    response = conversation_state.acknowledgement_response(state)

    assert response["sources"] == []
    assert response["conversation_state_id"] == state.conversation_state_id


def test_state_can_be_cleared_on_new_question():
    state = conversation_state.create_state(["cyber"], "cyber", "Account hacked.")

    conversation_state.clear_state(state.conversation_state_id)

    assert conversation_state.get_state(state.conversation_state_id) is None


def test_pipeline_message_does_not_require_full_chat_history():
    state = conversation_state.create_state(["tenancy"], "tenancy", "Delhi electricity dispute.", ["landlord cut electricity"])
    message = conversation_state.pipeline_message("What if rent is unpaid?", state)

    assert "Active case summary" in message
    assert "Known case facts" in message
    assert "assistant" not in message.lower()


def test_existing_ask_without_state_still_works(monkeypatch):
    patch_answer_flow(monkeypatch)

    response = client.post("/api/ask", json={"question": "landlord cut electricity"})

    assert response.status_code == 200
    assert response.json()["conversation_state_id"]
