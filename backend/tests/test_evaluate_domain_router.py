from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import evaluate_domain_router as evaluator
from domain_router import RouteDecision


def test_evaluate_case_supported_single_domain_match():
    case = {
        "expected_status": "classified",
        "expected_domains": ["cyber"],
        "expected_primary_domain": "cyber",
    }
    decision = RouteDecision(
        status="classified",
        domains=["cyber"],
        primary_domain="cyber",
        confidence="high",
        issue_summary="Possible cyber issue.",
        needs_clarification=False,
    )

    result = evaluator.evaluate_case(case, decision)

    assert result["correct"] is True
    assert result["domain_exact_match"] is True
    assert result["domain_recall"] == 1.0


def test_evaluate_case_multi_domain_recall_without_exact_match():
    case = {
        "expected_status": "classified",
        "expected_domains": ["consumer", "cyber"],
    }
    decision = RouteDecision(
        status="classified",
        domains=["consumer"],
        primary_domain="consumer",
        confidence="medium",
        issue_summary="Possible seller issue.",
        needs_clarification=False,
    )

    result = evaluator.evaluate_case(case, decision)

    assert result["domain_exact_match"] is False
    assert result["domain_recall"] == 0.5


def test_status_confusion_serialization():
    results = [
        {"expected_status": "classified", "decision": {"status": "classified"}},
        {"expected_status": "unsupported", "decision": {"status": "unclear"}},
    ]

    assert evaluator.status_confusion(results) == {
        "classified -> classified": 1,
        "unsupported -> unclear": 1,
    }
