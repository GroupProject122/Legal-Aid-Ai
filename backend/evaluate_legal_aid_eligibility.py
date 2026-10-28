from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path
from typing import Any

import legal_aid_eligibility as lae
from config import BASE_DIR

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_CASE_PATH = EVAL_DIR / "legal_aid_eligibility_cases.json"
JSON_PATH = EVAL_DIR / "legal_aid_eligibility_evaluation.json"
MD_PATH = EVAL_DIR / "legal_aid_eligibility_evaluation.md"


def load_cases(path: Path = DEFAULT_CASE_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    result = lae.check_eligibility(case["answers"])
    rule_ids = [rule["rule_id"] for rule in result.matched_rules]
    evaluation = {"result_correct": result.result == case["expected_result"]}
    if "expected_rule_ids" in case:
        evaluation["rules_correct"] = rule_ids == case["expected_rule_ids"]
    if "expected_needs" in case:
        evaluation["needs_correct"] = result.needs == case["expected_needs"]
    if result.result == lae.RESULT_LIKELY_NOT_ELIGIBLE:
        evaluation["alternatives_listed"] = bool(result.alternatives)
    evaluation["passed"] = all(evaluation.values())
    return {
        "id": case["id"],
        "group": case["group"],
        "expected_result": case["expected_result"],
        "result": result.result,
        "expected_rule_ids": case.get("expected_rule_ids"),
        "rule_ids": rule_ids,
        "needs": result.needs,
        "evaluation": evaluation,
    }


def per_group(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        grouped[item["group"]].append(item)
    return {
        group: {"count": len(items), "passed": sum(item["evaluation"]["passed"] for item in items)}
        for group, items in grouped.items()
    }


def evaluate(case_path: Path = DEFAULT_CASE_PATH) -> dict[str, Any]:
    results = [evaluate_case(case) for case in load_cases(case_path)]
    passed = sum(item["evaluation"]["passed"] for item in results)
    return {
        "evaluation_config": {
            "case_file": case_path.as_posix(),
            "mode": "rules_only",
            "llm_calls": 0,
            "limits_last_verified": lae.LAST_VERIFIED,
            "limits": {key: {"amount_inr": limit["amount_inr"], "comparison": limit["comparison"]} for key, limit in lae.LIMITS.items()},
        },
        "metrics": {
            "case_count": len(results),
            "passed": passed,
            "pass_rate": pct(passed, len(results)),
            "result_accuracy": pct(sum(item["evaluation"]["result_correct"] for item in results), len(results)),
        },
        "per_group": per_group(results),
        "results": results,
    }


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    config = report["evaluation_config"]
    metrics = report["metrics"]
    lines = [
        "# Free Legal Aid Eligibility Checker Evaluation (rules only)",
        "",
        f"- Cases: {metrics['case_count']}",
        f"- LLM calls: {config['llm_calls']}",
        f"- Limits last verified: {config['limits_last_verified']}",
        "",
        "## Headline metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Cases fully passed (result + rules + needs + alternatives) | {metrics['passed']}/{metrics['case_count']} ({percent(metrics['pass_rate'])}) |",
        f"| Result accuracy | {percent(metrics['result_accuracy'])} |",
        "",
        "## Limits used",
        "",
        "| Limit | Amount (INR) | Comparison |",
        "|---|---|---|",
    ]
    for key, limit in config["limits"].items():
        lines.append(f"| {key} | {limit['amount_inr']:,} | {limit['comparison']} |")
    lines.extend(["", "## Per group", "", "| Group | Cases | Passed |", "|---|---|---|"])
    for group, row in report["per_group"].items():
        lines.append(f"| {group} | {row['count']} | {row['passed']} |")
    lines.extend(["", "## Failures", ""])
    failures = [item for item in report["results"] if not item["evaluation"]["passed"]]
    if not failures:
        lines.append("- None.")
    for item in failures:
        lines.append(
            f"- `{item['id']}`: expected `{item['expected_result']}` {item['expected_rule_ids']}, "
            f"got `{item['result']}` {item['rule_ids']} needs={item['needs']}"
        )
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the Free Legal Aid Eligibility Checker.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASE_PATH)
    args = parser.parse_args()

    report = evaluate(args.cases)
    JSON_PATH.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    MD_PATH.write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))
    print(f"Saved {JSON_PATH} and {MD_PATH}")


if __name__ == "__main__":
    main()
