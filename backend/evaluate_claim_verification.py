from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from statistics import mean
from typing import Any

import claim_verifier
import rag
from config import BASE_DIR, GEMINI_MODEL

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_CASE_PATH = EVAL_DIR / "claim_verification_cases.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "claim_verification_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "claim_verification_evaluation.md"


def make_chunk(case: dict[str, Any]) -> rag.RetrievedChunk:
    return rag.RetrievedChunk(
        chunk_id=case["chunk_id"],
        text=case["source_text"],
        source=f"eval/{case['chunk_id']}.pdf",
        document_title=case["document_title"],
        page=1,
        page_start=1,
        page_end=1,
        score=0.9,
        rerank_score=0.9,
        domain=case.get("domain", "eval"),
        section_number=case.get("section_number"),
        section_title=case.get("section_title"),
    )


def make_response(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "answer": {
            "issue_summary": "Evaluation case.",
            "what_this_may_involve": [case["claim"]],
            "possible_legal_position": [],
            "suggested_next_steps": [],
            "evidence_to_preserve": [],
            "where_to_approach": [],
            "limitations": [],
            "possible_rights": [],
            "next_steps": [],
        },
        "sources": [{"chunk_id": case["chunk_id"]}],
        "confidence": "medium",
        "insufficient_context": False,
        "disclaimer": "This is legal information, not professional legal advice.",
        "source_chunk_ids": [case["chunk_id"]],
    }


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")).get("cases", [])


def evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    chunk = make_chunk(case)
    response = make_response(case)
    output = claim_verifier.verify_and_sanitize_response(response, [chunk])
    latency_ms = int((time.perf_counter() - started) * 1000)
    verification = output.get("verification", {})
    result = (verification.get("results") or [{}])[0] if verification.get("results") else {}
    actual_support = result.get("support")
    if verification.get("status") == "unavailable":
        actual_support = "verification_unavailable"
    expected = case["expected_support"]
    claim_visible = case["claim"] in json.dumps(output.get("answer", {}), ensure_ascii=False)
    unsupported_leaked = expected == "unsupported" and claim_visible
    false_rejection = expected == "supported" and not claim_visible
    false_acceptance = expected == "unsupported" and actual_support == "supported"
    partially_qualified = expected == "partially_supported" and any(
        str(item).startswith("The retrieved sources partly support")
        for values in output.get("answer", {}).values()
        if isinstance(values, list)
        for item in values
    )
    correct = verification.get("status") == "verified" and actual_support == expected and not unsupported_leaked and not false_rejection
    return {
        "id": case["id"],
        "claim": case["claim"],
        "expected_support": expected,
        "actual_support": actual_support,
        "verification_status": verification.get("status"),
        "latency_ms": latency_ms,
        "claim_visible_after_sanitization": claim_visible,
        "unsupported_claim_leaked": unsupported_leaked,
        "false_acceptance": false_acceptance,
        "false_rejection": false_rejection,
        "high_risk": claim_verifier.is_high_risk_claim(case["claim"]),
        "sanitization_correct": sanitization_correct(expected, actual_support, claim_visible, partially_qualified),
        "output_answer": output.get("answer", {}),
        "verification": verification,
        "correct": correct,
    }


def sanitization_correct(expected: str, actual: str | None, claim_visible: bool, partially_qualified: bool) -> bool:
    if actual == "verification_unavailable":
        return not claim_visible
    if actual == "supported":
        return claim_visible
    if actual == "partially_supported":
        return claim_visible or partially_qualified
    if actual == "unsupported":
        return not claim_visible
    return expected != "supported" and not claim_visible


def pct(count: int, total: int) -> float:
    return round(count / total, 3) if total else 0.0


