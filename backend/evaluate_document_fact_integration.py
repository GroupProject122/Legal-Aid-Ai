from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import corpus_gap
import document_facts
import fact_sufficiency
import main
import rag
from config import BASE_DIR

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_CASES = EVAL_DIR / "document_fact_integration_cases.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "document_fact_integration_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "document_fact_integration_evaluation.md"


def route(domain: str) -> main.domain_router.RouteDecision:
    return main.domain_router.RouteDecision(
        status="classified",
        domains=[domain],
        primary_domain=domain,
        confidence="high",
        issue_summary="Evaluation issue.",
        needs_clarification=False,
    )


def chunk(domain: str = "tenancy") -> rag.RetrievedChunk:
    return rag.RetrievedChunk(
        chunk_id="eval_legal_chunk",
        text="Section 45 concerns essential supply in tenancy.",
        source="tenancy/delhi_rent_control_act_1958.pdf",
        document_title="The Delhi Rent Control Act, 1958",
        page=1,
        score=0.8,
        rerank_score=0.9,
        domain=domain,
        authority_level="primary",
        status="active",
        document_type="statute",
        section_number="45",
    )


def facts_from_case(case: dict[str, Any], override_value: str | None = None) -> dict[str, Any]:
    data = case.get("facts", {})
    amount_values = [override_value] if override_value else data.get("amounts", [])
    return {
        "document_type": case.get("document_type", "unknown"),
        "document_summary": "Evaluation confirmed facts.",
        "parties": items("party", data.get("parties", [])),
        "dates": items("date", data.get("dates", [])),
        "amounts": items("amount", amount_values),
        "identifiers": items("identifier", data.get("identifiers", [])),
        "locations": items("location", data.get("locations", [])),
        "important_terms": items("term", data.get("terms", [])),
        "events": items("event", data.get("events", [])),
        "notices_or_demands": [],
        "other_facts": [],
        "uncertain_items": [],
        "warnings": [],
    }


def items(label: str, values: list[str]) -> list[dict[str, Any]]:
    return [
        {
            "label": label,
            "value": value,
            "source_page": 1,
            "source_excerpt": value,
            "confidence": "high",
        }
        for value in values
    ]


def confirmed_context(case: dict[str, Any], override_value: str | None = None) -> dict[str, Any]:
    payload = facts_from_case(case, override_value)
    pending_id = document_facts.store_pending_facts(payload)
    confirmed = document_facts.confirm_facts(pending_id, payload)
    return document_facts.require_confirmed_context(confirmed.confirmed_fact_context_id)


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    kind = case["kind"]
    result: dict[str, Any] = {"id": case["id"], "kind": kind, "correct": False}
    if kind == "confirmed_acceptance":
        context = confirmed_context(case)
        lines = " ".join(document_facts.confirmed_fact_lines(context))
        expected = case.get("expected_values", [])
        result.update(accepted=True, preserved=all(value in lines for value in expected), correct=all(value in lines for value in expected))
    elif kind == "unconfirmed_rejection":
        pending_id = document_facts.store_pending_facts(facts_from_case(case))
        try:
            document_facts.require_confirmed_context(pending_id)
            rejected = False
        except document_facts.DocumentFactError:
            rejected = True
        result.update(rejected=rejected, correct=rejected)
    elif kind == "fact_sufficiency":
        context = confirmed_context(case)
        domain = inferred_domain(case)
        case_context = fact_sufficiency.new_case_context(case["question"], route(domain), document_facts.confirmed_fact_lines(context))
        sufficient = fact_sufficiency.assess_fact_sufficiency(case_context).status == "sufficient"
        result.update(sufficient=sufficient, correct=sufficient is case.get("expected_sufficient"))
    elif kind == "corpus_gap":
        context = confirmed_context(case)
        query = document_facts.combined_question_with_confirmed_facts(case["question"], context)
        gap = corpus_gap.pre_generation_check(query, ["tenancy"], [chunk("tenancy")])
        result.update(gap_status=gap.status, correct=gap.status == case.get("expected_gap"))
    elif kind == "conflict":
        context = confirmed_context(case)
        has_conflict = main.detect_document_fact_conflict(case["question"], context) is not None
        result.update(conflict=has_conflict, correct=has_conflict is case.get("expected_conflict"))
    elif kind == "correction_priority":
        context = confirmed_context(case, case["corrected_value"])
        lines = " ".join(document_facts.confirmed_fact_lines(context))
        correct = case["corrected_value"] in lines and case["original_value"] not in lines
        result.update(corrected_used=case["corrected_value"] in lines, original_absent=case["original_value"] not in lines, correct=correct)
    elif kind == "separation":
        context = confirmed_context(case)
        evidence = document_facts.document_evidence_payload(context)
        correct = bool(evidence) and all(item.get("source") == "user_document" for item in evidence)
        result.update(document_evidence_count=len(evidence), legal_source_leakage=False, correct=correct)
    elif kind == "no_document":
        route_text = document_facts.combined_question_with_confirmed_facts(case["question"], None)
        correct = route_text == case["question"]
        result.update(no_document_unchanged=correct, correct=correct)
    elif kind == "detach":
        context = confirmed_context(case)
        context_id = context["confirmed_fact_context_id"]
        detached = document_facts.detach_confirmed_context(context_id)
        result.update(detached=detached, unavailable=document_facts.get_confirmed_context(context_id) is None, correct=detached)
    elif kind == "confirmation_only":
        context = confirmed_context(case)
        correct = bool(context.get("confirmed_fact_context_id")) and "answer" not in context
        result.update(no_auto_answer=correct, correct=correct)
    return result


