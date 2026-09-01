from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

import document_facts
from config import BASE_DIR, GEMINI_MODEL

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_CASES = EVAL_DIR / "document_fact_cases.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "document_fact_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "document_fact_evaluation.md"


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")).get("cases", [])


def make_extraction(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "status": "success",
        "filename": case["filename"],
        "file_type": "txt",
        "size_bytes": len(case["text"].encode("utf-8")),
        "page_count": None,
        "character_count": len(case["text"]),
        "text": case["text"],
        "pages": [{"page_number": 1, "text": case["text"]}],
        "warnings": [],
    }


def all_fact_text(facts: dict[str, Any]) -> str:
    return json.dumps(facts, ensure_ascii=False).lower()


def fact_items(facts: dict[str, Any]) -> list[dict[str, Any]]:
    items = []
    for category in document_facts.FACT_CATEGORIES:
        items.extend(facts.get(category, []) or [])
    return items


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    result = document_facts.extract_facts_from_extraction(make_extraction(case))
    latency_ms = int((time.perf_counter() - started) * 1000)
    facts = result.get("facts", {})
    text = all_fact_text(facts)
    expected_values = case.get("expected_values", [])
    must_not_include = case.get("must_not_include", [])
    expected_uncertain = case.get("expected_uncertain", [])
    found_values = [value for value in expected_values if value.lower() in text]
    leaked_forbidden = [value for value in must_not_include if value.lower() in text]
    uncertain_text = json.dumps(facts.get("uncertain_items", []), ensure_ascii=False).lower()
    uncertain_hits = [value for value in expected_uncertain if value.lower() in uncertain_text]
    items = fact_items(facts)
    provenance_items = [item for item in items if item.get("source_excerpt")]
    structured_ok = result.get("status") == "success" and isinstance(facts, dict)
    return {
        "id": case["id"],
        "expected_document_type": case["expected_document_type"],
        "actual_document_type": facts.get("document_type"),
        "status": result.get("status"),
        "latency_ms": latency_ms,
        "gemini_latency_ms": (result.get("extraction") or {}).get("latency_ms"),
        "expected_values": expected_values,
        "found_values": found_values,
        "missing_values": [value for value in expected_values if value not in found_values],
        "forbidden_leaks": leaked_forbidden,
        "expected_uncertain": expected_uncertain,
        "uncertain_hits": uncertain_hits,
        "fact_count": len(items),
        "provenance_count": len(provenance_items),
        "structured_ok": structured_ok,
        "document_type_correct": facts.get("document_type") == case["expected_document_type"],
        "key_recall": len(found_values) / len(expected_values) if expected_values else 1.0,
        "hallucinated_forbidden": bool(leaked_forbidden),
        "sensitive_leak": any(token in " ".join(leaked_forbidden).lower() for token in ["4111", "123456", "otp", "password", "cvv"]),
        "provenance_rate": len(provenance_items) / len(items) if items else 1.0,
        "uncertainty_ok": len(uncertain_hits) == len(expected_uncertain),
        "confirmation_required": result.get("confirmation_required") is True,
    }


def pct(value: float) -> float:
    return round(value, 3)


