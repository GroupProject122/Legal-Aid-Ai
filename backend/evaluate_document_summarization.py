from __future__ import annotations

import argparse
import json
import statistics
import time
from pathlib import Path
from typing import Any

import document_summarizer
from config import BASE_DIR

CASE_FILE = BASE_DIR / "eval" / "document_summarization_cases.json"
JSON_OUTPUT = BASE_DIR / "eval" / "document_summarization_evaluation.json"
MARKDOWN_OUTPUT = BASE_DIR / "eval" / "document_summarization_evaluation.md"


def load_cases(path: Path = CASE_FILE) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8"))


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    extraction = {
        "status": case.get("extraction_status", "success"),
        "filename": f"{case['case_id']}.txt",
        "file_type": "txt",
        "text": case.get("text", ""),
        "pages": [],
        "warnings": [],
    }
    started = time.perf_counter()
    result = document_summarizer.summarize_document(extraction)
    latency_ms = int((time.perf_counter() - started) * 1000)
    summary = result.get("summary") or ""
    expected_status = case.get("expected_status", "success")
    keyword_hits = [keyword for keyword in case.get("expected_keywords", []) if keyword.lower() in summary.lower()]
    forbidden_hits = [item for item in case.get("must_not_include", []) if item.lower() in summary.lower()]
    status_ok = result.get("status") == expected_status
    preservation_ok = len(keyword_hits) == len(case.get("expected_keywords", [])) if expected_status == "success" else True
    no_forbidden = not forbidden_hits
    return {
        "case_id": case["case_id"],
        "expected_status": expected_status,
        "status": result.get("status"),
        "structured_output": isinstance(result, dict) and "summary" in result,
        "summary": summary,
        "keyword_hits": keyword_hits,
        "forbidden_hits": forbidden_hits,
        "status_ok": status_ok,
        "factual_preservation_ok": preservation_ok,
        "hallucination_or_interpretation_leak": not no_forbidden,
        "sensitive_data_leak": any(hit for hit in forbidden_hits if any(token in hit.lower() for token in ["otp", "cvv", "password", "bluetiger", "884422"])),
        "gemini_calls": result.get("gemini_calls", 0),
        "latency_ms": result.get("latency_ms", latency_ms),
        "message": result.get("message"),
        "evaluated": True,
    }


def skipped_case(case: dict[str, Any], reason: str) -> dict[str, Any]:
    return {
        "case_id": case["case_id"],
        "expected_status": case.get("expected_status", "success"),
        "status": "not_evaluated",
        "structured_output": False,
        "summary": "",
        "keyword_hits": [],
        "forbidden_hits": [],
        "status_ok": False,
        "factual_preservation_ok": False,
        "hallucination_or_interpretation_leak": False,
        "sensitive_data_leak": False,
        "gemini_calls": 0,
        "latency_ms": None,
        "message": reason,
        "evaluated": False,
    }


def percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def ratio(count: int, total: int) -> float | None:
    return count / total if total else None


def build_report(cases: list[dict[str, Any]], results: list[dict[str, Any]]) -> dict[str, Any]:
    evaluated_results = [item for item in results if item.get("evaluated")]
    total = len(evaluated_results)
    success_results = [item for item in results if item["expected_status"] == "success"]
    evaluated_success_results = [item for item in evaluated_results if item["expected_status"] == "success"]
    latencies = [item["latency_ms"] for item in evaluated_results if isinstance(item.get("latency_ms"), int)]
    metrics = {
        "total_cases": len(results),
        "evaluated_cases": total,
        "not_evaluated_cases": len(results) - total,
        "structured_output_success_rate": ratio(sum(item["structured_output"] for item in evaluated_results), total),
        "status_accuracy": ratio(sum(item["status_ok"] for item in evaluated_results), total),
        "factual_preservation_rate": ratio(
            sum(item["factual_preservation_ok"] for item in evaluated_success_results), len(evaluated_success_results)
        ),
        "hallucinated_detail_or_legal_interpretation_leakage_rate": ratio(
            sum(item["hallucination_or_interpretation_leak"] for item in evaluated_results), total
        ),
        "sensitive_data_leakage_rate": ratio(sum(item["sensitive_data_leak"] for item in evaluated_results), total),
        "gemini_calls": sum(item.get("gemini_calls") or 0 for item in results),
        "average_latency_ms": statistics.mean(latencies) if latencies else None,
    }
    return {
        "case_file": str(CASE_FILE),
        "json_output": str(JSON_OUTPUT),
        "markdown_output": str(MARKDOWN_OUTPUT),
        "metrics": metrics,
        "results": results,
        "notes": [
            "This is a document-summary benchmark, not legal accuracy evaluation.",
            "Summaries are expected to use only uploaded document text.",
            "Gemini-dependent quality metrics may be provisional if quota/configuration is unavailable.",
        ],
        "dataset_size": len(cases),
    }


def write_outputs(report: dict[str, Any]) -> None:
    JSON_OUTPUT.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    metrics = report["metrics"]
    lines = [
        "# Document Summarization Evaluation",
        "",
        "## Overall Results",
        "",
        f"- Total cases: {metrics['total_cases']}",
        f"- Evaluated cases: {metrics['evaluated_cases']}",
        f"- Not evaluated: {metrics['not_evaluated_cases']}",
        f"- Structured-output success: {percent(metrics['structured_output_success_rate'])}",
        f"- Status accuracy: {percent(metrics['status_accuracy'])}",
        f"- Factual preservation: {percent(metrics['factual_preservation_rate'])}",
        f"- Hallucinated-detail / legal-interpretation leakage: {percent(metrics['hallucinated_detail_or_legal_interpretation_leakage_rate'])}",
        f"- Sensitive-data leakage: {percent(metrics['sensitive_data_leakage_rate'])}",
        f"- Gemini calls: {metrics['gemini_calls']}",
        f"- Average latency: {metrics['average_latency_ms']:.1f} ms" if metrics["average_latency_ms"] is not None else "- Average latency: N/A",
        "",
        "## Case Results",
        "",
    ]
    for item in report["results"]:
        lines.extend(
            [
                f"### {item['case_id']}",
                f"- Expected status: {item['expected_status']}",
                f"- Actual status: {item['status']}",
                f"- Keyword hits: {', '.join(item['keyword_hits']) or 'None'}",
                f"- Forbidden hits: {', '.join(item['forbidden_hits']) or 'None'}",
                f"- Message: {item.get('message') or 'N/A'}",
                "",
            ]
        )
    lines.extend(
        [
            "## Limitations",
            "",
            "- This evaluator checks factual preservation and leakage patterns, not legal correctness.",
            "- It does not add uploaded documents to the legal corpus, FAISS, or embeddings.",
        ]
    )
    MARKDOWN_OUTPUT.write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate uploaded document summarization.")
    parser.parse_args()
    cases = load_cases()
    results = []
    stopped_reason = None
    for case in cases:
        if stopped_reason:
            results.append(skipped_case(case, stopped_reason))
            continue
        result = evaluate_case(case)
        results.append(result)
        if case.get("expected_status", "success") == "success" and result["status"] == "summary_unavailable":
            stopped_reason = "Live summarization became unavailable; remaining cases were not evaluated to avoid repeated calls."
    report = build_report(cases, results)
    write_outputs(report)
    print(json.dumps(report["metrics"], indent=2))


if __name__ == "__main__":
    main()
