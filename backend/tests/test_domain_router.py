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
    monkeypatch.setattr(domain_router.genai, "Client", lambda api_key: FakeClient())

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