def pct_or_none(count: int, total: int) -> float | None:
    return round(count / total, 3) if total else None


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    verified = [item for item in results if item["verification_status"] == "verified"]
    expected_supported = [item for item in verified if item["expected_support"] == "supported"]
    predicted_supported = [item for item in verified if item["actual_support"] == "supported"]
    unsupported = [item for item in verified if item["expected_support"] == "unsupported"]
    partial = [item for item in verified if item["expected_support"] == "partially_supported"]
    high_risk = [item for item in verified if item["high_risk"]]
    return {
        "case_count": total,
        "verified_case_count": len(verified),
        "verifier_structured_output_success_rate": pct(len(verified), total),
        "overall_classification_accuracy": pct_or_none(sum(1 for item in verified if item["actual_support"] == item["expected_support"]), len(verified)),
        "supported_claim_precision": pct_or_none(sum(1 for item in predicted_supported if item["expected_support"] == "supported"), len(predicted_supported)),
        "supported_claim_recall": pct_or_none(sum(1 for item in expected_supported if item["actual_support"] == "supported"), len(expected_supported)),
        "unsupported_claim_detection_rate": pct_or_none(sum(1 for item in unsupported if item["actual_support"] == "unsupported"), len(unsupported)),
        "partially_supported_detection_rate": pct_or_none(sum(1 for item in partial if item["actual_support"] == "partially_supported"), len(partial)),
        "false_acceptance_rate": pct_or_none(sum(1 for item in verified if item["false_acceptance"]), len(verified)),
        "false_rejection_rate": pct_or_none(sum(1 for item in verified if item["false_rejection"]), len(verified)),
        "final_unsupported_claim_leakage_rate": pct_or_none(sum(1 for item in verified if item["unsupported_claim_leaked"]), len(verified)),
        "sanitization_correct_rate": pct_or_none(sum(1 for item in verified if item["sanitization_correct"]), len(verified)),
        "high_risk_case_count": len(high_risk),
        "high_risk_safe_handling_rate": pct_or_none(
            sum(1 for item in high_risk if not item["unsupported_claim_leaked"] and not item["false_acceptance"]),
            len(high_risk),
        ),
        "verifier_call_failure_rate": pct(sum(1 for item in results if item["verification_status"] == "unavailable"), total),
        "overall_verified_accuracy": pct_or_none(sum(1 for item in verified if item["correct"]), len(verified)),
    }


