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
DEFAULT_CASE_PATH = EVAL_DIR / "consumer_defective_goods_cases.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "consumer_defective_goods_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "consumer_defective_goods_evaluation.md"


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
        intake = drafter.ConsumerDefectiveGoodsIntake(**case["intake"])
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
    # + forum-tier + template-assembly pipeline (not a mock of it) and compare against expected.
    try:
        draft_result = drafter.assemble_consumer_defective_goods_draft(intake)
    except drafter.ComplaintDraftError as exc:
        result["actual_outcome"] = "assembly_error"
        result["failure_message"] = str(exc)
        result["correct"] = False
        result["latency_ms"] = int((time.perf_counter() - started) * 1000)
        return result

    expected_clause_file = case.get("expected_clause_file")
    actual_clause_file = drafter.GOODS_CLAUSE_FILE_BY_TYPE[intake.defect_or_deficiency_type]
    clause_selection_correct = actual_clause_file == expected_clause_file

    expected_citation = case.get("expected_citation") or {}
    citation_used = draft_result.citation_used
    citation_correct = all(citation_used.get(key) == value for key, value in expected_citation.items())

    expected_forum_tier = case.get("expected_forum_tier")
    forum_tier_correct = intake.forum_tier == expected_forum_tier

    all_citations = [draft_result.citation_used, *draft_result.additional_citations]
    all_citations_resolve = all(drafter.resolve_citation_against_corpus(item) for item in all_citations)

    result["actual_outcome"] = "pass"
    result["failure_message"] = None
    result["expected_clause_file"] = expected_clause_file
    result["actual_clause_file"] = actual_clause_file
    result["clause_selection_correct"] = clause_selection_correct
    result["expected_citation"] = expected_citation
    result["actual_citation"] = citation_used
    result["citation_correct"] = citation_correct
    result["expected_forum_tier"] = expected_forum_tier
    result["actual_forum_tier"] = intake.forum_tier
    result["forum_tier_correct"] = forum_tier_correct
    result["all_citations_resolved_against_corpus"] = all_citations_resolve
    result["docx_bytes_generated"] = len(draft_result.docx_bytes)
    result["correct"] = clause_selection_correct and citation_correct and forum_tier_correct and all_citations_resolve
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
        "forum_tier_accuracy": pct(sum(1 for item in pass_cases if item.get("forum_tier_correct")), len(pass_cases)),
        "citation_corpus_resolution_rate": pct(sum(1 for item in pass_cases if item.get("all_citations_resolved_against_corpus")), len(pass_cases)),
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


def evaluate_consumer_defective_goods(path: Path = DEFAULT_CASE_PATH) -> dict[str, Any]:
    cases = load_cases(path)
    results = [evaluate_case(case) for case in cases]
    latencies = [item["latency_ms"] for item in results]
    return {
        "evaluation_config": {
            "case_file": path.as_posix(),
            "scenario": "consumer_defective_goods",
            "act": "Consumer Protection Act, 2019",
            "llm_calls": 0,
            "note": "Slot-fill drafting pipeline only -- no LLM call is part of this path.",
        },
        "dataset_summary": {
            "total_cases": len(cases),
            "grounds_covered": sorted({ground.value for ground in drafter.DefectOrDeficiencyType}),
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
        "# Complaint Drafter Evaluation (Consumer Defective Goods / Deficient Service, Consumer Protection Act, 2019)",
        "",
        "## Overall Results",
        f"- Total cases: {report['dataset_summary']['total_cases']}",
        f"- Grounds covered: {', '.join(report['dataset_summary']['grounds_covered'])}",
        f"- Overall accuracy: {percent(metrics['overall_accuracy'])}",
        f"- Pass-case accuracy: {percent(metrics['pass_case_accuracy'])} ({metrics['pass_case_count']} cases)",
        f"- Clause-selection accuracy: {percent(metrics['clause_selection_accuracy'])}",
        f"- Citation accuracy: {percent(metrics['citation_accuracy'])}",
        f"- Forum-tier accuracy: {percent(metrics['forum_tier_accuracy'])}",
        f"- Citation corpus-resolution rate: {percent(metrics['citation_corpus_resolution_rate'])}",
        f"- Fail-case (hard validator) accuracy: {percent(metrics['fail_case_accuracy'])} ({metrics['fail_case_count']} cases)",
        f"- Hard-fail message match rate: {percent(metrics['hard_fail_message_match_rate'])}",
        "",
        "## Valid Drafts Per Ground",
    ]
    for item in report["results"]:
        if item["group"] == "valid_per_ground":
            lines.append(
                f"- `{item['id']}` -> clause `{item.get('actual_clause_file')}`, "
                f"citation `{item.get('actual_citation', {}).get('section_cite')}`, "
                f"forum_tier `{item.get('actual_forum_tier')}`, "
                f"all_citations_resolved={item.get('all_citations_resolved_against_corpus')}"
            )
    lines.extend(["", "## Forum-Tier Boundary (Sections 34/47/58, read with the 2021 Jurisdiction Rules)"])
    boundary_note = (
        "District Commission jurisdiction 'does not exceed' Rs. 50 lakh (Rule 3); State 'exceeds "
        "fifty lakh but does not exceed two crore' (Rule 4); National 'exceeds two crore' (Rule 5). "
        "Based on amount_paid alone (the Act's own phrase is 'value of goods or services paid as "
        "consideration' -- it does not mention compensation claimed)."
    )
    lines.append(f"- {boundary_note}")
    for item in report["results"]:
        if item["group"] == "forum_tier_boundary":
            lines.append(
                f"- `{item['id']}` expected tier `{item.get('expected_forum_tier')}` -> got "
                f"`{item.get('actual_forum_tier')}`"
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
            "- Citation resolution checks source_file + section_number/rule_number presence in the corpus "
            "rag.py loads, not clause-letter-level textual entailment -- it confirms Section 2 (or the "
            "relevant Rule) exists in the corpus, not that the specific sub-clause (10)/(11)/(43)/(47) "
            "appears verbatim (verified manually at authoring time; see complaint_drafter.py's "
            "GOODS_CLAUSE_CITATIONS comments).",
            "- short_delivery cites the same Section 2(10) as defective_goods (a different prong of the "
            "same defined term -- 'quantity' vs 'quality/potency/purity/standard'); the corpus-resolution "
            "check cannot distinguish prongs within one section, only that the section exists.",
            "",
            "## Recommendation",
            "- Re-run this eval whenever a clause file, citation mapping, forum-tier threshold, or hard "
            "validator changes; treat any drop below 100% pass/fail accuracy as a regression, since every "
            "case here encodes a specific, manually verified legal fact rather than a fuzzy quality judgment.",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Evaluate the consumer defective-goods complaint drafter scenario.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args(argv)
    report = evaluate_consumer_defective_goods(args.cases)
    write_reports(report, args.json_output, args.md_output)
    metrics = report["overall_metrics"]
    print(
        "Consumer defective-goods evaluation complete: "
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
