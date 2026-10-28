from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import config
import corpus_gap
import domain_router
import fact_sufficiency
import main
import query_normalizer


def _fake_client(response_text: str):
    class FakeModels:
        def generate_content(self, **_kwargs):
            class Response:
                text = response_text

            return Response()

    class FakeClient:
        models = FakeModels()

    return lambda **_kwargs: FakeClient()


# --- looks_like_plain_english ---


def test_plain_english_is_detected():
    assert query_normalizer.looks_like_plain_english("What is a consumer under the Consumer Protection Act?")
    assert query_normalizer.looks_like_plain_english("my Instagram account was hacked")
    assert query_normalizer.looks_like_plain_english("landlord is refusing to return my security deposit")


def test_hinglish_is_detected():
    assert not query_normalizer.looks_like_plain_english("mera Instagram hack ho gaya")
    assert not query_normalizer.looks_like_plain_english("seller refund nahi de raha")
    assert not query_normalizer.looks_like_plain_english("consumer complaint karni hai")


# --- english_retrieval_query ---


def test_english_passes_through_with_no_gemini_call(monkeypatch):
    def fail_if_called(**_kwargs):
        raise AssertionError("genai.Client should not be called for plain English text")

    monkeypatch.setattr(query_normalizer, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(query_normalizer.genai, "Client", fail_if_called)

    text = "my Instagram account was hacked"
    assert query_normalizer.english_retrieval_query(text) == text


def test_hinglish_is_rewritten(monkeypatch):
    monkeypatch.setattr(query_normalizer, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        query_normalizer.genai,
        "Client",
        _fake_client('{"english_query": "my Instagram account was hacked"}'),
    )

    result = query_normalizer.english_retrieval_query("mera Instagram hack ho gaya")
    assert result == "my Instagram account was hacked"


def test_gemini_failure_falls_back_to_original_text(monkeypatch):
    def raise_timeout(**_kwargs):
        raise TimeoutError("simulated timeout")

    monkeypatch.setattr(query_normalizer, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(query_normalizer.genai, "Client", raise_timeout)

    text = "mera Instagram hack ho gaya"
    assert query_normalizer.english_retrieval_query(text) == text


def test_invalid_json_falls_back_to_original_text(monkeypatch):
    monkeypatch.setattr(query_normalizer, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(query_normalizer.genai, "Client", _fake_client("{not valid json"))

    text = "mera Instagram hack ho gaya"
    assert query_normalizer.english_retrieval_query(text) == text


def test_empty_rewrite_falls_back_to_original_text(monkeypatch):
    monkeypatch.setattr(query_normalizer, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(query_normalizer.genai, "Client", _fake_client('{"english_query": "  "}'))

    text = "mera Instagram hack ho gaya"
    assert query_normalizer.english_retrieval_query(text) == text


def test_no_api_key_falls_back_to_original_text(monkeypatch):
    monkeypatch.setattr(query_normalizer, "GEMINI_API_KEY", "")
    text = "mera Instagram hack ho gaya"
    assert query_normalizer.english_retrieval_query(text) == text


def test_empty_text_returns_empty_without_gemini_call(monkeypatch):
    def fail_if_called(**_kwargs):
        raise AssertionError("genai.Client should not be called for empty text")

    monkeypatch.setattr(query_normalizer, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(query_normalizer.genai, "Client", fail_if_called)
    assert query_normalizer.english_retrieval_query("") == ""


# --- Integration: only the retrieval call receives the rewritten query ---


def _case_context(message: str, domains=("cyber",)) -> fact_sufficiency.CaseContext:
    route = domain_router.RouteDecision(
        status="classified",
        domains=list(domains),
        primary_domain=domains[0],
        confidence="high",
        issue_summary=message,
        needs_clarification=False,
    )
    return fact_sufficiency.new_case_context(message, route)


def test_rag_retrieve_receives_the_normalized_query(monkeypatch):
    context = _case_context("mera Instagram hack ho gaya")
    fact_result = fact_sufficiency.FactSufficiencyResult(
        status="sufficient",
        missing_facts=[],
        needs_fact_clarification=False,
        question=None,
        reason=None,
        normalized_case_summary="mera Instagram hack ho gaya",
    )

    captured = {}
    monkeypatch.setattr(main, "HINGLISH_RETRIEVAL_NORMALIZER", True)
    monkeypatch.setattr(query_normalizer, "english_retrieval_query", lambda text: "SENTINEL english query")
    monkeypatch.setattr(main, "query_normalizer", query_normalizer)

    def fake_retrieve(query, **_kwargs):
        captured["query"] = query
        return []  # Empty -> short-circuits to insufficient_response before anything else runs.

    monkeypatch.setattr(main.rag, "retrieve", fake_retrieve)

    main.answer_grounded_from_context(
        original_message="mera Instagram hack ho gaya",
        context=context,
        fact_result=fact_result,
    )

    assert captured["query"] == "SENTINEL english query"


def test_corpus_gap_receives_the_original_text_not_the_normalized_one(monkeypatch):
    context = _case_context("mera Instagram hack ho gaya")
    fact_result = fact_sufficiency.FactSufficiencyResult(
        status="sufficient",
        missing_facts=[],
        needs_fact_clarification=False,
        question=None,
        reason=None,
        normalized_case_summary="mera Instagram hack ho gaya",
    )

    captured = {}
    monkeypatch.setattr(main, "HINGLISH_RETRIEVAL_NORMALIZER", True)
    monkeypatch.setattr(query_normalizer, "english_retrieval_query", lambda text: "SENTINEL english query")
    monkeypatch.setattr(main, "query_normalizer", query_normalizer)
    monkeypatch.setattr(main.rag, "retrieve", lambda query, **_kwargs: ["fake-chunk"])

    def fake_pre_generation_check(retrieval_text, domains, chunks, raw_user_query=None):
        captured["retrieval_text"] = retrieval_text
        return corpus_gap.CorpusGapResult(
            status="insufficient",
            reason_codes=["no_relevant_source"],
            summary="stopped for test",
            allow_grounded_answer=False,
        )

    monkeypatch.setattr(main.corpus_gap, "pre_generation_check", fake_pre_generation_check)

    main.answer_grounded_from_context(
        original_message="mera Instagram hack ho gaya",
        context=context,
        fact_result=fact_result,
    )

    assert captured["retrieval_text"] == "mera Instagram hack ho gaya"
    assert captured["retrieval_text"] != "SENTINEL english query"


def test_normalizer_is_off_by_default_and_retrieval_gets_the_original_text(monkeypatch):
    assert config.HINGLISH_RETRIEVAL_NORMALIZER is False  # default, with no env override
    monkeypatch.setattr(main, "HINGLISH_RETRIEVAL_NORMALIZER", False)
    context = _case_context("mera Instagram hack ho gaya")
    fact_result = fact_sufficiency.FactSufficiencyResult(
        status="sufficient",
        missing_facts=[],
        needs_fact_clarification=False,
        question=None,
        reason=None,
        normalized_case_summary="mera Instagram hack ho gaya",
    )

    def must_not_be_called(_text):
        raise AssertionError("normaliser called while HINGLISH_RETRIEVAL_NORMALIZER is off")

    captured = {}
    monkeypatch.setattr(query_normalizer, "english_retrieval_query", must_not_be_called)

    def fake_retrieve(query, **_kwargs):
        captured["query"] = query
        return []

    monkeypatch.setattr(main.rag, "retrieve", fake_retrieve)
    main.answer_grounded_from_context(original_message="mera Instagram hack ho gaya", context=context, fact_result=fact_result)
    assert "mera Instagram hack ho gaya" in captured["query"]
