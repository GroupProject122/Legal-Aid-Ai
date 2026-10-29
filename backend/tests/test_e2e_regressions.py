"""Regression tests for failures found in the 2026-10-28 end-to-end run (54 cases, live Gemini).

Offline fallback: when the router cannot reach Gemini, main.offline_route_response() used to hand
back local retrieval for ANY question -- "Python code likho" and "weather tomorrow" were answered
with Constitution articles. These tests drive /api/ask with the router in its Gemini-failure
fallback (status=unclear, routing_error=True) and retrieval stubbed with the top scores measured
on the real rebuilt index for each query, so they need neither the network nor the vector store.

Case law: "What did the Supreme Court hold in Kesavananda Bharati case?" was expected to abstain
when the eval case was written (2026-09-01, no judgments in the corpus). The judgment has been in
the corpus since 2026-09-24, so answering from it is correct; a judgment the corpus does NOT hold
must still abstain.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import corpus_gap
import domain_router
import main
from rag import RetrievedChunk


def chunk(score: float, source: str = "constitutional_public_authority/constitution_of_india.pdf", **fields) -> RetrievedChunk:
    return RetrievedChunk(
        text=fields.pop("text", "Article text."),
        source=source,
        document_title=fields.pop("document_title", "The Constitution of India"),
        page=1,
        score=score,
        **fields,
    )


@pytest.fixture
def offline_router(monkeypatch, tmp_path):
    """Router in its Gemini-failure fallback; retrieval returns whatever the test sets."""
    monkeypatch.setattr(main.case_store, "DB_PATH", tmp_path / "legal_aid.db")
    monkeypatch.setattr(main, "LLM_PROVIDER", "gemini")

    def failed_route(*_args, **_kwargs):
        decision = domain_router.fallback_unclear_decision()
        decision.routing_error = True
        return decision

    monkeypatch.setattr(main.domain_router, "route_issue", failed_route)
    retrieved: list[RetrievedChunk] = []
    monkeypatch.setattr(main.rag, "retrieve", lambda _text: list(retrieved))
    return retrieved


def ask(question: str) -> dict:
    response = TestClient(main.app).post("/api/ask", json={"question": question})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize(
    ("question", "top_score"),
    [
        ("Python code likho", 0.351),  # gap_002_out_of_scope_python
        ("weather tomorrow", 0.238),  # gap_004_weather_out_scope
        ("best pizza recipe", 0.246),  # retrieval_queries.json non-legal
    ],
)
def test_offline_out_of_scope_question_is_declined_not_answered(offline_router, question, top_score):
    offline_router.append(chunk(top_score))
    payload = ask(question)
    assert payload["sources"] == []
    assert payload["insufficient_context"] is True
    assert not payload.get("offline")  # not rendered as an offline "here are the sections" answer
    assert payload["answer"]["issue_summary"] == main.OFFLINE_SCOPE_MESSAGE


def test_offline_legal_question_with_domain_signal_still_gets_sections(offline_router):
    offline_router.append(chunk(0.432, source="tenancy/delhi_rent_control_act_1958.pdf", document_title="The Delhi Rent Control Act, 1958"))
    payload = ask("landlord cut electricity")
    assert payload["offline"] is True
    assert [source["document"] for source in payload["sources"]] == ["The Delhi Rent Control Act, 1958"]


def test_offline_legal_question_without_domain_cues_still_gets_sections_when_clearly_relevant(offline_router):
    # "mera cyber issue hai" scores 0 on rag.detect_domain_signals (a known cue gap); its best
    # chunk on the real index scores 0.494, above the 0.44 "clearly relevant" line.
    offline_router.append(chunk(0.494, source="cyber/information_technology_act_2000.pdf", document_title="The Information Technology Act, 2000"))
    payload = ask("mera cyber issue hai")
    assert payload["offline"] is True
    assert payload["sources"]


def test_offline_clear_relevance_line_is_derived_from_rag_constants():
    assert main.OFFLINE_CLEAR_RELEVANCE_SCORE == pytest.approx(main.MIN_RELEVANCE_SCORE + main.RELEVANCE_WINDOW)


def test_case_law_question_answers_when_that_judgment_is_retrieved():
    question = "What did the Supreme Court hold in Kesavananda Bharati case?"
    judgment = chunk(
        0.62,
        source="constitutional_public_authority/case_law/case1_kesavananda_bharati_v_state_of_kerala_1973.pdf",
        document_title="Kesavananda Bharati Sripadagalvaru v. State of Kerala, (1973) 4 SCC 225",
        document_type="case_law",
        domain="constitutional_public_authority",
    )
    gap = corpus_gap.deterministic_pre_check(question, ["constitutional_public_authority"], [judgment], raw_user_query=question)
    assert "case_law_not_in_corpus" not in gap.reason_codes


def test_case_law_question_abstains_when_the_judgment_is_not_in_the_corpus():
    question = "What did the Supreme Court hold in the Indra Sawhney case?"
    statute_only = chunk(0.41, document_type="constitution", domain="constitutional_public_authority")
    gap = corpus_gap.deterministic_pre_check(question, ["constitutional_public_authority"], [statute_only], raw_user_query=question)
    assert gap.status == "insufficient"
    assert "case_law_not_in_corpus" in gap.reason_codes


def test_banking_07_second_turn_with_gemini_failing_is_not_asked_again(monkeypatch, tmp_path):
    # Set 1 banking_07: "Can I withdraw my complaint at any stage?" -> router asks which area ->
    # user: "complaint against my bank to the RBI Ombudsman". With Gemini failing on that second
    # routing call, continue_clarification() used to get a bare "unclear" (no keyword overrides,
    # no offline check) and asked "Briefly, who is involved and what happened?" again.
    import httpx

    monkeypatch.setattr(main.case_store, "DB_PATH", tmp_path / "legal_aid.db")
    monkeypatch.setattr(main, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(main, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(domain_router, "GEMINI_API_KEY", "test-key")
    calls = []

    class Models:
        def generate_content(self, **_kwargs):
            calls.append(1)
            if len(calls) == 1:  # the first-turn router call works and says "unclear"
                return type("Response", (), {"text": '{"status": "unclear", "domains": [], "primary_domain": "", '
                                                     '"confidence": "low", "issue_summary": "", "needs_clarification": true}'})()
            raise httpx.ConnectError("simulated Gemini failure")

    monkeypatch.setattr(domain_router.genai, "Client", lambda *_a, **_kw: type("Client", (), {"models": Models()})())
    monkeypatch.setattr(main.clarification, "GEMINI_API_KEY", "")  # deterministic clarification question
    monkeypatch.setattr(main.rag, "retrieve", lambda _text: [chunk(0.62, source="consumer/rbi_integrated_ombudsman_scheme.pdf",
                                                                    document_title="Reserve Bank - Integrated Ombudsman Scheme")])
    client = TestClient(main.app)

    first = client.post("/api/ask", json={"question": "Can I withdraw my complaint at any stage?"}).json()
    assert first["clarification"]["needed"] is True

    second = client.post("/api/ask", json={
        "question": "This is about a complaint against my bank to the RBI Ombudsman.",
        "clarification_state_id": first["clarification"]["state_id"],
    }).json()

    assert not (second.get("clarification") or {}).get("needed")
    assert second.get("offline") is True
    assert second["routing"]["domains"] == ["consumer"]
    assert second["sources"]


def test_router_failure_fallback_keeps_routing_error_after_keyword_override(monkeypatch):
    import httpx

    def failing_client(*_args, **_kwargs):
        raise httpx.ConnectError("simulated Gemini failure")

    monkeypatch.setattr(domain_router, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(domain_router.genai, "Client", failing_client)

    decision = domain_router.route_issue("Can I withdraw my complaint against my bank to the RBI Ombudsman?")

    assert decision.status == "classified"
    assert decision.domains == ["consumer"]
    assert decision.routing_error is True