def confusion_matrix(results: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    labels = ["supported", "partially_supported", "unsupported"]
    matrix = {expected: {predicted: 0 for predicted in labels} for expected in labels}
    for item in results:
        if item["verification_status"] != "verified":
            continue
        expected = item["expected_support"]
        predicted = item["actual_support"]
        if expected in matrix and predicted in matrix[expected]:
            matrix[expected][predicted] += 1
    return matrix


def evaluate_claim_verification(
    path: Path,
    max_cases: int | None = None,
    delay_seconds: float = 0.0,
    stop_on_call_failure: bool = True,
) -> dict[str, Any]:
    cases = load_cases(path)
    if max_cases is not None:
        cases = cases[:max_cases]
    results = []
    for index, case in enumerate(cases):
        if index and delay_seconds > 0:
            time.sleep(delay_seconds)
        results.append(evaluate_case(case))
        if stop_on_call_failure and results[-1]["verification_status"] == "unavailable":
            break
    latencies = [item["latency_ms"] for item in results if item["verification_status"] == "verified"]
    return {
        "evaluation_config": {
            "case_file": path.as_posix(),
            "gemini_model": GEMINI_MODEL,
            "max_cases": max_cases,
            "stop_on_call_failure": stop_on_call_failure,
        },
        "metrics": aggregate(results),
        "confusion_matrix": confusion_matrix(results),
        "high_risk_results": [item for item in results if item["high_risk"]],
        "wrong_source_or_section_results": [
            item for item in results if "wrong" in item["id"] or "fake" in item["id"]
        ],
        "latency": {
            "successful_verifier_calls": len(latencies),
            "average_latency_ms": round(mean(latencies), 1) if latencies else None,
            "min_latency_ms": min(latencies) if latencies else None,
            "max_latency_ms": max(latencies) if latencies else None,
        },
        "results": results,
        "failures": [item for item in results if not item["correct"]],
    }


def percent(value: float) -> str:
    if value is None:
        return "not measured"
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Claim Verification Evaluation",
        "",
        "## Overall Results",
        f"- Cases: {metrics['case_count']}",
        f"- Verified cases: {metrics['verified_case_count']}",
        f"- Verifier structured-output success rate: {percent(metrics['verifier_structured_output_success_rate'])}",
        f"- Overall classification accuracy: {percent(metrics['overall_classification_accuracy'])}",
        f"- Supported-claim precision: {percent(metrics['supported_claim_precision'])}",
        f"- Supported-claim recall: {percent(metrics['supported_claim_recall'])}",
        f"- Unsupported-claim detection rate: {percent(metrics['unsupported_claim_detection_rate'])}",
        f"- Partially-supported detection rate: {percent(metrics['partially_supported_detection_rate'])}",
        f"- False-acceptance rate: {percent(metrics['false_acceptance_rate'])}",
        f"- False-rejection rate: {percent(metrics['false_rejection_rate'])}",
        f"- Final unsupported-claim leakage rate: {percent(metrics['final_unsupported_claim_leakage_rate'])}",
        f"- Sanitization-correct rate: {percent(metrics['sanitization_correct_rate'])}",
        f"- High-risk safe handling rate: {percent(metrics['high_risk_safe_handling_rate'])}",
        f"- Verifier-call failure rate: {percent(metrics['verifier_call_failure_rate'])}",
        "",
        "## Confusion Matrix",
        "```json",
        json.dumps(report["confusion_matrix"], indent=2),
        "```",
        "",
        "## Supported Claims",
    ]
    for result in report["results"]:
        if result["expected_support"] == "supported":
            lines.append(f"- `{result['id']}` -> {result['actual_support']}")
    lines.extend(["", "## Partial-Support Cases"])
    for result in report["results"]:
        if result["expected_support"] == "partially_supported":
            lines.append(f"- `{result['id']}` -> {result['actual_support']}")
    lines.extend(["", "## Unsupported Claims"])
    for result in report["results"]:
        if result["expected_support"] == "unsupported":
            lines.append(f"- `{result['id']}` -> {result['actual_support']}; leaked={result['unsupported_claim_leaked']}")
    lines.extend(
        [
            "",
            "## High-Risk Claim Checks",
            f"- High-risk evaluated cases: {metrics['high_risk_case_count']}",
            f"- Safe handling rate: {percent(metrics['high_risk_safe_handling_rate'])}",
            "",
            "## Wrong-Source / Wrong-Section Cases",
            *[
                f"- `{result['id']}`: expected {result['expected_support']}, predicted {result['actual_support']}"
                for result in report["wrong_source_or_section_results"]
            ],
            "",
            "## Gemini Failure / Quota Handling",
            f"- Successful verifier calls: {report['latency']['successful_verifier_calls']}",
            f"- Average latency: {report['latency']['average_latency_ms']} ms",
            f"- Failure count: {sum(1 for item in report['results'] if item['verification_status'] == 'unavailable')}",
            "",
            "## Remaining Limitations",
            "- This is a lightweight Gemini verifier, not formal entailment/citation proof.",
            "- Quota failures are handled safely and reported separately from verifier quality.",
            "",
            "## Recommendation",
            "- Use this verifier as a guardrail, then add deeper claim-to-citation review in a later phase if needed.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate claim verification.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument("--max-cases", type=int, default=None)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    parser.add_argument("--continue-after-failure", action="store_true")
    args = parser.parse_args()
    report = evaluate_claim_verification(
        args.cases,
        args.max_cases,
        args.delay_seconds,
        stop_on_call_failure=not args.continue_after_failure,
    )
    args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    metrics = report["metrics"]
    print(
        "Claim verification evaluation complete: "
        f"{metrics['case_count']} cases; "
        f"verified={metrics['verified_case_count']}; "
        f"unsupported leakage={percent(metrics['final_unsupported_claim_leakage_rate'])}; "
        f"call failures={percent(metrics['verifier_call_failure_rate'])}"
    )


if __name__ == "__main__":
    main()
