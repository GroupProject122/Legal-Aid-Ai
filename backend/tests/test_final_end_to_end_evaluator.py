from __future__ import annotations

import evaluate_final_end_to_end as evaluator


def test_expected_document_hit_matches_source_title():
    sources = [{"document_title": "The Consumer Protection Act, 2019"}]

    assert evaluator.expected_doc_hit(sources, ["Consumer Protection Act"]) is True


def test_expected_provision_hit_matches_source_provision():
    sources = [{"provision": "Section 45 - Cutting off or withholding essential supply"}]

    assert evaluator.expected_provision_hit(sources, ["45"]) is True


def test_document_conflict_clarification_does_not_require_route():
    assert evaluator.domain_match(
        actual=[],
        expected=["consumer"],
        expected_status="clarification",
        actual_status_value="clarification",
    )


def test_document_as_legal_source_leak_detected():
    response = {"sources": [{"source": "user_document", "document_title": "Uploaded invoice"}]}

    assert evaluator.document_as_legal_source_leak(response)


def test_aggregate_tracks_unconfirmed_fact_leakage():
    result = {
        "case_id": "doc_003_unconfirmed_rejected",
        "category": "document_assisted",
        "query": "Can I use this invoice?",
        "expected_status": "abstained",
        "actual_status": "abstained",
        "expected_domains": ["consumer"],
        "actual_domains": [],
        "primary_domain": None,
        "route_correct": True,
        "clarification_triggered": False,
        "clarification_correct": True,
        "corpus_status": None,
        "expected_corpus_status": "unconfirmed_context_rejected",
        "corpus_gap_correct": True,
        "expected_legal_source_hit": None,
        "expected_provision_hit": None,
        "legal_source_validity": True,
        "unsupported_claim_leak": False,
        "document_context_expected": False,
        "document_context_used": False,
        "document_legal_source_separation": True,
        "unconfirmed_fact_leakage": False,
        "confirmed_fact_mutation": False,
        "safe_abstention_correct": True,
        "latency_ms": 1,
        "api_status_code": 400,
        "responses": [{"body": {"detail": "Fact extraction session was not found."}}],
        "failure_causes": [],
        "verification": None,
        "generation": None,
        "success": True,
        "manual_quality": {"total": 8},
    }

    metrics = evaluator.aggregate([result], total_case_count=1)

    assert metrics["unconfirmed_fact_leakage_rate"] == 0.0
    assert metrics["safe_abstention_accuracy"] == 1.0