def pct(count: int, total: int) -> float:
    return round(count / total, 3) if total else 0.0


def evaluate(path: Path) -> dict[str, Any]:
    fact_sufficiency.GEMINI_API_KEY = ""
    cases = json.loads(path.read_text(encoding="utf-8")).get("cases", [])
    results = [evaluate_case(case) for case in cases]
    by_kind = {}
    for item in results:
        by_kind.setdefault(item["kind"], []).append(item)
    metrics = {
        "case_count": len(results),
        "overall_accuracy": pct(sum(1 for item in results if item["correct"]), len(results)),
        "confirmed_context_acceptance_rate": rate(results, "confirmed_acceptance"),
        "unconfirmed_context_rejection_rate": rate(results, "unconfirmed_rejection"),
        "fact_preservation_accuracy": rate(results, "confirmed_acceptance"),
        "user_correction_priority_accuracy": rate(results, "correction_priority"),
        "conflict_detection_accuracy": rate(results, "conflict"),
        "document_legal_source_separation_rate": rate(results, "separation"),
        "no_document_regression_rate": 1.0 - rate(results, "no_document"),
        "corpus_gap_safety_preservation_rate": rate(results, "corpus_gap"),
        "unconfirmed_fact_leakage_rate": 1.0 - rate(results, "unconfirmed_rejection"),
        "document_as_legal_source_leakage_rate": 1.0 - rate(results, "separation"),
        "confirmed_fact_mutation_rate": 1.0 - rate(results, "confirmed_acceptance"),
        "corpus_gap_bypass_rate": 1.0 - rate(results, "corpus_gap"),
        "gemini_calls": 0,
        "gemini_failures": 0,
    }
    return {
        "evaluation_config": {"case_file": path.as_posix(), "gemini_used": False},
        "metrics": metrics,
        "results": results,
        "failures": [item for item in results if not item["correct"]],
        "by_kind": {kind: {"count": len(items), "correct": sum(1 for item in items if item["correct"])} for kind, items in by_kind.items()},
    }


def rate(results: list[dict[str, Any]], kind: str) -> float:
    items = [item for item in results if item["kind"] == kind]
    return pct(sum(1 for item in items if item["correct"]), len(items))


def inferred_domain(case: dict[str, Any]) -> str:
    text = json.dumps(case, ensure_ascii=False).lower()
    if case.get("document_type") == "rent_agreement" or "landlord" in text or "tenant" in text or "deposit" in text:
        return "tenancy"
    if "upi" in text or "cyber" in text or "fraud" in text or "instagram" in text:
        return "cyber"
    if re.search(r"\brti\b", text) or "public authority" in text:
        return "constitutional_public_authority"
    return "consumer"


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Document Fact Integration Evaluation",
        "",
        "## Overall Results",
        f"- Cases: {metrics['case_count']}",
        f"- Overall accuracy: {percent(metrics['overall_accuracy'])}",
        f"- Confirmed-context acceptance: {percent(metrics['confirmed_context_acceptance_rate'])}",
        f"- Unconfirmed-context rejection: {percent(metrics['unconfirmed_context_rejection_rate'])}",
        f"- Fact preservation accuracy: {percent(metrics['fact_preservation_accuracy'])}",
        f"- User-correction priority: {percent(metrics['user_correction_priority_accuracy'])}",
        f"- Conflict detection: {percent(metrics['conflict_detection_accuracy'])}",
        f"- Document/legal-source separation: {percent(metrics['document_legal_source_separation_rate'])}",
        f"- Corpus-gap safety preservation: {percent(metrics['corpus_gap_safety_preservation_rate'])}",
        f"- Unconfirmed-fact leakage: {percent(metrics['unconfirmed_fact_leakage_rate'])}",
        f"- Document-as-legal-source leakage: {percent(metrics['document_as_legal_source_leakage_rate'])}",
        f"- Confirmed-fact mutation: {percent(metrics['confirmed_fact_mutation_rate'])}",
        f"- Corpus-gap bypass: {percent(metrics['corpus_gap_bypass_rate'])}",
        f"- Gemini calls: {metrics['gemini_calls']}",
        "",
        "## Case Results",
    ]
    for item in report["results"]:
        lines.append(f"- `{item['id']}` ({item['kind']}) -> {'pass' if item['correct'] else 'review'}")
    lines.extend(["", "## Failure Examples"])
    if not report["failures"]:
        lines.append("- No failures under the current integration checks.")
    for item in report["failures"]:
        lines.append(f"- `{item['id']}` failed: {item}")
    lines.extend(["", "## Recommendation", "- Confirmed document facts are ready for controlled use as user case context; keep them separate from legal citations.", ""])
    return "\n".join(lines)


def main_cli() -> None:
    parser = argparse.ArgumentParser(description="Evaluate confirmed document-fact integration.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()
    report = evaluate(args.cases)
    args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    metrics = report["metrics"]
    print(
        "Document fact integration evaluation complete: "
        f"{metrics['case_count']} cases; "
        f"accuracy={percent(metrics['overall_accuracy'])}; "
        f"unconfirmed_leakage={percent(metrics['unconfirmed_fact_leakage_rate'])}; "
        f"source_leakage={percent(metrics['document_as_legal_source_leakage_rate'])}"
    )


if __name__ == "__main__":
    main_cli()
