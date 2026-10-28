from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

import scam_checker
from config import BASE_DIR, GEMINI_MODEL

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_CASE_PATH = EVAL_DIR / "scam_check_cases.json"


def output_paths(mode: str, tag: str = "") -> tuple[Path, Path]:
    stem = EVAL_DIR / f"scam_check_evaluation_{mode}{'_' + tag if tag else ''}"
    return stem.with_suffix(".json"), stem.with_suffix(".md")


def load_cases(path: Path = DEFAULT_CASE_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))["cases"]


def pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def evaluate_case(case: dict[str, Any], result: scam_checker.ScamCheckResult) -> dict[str, Any]:
    flagged = result.verdict in (scam_checker.VERDICT_HIGH_RISK, scam_checker.VERDICT_WARNING)
    evaluation = {
        "flagged": flagged,
        "high_risk": result.verdict == scam_checker.VERDICT_HIGH_RISK,
    }
    if case["label"] == "scam":
        evaluation["type_correct"] = result.scam_type == case.get("expected_type")
    return evaluation


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    scams = [item for item in results if item["label"] == "scam"]
    genuine = [item for item in results if item["label"] == "genuine"]
    return {
        "scam_count": len(scams),
        "genuine_count": len(genuine),
        "scam_recall": pct(sum(item["evaluation"]["flagged"] for item in scams), len(scams)),
        "scam_high_risk_rate": pct(sum(item["evaluation"]["high_risk"] for item in scams), len(scams)),
        "scam_type_accuracy": pct(sum(item["evaluation"]["type_correct"] for item in scams), len(scams)),
        "false_alarm_rate_high_risk": pct(sum(item["evaluation"]["high_risk"] for item in genuine), len(genuine)),
        "genuine_any_warning_rate": pct(sum(item["evaluation"]["flagged"] for item in genuine), len(genuine)),
    }


def per_type(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        if item["label"] == "scam":
            grouped[item["expected_type"]].append(item)
    return {
        scam_type: {
            "count": len(items),
            "flagged": sum(item["evaluation"]["flagged"] for item in items),
            "high_risk": sum(item["evaluation"]["high_risk"] for item in items),
            "type_correct": sum(item["evaluation"]["type_correct"] for item in items),
        }
        for scam_type, items in sorted(grouped.items())
    }


def per_language(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in results:
        grouped[item["language"]].append(item)
    return {language: aggregate(items) for language, items in sorted(grouped.items())}


def evaluate(case_path: Path = DEFAULT_CASE_PATH, use_ai: bool = False, delay_seconds: float = 0.0) -> dict[str, Any]:
    cases = load_cases(case_path)
    results = []
    ai_unavailable = 0
    for index, case in enumerate(cases):
        if use_ai and index and delay_seconds > 0:
            time.sleep(delay_seconds)
        result = scam_checker.check_message(case["message"], use_ai=use_ai)
        if result.ai_check == "unavailable":
            ai_unavailable += 1
        results.append(
            {
                "id": case["id"],
                "label": case["label"],
                "language": case["language"],
                "expected_type": case.get("expected_type"),
                "verdict": result.verdict,
                "scam_type": result.scam_type,
                "signs": [sign.rule_id for sign in result.signs_found],
                "ai_check": result.ai_check,
                "evaluation": evaluate_case(case, result),
            }
        )
    return {
        "evaluation_config": {
            "case_file": case_path.as_posix(),
            "mode": "with_gemini" if use_ai else "rules_only",
            "gemini_model": GEMINI_MODEL if use_ai else None,
            "gemini_calls": len(cases) if use_ai else 0,
            "gemini_unavailable_calls": ai_unavailable,
            "delay_seconds_between_calls": delay_seconds,
            "note": "Message text is deliberately not copied into this report; see the case file by id.",
        },
        "metrics": aggregate(results),
        "per_type": per_type(results),
        "per_language": per_language(results),
        "results": results,
    }


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    config = report["evaluation_config"]
    metrics = report["metrics"]
    lines = [
        f"# Scam Message Checker Evaluation ({config['mode']})",
        "",
        f"- Cases: {metrics['scam_count']} scam, {metrics['genuine_count']} genuine",
        f"- Gemini model: {config['gemini_model'] or 'not used'}",
        f"- Gemini calls unavailable: {config['gemini_unavailable_calls']}",
        "",
        "## Headline metrics",
        "",
        "| Metric | Value |",
        "|---|---|",
        f"| Scam recall (high_risk or warning_signs) | {percent(metrics['scam_recall'])} |",
        f"| Scams flagged high_risk | {percent(metrics['scam_high_risk_rate'])} |",
        f"| Scam type accuracy | {percent(metrics['scam_type_accuracy'])} |",
        f"| False-alarm rate (genuine flagged high_risk) | {percent(metrics['false_alarm_rate_high_risk'])} |",
        f"| Genuine messages with any warning | {percent(metrics['genuine_any_warning_rate'])} |",
        "",
        "## Per scam type",
        "",
        "| Expected type | Cases | Flagged | High risk | Type correct |",
        "|---|---|---|---|---|",
    ]
    for scam_type, row in report["per_type"].items():
        lines.append(f"| {scam_type} | {row['count']} | {row['flagged']} | {row['high_risk']} | {row['type_correct']} |")
    lines.extend(["", "## Per language", "", "| Language | Scam recall | False alarms (high_risk) | Genuine with any warning |", "|---|---|---|---|"])
    for language, row in report["per_language"].items():
        lines.append(
            f"| {language} | {percent(row['scam_recall'])} | {percent(row['false_alarm_rate_high_risk'])} | {percent(row['genuine_any_warning_rate'])} |"
        )
    lines.extend(["", "## Misses and false warnings", ""])
    problems = [
        item for item in report["results"]
        if (item["label"] == "scam" and not item["evaluation"]["flagged"])
        or (item["label"] == "genuine" and item["evaluation"]["flagged"])
        or (item["label"] == "scam" and not item["evaluation"]["type_correct"])
    ]
    if not problems:
        lines.append("- None.")
    for item in problems:
        expected = item["expected_type"] or "genuine"
        lines.append(f"- `{item['id']}`: expected {expected}, got `{item['verdict']}` / `{item['scam_type']}` signs={item['signs']}")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate the Scam Message Checker.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--with-gemini", action="store_true", help="Also make the Gemini call (default: rules only).")
    parser.add_argument("--delay", type=float, default=0.0, help="Seconds between Gemini calls.")
    parser.add_argument("--tag", default="", help="Suffix for the report file names, e.g. 'heldout'.")
    args = parser.parse_args()

    report = evaluate(args.cases, use_ai=args.with_gemini, delay_seconds=args.delay)
    json_path, md_path = output_paths(report["evaluation_config"]["mode"], args.tag)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))
    print(f"Saved {json_path} and {md_path}")


if __name__ == "__main__":
    main()
