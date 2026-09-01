from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import corpus_gap
import rag


def chunk(
    chunk_id="c1",
    domain="tenancy",
    score=0.8,
    authority_level="primary",
    status="active",
    document_type="statute",
    title="The Delhi Rent Control Act, 1958",
):
    return rag.RetrievedChunk(
        chunk_id=chunk_id,
        text="Section 45 says a landlord shall not cut off essential supply without just and sufficient cause.",
        source="tenancy/delhi_rent_control_act_1958.pdf",
        document_title=title,
        page=24,
        page_start=24,
        page_end=24,
        score=score,
        rerank_score=score,
        domain=domain,
        authority_level=authority_level,
        status=status,
        document_type=document_type,
        section_number="45",
        section_title="Cutting off or withholding essential supply or service",
    )


def test_strong_primary_source_retrieval_is_sufficient():
    gap = corpus_gap.pre_generation_check("landlord cut electricity", ["tenancy"], [chunk()])

    assert gap.status == "sufficient"
    assert gap.allow_grounded_answer is True


def test_delhi_tenancy_supported():
    gap = corpus_gap.pre_generation_check("landlord cut electricity in Delhi", ["tenancy"], [chunk()])

    assert gap.status == "sufficient"


def test_explicit_non_delhi_tenancy_is_jurisdiction_gap():
    gap = corpus_gap.pre_generation_check("my landlord in Mumbai cut electricity", ["tenancy"], [chunk()])

    assert gap.status == "insufficient"
    assert "jurisdiction_not_covered" in gap.reason_codes
    assert gap.allow_grounded_answer is False


def test_missing_case_law_is_insufficient():
    gap = corpus_gap.pre_generation_check("what did the Supreme Court hold in a specific case", ["constitutional_public_authority"], [chunk(domain="constitutional_public_authority")])

    assert gap.status == "insufficient"
    assert "case_law_not_in_corpus" in gap.reason_codes


def test_supporting_only_sources_are_limited():
    supporting = chunk(authority_level="primary", status="supporting_only", document_type="supporting_property_law")
    gap = corpus_gap.pre_generation_check("tenant landlord dispute", ["tenancy"], [supporting])

    assert gap.status == "limited"
    assert "supporting_sources_only" in gap.reason_codes


def test_grounded_answer_insufficient_context_affects_post_check():
    pre = corpus_gap.result("sufficient", [], "ok", True, False, False)
    response = {"insufficient_context": True, "answer": {}, "verification": {}}
    gap = corpus_gap.post_generation_check(response, pre)

    assert gap.status == "insufficient"
    assert gap.allow_grounded_answer is False


def test_verifier_stripping_core_claims_affects_final_gap_status():
    pre = corpus_gap.result("sufficient", [], "ok", True, False, False)
    response = {
        "insufficient_context": False,
        "verification": {
            "claim_count": 2,
            "removed_claim_count": 2,
            "verified_claim_count": 0,
            "partially_supported_claim_count": 0,
        },
    }
    gap = corpus_gap.post_generation_check(response, pre)

    assert gap.status == "insufficient"
    assert "verification_removed_core_claims" in gap.reason_codes


def test_sufficient_case_is_not_blocked():
    response = corpus_gap.abstention_response(corpus_gap.result("insufficient", ["no_relevant_source"], "No source.", False, True, True))

    assert response["insufficient_context"] is True
    assert response["corpus_status"] == "insufficient"


def test_missing_current_law_becomes_limited_not_forced_answer():
    gap = corpus_gap.pre_generation_check(
        "Does CERT-In direction require incident reporting?",
        ["cyber"],
        [chunk(domain="cyber", title="The Information Technology Act, 2000")],
    )

    assert gap.status == "limited"
    assert "missing_current_law" in gap.reason_codes


def test_no_retrieval_changes():
    before = rag.final_rerank_score
    corpus_gap.pre_generation_check("landlord cut electricity", ["tenancy"], [chunk()])

    assert rag.final_rerank_score is before
