from __future__ import annotations

import argparse
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Any

from pydantic import ValidationError

import complaint_drafter as drafter
from config import BASE_DIR

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_CASE_PATH = EVAL_DIR / "bank_fraud_complaint_cases.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "bank_fraud_complaint_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "bank_fraud_complaint_evaluation.md"


def load_cases(path: Path = DEFAULT_CASE_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")).get("cases", [])


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    result: dict[str, Any] = {
        "id": case["id"],
        "group": case.get("group", "uncategorized"),
        "description": case.get("description"),
        "expected_outcome": case["expected_outcome"],
    }

    try:
        intake = drafter.BankFraudComplaintIntake(**case["intake"])
    except ValidationError as exc:
        message = "; ".join(error.get("msg", "") for error in exc.errors())
        result["actual_outcome"] = "fail"
        result["failure_message"] = message
        if case["expected_outcome"] == "fail":
            expected_substring = case.get("expected_failure_message_contains", "")
            result["failure_message_matches_expected"] = expected_substring in message
            result["correct"] = result["failure_message_matches_expected"]
        else:
            result["failure_message_matches_expected"] = None
            result["correct"] = False
        result["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return result

    if case["expected_outcome"] == "fail":
        result["actual_outcome"] = "pass"
        result["failure_message"] = None
        result["failure_message_matches_expected"] = False
        result["correct"] = False
        result["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return result

    tier_correct = True
    if "expected_liability_tier" in case:
        tier_correct = intake.liability_tier == case["expected_liability_tier"]
    elapsed_correct = True
    if "expected_elapsed_days" in case:
        elapsed_correct = intake.elapsed_days_to_report == case["expected_elapsed_days"]

    try:
        draft_result = drafter.assemble_bank_fraud_complaint_draft(intake)
    except drafter.ComplaintDraftError as exc:
        result["actual_outcome"] = "assembly_error"
        result["failure_message"] = str(exc)
        result["correct"] = False
        result["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return result

    expected_citation = case.get("expected_citation") or {}
    citation_used = draft_result.citation_used
    citation_correct = all(citation_used.get(key) == value for key, value in expected_citation.items())

    expected_additional_section_cites = sorted(case.get("expected_additional_section_cites") or [])
    actual_additional_section_cites = sorted(item["section_cite"] for item in draft_result.additional_citations)
    additional_citations_correct = actual_additional_section_cites == expected_additional_section_cites

    all_citations = [citation_used, *draft_result.additional_citations]
    all_resolved = all(drafter.resolve_citation_against_corpus(item) for item in all_citations)

    result["actual_outcome"] = "pass"
    result["failure_message"] = None
    result["expected_liability_tier"] = case.get("expected_liability_tier")
    result["actual_liability_tier"] = intake.liability_tier
    result["tier_correct"] = tier_correct
    result["expected_elapsed_days"] = case.get("expected_elapsed_days")
    result["actual_elapsed_days"] = intake.elapsed_days_to_report
    result["elapsed_correct"] = elapsed_correct
    result["expected_citation"] = expected_citation
    result["actual_citation"] = citation_used
    result["citation_correct"] = citation_correct
    result["expected_additional_section_cites"] = expected_additional_section_cites
    result["actual_additional_section_cites"] = actual_additional_section_cites
    result["additional_citations_correct"] = additional_citations_correct
    result["citation_resolved_against_corpus"] = all_resolved
    result["docx_bytes_generated"] = len(draft_result.docx_bytes)
    result["correct"] = (
        tier_correct and elapsed_correct and citation_correct and additional_citations_correct and all_resolved
    )
    result["latency_ms"] = int((time.perf_counter() - started) * 1000)
    return result


def pct(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 3) if denominator else 0.0


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(results)
    pass_cases = [item for item in results if item["expected_outcome"] == "pass"]
    fail_cases = [item for item in results if item["expected_outcome"] == "fail"]
    return {
        "case_count": count,
        "overall_accuracy": pct(sum(1 for item in results if item["correct"]), count),
        "pass_case_count": len(pass_cases),
        "pass_case_accuracy": pct(sum(1 for item in pass_cases if item["correct"]), len(pass_cases)),
        "liability_tier_accuracy": pct(sum(1 for item in pass_cases if item.get("tier_correct")), len(pass_cases)),
        "citation_accuracy": pct(sum(1 for item in pass_cases if item.get("citation_correct")), len(pass_cases)),
        "additional_citation_accuracy": pct(sum(1 for item in pass_cases if item.get("additional_citations_correct")), len(pass_cases)),
        "citation_corpus_resolution_rate": pct(sum(1 for item in pass_cases if item.get("citation_resolved_against_corpus")), len(pass_cases)),
        "fail_case_count": len(fail_cases),
        "fail_case_accuracy": pct(sum(1 for item in fail_cases if item["correct"]), len(fail_cases)),
        "hard_fail_message_match_rate": pct(
            sum(1 for item in fail_cases if item.get("failure_message_matches_expected")), len(fail_cases)
        ),
    }


def group_breakdown(results: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for result in results:
        grouped[result["group"]].append(result)
    return {group: aggregate(items) for group, items in sorted(grouped.items())}


def evaluate_bank_fraud_complaint(path: Path = DEFAULT_CASE_PATH) -> dict[str, Any]:
    cases = load_cases(path)
    results = [evaluate_case(case) for case in cases]
    latencies = [item["latency_ms"] for item in results]
    return {
        "evaluation_config": {
            "case_file": path.as_posix(),
            "scenario": "bank_fraud_complaint",
            "act": "RBI Limiting Liability Directions, 2017 + IT Act, 2000 Section 66D",
            "llm_calls": 0,
            "note": "Slot-fill drafting pipeline only -- no LLM call is part of this path.",
        },
        "dataset_summary": {
            "total_cases": len(cases),
            "account_categories_covered": sorted({a.value for a in drafter.AccountCategory}),
            "liability_tiers_covered": sorted(
                {item["expected_liability_tier"] for item in cases if "expected_liability_tier" in item}
            ),
        },
        "overall_metrics": aggregate(results),
        "group_breakdown": group_breakdown(results),
        "latency": {
            "cases": len(results),
            "average_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
            "max_latency_ms": max(latencies) if latencies else None,
        },
        "results": results,
        "failures": [item for item in results if not item["correct"]],
    }


def percent(value: float | None) -> str:
    if value is None:
        return "not measured"
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["overall_metrics"]
    groups = report["group_breakdown"]
    lines = [
        "# Complaint Drafter Evaluation (Bank Fraud Complaint, RBI Limiting Liability Directions 2017 + IT Act Section 66D)",
        "",
        "## Overall Results",
        f"- Total cases: {report['dataset_summary']['total_cases']}",
        f"- Account categories covered: {', '.join(report['dataset_summary']['account_categories_covered'])}",
        f"- Liability tiers covered: {', '.join(report['dataset_summary']['liability_tiers_covered'])}",
        f"- Overall accuracy: {percent(metrics['overall_accuracy'])}",
        f"- Pass-case accuracy: {percent(metrics['pass_case_accuracy'])} ({metrics['pass_case_count']} cases)",
        f"- Liability-tier computation accuracy: {percent(metrics['liability_tier_accuracy'])}",
        f"- Citation accuracy: {percent(metrics['citation_accuracy'])}",
        f"- Additional-citation (cap + IT Act) accuracy: {percent(metrics['additional_citation_accuracy'])}",
        f"- Citation corpus-resolution rate: {percent(metrics['citation_corpus_resolution_rate'])}",
        f"- Fail-case (hard validator) accuracy: {percent(metrics['fail_case_accuracy'])} ({metrics['fail_case_count']} cases)",
        f"- Hard-fail message match rate: {percent(metrics['hard_fail_message_match_rate'])}",
        "",
        "## Group Breakdown",
    ]
    for group_name, group_metrics in groups.items():
        lines.append(f"- `{group_name}`: overall accuracy {percent(group_metrics['overall_accuracy'])} ({group_metrics['case_count']} cases)")
    lines.extend(["", "## Failures"])
    if not report["failures"]:
        lines.append("- No failures under the current case labels.")
    for item in report["failures"]:
        lines.append(
            f"- `{item['id']}`: expected `{item['expected_outcome']}`, got `{item['actual_outcome']}` "
            f"({item.get('failure_message') or 'see result details'})"
        )
    lines.extend(
        [
            "",
            "## Scope And Known Limitations",
            "- elapsed_days_to_report is calculated on a calendar-day basis, approximating the "
            "RBI circular's 'working days' standard -- a bank holiday inside the window would "
            "shift the true tier boundary by one or more days. The rendered clause text says so "
            "explicitly.",
            "- Does not draft a separate FIR / National Cybercrime Reporting Portal complaint; "
            "Section 66D of the IT Act is cited as an always-present additional citation pointing "
            "the complainant to that separate channel, not drafted as its own document.",
            "",
            "## Recommendation",
            "- Re-run this eval whenever a clause file, citation mapping, or hard validator "
            "changes; treat any drop below 100% pass/fail accuracy as a regression.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Evaluate the bank fraud complaint drafter scenario.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args(argv)
    report = evaluate_bank_fraud_complaint(args.cases)
    write_reports(report, args.json_output, args.md_output)
    metrics = report["overall_metrics"]
    print(
        "Bank fraud complaint evaluation complete: "
        f"{report['dataset_summary']['total_cases']} cases; "
        f"overall accuracy={percent(metrics['overall_accuracy'])}; "
        f"pass-case accuracy={percent(metrics['pass_case_accuracy'])}; "
        f"fail-case accuracy={percent(metrics['fail_case_accuracy'])}"
    )
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.md_output}")
    return report


if __name__ == "__main__":
    main()
