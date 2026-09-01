from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import claim_verifier
import grounded_answer
import rag


def chunk(chunk_id="c1", text=None):
    return rag.RetrievedChunk(
        chunk_id=chunk_id,
        text=text or "Section 45 says a landlord shall not cut off essential supply without just and sufficient cause.",
        source="tenancy/delhi_rent_control_act_1958.pdf",
        document_title="Delhi Rent Control Act, 1958",
        page=24,
        page_start=24,
        page_end=24,
        score=0.8,
        domain="tenancy",
        section_number="45",
        section_title="Cutting off or withholding essential supply or service",
    )


def response_with_claims(*claims):
    values = list(claims)
    return {
        "answer": {
            "issue_summary": "User reports landlord cut electricity.",
            "what_this_may_involve": values[:1],
            "possible_legal_position": values[1:],
            "suggested_next_steps": [],
            "evidence_to_preserve": ["Keep records if available."],
            "where_to_approach": [],
            "limitations": [],
            "possible_rights": values[1:],
            "next_steps": [],
        },
        "sources": [{"chunk_id": "c1"}],
        "confidence": "medium",
        "insufficient_context": False,
        "disclaimer": "This is legal information, not professional legal advice.",
        "source_chunk_ids": ["c1"],
    }


def test_valid_source_supported_claim_retained(monkeypatch):
    monkeypatch.setattr(claim_verifier, "GEMINI_API_KEY", "test")
    monkeypatch.setattr(
        claim_verifier,
        "call_gemini_verifier",
        lambda claims, chunks: {
            claims[0].claim_id: {
                "claim_id": claims[0].claim_id,
                "support": "supported",
                "supporting_chunk_ids": ["c1"],
                "reason": "Supported.",
            }
        },
    )

    output = claim_verifier.verify_and_sanitize_response(
        response_with_claims("Section 45 may address cutting off electricity."),
        [chunk()],
    )

    assert output["answer"]["what_this_may_involve"] == ["Section 45 may address cutting off electricity."]
    assert output["verification"]["verified_claim_count"] == 1


def test_unknown_source_id_rejected():
    output = claim_verifier.verify_and_sanitize_response(
        {**response_with_claims("Section 45 may apply."), "source_chunk_ids": ["missing"]},
        [chunk()],
    )

    assert output["verification"]["status"] == "verified"
    assert output["verification"]["removed_claim_count"] == 1
    assert output["verification"]["deterministic_rejections"]


def test_unsupported_claim_removed(monkeypatch):
    monkeypatch.setattr(claim_verifier, "GEMINI_API_KEY", "test")
    monkeypatch.setattr(
        claim_verifier,
        "call_gemini_verifier",
        lambda claims, chunks: {
            claims[0].claim_id: {
                "claim_id": claims[0].claim_id,
                "support": "unsupported",
                "supporting_chunk_ids": [],
                "reason": "No support.",
            }
        },
    )

    output = claim_verifier.verify_and_sanitize_response(
        response_with_claims("The landlord must pay compensation within 30 days."),
        [chunk()],
    )

    assert output["answer"]["what_this_may_involve"] == []
    assert output["verification"]["removed_claim_count"] == 1


def test_partially_supported_claim_is_qualified(monkeypatch):
    monkeypatch.setattr(claim_verifier, "GEMINI_API_KEY", "test")
    monkeypatch.setattr(
        claim_verifier,
        "call_gemini_verifier",
        lambda claims, chunks: {
            claims[0].claim_id: {
                "claim_id": claims[0].claim_id,
                "support": "partially_supported",
                "supporting_chunk_ids": ["c1"],
                "reason": "Only part is supported.",
            }
        },
    )

    output = claim_verifier.verify_and_sanitize_response(
        response_with_claims("The landlord may have cut an essential supply and must pay damages."),
        [chunk()],
    )

    assert output["answer"]["what_this_may_involve"][0] == "The landlord may have cut an essential supply and must pay damages."
    assert output["verification"]["partially_supported_claim_count"] == 1


