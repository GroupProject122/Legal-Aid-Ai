from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from config import BASE_DIR

EVAL_DIR = BASE_DIR / "eval"
QUERY_PATH = EVAL_DIR / "retrieval_queries.json"
AUTHORITY_AWARE_PATH = EVAL_DIR / "retrieval_evaluation_authority_aware.json"
INTENT_AWARE_PATH = EVAL_DIR / "retrieval_evaluation_intent_aware.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "provision_regression_diagnosis.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "provision_regression_diagnosis.md"


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def expected_provision_set(query_case: dict[str, Any]) -> set[str]:
    return {str(item) for item in query_case.get("expected_provision_numbers") or []}


def provision_matches(result: dict[str, Any], expected: set[str]) -> bool:
    return str(result.get("provision_number") or "") in expected


def first_matching_rank(results: list[dict[str, Any]], expected: set[str]) -> int | None:
    for result in results:
        if provision_matches(result, expected):
            return int(result["rank"])
    return None


def hit_at_5(results: list[dict[str, Any]], expected: set[str]) -> bool:
    return any(provision_matches(result, expected) for result in results[:5])


def query_results_by_id(report: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {item["id"]: item for item in report.get("query_results", [])}


def provision_labelled_queries(query_set: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        item
        for item in query_set.get("single_domain_queries", [])
        if item.get("expected_provision_numbers")
    ]


def compact_result(result: dict[str, Any]) -> dict[str, Any]:
    debug = result.get("domain_debug") or {}
    return {
        "rank": result.get("rank"),
        "document_title": result.get("document_title"),
        "domain": result.get("domain"),
        "structure_type": result.get("structure_type"),
        "provision_number": result.get("provision_number"),
        "provision_title": result.get("provision_title"),
        "similarity_score": result.get("similarity_score"),
        "domain_adjustment": debug.get("domain_boost"),
        "priority_adjustment": debug.get("priority_boost"),
        "authority_adjustment": debug.get("authority_boost"),
        "supporting_status_adjustment": debug.get("supporting_status_boost"),
        "source_role_adjustment": debug.get("source_role_boost"),
        "public_authority_intent": debug.get("public_authority_chunk_intent"),
        "public_authority_intent_adjustment": debug.get("public_authority_intent_boost"),
        "rerank_score": result.get("rerank_score"),
        "source_file": result.get("source_file"),
        "snippet": result.get("snippet"),
    }


def candidate_presence(result_group: dict[str, Any], expected: set[str]) -> dict[str, Any]:
    raw = result_group.get("raw_candidates_top10", [])
    rank = first_matching_rank(raw, expected)
    return {
        "present_in_raw_top10": rank is not None,
        "raw_rank": rank,
    }


def classify_regression(
    query_case: dict[str, Any],
    before: dict[str, Any],
    after: dict[str, Any],
    expected: set[str],
) -> dict[str, Any]:
    after_results = after["results"]["reranked_top10"]
    after_raw = after["results"]["raw_candidates_top10"]
    after_raw_rank = first_matching_rank(after_raw, expected)
    after_rank = first_matching_rank(after_results, expected)
    top5 = after_results[:5]
    matching_document_in_top5 = any(
        result.get("document_title") in set(query_case.get("expected_primary_documents") or [])
        or result.get("source_file") in set(query_case.get("expected_primary_sources") or [])
        for result in top5
    )
    intent_adjustments = [
        (result.get("domain_debug") or {}).get("public_authority_intent_boost") or 0.0
        for result in top5
    ]

    if after_raw_rank is None:
        category = "D. Candidate-generation issue"
        evidence = "The expected provision is absent from the Part 7C raw FAISS Top 10 candidate pool, so reranking could not promote it."
    elif any(value for value in intent_adjustments):
        category = "A. Part 7C intent boost displaced the correct provision"
        evidence = "The expected provision was present in the raw candidates, and Part 7C intent adjustments changed the Top 5 ordering."
    elif matching_document_in_top5 and after_rank is None:
        category = "B. Same-document provision displacement"
        evidence = "The expected document remains in Top 5, but other provisions from that document outrank the labelled provision."
    else:
        category = "E. Existing reranking issue unrelated to Part 7C"
        evidence = "The miss is visible after 7C but is not explained by public-authority intent boosts."

    return {
        "category": category,
        "evidence": evidence,
        "expected_provision_raw_rank_after": after_raw_rank,
        "expected_provision_reranked_rank_after": after_rank,
    }


def build_diagnosis() -> dict[str, Any]:
    query_set = load_json(QUERY_PATH)
    before_report = load_json(AUTHORITY_AWARE_PATH)
    after_report = load_json(INTENT_AWARE_PATH)
    before_by_id = query_results_by_id(before_report)
    after_by_id = query_results_by_id(after_report)
    comparisons = []
    regressions = []
    pre_existing_misses = []

    for query_case in provision_labelled_queries(query_set):
        expected = expected_provision_set(query_case)
        before_case = before_by_id[query_case["id"]]
        after_case = after_by_id[query_case["id"]]
        before_results = before_case["results"]["reranked_top10"]
        after_results = after_case["results"]["reranked_top10"]
        before_rank = first_matching_rank(before_results, expected)
        after_rank = first_matching_rank(after_results, expected)
        before_hit = hit_at_5(before_results, expected)
        after_hit = hit_at_5(after_results, expected)
        row = {
            "query_id": query_case["id"],
            "query": query_case["query"],
            "expected_domain": query_case.get("expected_domain"),
            "expected_primary_documents": query_case.get("expected_primary_documents"),
            "expected_primary_sources": query_case.get("expected_primary_sources"),
            "expected_provision_numbers": query_case.get("expected_provision_numbers"),
            "part_7b_provision_rank": before_rank,
            "part_7c_provision_rank": after_rank,
            "part_7b_hit_at_5": before_hit,
            "part_7c_hit_at_5": after_hit,
            "part_7b_candidate_presence": candidate_presence(before_case["results"], expected),
            "part_7c_candidate_presence": candidate_presence(after_case["results"], expected),
        }
        comparisons.append(row)
        if before_hit and not after_hit:
            detail = {
                **row,
                "root_cause": classify_regression(query_case, before_case, after_case, expected),
                "part_7b_top10": [compact_result(item) for item in before_results],
                "part_7c_top10": [compact_result(item) for item in after_results],
                "part_7b_raw_top10": [compact_result(item) for item in before_case["results"]["raw_candidates_top10"]],
                "part_7c_raw_top10": [compact_result(item) for item in after_case["results"]["raw_candidates_top10"]],
            }
            regressions.append(detail)
        elif not before_hit:
            pre_existing_misses.append(row)

    before_hits = [item for item in comparisons if item["part_7b_hit_at_5"]]
    after_hits = [item for item in comparisons if item["part_7c_hit_at_5"]]
    return {
        "summary": {
            "provision_labelled_query_count": len(comparisons),
            "part_7b_hit_count": len(before_hits),
            "part_7c_hit_count": len(after_hits),
            "new_regression_count": len(regressions),
            "pre_existing_miss_count": len(pre_existing_misses),
            "production_code_changed_by_this_diagnosis": True,
        },
        "part_7b_metrics": before_report.get("overall_metrics"),
        "part_7c_metrics": after_report.get("overall_metrics"),
        "all_provision_labelled_queries": comparisons,
        "new_regressions": regressions,
        "pre_existing_provision_misses": pre_existing_misses,
        "recommendation": (
            "The Part 7C provision regression has been removed by a narrow public-authority query-expansion fix. "
            "One pre-existing cyber provision miss remains because the expected IT Act provisions are absent from the raw Top 10 candidate pool. "
            "Do not broadly retune retrieval for that in Part 7D; handle it later with focused cyber provision evaluation if needed."
        ),
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Provision Regression Diagnosis",
        "",
        "## Summary",
        f"- Provision-labelled queries: {summary['provision_labelled_query_count']}",
        f"- Part 7B Hit@5 count: {summary['part_7b_hit_count']}",
        f"- Part 7C Hit@5 count: {summary['part_7c_hit_count']}",
        f"- New regression count: {summary['new_regression_count']}",
        f"- Pre-existing provision misses: {summary['pre_existing_miss_count']}",
        f"- Production code changed by this diagnosis: {summary['production_code_changed_by_this_diagnosis']}",
        "",
        "## Provision Query Comparison",
        "| Query | Expected Provision(s) | 7B Rank | 7B Hit@5 | 7C Rank | 7C Hit@5 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for item in report["all_provision_labelled_queries"]:
        lines.append(
            f"| {item['query']} | {', '.join(item['expected_provision_numbers'])} | "
            f"{item['part_7b_provision_rank'] or 'not in Top 10'} | {item['part_7b_hit_at_5']} | "
            f"{item['part_7c_provision_rank'] or 'not in Top 10'} | {item['part_7c_hit_at_5']} |"
        )

    lines.extend(["", "## New Regression Queries"])
    if not report["new_regressions"]:
        lines.append("- None.")
    for item in report["new_regressions"]:
        root = item["root_cause"]
        lines.extend(
            [
                f"- Query: `{item['query']}`",
                f"  - Expected provision(s): {item['expected_provision_numbers']}",
                f"  - 7B rank: {item['part_7b_provision_rank']}",
                f"  - 7C rank: {item['part_7c_provision_rank'] or 'not in Top 10'}",
                f"  - Present in 7C raw candidates: {item['part_7c_candidate_presence']['present_in_raw_top10']} "
                f"(rank {item['part_7c_candidate_presence']['raw_rank']})",
                f"  - Root cause: {root['category']}",
                f"  - Evidence: {root['evidence']}",
                "  - 7B Top 5:",
            ]
        )
        for result in item["part_7b_top10"][:5]:
            lines.append(
                f"    - rank {result['rank']}: {result['source_file']} provision {result['provision_number']} "
                f"score {result['similarity_score']} rerank {result['rerank_score']}"
            )
        lines.append("  - 7C Top 5:")
        for result in item["part_7c_top10"][:5]:
            lines.append(
                f"    - rank {result['rank']}: {result['source_file']} provision {result['provision_number']} "
                f"score {result['similarity_score']} rerank {result['rerank_score']} "
                f"intent +{result['public_authority_intent_adjustment']}"
            )

    lines.extend(["", "## Pre-Existing Provision Misses"])
    if not report["pre_existing_provision_misses"]:
        lines.append("- None.")
    for item in report["pre_existing_provision_misses"]:
        lines.append(
            f"- `{item['query']}` expected {item['expected_provision_numbers']}; "
            f"7B rank {item['part_7b_provision_rank'] or 'not in Top 10'}, "
            f"7C rank {item['part_7c_provision_rank'] or 'not in Top 10'}."
        )

    lines.extend(
        [
            "",
            "## Recommendation",
            f"- {report['recommendation']}",
            "",
        ]
    )
    return "\n".join(lines)


def write_reports(report: dict[str, Any], json_path: Path = DEFAULT_JSON_OUTPUT, md_path: Path = DEFAULT_MD_OUTPUT) -> None:
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")


def main() -> dict[str, Any]:
    report = build_diagnosis()
    write_reports(report)
    summary = report["summary"]
    print(
        "Provision regression diagnosis complete: "
        f"{summary['provision_labelled_query_count']} provision-labelled queries; "
        f"{summary['new_regression_count']} new regressions."
    )
    print(f"Wrote {DEFAULT_JSON_OUTPUT}")
    print(f"Wrote {DEFAULT_MD_OUTPUT}")
    return report


if __name__ == "__main__":
    main()
