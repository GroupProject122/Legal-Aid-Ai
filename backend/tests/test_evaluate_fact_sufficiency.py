from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import evaluate_fact_sufficiency


def result(**overrides):
    base = {
        "expected_needs_clarification": False,
        "expected_final_status": "sufficient",
        "first_result": {"needs_fact_clarification": False},
        "final_result": {"status": "sufficient"},
        "asked_questions": [],
        "id": "case_01",
        "evaluation": {
            "sufficiency_decision_correct": True,
            "unnecessary_question": False,
            "missing_question": False,
            "final_sufficiency_correct": True,
            "one_turn_resolved": False,
            "repeated_question": False,
            "stuck_safety_success": False,
            "correct": True,
        },
    }
    base.update(overrides)
    return base


def test_aggregate_fact_metrics():
    metrics = evaluate_fact_sufficiency.aggregate(
        [
            result(),
            result(
                id="case_02",
                expected_needs_clarification=True,
                first_result={"needs_fact_clarification": True},
                asked_questions=["What happened?"],
                evaluation={
                    **result()["evaluation"],
                    "one_turn_resolved": True,
                },
            ),
        ]
    )

    assert metrics["scenario_count"] == 2
    assert metrics["sufficiency_decision_accuracy"] == 1.0
    assert metrics["unnecessary_question_rate"] == 0.0
    assert metrics["one_turn_resolution_rate"] == 1.0


def test_missing_question_metric():
    metrics = evaluate_fact_sufficiency.aggregate(
        [
            result(
                expected_needs_clarification=True,
                evaluation={
                    **result()["evaluation"],
                    "sufficiency_decision_correct": False,
                    "missing_question": True,
                    "correct": False,
                },
            )
        ]
    )

    assert metrics["missing_question_rate"] == 1.0


def test_markdown_contains_core_sections():
    report = {
        "metrics": evaluate_fact_sufficiency.aggregate([result(message="seller refund")]),
        "results": [result(message="seller refund")],
        "failures": [],
        "call_counts": {"fact_sufficiency_gemini_calls": 0},
        "latency": {"average_fact_latency_ms": None},
    }

    markdown = evaluate_fact_sufficiency.render_markdown(report)

    assert "# Fact Sufficiency Evaluation" in markdown
    assert "Unnecessary Clarification Cases" in markdown
