from __future__ import annotations

import argparse
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any

from config import BASE_DIR, GEMINI_MODEL
from domain_router import RouteDecision, route_issue

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_QUERY_PATH = EVAL_DIR / "domain_router_queries.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "domain_router_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "domain_router_evaluation.md"


def load_query_set(path: Path = DEFAULT_QUERY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def flatten_cases(query_set: dict[str, Any]) -> list[dict[str, Any]]:
    cases = []
    for group in (
        "single_domain_queries",
        "multi_domain_queries",
        "unclear_queries",
        "unsupported_queries",
        "out_of_scope_queries",
    ):
        for item in query_set.get(group, []):
            cases.append({**item, "group": group})
    return cases


def evaluate_case(case: dict[str, Any], decision: RouteDecision) -> dict[str, Any]:
    expected_status = case["expected_status"]
    expected_domains = set(case.get("expected_domains") or [])
    actual_domains = set(decision.domains)
    status_correct = decision.status == expected_status
    domain_exact = actual_domains == expected_domains if expected_domains else decision.domains == []
    domain_recall = (
        len(expected_domains & actual_domains) / len(expected_domains)
        if expected_domains
        else 1.0 if not decision.domains else 0.0
    )
    primary_correct = (
        decision.primary_domain == case.get("expected_primary_domain")
        if case.get("expected_primary_domain")
        else True
    )
    return {
        "status_correct": status_correct,
        "domain_exact_match": domain_exact,
        "domain_recall": round(domain_recall, 3),
        "primary_domain_correct": primary_correct,
        "correct": status_correct and (domain_exact if expected_status == "classified" else True) and primary_correct,
    }


def pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(results)
    return {
        "count": count,
        "status_accuracy": pct(sum(1 for item in results if item["evaluation"]["status_correct"]), count),
        "overall_accuracy": pct(sum(1 for item in results if item["evaluation"]["correct"]), count),
        "domain_exact_accuracy": pct(sum(1 for item in results if item["evaluation"]["domain_exact_match"]), count),
        "average_domain_recall": round(mean(item["evaluation"]["domain_recall"] for item in results), 3) if results else 0.0,
        "primary_domain_accuracy": pct(sum(1 for item in results if item["evaluation"]["primary_domain_correct"]), count),
    }


def group_breakdown(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[result["group"]].append(result)
    return {group: aggregate(items) for group, items in sorted(grouped.items())}


def status_confusion(results: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for item in results:
        counter[f"{item['expected_status']} -> {item['decision']['status']}"] += 1
    return dict(counter)


def evaluate_router(query_path: Path = DEFAULT_QUERY_PATH, delay_seconds: float = 0.0) -> dict[str, Any]:
    query_set = load_query_set(query_path)
    cases = flatten_cases(query_set)
    results = []
    failed_calls = 0
    latencies = []
    for index, case in enumerate(cases):
        if index and delay_seconds > 0:
            time.sleep(delay_seconds)
        decision = route_issue(case["query"])
        if decision.routing_error:
            failed_calls += 1
        if decision.latency_ms is not None:
            latencies.append(decision.latency_ms)
        evaluation = evaluate_case(case, decision)
        results.append(
            {
                **case,
                "decision": decision.to_dict(),
                "evaluation": evaluation,
            }
        )

    return {
        "evaluation_config": {
            "query_file": query_path.as_posix(),
            "gemini_model": GEMINI_MODEL,
            "router_gemini_calls": len(cases),
            "delay_seconds_between_calls": delay_seconds,
            "gemini_used_for_answer_generation": False,
        },
        "dataset_summary": {
            "total_queries": len(cases),
            "single_domain_queries": len(query_set.get("single_domain_queries", [])),
            "multi_domain_queries": len(query_set.get("multi_domain_queries", [])),
            "unclear_queries": len(query_set.get("unclear_queries", [])),
            "unsupported_queries": len(query_set.get("unsupported_queries", [])),
            "out_of_scope_queries": len(query_set.get("out_of_scope_queries", [])),
        },
        "overall_metrics": aggregate(results),
        "group_breakdown": group_breakdown(results),
        "status_confusion": status_confusion(results),
        "latency": {
            "calls": len(cases),
            "failed_or_fallback_calls": failed_calls,
            "average_latency_ms": round(mean(latencies), 1) if latencies else None,
            "min_latency_ms": min(latencies) if latencies else None,
            "max_latency_ms": max(latencies) if latencies else None,
        },
        "results": results,
        "failures": [item for item in results if not item["evaluation"]["correct"]],
    }


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["overall_metrics"]
    groups = report["group_breakdown"]
    failures = report["failures"][:12]
    lines = [
        "# Gemini Domain Router Evaluation",
        "",
        "## Overall Results",
        f"- Total queries: {report['dataset_summary']['total_queries']}",
        f"- Overall accuracy: {percent(metrics['overall_accuracy'])}",
        f"- Status accuracy: {percent(metrics['status_accuracy'])}",
        f"- Domain exact accuracy: {percent(metrics['domain_exact_accuracy'])}",
        f"- Average domain recall: {percent(metrics['average_domain_recall'])}",
        f"- Primary-domain accuracy: {percent(metrics['primary_domain_accuracy'])}",
        "",
        "## Supported Domain Classification",
    ]
    single = groups.get("single_domain_queries", {})
    lines.append(
        f"- Single-domain accuracy: {percent(single.get('overall_accuracy', 0.0))}; "
        f"primary-domain accuracy: {percent(single.get('primary_domain_accuracy', 0.0))}"
    )
    lines.extend(["", "## Multi-Domain Cases"])
    multi = groups.get("multi_domain_queries", {})
    lines.append(
        f"- Exact-match accuracy: {percent(multi.get('domain_exact_accuracy', 0.0))}; "
        f"average domain recall: {percent(multi.get('average_domain_recall', 0.0))}"
    )
    lines.extend(["", "## Unclear Cases"])
    unclear = groups.get("unclear_queries", {})
    lines.append(f"- Unclear detection accuracy: {percent(unclear.get('status_accuracy', 0.0))}")
    lines.extend(["", "## Unsupported Legal Cases"])
    unsupported = groups.get("unsupported_queries", {})
    lines.append(f"- Unsupported detection accuracy: {percent(unsupported.get('status_accuracy', 0.0))}")
    lines.extend(["", "## Out-of-Scope Cases"])
    out = groups.get("out_of_scope_queries", {})
    lines.append(f"- Out-of-scope detection accuracy: {percent(out.get('status_accuracy', 0.0))}")
    lines.extend(["", "## Hinglish Examples"])
    for item in report["results"]:
        if any(token in item["query"].lower() for token in ("nahi", "kaise", "mujhe", "mera", "kar", "gaya", "hai")):
            lines.append(
                f"- `{item['query']}` -> `{item['decision']['status']}` "
                f"{item['decision']['domains']}"
            )
        if len(lines) > 42:
            break
    lines.extend(["", "## Failure Examples"])
    if not failures:
        lines.append("- No failures under the current labels.")
    for item in failures:
        lines.append(
            f"- `{item['query']}` expected `{item['expected_status']}` {item.get('expected_domains') or []}; "
            f"got `{item['decision']['status']}` {item['decision']['domains']}"
        )
    lines.extend(
        [
            "",
            "## Cost And Latency",
            f"- Router Gemini calls: {report['latency']['calls']}",
            f"- Failed/fallback calls: {report['latency']['failed_or_fallback_calls']}",
            f"- Average routing latency: {report['latency']['average_latency_ms']} ms",
            "",
            "## Recommended Next Step",
            "- Part 8B should add clarification-question generation for `unclear` cases without changing retrieval ranking.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Evaluate Gemini domain router behavior.")
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERY_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    args = parser.parse_args(argv)
    report = evaluate_router(args.queries, delay_seconds=args.delay_seconds)
    write_reports(report, args.json_output, args.md_output)
    print(
        "Domain router evaluation complete: "
        f"{report['dataset_summary']['total_queries']} queries; "
        f"status accuracy={percent(report['overall_metrics']['status_accuracy'])}; "
        f"overall accuracy={percent(report['overall_metrics']['overall_accuracy'])}"
    )
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.md_output}")
    return report


if __name__ == "__main__":
    main()
