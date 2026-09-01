from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

import corpus_gap
import rag
from config import BASE_DIR, GEMINI_MODEL

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_CASE_PATH = EVAL_DIR / "corpus_gap_cases.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "corpus_gap_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "corpus_gap_evaluation.md"


def make_chunk(case_id: str, index: int, item: dict[str, Any]) -> rag.RetrievedChunk:
    return rag.RetrievedChunk(
        chunk_id=f"{case_id}__chunk_{index:03d}",
        text=item.get("text", ""),
        source=f"eval/{case_id}.pdf",
        document_title=item.get("document_title", "Evaluation Source"),
        page=1,
        page_start=1,
        page_end=1,
        score=float(item.get("score", 0.0)),
        rerank_score=float(item.get("score", 0.0)),
        domain=item.get("domain"),
        authority_level=item.get("authority_level"),
        status=item.get("status"),
        document_type=item.get("document_type"),
    )


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")).get("cases", [])


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    chunks = [make_chunk(case["id"], index, item) for index, item in enumerate(case.get("chunks", []), start=1)]
    started = time.perf_counter()
    gap = corpus_gap.pre_generation_check(case["issue"], case.get("domains", []), chunks)
    latency_ms = int((time.perf_counter() - started) * 1000)
    expected = case["expected_status"]
    expected_reasons = set(case.get("expected_reason_codes", []))
    actual_reasons = set(gap.reason_codes)
    unsafe_answer = expected == "insufficient" and gap.allow_grounded_answer
    unnecessary_abstention = expected == "sufficient" and not gap.allow_grounded_answer
    reason_hit = not expected_reasons or bool(expected_reasons & actual_reasons)
    return {
        "id": case["id"],
        "issue": case["issue"],
        "domains": case.get("domains", []),
        "expected_status": expected,
        "actual_status": gap.status,
        "expected_reason_codes": sorted(expected_reasons),
        "actual_reason_codes": gap.reason_codes,
        "allow_grounded_answer": gap.allow_grounded_answer,
        "require_limitation": gap.require_limitation,
        "suggest_professional_help": gap.suggest_professional_help,
        "source": gap.source,
        "latency_ms": latency_ms,
        "gemini_latency_ms": gap.latency_ms,
        "unsafe_answer": unsafe_answer,
        "unnecessary_abstention": unnecessary_abstention,
        "reason_hit": reason_hit,
        "correct": gap.status == expected and reason_hit and not unsafe_answer and not unnecessary_abstention,
        "summary": gap.summary,
    }


def pct(count: int, total: int) -> float:
    return round(count / total, 3) if total else 0.0


def precision_recall(results: list[dict[str, Any]], label: str) -> dict[str, float]:
    predicted = [item for item in results if item["actual_status"] == label]
    expected = [item for item in results if item["expected_status"] == label]
    true_positive = [item for item in predicted if item["expected_status"] == label]
    return {
        "precision": pct(len(true_positive), len(predicted)),
        "recall": pct(len(true_positive), len(expected)),
    }


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    sufficient = precision_recall(results, "sufficient")
    limited = precision_recall(results, "limited")
    insufficient = precision_recall(results, "insufficient")
    jurisdiction_cases = [item for item in results if "jurisdiction_not_covered" in item["expected_reason_codes"]]
    missing_primary = [item for item in results if "missing_primary_authority" in item["expected_reason_codes"] or "supporting_sources_only" in item["expected_reason_codes"]]
    return {
        "case_count": total,
        "overall_classification_accuracy": pct(sum(1 for item in results if item["actual_status"] == item["expected_status"]), total),
        "overall_reason_aware_accuracy": pct(sum(1 for item in results if item["correct"]), total),
        "sufficient_precision": sufficient["precision"],
        "sufficient_recall": sufficient["recall"],
        "limited_detection_accuracy": limited["recall"],
        "insufficient_detection_accuracy": insufficient["recall"],
        "unsafe_answer_rate": pct(sum(1 for item in results if item["unsafe_answer"]), sum(1 for item in results if item["expected_status"] == "insufficient")),
        "unnecessary_abstention_rate": pct(sum(1 for item in results if item["unnecessary_abstention"]), sum(1 for item in results if item["expected_status"] == "sufficient")),
        "jurisdiction_gap_detection_rate": pct(sum(1 for item in jurisdiction_cases if item["actual_status"] == "insufficient"), len(jurisdiction_cases)),
        "missing_primary_source_detection_rate": pct(sum(1 for item in missing_primary if item["actual_status"] in {"limited", "insufficient"}), len(missing_primary)),
        "gemini_corpus_gap_calls": sum(1 for item in results if item["source"] == "gemini"),
        "gemini_failures": 0,
    }


