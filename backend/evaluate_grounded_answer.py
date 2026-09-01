from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path
from statistics import mean
from typing import Any

import grounded_answer
from config import BASE_DIR, GEMINI_MODEL
from rag import rag

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_QUERY_PATH = EVAL_DIR / "grounded_answer_queries.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "grounded_answer_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "grounded_answer_evaluation.md"

UNSAFE_CERTAINTY = (
    "definitely",
    "guaranteed",
    "you will win",
    "must refund",
    "must compensate",
    "is guilty",
    "illegally disconnected",
    "convicted",
)


def load_scenarios(path: Path = DEFAULT_QUERY_PATH) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")).get("scenarios", [])


def evaluate_scenario(case: dict[str, Any]) -> dict[str, Any]:
    chunks = rag.retrieve(case["query"])
    try:
        response = grounded_answer.generate_grounded_answer(
            original_message=case["query"],
            normalized_case_summary=case["query"],
            domains=case.get("domains", []),
            chunks=chunks,
        )
        failed = False
        error = None
    except Exception as exc:  # evaluation records failures instead of aborting
        response = grounded_answer.insufficient_response(str(exc))
        failed = True
        error = f"{exc.__class__.__name__}: {exc}"

    valid_chunk_ids = {grounded_answer.chunk_id(chunk) for chunk in chunks}
    returned_ids = set(response.get("source_chunk_ids", []))
    source_id_valid = returned_ids <= valid_chunk_ids
    text = response_text(response)
    expected_docs = case.get("expected_documents", [])
    should_insufficient = bool(case.get("should_mark_insufficient", False))
    expected_doc_present = True if (not expected_docs or response.get("insufficient_context") is True) else any(
        expected.lower() in json.dumps(response.get("sources", [])).lower()
        for expected in expected_docs
    )
    expected_provisions = [str(value) for value in case.get("expected_provisions", [])]
    expected_provision_present = True if (not expected_provisions or response.get("insufficient_context") is True) else any(
        provision_matches_source(expected, response.get("sources", []))
        for expected in expected_provisions
    )
    must_not_claim = [claim for claim in case.get("must_not_claim", []) if claim.lower() in text.lower()]
    unsafe_claims = [claim for claim in UNSAFE_CERTAINTY if unsafe_phrase_present(claim, text)]
    unsupported_source_claims = unsupported_source_claims_in_text(text, response.get("sources", []))
    insufficient_ok = response.get("insufficient_context") is True if should_insufficient else True
    structured_valid = has_valid_structure(response)
    disclaimer_present = bool(response.get("disclaimer"))
    return {
        "id": case["id"],
        "query": case["query"],
        "domains": case.get("domains", []),
        "retrieved_chunks": [
            {
                "chunk_id": grounded_answer.chunk_id(chunk),
                "document": chunk.document_title,
                "provision": grounded_answer.provision_label(chunk),
                "page": chunk.page,
                "score": round(chunk.score, 4),
                "rerank_score": round(chunk.rerank_score, 4),
            }
            for chunk in chunks
        ],
        "response": response,
        "error": error,
        "evaluation": {
            "generation_failed": failed,
            "structured_valid": structured_valid,
            "source_id_valid": source_id_valid,
            "unsupported_source_hallucination": bool(unsupported_source_claims),
            "unsafe_certainty": bool(unsafe_claims or must_not_claim),
            "expected_document_present": expected_doc_present,
            "expected_provision_present": expected_provision_present,
            "insufficient_context_ok": insufficient_ok,
            "disclaimer_present": disclaimer_present,
            "correct": structured_valid
            and not failed
            and source_id_valid
            and not unsupported_source_claims
            and not unsafe_claims
            and not must_not_claim
            and expected_doc_present
            and expected_provision_present
            and insufficient_ok
            and disclaimer_present,
        },
        "findings": {
            "must_not_claim_hits": must_not_claim,
            "unsafe_certainty_hits": unsafe_claims,
            "unsupported_source_claims": unsupported_source_claims,
        },
    }


def has_valid_structure(response: dict[str, Any]) -> bool:
    answer = response.get("answer")
    if not isinstance(answer, dict):
        return False
    required_lists = (
        "what_this_may_involve",
        "possible_legal_position",
        "suggested_next_steps",
        "evidence_to_preserve",
        "where_to_approach",
        "limitations",
    )
    return isinstance(answer.get("issue_summary"), str) and all(isinstance(answer.get(field), list) for field in required_lists)


def response_text(response: dict[str, Any]) -> str:
    return json.dumps(response.get("answer", {}), ensure_ascii=False)


def unsupported_source_claims_in_text(text: str, sources: list[dict[str, Any]]) -> list[str]:
    source_text = json.dumps(sources).lower()
    known_source_terms = {
        "income tax act": "income tax",
        "criminal procedure code": "criminal procedure",
        "specific relief act": "specific relief",
    }
    return [term for term, source_hint in known_source_terms.items() if term in text.lower() and source_hint not in source_text]


def provision_matches_source(expected: str, sources: list[dict[str, Any]]) -> bool:
    expected_norm = re.sub(r"[^a-z0-9]+", "", expected.lower())
    for source in sources:
        candidates = [
            source.get("section"),
            source.get("provision"),
            source.get("document"),
            source.get("document_title"),
        ]
        for candidate in candidates:
            candidate_norm = re.sub(r"[^a-z0-9]+", "", str(candidate or "").lower())
            if expected_norm and any(
                marker in candidate_norm
                for marker in (
                    f"section{expected_norm}",
                    f"article{expected_norm}",
                    f"rule{expected_norm}",
                    f"regulation{expected_norm}",
                )
            ):
                return True
    return False


