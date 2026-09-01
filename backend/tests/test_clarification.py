from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import clarification
import domain_router
import main
import rag


client = TestClient(main.app)


def route(status: str, domains: list[str] | None = None) -> domain_router.RouteDecision:
    return domain_router.RouteDecision(
        status=status,
        domains=domains or [],
        primary_domain=domains[0] if domains else None,
        confidence="high" if status != "unclear" else "low",
        issue_summary="Mock route." if status != "unclear" else None,
        needs_clarification=status == "unclear",
    )


def test_unclear_route_generates_one_clarification_question(monkeypatch):
    monkeypatch.setattr(clarification, "GEMINI_API_KEY", "")
    state, question = clarification.start_clarification("mere paise fas gaye", route("unclear"))

    assert state.state_id
    assert len(state.clarification_history) == 1
    assert question.question


def test_classified_route_generates_no_clarification(monkeypatch):
    called = {"clarification": False}

    def classified(_question: str):
        return route("classified", ["consumer"])

    def fail_start(*_args, **_kwargs):
        called["clarification"] = True
        raise AssertionError("clarification should not start")

    monkeypatch.setattr(main.domain_router, "route_issue", classified)
    monkeypatch.setattr(main.clarification, "start_clarification", fail_start)
    monkeypatch.setattr(
        main,
        "answer_grounded_from_context",
        lambda *_args, **_kwargs: {
            "answer": {"issue_summary": "Mock", "possible_rights": [], "next_steps": []},
            "sources": [],
            "confidence": "medium",
            "insufficient_context": False,
            "disclaimer": "This is legal information, not professional legal advice.",
        },
    )

    response = client.post("/api/ask", json={"question": "seller refund nahi de raha"})

    assert response.status_code == 200
    assert called["clarification"] is False


def test_useful_answer_updates_accumulated_context(monkeypatch):
    monkeypatch.setattr(clarification, "GEMINI_API_KEY", "")
    state, _question = clarification.start_clarification("mere paise fas gaye", route("unclear"))
    progress = clarification.record_answer(state, "Instagram seller ko payment ki thi")

    assert progress.progress == "meaningful"
    assert "Instagram seller" in state.accumulated_context


def test_rerouting_after_answer_works_and_stops_when_classified(monkeypatch):
    calls = []

    def route_issue(message: str):
        calls.append(message)
        if len(calls) == 1:
            return route("unclear")
        return route("classified", ["consumer"])

    monkeypatch.setattr(main.domain_router, "route_issue", route_issue)
    monkeypatch.setattr(main.clarification, "GEMINI_API_KEY", "")
    monkeypatch.setattr(
        main,
        "answer_grounded_from_context",
        lambda original_message, context, fact_result: {
            "answer": {"issue_summary": " ".join(context.facts), "possible_rights": [], "next_steps": []},
            "sources": [],
            "confidence": "medium",
            "insufficient_context": False,
            "disclaimer": "This is legal information, not professional legal advice.",
        },
    )

    first = client.post("/api/ask", json={"question": "mere paise fas gaye"}).json()
    second = client.post(
        "/api/ask",
        json={
            "question": "Instagram seller ko payment ki thi",
            "clarification_state_id": first["clarification"]["state_id"],
        },
    )

    assert second.status_code == 200
    assert "clarification" not in second.json()
    assert "Instagram seller" in second.json()["answer"]["issue_summary"]


def test_clarification_stops_when_unsupported(monkeypatch):
    monkeypatch.setattr(main.clarification, "GEMINI_API_KEY", "")
    responses = [route("unclear"), route("unsupported")]
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _message: responses.pop(0))
    monkeypatch.setattr(main.rag, "answer", lambda *_args, **_kwargs: pytest.fail("retrieval should not run"))

    first = client.post("/api/ask", json={"question": "mujhe notice mila hai"}).json()
    second = client.post(
        "/api/ask",
        json={"question": "income tax notice hai", "clarification_state_id": first["clarification"]["state_id"]},
    )

    assert second.status_code == 200
    assert second.json()["sources"] == []
    assert second.json()["insufficient_context"] is True


def test_clarification_stops_when_out_of_scope(monkeypatch):
    monkeypatch.setattr(main.clarification, "GEMINI_API_KEY", "")
    responses = [route("unclear"), route("out_of_scope")]
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _message: responses.pop(0))
    monkeypatch.setattr(main.rag, "answer", lambda *_args, **_kwargs: pytest.fail("retrieval should not run"))

    first = client.post("/api/ask", json={"question": "help karo"}).json()
    second = client.post(
        "/api/ask",
        json={"question": "weather tomorrow", "clarification_state_id": first["clarification"]["state_id"]},
    )

    assert second.status_code == 200
    assert second.json()["sources"] == []
    assert second.json()["insufficient_context"] is True


def test_same_question_is_not_repeated(monkeypatch):
    monkeypatch.setattr(clarification, "GEMINI_API_KEY", "")
    state, question = clarification.start_clarification("matter hai", route("unclear"))
    next_question = clarification.generate_next_question(state, route("unclear"))

    assert next_question.question != question.question or next_question.question == clarification.BROAD_FALLBACK_QUESTION


def test_non_informative_reply_detected(monkeypatch):
    monkeypatch.setattr(clarification, "GEMINI_API_KEY", "")
    state, _question = clarification.start_clarification("mera matter hai", route("unclear"))
    progress = clarification.record_answer(state, "matter hai bas")

    assert progress.progress in {"none", "minimal"}


def test_stuck_loop_exits_safely(monkeypatch):
    monkeypatch.setattr(main.clarification, "GEMINI_API_KEY", "")
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _message: route("unclear"))

    first = client.post("/api/ask", json={"question": "mera matter hai"}).json()
    second = client.post(
        "/api/ask",
        json={"question": "matter hai bas", "clarification_state_id": first["clarification"]["state_id"]},
    ).json()
    third = client.post(
        "/api/ask",
        json={"question": "same matter hai", "clarification_state_id": second["clarification"]["state_id"]},
    ).json()

    assert third["clarification"]["needed"] is False
    assert "not have enough factual detail" in third["answer"]["issue_summary"]


def test_no_jurisdiction_question_is_accepted():
    with pytest.raises(ValueError):
        clarification.validate_clarification_question(
            {
                "question": "Which state is the property located in?",
                "missing_information_type": "location",
                "reason_code": "tenancy_context",
            }
        )


def test_existing_retrieval_behavior_remains_unchanged():
    signals = rag.detect_domain_signals("cyber fraud online payment")

    assert "cyber" in signals["primary_domains"]
