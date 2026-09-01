from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import claim_verifier
import rag
from config import BASE_DIR

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_CASE_PATH = EVAL_DIR / "manual_regression_cases.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "manual_regression_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "manual_regression_evaluation.md"


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")).get("cases", [])


def pct(count: int, total: int) -> float:
    return round(count / total, 3) if total else 0.0


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def provision_number(chunk: rag.RetrievedChunk) -> str:
    return str(chunk.section_number or chunk.rule_number or chunk.article_number or chunk.regulation_number or "")


def source_family(chunk: rag.RetrievedChunk) -> str:
    return (chunk.domain or (chunk.source or "").split("/", 1)[0] or "").lower()


def document_hit(chunks: list[rag.RetrievedChunk], expected: list[str]) -> bool:
    if not expected:
        return True
    titles = " ".join(chunk.document_title for chunk in chunks).lower()
    return any(item.lower() in titles for item in expected)


def provision_hit(chunks: list[rag.RetrievedChunk], expected: list[str]) -> bool:
    if not expected:
        return True
    provisions = {provision_number(chunk).lower() for chunk in chunks}
    return any(str(item).lower() in provisions for item in expected)


def product_liability_not_dominant(chunks: list[rag.RetrievedChunk], disfavored: list[str]) -> bool:
    if not disfavored:
        return True
    top_two = {provision_number(chunk) for chunk in chunks[:2]}
    return not top_two.issubset(set(disfavored))


def disfavored_provisions_absent(chunks: list[rag.RetrievedChunk], disfavored: list[str]) -> bool:
    if not disfavored:
        return True
    retrieved = {provision_number(chunk) for chunk in chunks}
    return retrieved.isdisjoint(set(disfavored))


def preferred_before_disfavored(chunks: list[rag.RetrievedChunk], expectations: dict[str, list[str]]) -> bool:
    if not expectations:
        return True
    ranks = {provision_number(chunk): index for index, chunk in enumerate(chunks, start=1)}
    for preferred, disfavored_values in expectations.items():
        preferred_rank = ranks.get(str(preferred))
        if preferred_rank is None:
            return False
        for disfavored in disfavored_values:
            disfavored_rank = ranks.get(str(disfavored))
            if disfavored_rank is not None and preferred_rank > disfavored_rank:
                return False
    return True


def source_family_coverage(chunks: list[rag.RetrievedChunk], expected: list[str]) -> bool:
    if not expected:
        return True
    families = {source_family(chunk) for chunk in chunks}
    return set(expected).issubset(families)


def evaluate_case(engine: rag.LegalRAG, case: dict[str, Any]) -> dict[str, Any]:
    query = case["query"]
    chunks = engine.retrieve(query)
    result = {
        "case_id": case["case_id"],
        "query": query,
        "retrieved": [
            {
                "rank": index,
                "document_title": chunk.document_title,
                "domain": chunk.domain,
                "provision": provision_number(chunk),
                "section_title": chunk.section_title or chunk.rule_title or chunk.article_title,
                "score": round(chunk.score, 4),
                "rerank_score": round(chunk.rerank_score, 4),
            }
            for index, chunk in enumerate(chunks, start=1)
        ],
    }
    result["document_hit"] = document_hit(chunks, case.get("expected_primary_documents", []))
    result["preferred_provision_hit"] = provision_hit(chunks, case.get("preferred_provisions", []))
    result["product_liability_not_dominant"] = product_liability_not_dominant(chunks, case.get("must_not_prioritize", []))
    result["disfavored_provisions_absent"] = disfavored_provisions_absent(chunks, case.get("must_not_surface_provisions", []))
    result["preferred_before_disfavored"] = preferred_before_disfavored(chunks, case.get("preferred_before_provisions", {}))
    result["source_family_coverage"] = source_family_coverage(chunks, case.get("expected_source_families", []))
    result["debug_language_clean"] = frontend_and_verifier_language_clean()
    result["empty_section_guard_present"] = frontend_empty_section_guard_present()
    result["category_sync_present"] = frontend_category_sync_present(case.get("expected_ui_category"))
    result["verifier_fallback_useful"] = verifier_fallback_keeps_traceable_claim() if case.get("verifier_fallback_should_remain_useful") else True
    result["correct"] = all(
        [
            result["document_hit"],
            result["preferred_provision_hit"],
            result["product_liability_not_dominant"],
            result["disfavored_provisions_absent"],
            result["preferred_before_disfavored"],
            result["source_family_coverage"],
            result["debug_language_clean"],
            result["empty_section_guard_present"],
            result["category_sync_present"],
            result["verifier_fallback_useful"],
        ]
    )
    return result


def frontend_and_verifier_language_clean() -> bool:
    verifier_text = Path("backend/claim_verifier.py").read_text(encoding="utf-8")
    return "The retrieved sources partly support this point" not in verifier_text and "Claim verification could not be completed right now" not in verifier_text


def frontend_empty_section_guard_present() -> bool:
    text = Path("src/App.jsx").read_text(encoding="utf-8")
    return "!clarificationQuestion && nextSteps.length > 0" in text and "!clarificationQuestion && sources.length > 0" in text


def frontend_category_sync_present(_expected: str | None) -> bool:
    text = Path("src/App.jsx").read_text(encoding="utf-8")
    return "displayCategoryFromRouting" in text and "setCategory(routedCategory)" in text