def unsafe_phrase_present(phrase: str, text: str) -> bool:
    lowered = text.lower()
    if phrase == "guaranteed" and re.search(r"\b(cannot|can't|not|no outcome is)\s+be\s+guaranteed\b", lowered):
        lowered = re.sub(r"\b(cannot|can't|not|no outcome is)\s+be\s+guaranteed\b", " ", lowered)
    return phrase in lowered


def pct(count: int, total: int) -> float:
    return round(count / total, 3) if total else 0.0


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    total = len(results)
    return {
        "scenario_count": total,
        "valid_structured_output_rate": pct(sum(1 for r in results if r["evaluation"]["structured_valid"]), total),
        "source_id_validity_rate": pct(sum(1 for r in results if r["evaluation"]["source_id_valid"]), total),
        "unsupported_source_hallucination_rate": pct(sum(1 for r in results if r["evaluation"]["unsupported_source_hallucination"]), total),
        "unsafe_certainty_rate": pct(sum(1 for r in results if r["evaluation"]["unsafe_certainty"]), total),
        "insufficient_context_handling_rate": pct(sum(1 for r in results if r["evaluation"]["insufficient_context_ok"]), total),
        "disclaimer_presence_rate": pct(sum(1 for r in results if r["evaluation"]["disclaimer_present"]), total),
        "expected_document_presence_rate": pct(sum(1 for r in results if r["evaluation"]["expected_document_present"]), total),
        "expected_provision_presence_rate": pct(sum(1 for r in results if r["evaluation"]["expected_provision_present"]), total),
        "overall_heuristic_pass_rate": pct(
            sum(1 for r in results if r["evaluation"]["correct"] and not r["evaluation"]["generation_failed"]),
            total,
        ),
        "failed_generation_count": sum(1 for r in results if r["evaluation"]["generation_failed"]),
    }


def evaluate_grounded_answers(query_path: Path = DEFAULT_QUERY_PATH, delay_seconds: float = 0.0) -> dict[str, Any]:
    scenarios = load_scenarios(query_path)
    results = []
    for index, case in enumerate(scenarios):
        if index and delay_seconds > 0:
            time.sleep(delay_seconds)
        results.append(evaluate_scenario(case))
    latencies = [
        result["response"].get("generation", {}).get("latency_ms")
        for result in results
        if result["response"].get("generation", {}).get("latency_ms") is not None
    ]
    return {
        "evaluation_config": {
            "query_file": query_path.as_posix(),
            "gemini_model": GEMINI_MODEL,
            "retrieval_unchanged": True,
        },
        "metrics": aggregate(results),
        "latency": {
            "generation_calls": len(latencies),
            "scenario_count": len(scenarios),
            "average_generation_latency_ms": round(mean(latencies), 1) if latencies else None,
            "min_generation_latency_ms": min(latencies) if latencies else None,
            "max_generation_latency_ms": max(latencies) if latencies else None,
        },
        "results": results,
        "failures": [r for r in results if not r["evaluation"]["correct"]],
    }


def percent(value: float) -> str:
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    lines = [
        "# Grounded Answer Evaluation",
        "",
        "## Overall Results",
        f"- Scenarios: {metrics['scenario_count']}",
        f"- Valid structured-output rate: {percent(metrics['valid_structured_output_rate'])}",
        f"- Source-ID validity rate: {percent(metrics['source_id_validity_rate'])}",
        f"- Unsupported-source hallucination rate: {percent(metrics['unsupported_source_hallucination_rate'])}",
        f"- Unsafe certainty rate: {percent(metrics['unsafe_certainty_rate'])}",
        f"- Insufficient-context handling rate: {percent(metrics['insufficient_context_handling_rate'])}",
        f"- Disclaimer presence rate: {percent(metrics['disclaimer_presence_rate'])}",
        f"- Expected-document presence rate: {percent(metrics['expected_document_presence_rate'])}",
        f"- Expected-provision presence rate: {percent(metrics['expected_provision_presence_rate'])}",
        f"- Overall heuristic pass rate: {percent(metrics['overall_heuristic_pass_rate'])}",
        "",
        "## Strong Examples",
    ]
    for result in report["results"][:8]:
        if result["evaluation"]["correct"]:
            lines.append(f"- `{result['query']}` -> {len(result['response'].get('sources', []))} source(s)")
    lines.extend(["", "## Failure Examples"])
    if not report["failures"]:
        lines.append("- No failures under the current heuristic checks.")
    for result in report["failures"][:10]:
        lines.append(f"- `{result['query']}`: {result['findings'] or result['error']}")
    lines.extend(
        [
            "",
            "## Manual Spot-Check Candidates",
            "- `landlord cut electricity`",
            "- `online seller refusing refund`",
            "- `cyber fraud online payment`",
            "- `right to equality`",
            "- `RTI application ka reply nahi mila`",
            "- `Instagram seller took payment and blocked me`",
            "",
            "## Gemini Calls And Latency",
            f"- Generation calls: {report['latency']['generation_calls']}",
            f"- Average generation latency: {report['latency']['average_generation_latency_ms']} ms",
            "",
            "## Recommendation",
            "- Part 9B should add claim-to-source citation verification on top of this backend-controlled source-ID approach.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate grounded answer generation.")
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERY_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    args = parser.parse_args()
    report = evaluate_grounded_answers(args.queries, delay_seconds=args.delay_seconds)
    args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    metrics = report["metrics"]
    print(
        "Grounded answer evaluation complete: "
        f"{metrics['scenario_count']} scenarios; "
        f"structured={percent(metrics['valid_structured_output_rate'])}; "
        f"source IDs={percent(metrics['source_id_validity_rate'])}; "
        f"unsafe certainty={percent(metrics['unsafe_certainty_rate'])}"
    )
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.md_output}")


if __name__ == "__main__":
    main()