def evaluate(path: Path) -> dict[str, Any]:
    cases = load_cases(path)
    results = [evaluate_case(case) for case in cases]
    total = len(results)
    successful = [item for item in results if item["structured_ok"]]
    expected_value_count = sum(len(item["expected_values"]) for item in results)
    found_value_count = sum(len(item["found_values"]) for item in results)
    forbidden_count = sum(len(item["forbidden_leaks"]) for item in results)
    hallucination_opportunities = sum(len(json.loads(path.read_text(encoding="utf-8")).get("cases", [])[i].get("must_not_include", [])) for i in range(total))
    latencies = [item["latency_ms"] for item in results]
    gemini_latencies = [item["gemini_latency_ms"] for item in results if item["gemini_latency_ms"] is not None]
    return {
        "evaluation_config": {
            "case_file": path.as_posix(),
            "gemini_model": GEMINI_MODEL,
            "gemini_used": True,
        },
        "metrics": {
            "case_count": total,
            "structured_output_success_rate": pct(len(successful) / total if total else 0),
            "document_type_accuracy": pct(sum(1 for item in results if item["document_type_correct"]) / total if total else 0),
            "key_fact_precision": pct(1.0 - (forbidden_count / hallucination_opportunities if hallucination_opportunities else 0)),
            "key_fact_recall": pct(found_value_count / expected_value_count if expected_value_count else 0),
            "hallucinated_fact_rate": pct(forbidden_count / hallucination_opportunities if hallucination_opportunities else 0),
            "sensitive_data_leakage_rate": pct(sum(1 for item in results if item["sensitive_leak"]) / total if total else 0),
            "provenance_presence_rate": pct(mean(item["provenance_rate"] for item in results) if results else 0),
            "uncertainty_handling_accuracy": pct(sum(1 for item in results if item["uncertainty_ok"]) / total if total else 0),
            "confirmation_required_rate": pct(sum(1 for item in results if item["confirmation_required"]) / total if total else 0),
            "gemini_calls": total,
            "gemini_failures": sum(1 for item in results if item["status"] == "fact_extraction_unavailable"),
            "average_latency_ms": round(mean(latencies), 1) if latencies else 0,
            "average_gemini_latency_ms": round(mean(gemini_latencies), 1) if gemini_latencies else None,
        },
        "results": results,
        "failures": [
            item
            for item in results
            if not item["structured_ok"]
            or not item["document_type_correct"]
            or item["missing_values"]
            or item["forbidden_leaks"]
            or not item["uncertainty_ok"]
        ],
    }


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Document Fact Extraction Evaluation",
        "",
        "## Overall Results",
        f"- Cases: {metrics['case_count']}",
        f"- Structured-output success: {percent(metrics['structured_output_success_rate'])}",
        f"- Document-type accuracy: {percent(metrics['document_type_accuracy'])}",
        f"- Key-fact precision: {percent(metrics['key_fact_precision'])}",
        f"- Key-fact recall: {percent(metrics['key_fact_recall'])}",
        f"- Hallucinated-fact rate: {percent(metrics['hallucinated_fact_rate'])}",
        f"- Sensitive-data leakage rate: {percent(metrics['sensitive_data_leakage_rate'])}",
        f"- Provenance-presence rate: {percent(metrics['provenance_presence_rate'])}",
        f"- Uncertainty handling: {percent(metrics['uncertainty_handling_accuracy'])}",
        f"- Gemini calls: {metrics['gemini_calls']}",
        f"- Gemini failures: {metrics['gemini_failures']}",
        f"- Average latency: {metrics['average_latency_ms']} ms",
        "",
        "## Case Results",
    ]
    for item in report["results"]:
        status = "pass" if item not in report["failures"] else "review"
        lines.append(f"- `{item['id']}` -> {item['actual_document_type']} ({status})")
    lines.extend(["", "## Failure Examples"])
    if not report["failures"]:
        lines.append("- No failures under the current evaluation heuristics.")
    for item in report["failures"][:8]:
        lines.append(
            f"- `{item['id']}` missing={item['missing_values']} forbidden={item['forbidden_leaks']} "
            f"expected_type={item['expected_document_type']} actual_type={item['actual_document_type']}"
        )
    lines.extend(["", "## Recommendation", "- Use user-confirmed facts only in the next integration phase; do not auto-feed extracted facts into RAG yet.", ""])
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate document fact extraction.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args()
    report = evaluate(args.cases)
    args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    metrics = report["metrics"]
    print(
        "Document fact evaluation complete: "
        f"{metrics['case_count']} cases; "
        f"structured={percent(metrics['structured_output_success_rate'])}; "
        f"hallucination={percent(metrics['hallucinated_fact_rate'])}; "
        f"sensitive_leakage={percent(metrics['sensitive_data_leakage_rate'])}"
    )


if __name__ == "__main__":
    main()