def confusion_matrix(results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    labels = ["sufficient", "limited", "insufficient"]
    matrix = {expected: {actual: 0 for actual in labels} for expected in labels}
    for item in results:
        matrix[item["expected_status"]][item["actual_status"]] += 1
    return matrix


def evaluate_corpus_gap(path: Path, delay_seconds: float = 0.0) -> dict[str, Any]:
    cases = load_cases(path)
    results = []
    for index, case in enumerate(cases):
        if index and delay_seconds > 0:
            time.sleep(delay_seconds)
        results.append(evaluate_case(case))
    gemini_latencies = [item["gemini_latency_ms"] for item in results if item["gemini_latency_ms"] is not None]
    return {
        "evaluation_config": {
            "case_file": path.as_posix(),
            "gemini_model": GEMINI_MODEL,
        },
        "metrics": aggregate(results),
        "confusion_matrix": confusion_matrix(results),
        "latency": {
            "gemini_corpus_gap_calls": len(gemini_latencies),
            "average_gemini_latency_ms": round(mean(gemini_latencies), 1) if gemini_latencies else None,
            "min_gemini_latency_ms": min(gemini_latencies) if gemini_latencies else None,
            "max_gemini_latency_ms": max(gemini_latencies) if gemini_latencies else None,
        },
        "results": results,
        "failures": [item for item in results if not item["correct"]],
    }


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Corpus Gap Evaluation",
        "",
        "## Overall Results",
        f"- Cases: {metrics['case_count']}",
        f"- Overall classification accuracy: {percent(metrics['overall_classification_accuracy'])}",
        f"- Reason-aware accuracy: {percent(metrics['overall_reason_aware_accuracy'])}",
        f"- Sufficient precision: {percent(metrics['sufficient_precision'])}",
        f"- Sufficient recall: {percent(metrics['sufficient_recall'])}",
        f"- Limited detection accuracy: {percent(metrics['limited_detection_accuracy'])}",
        f"- Insufficient detection accuracy: {percent(metrics['insufficient_detection_accuracy'])}",
        f"- Unsafe-answer rate: {percent(metrics['unsafe_answer_rate'])}",
        f"- Unnecessary-abstention rate: {percent(metrics['unnecessary_abstention_rate'])}",
        f"- Jurisdiction-gap detection rate: {percent(metrics['jurisdiction_gap_detection_rate'])}",
        f"- Missing-primary-source detection rate: {percent(metrics['missing_primary_source_detection_rate'])}",
        "",
        "## Confusion Matrix",
        "```json",
        json.dumps(report["confusion_matrix"], indent=2),
        "```",
        "",
        "## Sufficient Cases",
    ]
    for item in report["results"]:
        if item["expected_status"] == "sufficient":
            lines.append(f"- `{item['id']}` -> {item['actual_status']}")
    lines.extend(["", "## Limited Cases"])
    for item in report["results"]:
        if item["expected_status"] == "limited":
            lines.append(f"- `{item['id']}` -> {item['actual_status']} ({', '.join(item['actual_reason_codes']) or 'no reason'})")
    lines.extend(["", "## Insufficient Cases"])
    for item in report["results"]:
        if item["expected_status"] == "insufficient":
            lines.append(f"- `{item['id']}` -> {item['actual_status']} ({', '.join(item['actual_reason_codes']) or 'no reason'})")
    lines.extend(["", "## Failure Examples"])
    if not report["failures"]:
        lines.append("- No failures under the current deterministic corpus-gap checks.")
    for item in report["failures"][:10]:
        lines.append(f"- `{item['id']}` expected {item['expected_status']}, got {item['actual_status']}: {item['summary']}")
    lines.extend(
        [
            "",
            "## Recommendation",
            "- Use the current layer to prevent obvious corpus gaps, then review any failure examples before broadening coverage.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate corpus-gap detection.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    args = parser.parse_args()
    report = evaluate_corpus_gap(args.cases, args.delay_seconds)
    args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    metrics = report["metrics"]
    print(
        "Corpus gap evaluation complete: "
        f"{metrics['case_count']} cases; "
        f"accuracy={percent(metrics['overall_classification_accuracy'])}; "
        f"unsafe={percent(metrics['unsafe_answer_rate'])}; "
        f"unnecessary abstention={percent(metrics['unnecessary_abstention_rate'])}"
    )


if __name__ == "__main__":
    main()
