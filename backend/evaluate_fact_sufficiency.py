from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

import domain_router
import fact_sufficiency
from config import BASE_DIR, GEMINI_MODEL

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_QUERY_PATH = EVAL_DIR / "fact_sufficiency_queries.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "fact_sufficiency_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "fact_sufficiency_evaluation.md"


def load_scenarios(path: Path = DEFAULT_QUERY_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")).get("scenarios", [])


def route_for_case(case: dict[str, Any]) -> domain_router.RouteDecision:
    return domain_router.RouteDecision(
        status="classified",
        domains=list(case["domains"]),
        primary_domain=case["domains"][0],
        confidence="high",
        issue_summary=case.get("issue_summary"),
        needs_clarification=False,
    )


def evaluate_scenario(case: dict[str, Any], delay_seconds: float = 0.0) -> dict[str, Any]:
    route = route_for_case(case)
    context, first_result = fact_sufficiency.start_fact_check(case["message"], route)
    fact_calls = 1 if first_result.provider == "gemini" else 0
    latencies = [first_result.latency_ms] if first_result.latency_ms is not None else []
    final_result = first_result
    asked_questions = [first_result.question] if first_result.needs_fact_clarification and first_result.question else []
    stopped_reason = first_result.status
    if first_result.needs_fact_clarification:
        for reply_index, reply in enumerate(case.get("replies", [])):
            if delay_seconds > 0 and reply_index:
                time.sleep(delay_seconds)
            progress, final_result = fact_sufficiency.continue_fact_check(context, reply)
            if final_result.provider == "gemini":
                fact_calls += 1
            if final_result.latency_ms is not None:
                latencies.append(final_result.latency_ms)
            if final_result.status == "sufficient":
                fact_sufficiency.clear_state(context.state_id)
                stopped_reason = "sufficient"
                break
            if progress.safe_exit:
                fact_sufficiency.clear_state(context.state_id)
                stopped_reason = "stuck_exit"
                break
            if final_result.question:
                asked_questions.append(final_result.question)
        else:
            stopped_reason = final_result.status

    expected_needs = bool(case["expected_needs_clarification"])
    actual_needs = first_result.needs_fact_clarification
    expected_final = case["expected_final_status"]
    final_status_match = final_result.status == expected_final
    repeated_question = len({q.lower().strip() for q in asked_questions if q}) != len([q for q in asked_questions if q])
    unnecessary_question = actual_needs and not expected_needs
    missing_question = expected_needs and not actual_needs
    return {
        "id": case["id"],
        "message": case["message"],
        "domains": case["domains"],
        "replies": case.get("replies", []),
        "expected_needs_clarification": expected_needs,
        "expected_final_status": expected_final,
        "first_result": first_result.to_dict(),
        "final_result": final_result.to_dict(),
        "asked_questions": asked_questions,
        "case_context": context.to_dict(),
        "stopped_reason": stopped_reason,
        "evaluation": {
            "sufficiency_decision_correct": actual_needs == expected_needs,
            "unnecessary_question": unnecessary_question,
            "missing_question": missing_question,
            "final_sufficiency_correct": final_status_match,
            "one_turn_resolved": expected_needs and len(case.get("replies", [])) >= 1 and final_result.status == "sufficient",
            "repeated_question": repeated_question,
            "stuck_safety_success": case["id"].startswith("stuck_") and final_result.status == "insufficient" and not repeated_question,
            "correct": actual_needs == expected_needs and final_status_match,
        },
        "call_counts": {"fact_gemini_calls": fact_calls},
        "latency": {"fact_latency_ms": latencies},
    }


def pct(count: int, total: int) -> float:
    return round(count / total, 3) if total else 0.0


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    needs = [r for r in results if r["expected_needs_clarification"]]
    stuck = [r for r in results if r["id"].startswith("stuck_")]
    return {
        "scenario_count": total,
        "sufficiency_decision_accuracy": pct(sum(1 for r in results if r["evaluation"]["sufficiency_decision_correct"]), total),
        "unnecessary_question_rate": pct(sum(1 for r in results if r["evaluation"]["unnecessary_question"]), total),
        "missing_question_rate": pct(sum(1 for r in results if r["evaluation"]["missing_question"]), total),
        "one_turn_resolution_rate": pct(sum(1 for r in needs if r["evaluation"]["one_turn_resolved"]), len(needs)),
        "final_sufficiency_accuracy": pct(sum(1 for r in results if r["evaluation"]["final_sufficiency_correct"]), total),
        "overall_accuracy": pct(sum(1 for r in results if r["evaluation"]["correct"]), total),
        "repeated_question_rate": pct(sum(1 for r in results if r["evaluation"]["repeated_question"]), total),
        "stuck_safety_success_rate": pct(sum(1 for r in stuck if r["evaluation"]["stuck_safety_success"]), len(stuck)),
    }


def evaluate_fact_sufficiency(query_path: Path = DEFAULT_QUERY_PATH, delay_seconds: float = 0.0) -> dict[str, Any]:
    scenarios = load_scenarios(query_path)
    results = []
    for index, case in enumerate(scenarios):
        if index and delay_seconds > 0:
            time.sleep(delay_seconds)
        results.append(evaluate_scenario(case, delay_seconds=delay_seconds))
    latencies = [latency for result in results for latency in result["latency"]["fact_latency_ms"]]
    return {
        "evaluation_config": {
            "query_file": query_path.as_posix(),
            "gemini_model": GEMINI_MODEL,
            "gemini_used_for_legal_answer_generation": False,
        },
        "metrics": aggregate(results),
        "call_counts": {
            "fact_sufficiency_gemini_calls": sum(r["call_counts"]["fact_gemini_calls"] for r in results),
        },
        "latency": {
            "average_fact_latency_ms": round(mean(latencies), 1) if latencies else None,
            "min_fact_latency_ms": min(latencies) if latencies else None,
            "max_fact_latency_ms": max(latencies) if latencies else None,
        },
        "results": results,
        "failures": [r for r in results if not r["evaluation"]["correct"]],
    }


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Fact Sufficiency Evaluation",
        "",
        "## Overall Results",
        f"- Scenarios: {metrics['scenario_count']}",
        f"- Sufficiency decision accuracy: {percent(metrics['sufficiency_decision_accuracy'])}",
        f"- Final sufficiency accuracy: {percent(metrics['final_sufficiency_accuracy'])}",
        f"- Overall accuracy: {percent(metrics['overall_accuracy'])}",
        f"- Unnecessary-question rate: {percent(metrics['unnecessary_question_rate'])}",
        f"- Missing-question rate: {percent(metrics['missing_question_rate'])}",
        "",
        "## Queries Correctly Allowed Through",
    ]
    for result in report["results"]:
        if not result["expected_needs_clarification"] and result["evaluation"]["sufficiency_decision_correct"]:
            lines.append(f"- `{result['message']}`")
    lines.extend(["", "## Queries Correctly Clarified"])
    for result in report["results"]:
        if result["expected_needs_clarification"] and result["evaluation"]["sufficiency_decision_correct"]:
            lines.append(f"- `{result['message']}` -> `{result['asked_questions'][0] if result['asked_questions'] else ''}`")
    lines.extend(["", "## Unnecessary Clarification Cases"])
    unnecessary = [r for r in report["results"] if r["evaluation"]["unnecessary_question"]]
    if not unnecessary:
        lines.append("- None.")
    for result in unnecessary:
        lines.append(f"- `{result['message']}`")
    lines.extend(
        [
            "",
            "## One-Turn Resolution",
            f"- One-turn resolution rate: {percent(metrics['one_turn_resolution_rate'])}",
            "",
            "## Hinglish Cases",
        ]
    )
    for result in report["results"]:
        text = result["message"].lower()
        if any(token in text for token in ("nahi", "mujhe", "mera", "hai", "paise", "karni")):
            lines.append(f"- `{result['message']}` -> `{result['final_result']['status']}`")
    lines.extend(["", "## Stuck Cases"])
    for result in report["results"]:
        if result["id"].startswith("stuck_"):
            lines.append(f"- `{result['message']}` stopped by `{result['stopped_reason']}`")
    lines.extend(["", "## Failure Examples"])
    if not report["failures"]:
        lines.append("- No failures under the current labels.")
    for result in report["failures"][:10]:
        lines.append(
            f"- `{result['message']}` expected first clarification `{result['expected_needs_clarification']}` "
            f"and final `{result['expected_final_status']}`; got first clarification "
            f"`{result['first_result']['needs_fact_clarification']}` and final `{result['final_result']['status']}`"
        )
    lines.extend(
        [
            "",
            "## Cost And Latency",
            f"- Gemini fact-sufficiency calls: {report['call_counts']['fact_sufficiency_gemini_calls']}",
            f"- Average fact-check latency: {report['latency']['average_fact_latency_ms']} ms",
            "",
            "## Recommendation",
            "- Proceed to the next conversation layer only after reviewing any remaining unnecessary or missing clarification cases.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate fact-sufficiency behavior.")
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERY_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    args = parser.parse_args()
    report = evaluate_fact_sufficiency(args.queries, delay_seconds=args.delay_seconds)
    args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    metrics = report["metrics"]
    print(
        "Fact sufficiency evaluation complete: "
        f"{metrics['scenario_count']} scenarios; "
        f"decision accuracy={percent(metrics['sufficiency_decision_accuracy'])}; "
        f"unnecessary-question rate={percent(metrics['unnecessary_question_rate'])}; "
        f"overall={percent(metrics['overall_accuracy'])}"
    )
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.md_output}")


if __name__ == "__main__":
    main()