def test_deadline_claim_without_source_support_is_removed(monkeypatch):
    monkeypatch.setattr(claim_verifier, "GEMINI_API_KEY", "test")
    monkeypatch.setattr(claim_verifier, "call_gemini_verifier", lambda claims, chunks: {})

    output = claim_verifier.verify_and_sanitize_response(
        response_with_claims("You must file within 30 days."),
        [chunk()],
    )

    assert output["answer"]["what_this_may_involve"] == []


def test_forum_claim_without_support_is_removed(monkeypatch):
    monkeypatch.setattr(claim_verifier, "GEMINI_API_KEY", "test")
    monkeypatch.setattr(claim_verifier, "call_gemini_verifier", lambda claims, chunks: {})

    output = claim_verifier.verify_and_sanitize_response(
        response_with_claims("You must approach the High Court."),
        [chunk()],
    )

    assert output["answer"]["what_this_may_involve"] == []


def test_user_fact_summary_is_not_treated_as_legal_claim():
    output = claim_verifier.verify_and_sanitize_response(
        response_with_claims(),
        [chunk()],
    )

    assert output["answer"]["issue_summary"] == "User reports landlord cut electricity."
    assert output["verification"]["claim_count"] == 0


def test_multi_source_support_works(monkeypatch):
    monkeypatch.setattr(claim_verifier, "GEMINI_API_KEY", "test")
    other = chunk("c2", "The Controller may direct restoration of supply.")
    response = response_with_claims("The Controller may direct restoration of supply.")
    response["source_chunk_ids"] = ["c1", "c2"]
    monkeypatch.setattr(
        claim_verifier,
        "call_gemini_verifier",
        lambda claims, chunks: {
            claims[0].claim_id: {
                "claim_id": claims[0].claim_id,
                "support": "supported",
                "supporting_chunk_ids": ["c1", "c2"],
                "reason": "Both support.",
            }
        },
    )

    output = claim_verifier.verify_and_sanitize_response(response, [chunk(), other])

    assert output["verification"]["results"][0]["supporting_chunk_ids"] == ["c1", "c2"]


def test_verifier_api_failure_uses_safe_fallback(monkeypatch):
    monkeypatch.setattr(claim_verifier, "GEMINI_API_KEY", "test")

    def fail(_claims, _chunks):
        raise RuntimeError("quota")

    monkeypatch.setattr(claim_verifier, "call_gemini_verifier", fail)
    output = claim_verifier.verify_and_sanitize_response(
        response_with_claims("The landlord must restore electricity within 24 hours."),
        [chunk()],
    )

    assert output["verification"]["status"] == "unavailable"
    assert output["answer"]["what_this_may_involve"] == []


def test_verifier_api_failure_keeps_narrow_traceable_section_claim(monkeypatch):
    monkeypatch.setattr(claim_verifier, "GEMINI_API_KEY", "test")

    def fail(_claims, _chunks):
        raise RuntimeError("quota")

    monkeypatch.setattr(claim_verifier, "call_gemini_verifier", fail)
    output = claim_verifier.verify_and_sanitize_response(
        response_with_claims("Section 45 addresses essential supply."),
        [chunk()],
    )

    assert output["verification"]["status"] == "unavailable"
    assert output["answer"]["what_this_may_involve"] == ["Section 45 addresses essential supply."]


def test_grounded_answer_source_mapping_remains_intact():
    output = grounded_answer.normalize_grounded_output(
        {
            "issue_summary": "Neutral.",
            "what_this_may_involve": [],
            "possible_legal_position": [],
            "suggested_next_steps": [],
            "evidence_to_preserve": [],
            "where_to_approach": [],
            "limitations": [],
            "source_chunk_ids": ["c1"],
            "confidence": "medium",
            "insufficient_context": False,
            "disclaimer": "This is general legal information.",
        },
        [chunk()],
    )

    assert output["sources"][0]["chunk_id"] == "c1"
