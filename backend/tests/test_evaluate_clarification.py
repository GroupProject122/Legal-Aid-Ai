from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import evaluate_clarification


def result(**overrides):
    base = {
        "asked_questions": ["What happened?"],
        "initial_route": {"status": "unclear"},
        "expected_final_status": "classified",
        "expected_domains": ["consumer"],
        "final_route": {"status": "classified", "domains": ["consumer"]},
        "id": "case_01",
        "evaluation": {
            "clarification_trigger_correct": True,
            "status_match": True,
            "domain_match": True,
            "correct": True,
            "one_turn_resolved": True,
            "repeated_question": False,
            "stuck_safety_success": False,
        },
    }
    base.update(overrides)
    return base


def test_aggregate_clarification_metrics():
    metrics = evaluate_clarification.aggregate([result(), result(id="case_02", final_route={"status": "classified", "domains": ["cyber"]}, evaluation={**result()["evaluation"], "domain_match": False, "correct": False})])

    assert metrics["scenario_count"] == 2
    assert metrics["clarification_trigger_accuracy"] == 1.0
    assert metrics["final_domain_accuracy"] == 0.5
    assert metrics["overall_accuracy"] == 0.5


def test_stuck_safety_metric():
    metrics = evaluate_clarification.aggregate(
        [
            result(
                id="stuck_01",
                expected_final_status="unclear",
                expected_domains=[],
                final_route={"status": "unclear", "domains": []},
                evaluation={
                    **result()["evaluation"],
                    "stuck_safety_success": True,
                    "correct": True,
                },
            )
        ]
    )

    assert metrics["stuck_safety_success_rate"] == 1.0


def test_markdown_serialization_contains_core_sections():
    report = {
        "metrics": evaluate_clarification.aggregate([result()]),
        "results": [result(initial_message="mere paise fas gaye")],
        "failures": [],
        "call_counts": {"router_calls": 2, "clarification_gemini_calls": 1},
        "latency": {"average_clarification_latency_ms": 1200},
    }

    markdown = evaluate_clarification.render_markdown(report)

    assert "# Adaptive Clarification Evaluation" in markdown
    assert "One-Turn Resolution" in markdown
