from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import domain_router
import main
import rag


client = TestClient(main.app)


def test_valid_classified_schema():
    decision = domain_router.validate_route_decision(
        {
            "status": "classified",
            "domains": ["cyber"],
            "primary_domain": "cyber",
            "confidence": "high",
            "issue_summary": "Possible online payment fraud.",
            "needs_clarification": False,
        }
    )

    assert decision.status == "classified"
    assert decision.domains == ["cyber"]
    assert decision.primary_domain == "cyber"


def test_valid_multi_domain_schema():
    decision = domain_router.validate_route_decision(
        {
            "status": "classified",
            "domains": ["consumer", "cyber", "consumer"],
            "primary_domain": "consumer",
            "confidence": "medium",
            "issue_summary": "Possible seller dispute with online fraud element.",
            "needs_clarification": False,
        }
    )

    assert decision.domains == ["consumer", "cyber"]
    assert decision.primary_domain == "consumer"


def test_unclear_schema_normalizes_empty_domains():
    decision = domain_router.validate_route_decision(
        {
            "status": "unclear",
            "domains": ["consumer"],
            "primary_domain": "consumer",
            "confidence": "medium",
            "issue_summary": "",
            "needs_clarification": False,
        }
    )

    assert decision.status == "unclear"
    assert decision.domains == []
    assert decision.primary_domain is None
    assert decision.confidence == "low"
    assert decision.needs_clarification is True


def test_unsupported_schema_normalizes_domains():
    decision = domain_router.validate_route_decision(
        {
            "status": "unsupported",
            "domains": ["tenancy"],
            "primary_domain": "tenancy",
            "confidence": "high",
            "issue_summary": "Possible divorce issue.",
            "needs_clarification": True,
        }
    )

    assert decision.status == "unsupported"
    assert decision.domains == []
    assert decision.primary_domain is None
    assert decision.needs_clarification is False


def test_out_of_scope_schema_normalizes_domains():
    decision = domain_router.validate_route_decision(
        {
            "status": "out_of_scope",
            "domains": ["cyber"],
            "primary_domain": "cyber",
            "confidence": "high",
            "issue_summary": "Weather question.",
            "needs_clarification": True,
        }
    )

    assert decision.status == "out_of_scope"
    assert decision.domains == []
    assert decision.primary_domain is None
    assert decision.needs_clarification is False