def verifier_fallback_keeps_traceable_claim() -> bool:
    response = {
        "answer": {
            "issue_summary": "RTI no reply.",
            "what_this_may_involve": ["Section 19 provides an appeal mechanism."],
            "possible_legal_position": [],
            "suggested_next_steps": [],
            "where_to_approach": [],
            "limitations": [],
        },
        "source_chunk_ids": ["rti_19"],
    }
    chunk = rag.RetrievedChunk(
        chunk_id="rti_19",
        text="Section 19. Appeal. Any person who does not receive a decision may prefer an appeal.",
        source="constitutional_public_authority/right_to_information_act_2005.pdf",
        document_title="The Right to Information Act, 2005",
        page=10,
        score=0.9,
        rerank_score=0.9,
        domain="constitutional_public_authority",
        section_number="19",
        section_title="Appeal",
    )
    original_key = claim_verifier.GEMINI_API_KEY
    try:
        claim_verifier.GEMINI_API_KEY = ""
        output = claim_verifier.verify_and_sanitize_response(response, [chunk])
    finally:
        claim_verifier.GEMINI_API_KEY = original_key
    return "Section 19 provides an appeal mechanism." in json.dumps(output.get("answer", {}))


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    return {
        "case_count": total,
        "overall_expected_behavior_rate": pct(sum(item["correct"] for item in results), total),
        "consumer_primary_framing_correctness": subset_rate(results, ("manual_01", "manual_08", "manual_13")),
        "consumer_no_harm_suppression": subset_rate(results, ("manual_13",), "disfavored_provisions_absent"),
        "cyber_identity_misuse_provision_hit": subset_rate(results, ("manual_03", "manual_04"), "preferred_provision_hit"),
        "multi_domain_source_coverage": subset_rate(results, ("manual_09", "manual_14"), "source_family_coverage"),
        "rti_no_response_priority": subset_rate(results, ("manual_15",), "preferred_before_disfavored"),
        "verifier_fallback_usefulness": pct(sum(item["verifier_fallback_useful"] for item in results), total),
        "empty_section_guard_rate": pct(sum(item["empty_section_guard_present"] for item in results), total),
        "category_sync_correctness": pct(sum(item["category_sync_present"] for item in results), total),
        "debug_language_leakage_rate": pct(sum(not item["debug_language_clean"] for item in results), total),
        "passed_cases": [item["case_id"] for item in results if item["correct"]],
        "failed_cases": [item["case_id"] for item in results if not item["correct"]],
    }


def subset_rate(results: list[dict[str, Any]], prefixes: tuple[str, ...], key: str = "correct") -> float:
    subset = [item for item in results if item["case_id"].startswith(prefixes)]
    return pct(sum(bool(item[key]) for item in subset), len(subset))


def evaluate(path: Path) -> dict[str, Any]:
    engine = rag.LegalRAG()
    engine.load()
    cases = load_cases(path)
    results = [evaluate_case(engine, case) for case in cases]
    return {
        "evaluation_config": {"case_file": path.as_posix(), "live_gemini_calls": 0},
        "metrics": aggregate(results),
        "results": results,
        "failures": [item for item in results if not item["correct"]],
    }


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Manual Regression Evaluation",
        "",
        "## Overall Results",
        f"- Cases: {metrics['case_count']}",
        f"- Overall expected-behavior rate: {percent(metrics['overall_expected_behavior_rate'])}",
        f"- Consumer primary framing correctness: {percent(metrics['consumer_primary_framing_correctness'])}",
        f"- Consumer no-harm product-liability suppression: {percent(metrics['consumer_no_harm_suppression'])}",
        f"- Cyber identity-misuse provision hit: {percent(metrics['cyber_identity_misuse_provision_hit'])}",
        f"- Multi-domain source coverage: {percent(metrics['multi_domain_source_coverage'])}",
        f"- RTI no-response Section 19 priority: {percent(metrics['rti_no_response_priority'])}",
        f"- Verifier fallback usefulness: {percent(metrics['verifier_fallback_usefulness'])}",
        f"- Empty-section guard rate: {percent(metrics['empty_section_guard_rate'])}",
        f"- Category sync correctness: {percent(metrics['category_sync_correctness'])}",
        f"- Debug-language leakage rate: {percent(metrics['debug_language_leakage_rate'])}",
        "",
        "## Case Results",
    ]
    for item in report["results"]:
        status = "PASS" if item["correct"] else "REVIEW"
        top = item["retrieved"][0] if item["retrieved"] else {}
        lines.append(
            f"- `{item['case_id']}`: {status}; top source={top.get('document_title', 'none')} {top.get('provision', '')}"
        )
    lines.extend(["", "## Remaining Failures"])
    if not report["failures"]:
        lines.append("- None under the targeted regression checks.")
    for item in report["failures"]:
        lines.append(f"- `{item['case_id']}` needs review.")
    lines.extend(["", "## Recommendation", "- Proceed to final manual retest of the 12 scenarios."])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate targeted manual regression cases.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()
    report = evaluate(args.cases)
    args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    print(
        "Manual regression evaluation complete: "
        f"{report['metrics']['case_count']} cases; "
        f"expected_behavior={percent(report['metrics']['overall_expected_behavior_rate'])}; "
        f"debug_leakage={percent(report['metrics']['debug_language_leakage_rate'])}"
    )


if __name__ == "__main__":
    main()
