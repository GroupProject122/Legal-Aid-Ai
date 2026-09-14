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
DEFAULT_CASE_PATH = EVAL_DIR / "consumer_misleading_ads_cases.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "consumer_misleading_ads_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "consumer_misleading_ads_evaluation.md"


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
        intake = drafter.MisleadingAdvertisementIntake(**case["intake"])
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

    # Validation passed. If a failure was expected, this is a miss regardless of what happens next.
    if case["expected_outcome"] == "fail":
        result["actual_outcome"] = "pass"
        result["failure_message"] = None
        result["failure_message_matches_expected"] = False
        result["correct"] = False
        result["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return result

    # Validation passed as expected -- now run the actual clause-selection + citation-resolution
    # + template-assembly pipeline (not a mock of it) and compare against expected outcome.
    try:
        draft_result = drafter.assemble_misleading_advertisement_draft(intake)
    except drafter.ComplaintDraftError as exc:
        result["actual_outcome"] = "assembly_error"
        result["failure_message"] = str(exc)
        result["correct"] = False
        result["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return result

    expected_clause_file = case.get("expected_clause_file")
    actual_clause_file = drafter.ADS_CLAUSE_FILE_BY_TYPE[intake.claim_type]
    clause_selection_correct = actual_clause_file == expected_clause_file

    expected_citation = case.get("expected_citation") or {}
    citation_used = draft_result.citation_used
    citation_correct = all(citation_used.get(key) == value for key, value in expected_citation.items())

    expected_review = case.get("expected_citation_review_required")
    review_correct = draft_result.citation_review_required == expected_review

    result["actual_outcome"] = "pass"
    result["failure_message"] = None
    result["expected_clause_file"] = expected_clause_file
    result["actual_clause_file"] = actual_clause_file
    result["clause_selection_correct"] = clause_selection_correct
    result["expected_citation"] = expected_citation
    result["actual_citation"] = citation_used
    result["citation_correct"] = citation_correct
    result["citation_resolved_against_corpus"] = drafter.resolve_citation_against_corpus(citation_used)
    result["expected_citation_review_required"] = expected_review
    result["actual_citation_review_required"] = draft_result.citation_review_required
    result["citation_review_flag_correct"] = review_correct
    result["docx_bytes_generated"] = len(draft_result.docx_bytes)
    result["correct"] = (
        clause_selection_correct and citation_correct and result["citation_resolved_against_corpus"] and review_correct
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
        "clause_selection_accuracy": pct(sum(1 for item in pass_cases if item.get("clause_selection_correct")), len(pass_cases)),
        "citation_accuracy": pct(sum(1 for item in pass_cases if item.get("citation_correct")), len(pass_cases)),
        "citation_review_flag_accuracy": pct(sum(1 for item in pass_cases if item.get("citation_review_flag_correct")), len(pass_cases)),
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


def evaluate_consumer_misleading_ads(path: Path = DEFAULT_CASE_PATH) -> dict[str, Any]:
    cases = load_cases(path)
    results = [evaluate_case(case) for case in cases]
    latencies = [item["latency_ms"] for item in results]
    return {
        "evaluation_config": {
            "case_file": path.as_posix(),
            "scenario": "consumer_misleading_ads",
            "act": "Consumer Protection Act, 2019 (informed by the CCPA misleading-ads and dark-patterns guidelines)",
            "llm_calls": 0,
            "note": "Slot-fill drafting pipeline only -- no LLM call is part of this path.",
        },
        "dataset_summary": {
            "total_cases": len(cases),
            "claim_types_covered": sorted({claim_type.value for claim_type in drafter.AdvertisementClaimType}),
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
        "# Complaint Drafter Evaluation (Misleading Advertisement / Dark Patterns, Consumer Protection Act, 2019)",
        "",
        "## Overall Results",
        f"- Total cases: {report['dataset_summary']['total_cases']}",
        f"- Claim types covered: {', '.join(report['dataset_summary']['claim_types_covered'])}",
        f"- Overall accuracy: {percent(metrics['overall_accuracy'])}",
        f"- Pass-case accuracy: {percent(metrics['pass_case_accuracy'])} ({metrics['pass_case_count']} cases)",
        f"- Clause-selection accuracy: {percent(metrics['clause_selection_accuracy'])}",
        f"- Citation accuracy: {percent(metrics['citation_accuracy'])}",
        f"- Citation review-flag accuracy: {percent(metrics['citation_review_flag_accuracy'])}",
        f"- Citation corpus-resolution rate: {percent(metrics['citation_corpus_resolution_rate'])}",
        f"- Fail-case (hard validator) accuracy: {percent(metrics['fail_case_accuracy'])} ({metrics['fail_case_count']} cases)",
        f"- Hard-fail message match rate: {percent(metrics['hard_fail_message_match_rate'])}",
        "",
        "## Valid Drafts Per Claim Type",
    ]
    for item in report["results"]:
        if item["group"] in ("valid_per_ground", "no_transaction_case"):
            lines.append(
                f"- `{item['id']}` -> clause `{item.get('actual_clause_file')}`, "
                f"citation `{item.get('actual_citation', {}).get('section_cite')}` "
                f"(authority_level={item.get('actual_citation', {}).get('authority_level')}), "
                f"review_required={item.get('actual_citation_review_required')}, "
                f"resolved_against_corpus={item.get('citation_resolved_against_corpus')}"
            )
    lines.extend(["", "## Dark-Pattern Citation Flag"])
    lines.append(
        "- dark_pattern_deceptive_design cites Guideline 4 (prohibition) + Guideline 2(e) (definition) of "
        "the Dark Patterns Guidelines, 2023 -- both exist in the corpus and the citation resolves -- but "
        "Guideline 2(e) itself defines a dark pattern as amounting to misleading advertisement OR unfair "
        "trade practice OR violation of consumer rights, an explicit either/or rather than one fixed Act "
        "provision. That is flagged citation_review_required=true (same mechanism, same reasoning, as "
        "tenancy's dropped unauthorized_construction ground), not silently asserted."
    )
    lines.extend(["", "## Hard Validator Cases"])
    for item in report["results"]:
        if item["group"] == "hard_validators":
            lines.append(
                f"- `{item['id']}` expected `{item['expected_outcome']}` -> got `{item['actual_outcome']}`"
                + (f"; message matched={item.get('failure_message_matches_expected')}" if item["expected_outcome"] == "fail" else "")
            )
    lines.extend(["", "## Group Breakdown"])
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
            "## Cost And Latency",
            f"- Cases run: {report['latency']['cases']}",
            f"- LLM calls: {report['evaluation_config']['llm_calls']} (no LLM is part of the drafting path)",
            f"- Average latency: {report['latency']['average_latency_ms']} ms",
            f"- Max latency: {report['latency']['max_latency_ms']} ms",
            "",
            "## Remaining Limitations",
            "- Citation resolution checks source_file + section_number/guideline_number presence in the "
            "corpus rag.py loads, not clause-letter-level textual entailment (same limitation as the other "
            "two scenarios; see complaint_drafter.py's ADS_CLAUSE_CITATIONS comments).",
            "- surrogate_advertisement and dark_pattern_deceptive_design cite CCPA guidelines "
            "(document_type=guidelines, authority_level=official_guidance), not the Act itself "
            "(document_type=statute, authority_level=primary) -- reflected in each citation's "
            "authority_level field and in the clause text, not asserted with statute-level confidence.",
            "",
            "## Recommendation",
            "- Re-run this eval whenever a clause file, citation mapping, or hard validator changes; treat "
            "any drop below 100% pass/fail accuracy as a regression, since every case here encodes a "
            "specific, manually verified legal fact rather than a fuzzy quality judgment.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Evaluate the misleading-advertisement complaint drafter scenario.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args(argv)
    report = evaluate_consumer_misleading_ads(args.cases)
    write_reports(report, args.json_output, args.md_output)
    metrics = report["overall_metrics"]
    print(
        "Consumer misleading-ads evaluation complete: "
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