def test_invalid_gemini_output_safely_becomes_unclear(monkeypatch):
    class FakeModels:
        def generate_content(self, **_kwargs):
            class Response:
                text = "{not valid json"

            return Response()

    class FakeClient:
        models = FakeModels()

    monkeypatch.setattr(domain_router, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(domain_router.genai, "Client", lambda api_key, **_kw: FakeClient())

    decision = domain_router.route_issue("seller refund nahi de raha")

    assert decision.status == "unclear"
    assert decision.needs_clarification is True


def test_invalid_domain_is_rejected():
    with pytest.raises(ValueError):
        domain_router.validate_route_decision(
            {
                "status": "classified",
                "domains": ["family_law"],
                "primary_domain": "family_law",
                "confidence": "high",
                "issue_summary": "Possible divorce issue.",
                "needs_clarification": False,
            }
        )


def test_primary_domain_must_belong_to_domains():
    with pytest.raises(ValueError):
        domain_router.validate_route_decision(
            {
                "status": "classified",
                "domains": ["consumer"],
                "primary_domain": "cyber",
                "confidence": "high",
                "issue_summary": "Possible online seller dispute.",
                "needs_clarification": False,
            }
        )


def test_router_schema_does_not_include_legal_answer_fields():
    fields = set(domain_router.ROUTER_SCHEMA["properties"])

    assert "answer" not in fields
    assert "sources" not in fields
    assert "possible_rights" not in fields
    assert "next_steps" not in fields


def test_unsupported_does_not_trigger_normal_retrieval(monkeypatch):
    def unsupported(_question: str):
        return domain_router.RouteDecision(
            status="unsupported",
            domains=[],
            primary_domain=None,
            confidence="high",
            issue_summary="Possible divorce issue.",
            needs_clarification=False,
        )

    def fail_answer(*_args, **_kwargs):
        raise AssertionError("retrieval should not run")

    monkeypatch.setattr(main.domain_router, "route_issue", unsupported)
    monkeypatch.setattr(main.rag, "answer", fail_answer)

    response = client.post("/api/ask", json={"question": "mujhe divorce chahiye"})

    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert response.json()["insufficient_context"] is True


def test_out_of_scope_does_not_trigger_normal_retrieval(monkeypatch):
    def out_of_scope(_question: str):
        return domain_router.RouteDecision(
            status="out_of_scope",
            domains=[],
            primary_domain=None,
            confidence="high",
            issue_summary="Weather question.",
            needs_clarification=False,
        )

    def fail_answer(*_args, **_kwargs):
        raise AssertionError("retrieval should not run")

    monkeypatch.setattr(main.domain_router, "route_issue", out_of_scope)
    monkeypatch.setattr(main.rag, "answer", fail_answer)

    response = client.post("/api/ask", json={"question": "weather tomorrow"})

    assert response.status_code == 200
    assert response.json()["sources"] == []
    assert response.json()["insufficient_context"] is True


def test_classified_query_continues_to_retrieval(monkeypatch):
    called = {}

    def classified(_question: str):
        return domain_router.RouteDecision(
            status="classified",
            domains=["tenancy"],
            primary_domain="tenancy",
            confidence="high",
            issue_summary="Possible tenancy issue.",
            needs_clarification=False,
        )

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

    monkeypatch.setattr(main.domain_router, "route_issue", classified)
    monkeypatch.setattr(main, "answer_grounded_from_context", fake_grounded)

    response = client.post("/api/ask", json={"question": "landlord cut electricity"})

    assert response.status_code == 200
    assert called == {"question": "landlord cut electricity", "domains": ["tenancy"]}


def test_existing_part_7_retrieval_signal_remains_available():
    signals = rag.detect_domain_signals("cyber fraud online payment")

    assert "cyber" in signals["primary_domains"]


def test_domain_cues_match_whole_words_only():
    # Regression: "rent" matched inside "Current", and every follow-up is routed as
    # "Current user question: ...", so tenancy was added to every follow-up.
    assert domain_router.domains_from_supported_cues("current user question: my whatsapp was hacked") == {"cyber"}
    assert domain_router.domains_from_supported_cues("my parent has a different problem") == set()
    assert domain_router.domains_from_supported_cues("i rented a flat and the landlord is hacking my wifi") == {"tenancy", "cyber"}


def test_router_timeout_falls_back_safely(monkeypatch):
    # Regression: Gemini calls had no time limit, so a stalled connection left the question
    # unanswered forever. A timeout now raises an httpx error that routing handles safely.
    import httpx

    def timing_out_client(api_key=None, **_kw):
        raise httpx.ReadTimeout("timed out")

    monkeypatch.setattr(domain_router, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(domain_router.genai, "Client", timing_out_client)

    decision = domain_router.route_issue("my landlord cut the electricity")

    assert decision.routing_error is True
    assert decision.status == "unclear"


def test_every_gemini_client_has_a_timeout():
    from gemini_http import gemini_http_options

    assert gemini_http_options().timeout and gemini_http_options().timeout > 0
    backend = Path(__file__).resolve().parents[1]
    for path in backend.glob("*.py"):
        if path.name.startswith("evaluate_"):
            continue
        text = path.read_text(encoding="utf-8")
        assert "genai.Client(api_key=GEMINI_API_KEY)" not in text, f"{path.name} creates a Gemini client with no timeout"


def test_rbi_ombudsman_questions_route_to_consumer():
    # Regression: "RBI Ombudsman" reads like a government body, so the model routed these to
    # constitutional_public_authority and retrieval searched the wrong laws.
    misrouted = domain_router.RouteDecision(
        status="classified", domains=["constitutional_public_authority"], primary_domain="constitutional_public_authority",
        confidence="high", issue_summary="RBI Ombudsman complaint", needs_clarification=False,
    )
    decision = domain_router.route_financial_ombudsman("is there any fee for filing a complaint with the rbi ombudsman?", misrouted)
    assert decision.domains == ["consumer"]
    assert decision.primary_domain == "consumer"


def test_rbi_ombudsman_with_real_public_authority_cue_keeps_both():
    decision = domain_router.RouteDecision(
        status="classified", domains=["constitutional_public_authority"], primary_domain="constitutional_public_authority",
        confidence="high", issue_summary="", needs_clarification=False,
    )
    routed = domain_router.route_financial_ombudsman("can i file an rti about how the banking ombudsman handled my case", decision)
    assert set(routed.domains) == {"consumer", "constitutional_public_authority"}


def test_unclear_rbi_ombudsman_question_becomes_consumer():
    unclear = domain_router.RouteDecision(
        status="unclear", domains=[], primary_domain=None, confidence="low", issue_summary=None, needs_clarification=True,
    )
    routed = domain_router.route_financial_ombudsman("what is the rb-ios scheme", unclear)
    assert routed.status == "classified" and routed.domains == ["consumer"]


def test_non_ombudsman_questions_are_untouched():
    decision = domain_router.RouteDecision(
        status="classified", domains=["constitutional_public_authority"], primary_domain="constitutional_public_authority",
        confidence="high", issue_summary="", needs_clarification=False,
    )
    assert domain_router.route_financial_ombudsman("my rti application got no reply", decision) is decision
