from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import domain_router
import fact_sufficiency
import main


client = TestClient(main.app)


def route(domain: str) -> domain_router.RouteDecision:
    return domain_router.RouteDecision(
        status="classified",
        domains=[domain],
        primary_domain=domain,
        confidence="high",
        issue_summary=f"Possible {domain} issue.",
        needs_clarification=False,
    )


def test_clearly_sufficient_consumer_query_proceeds():
    context, result = fact_sufficiency.start_fact_check(
        "seller refusing refund for defective product",
        route("consumer"),
    )

    assert result.status == "sufficient"
    assert result.needs_fact_clarification is False
    assert "seller refusing refund" in fact_sufficiency.retrieval_query(context, result)


def test_vague_consumer_query_asks_one_question(monkeypatch):
    monkeypatch.setattr(fact_sufficiency, "GEMINI_API_KEY", "")
    _context, result = fact_sufficiency.start_fact_check("consumer complaint karni hai", route("consumer"))

    assert result.status == "insufficient"
    assert result.needs_fact_clarification is True
    assert result.question == "What happened with the product or service?"


def test_clearly_sufficient_cyber_query_proceeds():
    _context, result = fact_sufficiency.start_fact_check("my Instagram account was hacked", route("cyber"))

    assert result.status == "sufficient"


def test_vague_cyber_query_asks_one_question(monkeypatch):
    monkeypatch.setattr(fact_sufficiency, "GEMINI_API_KEY", "")
    _context, result = fact_sufficiency.start_fact_check("mera cyber issue hai", route("cyber"))

    assert result.status == "insufficient"
    assert "What happened" in result.question


def test_tenancy_query_does_not_ask_state(monkeypatch):
    monkeypatch.setattr(fact_sufficiency, "GEMINI_API_KEY", "")
    _context, result = fact_sufficiency.start_fact_check("landlord dispute hai", route("tenancy"))

    assert result.status == "insufficient"
    assert "state" not in result.question.lower()
    assert "city" not in result.question.lower()


def test_clear_tenancy_dispute_proceeds():
    _context, result = fact_sufficiency.start_fact_check("landlord security deposit return nahi kar raha", route("tenancy"))

    assert result.status == "sufficient"


def test_clear_rti_and_legal_aid_queries_proceed():
    _context, rti = fact_sufficiency.start_fact_check("RTI application ka reply nahi mila", route("constitutional_public_authority"))
    _context, legal_aid = fact_sufficiency.start_fact_check("I want free legal aid", route("constitutional_public_authority"))

    assert rti.status == "sufficient"
    assert legal_aid.status == "sufficient"


def test_user_reply_updates_case_context(monkeypatch):
    monkeypatch.setattr(fact_sufficiency, "GEMINI_API_KEY", "")
    context, _result = fact_sufficiency.start_fact_check("consumer complaint karni hai", route("consumer"))
    progress = fact_sufficiency.record_fact_answer(context, "phone defective tha")

    assert progress.progress == "meaningful"
    assert "phone defective" in " ".join(context.facts)


def test_fact_sufficiency_recheck_works(monkeypatch):
    monkeypatch.setattr(fact_sufficiency, "GEMINI_API_KEY", "")
    context, _result = fact_sufficiency.start_fact_check("consumer complaint karni hai", route("consumer"))
    _progress, result = fact_sufficiency.continue_fact_check(context, "phone defective tha aur seller refund nahi de raha")

    assert result.status == "sufficient"


def test_repeated_vague_replies_do_not_loop_forever(monkeypatch):
    monkeypatch.setattr(fact_sufficiency, "GEMINI_API_KEY", "")
    context, _result = fact_sufficiency.start_fact_check("consumer issue hai", route("consumer"))
    fact_sufficiency.continue_fact_check(context, "issue hai bas")
    progress, result = fact_sufficiency.continue_fact_check(context, "same issue")

    assert progress.safe_exit is True
    assert result.status == "insufficient"


def test_sensitive_credentials_are_never_requested():
    for question in ("What is your OTP?", "Please share your password", "What is your Aadhaar number?"):
        assert fact_sufficiency.asks_for_sensitive_info(question)
        with pytest.raises(ValueError):
            fact_sufficiency.validate_fact_result(
                {
                    "status": "insufficient",
                    "missing_facts": ["secret"],
                    "needs_fact_clarification": True,
                    "question": question,
                    "reason": "unsafe",
                    "normalized_case_summary": "",
                }
            )


def test_classified_api_runs_fact_sufficiency_before_retrieval(monkeypatch):
    called = {}

    monkeypatch.setattr(main.domain_router, "route_issue", lambda _question: route("consumer"))

    def fake_grounded(original_message, context, fact_result):
        called["question"] = original_message
        called["domains"] = context.domains
        return {
            "answer": {"issue_summary": "Mock", "possible_rights": [], "next_steps": []},
            "sources": [],
            "confidence": "medium",
            "insufficient_context": False,
            "disclaimer": "This is legal information, not professional legal advice.",
        }

    monkeypatch.setattr(main, "answer_grounded_from_context", fake_grounded)

    response = client.post("/api/ask", json={"question": "seller refusing refund for defective product"})

    assert response.status_code == 200
    assert called["domains"] == ["consumer"]


def test_vague_classified_api_returns_fact_question_without_retrieval(monkeypatch):
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _question: route("consumer"))
    monkeypatch.setattr(main.fact_sufficiency, "GEMINI_API_KEY", "")
    monkeypatch.setattr(main.rag, "answer", lambda *_args, **_kwargs: pytest.fail("retrieval should not run"))

    response = client.post("/api/ask", json={"question": "consumer complaint karni hai"})

    assert response.status_code == 200
    data = response.json()
    assert data["clarification"]["type"] == "fact_sufficiency"
    assert data["clarification"]["needed"] is True


def test_fact_reply_can_continue_to_retrieval(monkeypatch):
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _question: route("consumer"))
    monkeypatch.setattr(main.fact_sufficiency, "GEMINI_API_KEY", "")
    monkeypatch.setattr(
        main,
        "answer_grounded_from_context",
        lambda original_message, context, fact_result: {
            "answer": {"issue_summary": fact_sufficiency.retrieval_query(context, fact_result), "possible_rights": [], "next_steps": []},
            "sources": [],
            "confidence": "medium",
            "insufficient_context": False,
            "disclaimer": "This is legal information, not professional legal advice.",
        },
    )

    first = client.post("/api/ask", json={"question": "consumer complaint karni hai"}).json()
    second = client.post(
        "/api/ask",
        json={
            "question": "phone defective tha aur seller refund nahi de raha",
            "clarification_state_id": first["clarification"]["state_id"],
        },
    ).json()

    assert "phone defective" in second["answer"]["issue_summary"].lower()
    assert "clarification" not in second
