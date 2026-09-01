from __future__ import annotations

import argparse
import json
import time
from collections import Counter
from pathlib import Path
from statistics import mean
from typing import Any

import clarification
import domain_router
from config import BASE_DIR, GEMINI_MODEL

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_QUERY_PATH = EVAL_DIR / "clarification_queries.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "clarification_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "clarification_evaluation.md"


def load_scenarios(path: Path = DEFAULT_QUERY_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")).get("scenarios", [])


def evaluate_scenario(case: dict[str, Any], delay_seconds: float = 0.0) -> dict[str, Any]:
    clarification.clear_state(None)
    router_calls = 1
    clarification_calls = 0
    clarification_latencies: list[int] = []
    initial_route = domain_router.route_issue(case["initial_message"])
    asked_questions: list[str] = []
    final_route = initial_route
    state = None
    stopped_reason = "initial_route"

    if initial_route.status == "unclear":
        if delay_seconds > 0:
            time.sleep(delay_seconds)
        clarification_calls += 1
        state, question = clarification.start_clarification(case["initial_message"], initial_route)
        if question.latency_ms is not None:
            clarification_latencies.append(question.latency_ms)
        asked_questions.append(question.question)
        for reply_index, reply in enumerate(case.get("replies", [])):
            progress = clarification.record_answer(state, reply)
            if delay_seconds > 0:
                time.sleep(delay_seconds)
            router_calls += 1
            final_route = domain_router.route_issue(state.accumulated_context)
            if final_route.status in {"classified", "unsupported", "out_of_scope"}:
                clarification.clear_state(state.state_id)
                stopped_reason = final_route.status
                break
            if progress.safe_exit:
                clarification.clear_state(state.state_id)
                stopped_reason = "stuck_exit"
                break
            if reply_index < len(case.get("replies", [])) - 1:
                if delay_seconds > 0:
                    time.sleep(delay_seconds)
                clarification_calls += 1
                question = clarification.generate_next_question(state, final_route, progress)
                if question.latency_ms is not None:
                    clarification_latencies.append(question.latency_ms)
                asked_questions.append(question.question)
        else:
            stopped_reason = final_route.status

    expected_domains = set(case.get("expected_domains") or [])
    actual_domains = set(final_route.domains)
    expected_status = case["expected_final_status"]
    clarification_expected = bool(case.get("expected_clarification"))
    clarification_triggered = initial_route.status == "unclear"
    status_match = final_route.status == expected_status
    domain_match = actual_domains == expected_domains if expected_domains else not actual_domains
    resolved = final_route.status in {"classified", "unsupported", "out_of_scope"}
    repeated_question = len({q.lower().strip() for q in asked_questions}) != len(asked_questions)

    return {
        "id": case["id"],
        "initial_message": case["initial_message"],
        "replies": case.get("replies", []),
        "expected_final_status": expected_status,
        "expected_domains": sorted(expected_domains),
        "initial_route": initial_route.to_dict(),
        "final_route": final_route.to_dict(),
        "asked_questions": asked_questions,
        "stopped_reason": stopped_reason,
        "evaluation": {
            "clarification_trigger_correct": clarification_triggered == clarification_expected,
            "status_match": status_match,
            "domain_match": domain_match,
            "correct": status_match and domain_match and clarification_triggered == clarification_expected,
            "resolved": resolved,
            "one_turn_resolved": resolved and len(case.get("replies", [])) >= 1 and len(asked_questions) == 1,
            "multi_turn_behavior": len(asked_questions) > 1,
            "repeated_question": repeated_question,
            "stuck_safety_success": case["id"].startswith("stuck_")
            and final_route.status == "unclear"
            and not repeated_question,
        },
        "call_counts": {
            "router_calls": router_calls,
            "clarification_calls": clarification_calls,
        },
        "latency": {
            "clarification_latency_ms": clarification_latencies,
        },
    }


def pct(count: int, total: int) -> float:
    return round(count / total, 3) if total else 0.0


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    clarification_expected = [r for r in results if r["asked_questions"] or r["initial_route"]["status"] == "unclear"]
    supported = [r for r in results if r["expected_final_status"] == "classified"]
    stuck = [r for r in results if r["id"].startswith("stuck_")]
    return {
        "scenario_count": total,
        "clarification_trigger_accuracy": pct(
            sum(1 for r in results if r["evaluation"]["clarification_trigger_correct"]),
            total,
        ),
        "final_status_accuracy": pct(sum(1 for r in results if r["evaluation"]["status_match"]), total),
        "final_domain_accuracy": pct(sum(1 for r in results if r["evaluation"]["domain_match"]), total),
        "overall_accuracy": pct(sum(1 for r in results if r["evaluation"]["correct"]), total),
        "one_turn_resolution_rate": pct(
            sum(1 for r in clarification_expected if r["evaluation"]["one_turn_resolved"]),
            len(clarification_expected),
        ),
        "supported_domain_accuracy": pct(
            sum(1 for r in supported if r["evaluation"]["domain_match"]),
            len(supported),
        ),
        "repeated_question_rate": pct(sum(1 for r in results if r["evaluation"]["repeated_question"]), total),
        "stuck_safety_success_rate": pct(
            sum(1 for r in stuck if r["evaluation"]["stuck_safety_success"]),
            len(stuck),
        ),
    }


def evaluate_clarification(query_path: Path = DEFAULT_QUERY_PATH, delay_seconds: float = 0.0) -> dict[str, Any]:
    scenarios = load_scenarios(query_path)
    results = []
    for index, case in enumerate(scenarios):
        if index and delay_seconds > 0:
            time.sleep(delay_seconds)
        results.append(evaluate_scenario(case, delay_seconds=delay_seconds))
    clarification_latencies = [
        latency
        for result in results
        for latency in result["latency"]["clarification_latency_ms"]
    ]
    status_confusion = Counter(
        f"{result['expected_final_status']} -> {result['final_route']['status']}" for result in results
    )
    return {
        "evaluation_config": {
            "query_file": query_path.as_posix(),
            "gemini_model": GEMINI_MODEL,
            "gemini_used_for_legal_answer_generation": False,
        },
        "metrics": aggregate(results),
        "call_counts": {
            "router_calls": sum(result["call_counts"]["router_calls"] for result in results),
            "clarification_gemini_calls": sum(result["call_counts"]["clarification_calls"] for result in results),
        },
        "latency": {
            "average_clarification_latency_ms": round(mean(clarification_latencies), 1)
            if clarification_latencies
            else None,
            "min_clarification_latency_ms": min(clarification_latencies) if clarification_latencies else None,
            "max_clarification_latency_ms": max(clarification_latencies) if clarification_latencies else None,
        },
        "status_confusion": dict(status_confusion),
        "results": results,
        "failures": [result for result in results if not result["evaluation"]["correct"]],
    }


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Adaptive Clarification Evaluation",
        "",
        "## Overall Results",
        f"- Scenarios: {metrics['scenario_count']}",
        f"- Clarification-trigger accuracy: {percent(metrics['clarification_trigger_accuracy'])}",
        f"- Final status accuracy: {percent(metrics['final_status_accuracy'])}",
        f"- Final domain accuracy: {percent(metrics['final_domain_accuracy'])}",
        f"- Overall accuracy: {percent(metrics['overall_accuracy'])}",
        "",
        "## One-Turn Resolution",
        f"- One-turn resolution rate: {percent(metrics['one_turn_resolution_rate'])}",
        "",
        "## Multi-Turn Resolution",
        f"- Repeated-question rate: {percent(metrics['repeated_question_rate'])}",
        f"- Stuck safety success rate: {percent(metrics['stuck_safety_success_rate'])}",
        "",
        "## Hinglish Cases",
    ]
    for result in report["results"]:
        text = result["initial_message"].lower()
        if any(token in text for token in ("mujhe", "mere", "mera", "nahi", "kaise", "paise", "hai")):
            lines.append(
                f"- `{result['initial_message']}` -> questions {len(result['asked_questions'])}; "
                f"final `{result['final_route']['status']}` {result['final_route']['domains']}"
            )
    lines.extend(["", "## Unsupported Resolution"])
    for result in report["results"]:
        if result["expected_final_status"] == "unsupported":
            lines.append(f"- `{result['initial_message']}` -> `{result['final_route']['status']}`")
    lines.extend(["", "## Stuck / Non-Informative Cases"])
    for result in report["results"]:
        if result["id"].startswith("stuck_"):
            lines.append(f"- `{result['initial_message']}` stopped by `{result['stopped_reason']}`")
    lines.extend(["", "## Failure Examples"])
    if not report["failures"]:
        lines.append("- No failures under the current labels.")
    for result in report["failures"][:10]:
        lines.append(
            f"- `{result['initial_message']}` expected `{result['expected_final_status']}` "
            f"{result['expected_domains']}; got `{result['final_route']['status']}` "
            f"{result['final_route']['domains']}"
        )
    lines.extend(
        [
            "",
            "## Cost And Latency",
            f"- Router calls: {report['call_counts']['router_calls']}",
            f"- Gemini clarification calls: {report['call_counts']['clarification_gemini_calls']}",
            f"- Average clarification latency: {report['latency']['average_clarification_latency_ms']} ms",
            "",
            "## Recommended Next Step",
            "- Part 8C can add conditional jurisdiction questions after a domain is clear.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate adaptive clarification behavior.")
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERY_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    args = parser.parse_args()
    report = evaluate_clarification(args.queries, delay_seconds=args.delay_seconds)
    args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    metrics = report["metrics"]
    print(
        "Clarification evaluation complete: "
        f"{metrics['scenario_count']} scenarios; "
        f"trigger accuracy={percent(metrics['clarification_trigger_accuracy'])}; "
        f"final status accuracy={percent(metrics['final_status_accuracy'])}; "
        f"overall={percent(metrics['overall_accuracy'])}"
    )
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.md_output}")


if __name__ == "__main__":
    main()
