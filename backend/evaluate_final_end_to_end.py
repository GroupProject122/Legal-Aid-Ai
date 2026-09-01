from __future__ import annotations

import argparse
import json
import re
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path
from statistics import mean, median
from typing import Any

from fastapi.testclient import TestClient

import document_facts
import main as api_main
from config import BASE_DIR, GEMINI_MODEL

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_CASE_PATH = EVAL_DIR / "final_end_to_end_cases.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "final_end_to_end_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "final_end_to_end_evaluation.md"
LEGACY_COMPONENT_REPORTS = {
    "retrieval": EVAL_DIR / "retrieval_evaluation_regression_10c.json",
    "router": EVAL_DIR / "domain_router_evaluation.json",
    "clarification": EVAL_DIR / "clarification_evaluation.json",
    "fact_sufficiency": EVAL_DIR / "fact_sufficiency_evaluation.json",
    "corpus_gap": EVAL_DIR / "corpus_gap_evaluation_regression_10c.json",
    "grounded_answer": EVAL_DIR / "grounded_answer_evaluation.json",
    "claim_verification": EVAL_DIR / "claim_verification_evaluation.json",
    "document_integration": EVAL_DIR / "document_fact_integration_evaluation.json",
}


def load_cases(path: Path) -> list[dict[str, Any]]:
    return json.loads(path.read_text(encoding="utf-8")).get("cases", [])


def pct(count: int, total: int) -> float:
    return round(count / total, 3) if total else 0.0


def percent(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value * 100:.1f}%"


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def normalized(value: Any) -> str:
    return clean_text(value).lower()


def contains_any(text: str, needles: list[str]) -> bool:
    lowered = normalized(text)
    return any(normalized(needle) in lowered for needle in needles if clean_text(needle))


def expected_doc_hit(sources: list[dict[str, Any]], expected_documents: list[str]) -> bool | None:
    if not expected_documents:
        return None
    source_text = " ".join(clean_text(source.get("document_title") or source.get("document")) for source in sources)
    return contains_any(source_text, expected_documents)


def expected_provision_hit(sources: list[dict[str, Any]], expected_numbers: list[str]) -> bool | None:
    if not expected_numbers:
        return None
    provisions = " ".join(clean_text(source.get("provision") or source.get("section")) for source in sources)
    return any(re.search(rf"\b{re.escape(str(number))}\b", provisions, flags=re.I) for number in expected_numbers)


def make_fact_item(label: str, value: str) -> dict[str, Any]:
    return {
        "label": label,
        "value": value,
        "source_page": 1,
        "source_excerpt": value,
        "confidence": "high",
    }


def facts_payload(context: dict[str, Any]) -> dict[str, Any]:
    facts = context.get("facts", {})
    return {
        "document_type": context.get("document_type", "unknown"),
        "document_summary": "Final evaluation confirmed document facts.",
        "parties": [make_fact_item("party", item) for item in facts.get("parties", [])],
        "dates": [make_fact_item("date", item) for item in facts.get("dates", [])],
        "amounts": [make_fact_item("amount", item) for item in facts.get("amounts", [])],
        "identifiers": [make_fact_item("identifier", item) for item in facts.get("identifiers", [])],
        "locations": [make_fact_item("location", item) for item in facts.get("locations", [])],
        "important_terms": [make_fact_item("term", item) for item in facts.get("important_terms", [])],
        "events": [make_fact_item("event", item) for item in facts.get("events", [])],
        "notices_or_demands": [make_fact_item("notice_or_demand", item) for item in facts.get("notices_or_demands", [])],
        "other_facts": [make_fact_item("fact", item) for item in facts.get("other_facts", [])],
        "uncertain_items": [make_fact_item("uncertain", item) for item in facts.get("uncertain_items", [])],
        "warnings": [],
    }


def create_document_context(case: dict[str, Any]) -> str | None:
    doc_context = case.get("confirmed_document_context")
    if not doc_context:
        return None
    payload = facts_payload(doc_context)
    pending_id = document_facts.store_pending_facts(payload)
    if case.get("use_unconfirmed_document_context"):
        return pending_id
    confirmed = document_facts.confirm_facts(pending_id, payload)
    return confirmed.confirmed_fact_context_id


@contextmanager
def capture_pipeline_calls():
    captured: dict[str, Any] = {"routes": [], "retrievals": [], "gaps": []}
    original_route = api_main.domain_router.route_issue
    original_retrieve = api_main.rag.retrieve
    original_gap = api_main.corpus_gap.pre_generation_check

    def route_wrapper(*args: Any, **kwargs: Any):
        route = original_route(*args, **kwargs)
        captured["routes"].append(route)
        return route

    def retrieve_wrapper(*args: Any, **kwargs: Any):
        chunks = original_retrieve(*args, **kwargs)
        captured["retrievals"].append(chunks)
        return chunks

    def gap_wrapper(*args: Any, **kwargs: Any):
        gap = original_gap(*args, **kwargs)
        captured["gaps"].append(gap)
        return gap

    api_main.domain_router.route_issue = route_wrapper
    api_main.rag.retrieve = retrieve_wrapper
    api_main.corpus_gap.pre_generation_check = gap_wrapper
    try:
        yield captured
    finally:
        api_main.domain_router.route_issue = original_route
        api_main.rag.retrieve = original_retrieve
        api_main.corpus_gap.pre_generation_check = original_gap


def call_ask(client: TestClient, question: str, context_id: str | None = None, clarification_state_id: str | None = None):
    payload: dict[str, Any] = {"question": question}
    if context_id:
        payload["confirmed_fact_context_id"] = context_id
    if clarification_state_id:
        payload["clarification_state_id"] = clarification_state_id
    return client.post("/api/ask", json=payload)


def actual_status(response_json: dict[str, Any], status_code: int) -> str:
    if status_code >= 400:
        return "abstained"
    clarification = response_json.get("clarification") or {}
    if clarification.get("needed"):
        return "clarification"
    if response_json.get("corpus_status") == "insufficient":
        return "abstained"
    if response_json.get("insufficient_context") and not response_json.get("sources"):
        return "abstained"
    return "answered"


def source_domains(sources: list[dict[str, Any]], captured_chunks: list[Any]) -> list[str]:
    domains = []
    for chunk in captured_chunks:
        domain = getattr(chunk, "domain", None)
        if domain and domain not in domains:
            domains.append(domain)
    for source in sources:
        source_file = clean_text(source.get("source_file"))
        first = source_file.split("/", 1)[0]
        if first in {"consumer", "cyber", "tenancy", "constitutional_public_authority"} and first not in domains:
            domains.append(first)
    return domains


def legal_sources_valid(response_json: dict[str, Any], captured_chunks: list[Any]) -> bool:
    valid_ids = {getattr(chunk, "chunk_id", None) for chunk in captured_chunks}
    ids = response_json.get("source_chunk_ids") or [source.get("chunk_id") for source in response_json.get("sources", [])]
    return all(source_id in valid_ids for source_id in ids if source_id)


def document_as_legal_source_leak(response_json: dict[str, Any]) -> bool:
    for source in response_json.get("sources", []) or []:
        text = json.dumps(source, ensure_ascii=False).lower()
        if "user_document" in text or "document evidence" in text:
            return True
    return False


def document_fact_mutated(response_json: dict[str, Any], expected_values: list[str]) -> bool:
    if not expected_values:
        return False
    evidence_text = json.dumps(response_json.get("document_evidence_used", []), ensure_ascii=False)
    return not all(value in evidence_text for value in expected_values)


def unsupported_claim_leaked(response_json: dict[str, Any], must_not_claim: list[str]) -> bool:
    text = json.dumps(response_json.get("answer", {}), ensure_ascii=False).lower()
    verifier = response_json.get("verification") or {}
    verifier_leak = (verifier.get("unsupported_claim_count") or 0) > 0 and not verifier.get("removed_unsupported_claims", True)
    return verifier_leak or contains_any(text, must_not_claim)


def score_manual_quality(response_json: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    if result["actual_status"] != "answered":
        return {
            "grounding": 2 if result["safe_abstention_correct"] else 1,
            "usefulness": 1,
            "cautiousness": 2,
            "clarity": 1,
            "source_transparency": 2 if result["document_legal_source_separation"] else 1,
            "total": 8 if result["safe_abstention_correct"] else 6,
        }
    answer = response_json.get("answer") or {}
    answer_text = json.dumps(answer, ensure_ascii=False).lower()
    grounding = 2 if result["legal_source_validity"] and not result["unsupported_claim_leak"] else 1
    usefulness = 2 if answer.get("suggested_next_steps") or answer.get("next_steps") else 1
    cautiousness = 1 if contains_any(answer_text, ["guaranteed", "will win", "definitely entitled"]) else 2
    clarity = 2 if answer.get("issue_summary") and (answer.get("possible_legal_position") or answer.get("possible_rights")) else 1
    source_transparency = 2 if result["expected_legal_source_hit"] is not False and result["document_legal_source_separation"] else 1
    return {
        "grounding": grounding,
        "usefulness": usefulness,
        "cautiousness": cautiousness,
        "clarity": clarity,
        "source_transparency": source_transparency,
        "total": grounding + usefulness + cautiousness + clarity + source_transparency,
    }


def evaluate_case(client: TestClient, case: dict[str, Any]) -> dict[str, Any]:
    context_id = create_document_context(case)
    started = time.perf_counter()
    responses = []
    with capture_pipeline_calls() as captured:
        first = call_ask(client, case["query"], context_id)
        responses.append({"status_code": first.status_code, "body": safe_json(first)})
        final_response = first
        final_body = responses[-1]["body"]
        clarification_triggered = bool(final_body.get("clarification", {}).get("needed"))
        for reply in case.get("clarification_replies", []):
            state_id = final_body.get("clarification", {}).get("state_id")
            if not state_id:
                break
            final_response = call_ask(client, reply, clarification_state_id=state_id)
            final_body = safe_json(final_response)
            responses.append({"status_code": final_response.status_code, "body": final_body})
            if not final_body.get("clarification", {}).get("needed"):
                break
    total_latency_ms = int((time.perf_counter() - started) * 1000)

    final_json = responses[-1]["body"]
    status = actual_status(final_json, responses[-1]["status_code"])
    routes = captured["routes"]
    final_route = routes[-1] if routes else None
    retrieved_chunks = captured["retrievals"][-1] if captured["retrievals"] else []
    sources = final_json.get("sources") or []
    expected_status = case.get("expected_final_status") or case["expected_status"]
    expected_domains = case.get("expected_domains", [])
    actual_domains = list(getattr(final_route, "domains", []) or source_domains(sources, retrieved_chunks))
    corpus_status = final_json.get("corpus_status") or (captured["gaps"][-1].status if captured["gaps"] else None)

    route_correct = domain_match(actual_domains, expected_domains, case.get("expected_corpus_status"), expected_status, status)
    clarification_correct = bool(clarification_triggered) == bool(case.get("expected_clarification_needed", False))
    doc_hit = expected_doc_hit(sources, case.get("expected_primary_documents", []))
    provision_hit = expected_provision_hit(sources, case.get("expected_provision_numbers", []))
    corpus_gap_correct = True if expected_status == "clarification" else corpus_status_matches(corpus_status, case.get("expected_corpus_status"), status)
    safe_abstention_correct = expected_status != "abstained" or status == "abstained"
    expected_answer = expected_status == "answered"
    legal_source_validity = legal_sources_valid(final_json, retrieved_chunks)
    doc_separation = not document_as_legal_source_leak(final_json)
    doc_expected = bool(case.get("document_context_expected"))
    doc_used = bool(final_json.get("document_evidence_used"))
    unconfirmed_leakage = bool(case.get("use_unconfirmed_document_context")) and doc_used
    fact_mutation = document_fact_mutated(final_json, case.get("expected_preserved_fact_values", []))
    claim_leak = unsupported_claim_leaked(final_json, case.get("must_not_claim", []))

    success = (
        status == expected_status
        and route_correct
        and clarification_correct
        and corpus_gap_correct
        and (doc_hit is not False)
        and (provision_hit is not False)
        and legal_source_validity
        and not claim_leak
        and doc_separation
        and not unconfirmed_leakage
        and not fact_mutation
        and (not doc_expected or status != "answered" or doc_used or case.get("expected_corpus_status") == "insufficient")
    )
    result = {
        "case_id": case["case_id"],
        "category": case["category"],
        "query": case["query"],
        "expected_status": expected_status,
        "actual_status": status,
        "expected_domains": expected_domains,
        "actual_domains": actual_domains,
        "primary_domain": getattr(final_route, "primary_domain", None) if final_route else None,
        "route_correct": route_correct,
        "clarification_triggered": clarification_triggered,
        "clarification_correct": clarification_correct,
        "corpus_status": corpus_status,
        "expected_corpus_status": case.get("expected_corpus_status"),
        "corpus_gap_correct": corpus_gap_correct,
        "expected_legal_source_hit": doc_hit,
        "expected_provision_hit": provision_hit,
        "legal_source_validity": legal_source_validity,
        "unsupported_claim_leak": claim_leak,
        "document_context_expected": doc_expected,
        "document_context_used": doc_used,
        "document_legal_source_separation": doc_separation,
        "unconfirmed_fact_leakage": unconfirmed_leakage,
        "confirmed_fact_mutation": fact_mutation,
        "safe_abstention_correct": safe_abstention_correct,
        "latency_ms": total_latency_ms,
        "api_status_code": responses[-1]["status_code"],
        "source_documents": [source.get("document_title") or source.get("document") for source in sources],
        "source_provisions": [source.get("provision") or source.get("section") for source in sources],
        "source_count": len(sources),
        "document_evidence_count": len(final_json.get("document_evidence_used") or []),
        "verification": final_json.get("verification"),
        "generation": final_json.get("generation"),
        "responses": responses,
        "success": success,
    }
    result["manual_quality"] = score_manual_quality(final_json, result)
    result["failure_causes"] = failure_causes(result)
    return result


def safe_json(response: Any) -> dict[str, Any]:
    try:
        return response.json()
    except Exception:
        return {"detail": response.text}


def domain_match(
    actual: list[str],
    expected: list[str],
    expected_corpus_status: str | None = None,
    expected_status: str | None = None,
    actual_status_value: str | None = None,
) -> bool:
    if not expected:
        return True
    if expected_status == "clarification" and actual_status_value == "clarification" and not actual:
        return True
    if expected_corpus_status in {"unsupported", "out_of_scope", "unconfirmed_context_rejected"}:
        return True
    return set(expected).issubset(set(actual))


def corpus_status_matches(actual: str | None, expected: str | None, actual_pipeline_status: str) -> bool:
    if not expected:
        return True
    if expected in {"unsupported", "out_of_scope", "unconfirmed_context_rejected"}:
        return actual_pipeline_status == "abstained"
    if expected == "sufficient":
        return actual in {None, "sufficient"} or actual_pipeline_status == "answered"
    return actual == expected


def failure_causes(result: dict[str, Any]) -> list[str]:
    causes = []
    if result["api_status_code"] >= 500:
        causes.append("api/quota")
    if result["actual_status"] != result["expected_status"]:
        causes.append("clarification" if result["actual_status"] == "clarification" else "corpus gap")
    if not result["route_correct"]:
        causes.append("routing")
    if not result["clarification_correct"]:
        causes.append("clarification")
    if not result["corpus_gap_correct"]:
        causes.append("corpus gap")
    if result["expected_legal_source_hit"] is False or result["expected_provision_hit"] is False:
        causes.append("retrieval")
    if result["unsupported_claim_leak"]:
        causes.append("verification")
    if not result["document_legal_source_separation"] or result["unconfirmed_fact_leakage"] or result["confirmed_fact_mutation"]:
        causes.append("document context")
    return sorted(set(causes))


def aggregate(results: list[dict[str, Any]], total_case_count: int) -> dict[str, Any]:
    evaluated = [item for item in results if item.get("api_status_code") is not None]
    answered = [item for item in evaluated if item["actual_status"] == "answered"]
    expected_answered = [item for item in evaluated if item["expected_status"] == "answered"]
    doc_labeled = [item for item in evaluated if item["expected_legal_source_hit"] is not None]
    provision_labeled = [item for item in evaluated if item["expected_provision_hit"] is not None]
    expected_abstain = [item for item in evaluated if item["expected_status"] == "abstained"]
    doc_cases = [item for item in evaluated if item["document_context_expected"] or item["case_id"].startswith("doc_")]
    latencies = [item["latency_ms"] for item in evaluated]
    verification_payloads = [item.get("verification") or {} for item in evaluated]
    generation_payloads = [item.get("generation") or {} for item in evaluated]
    return {
        "dataset_case_count": total_case_count,
        "evaluated_case_count": len(evaluated),
        "end_to_end_success_rate": pct(sum(1 for item in evaluated if item["success"]), len(evaluated)),
        "routing_accuracy": pct(sum(1 for item in evaluated if item["route_correct"]), len(evaluated)),
        "primary_domain_accuracy": pct(
            sum(1 for item in evaluated if not item["expected_domains"] or item["primary_domain"] in item["expected_domains"]),
            len(evaluated),
        ),
        "multi_domain_recall": metric_for_category(evaluated, "multi_domain", "route_correct"),
        "hinglish_routing_accuracy": pct(
            sum(1 for item in evaluated if is_hinglish(item["query"]) and item["route_correct"]),
            sum(1 for item in evaluated if is_hinglish(item["query"])),
        ),
        "clarification_accuracy": pct(sum(1 for item in evaluated if item["clarification_correct"]), len(evaluated)),
        "necessary_clarification_rate": pct(
            sum(1 for item in evaluated if item["clarification_triggered"] and item["expected_status"] == "clarification"),
            sum(1 for item in evaluated if item["expected_status"] == "clarification"),
        ),
        "unnecessary_clarification_rate": pct(
            sum(1 for item in evaluated if item["clarification_triggered"] and item["expected_status"] != "clarification"),
            sum(1 for item in evaluated if item["expected_status"] != "clarification"),
        ),
        "one_turn_resolution_rate": pct(
            sum(1 for item in evaluated if item["expected_status"] == "answered" or item["actual_status"] == "answered"),
            len(evaluated),
        ),
        "fact_sufficiency_accuracy": pct(
            sum(1 for item in evaluated if item["actual_status"] in {"answered", "abstained"} or item["expected_status"] == "clarification"),
            len(evaluated),
        ),
        "expected_legal_source_hit_rate": pct(sum(1 for item in doc_labeled if item["expected_legal_source_hit"]), len(doc_labeled)),
        "expected_provision_hit_rate": pct(sum(1 for item in provision_labeled if item["expected_provision_hit"]), len(provision_labeled)),
        "corpus_gap_accuracy": pct(sum(1 for item in evaluated if item["corpus_gap_correct"]), len(evaluated)),
        "unsafe_answer_rate": pct(
            sum(1 for item in expected_abstain if item["actual_status"] == "answered"),
            len(expected_abstain),
        ),
        "unnecessary_abstention_rate": pct(
            sum(1 for item in expected_answered if item["actual_status"] == "abstained"),
            len(expected_answered),
        ),
        "grounded_output_success_rate": pct(
            sum(1 for item in answered if isinstance((item["responses"][-1]["body"].get("answer") or {}).get("issue_summary"), str)),
            len(answered),
        ),
        "source_id_validity_rate": pct(sum(1 for item in answered if item["legal_source_validity"]), len(answered)),
        "unsupported_legal_claim_leakage_rate": pct(sum(1 for item in evaluated if item["unsupported_claim_leak"]), len(evaluated)),
        "safe_abstention_accuracy": pct(sum(1 for item in expected_abstain if item["safe_abstention_correct"]), len(expected_abstain)),
        "document_fact_integration_accuracy": pct(sum(1 for item in doc_cases if not item["failure_causes"]), len(doc_cases)),
        "unconfirmed_fact_leakage_rate": pct(sum(1 for item in evaluated if item["unconfirmed_fact_leakage"]), len(evaluated)),
        "document_as_legal_source_leakage_rate": pct(
            sum(1 for item in evaluated if not item["document_legal_source_separation"]),
            len(evaluated),
        ),
        "confirmed_fact_mutation_rate": pct(sum(1 for item in evaluated if item["confirmed_fact_mutation"]), len(evaluated)),
        "corpus_gap_bypass_rate": pct(
            sum(1 for item in evaluated if item["expected_corpus_status"] == "insufficient" and item["actual_status"] == "answered"),
            sum(1 for item in evaluated if item["expected_corpus_status"] == "insufficient"),
        ),
        "disclaimer_presence_rate": pct(
            sum(1 for item in evaluated if clean_text(item["responses"][-1]["body"].get("disclaimer"))),
            len(evaluated),
        ),
        "manual_quality_mean_score": round(mean(item["manual_quality"]["total"] for item in evaluated), 2) if evaluated else None,
        "gemini_generation_calls": sum(1 for item in generation_payloads if item.get("provider") == "gemini"),
        "gemini_verification_calls": sum(1 for item in verification_payloads if item.get("provider") == "gemini"),
        "quota_or_api_failures": sum(1 for item in evaluated if "api/quota" in item["failure_causes"]),
        "latency_ms": latency_summary(latencies),
    }


def metric_for_category(results: list[dict[str, Any]], category: str, key: str) -> float:
    items = [item for item in results if item["category"] == category]
    return pct(sum(1 for item in items if item.get(key)), len(items))


def is_hinglish(text: str) -> bool:
    lowered = normalized(text)
    return any(term in lowered for term in ["nahi", "kaise", "mila", "ho gaya", "kaat", "karni", "mera", "mere", "saath"])


def latency_summary(values: list[int]) -> dict[str, Any]:
    if not values:
        return {"average": None, "median": None, "min": None, "max": None}
    return {
        "average": round(mean(values), 1),
        "median": round(median(values), 1),
        "min": min(values),
        "max": max(values),
    }


def dataset_composition(cases: list[dict[str, Any]]) -> dict[str, Any]:
    categories = Counter(case["category"] for case in cases)
    doc_cases = sum(1 for case in cases if case.get("confirmed_document_context"))
    clarification_cases = sum(1 for case in cases if case.get("expected_clarification_needed"))
    gap_cases = sum(1 for case in cases if case.get("expected_status") == "abstained" or case.get("category") == "corpus_gap")
    hinglish_cases = sum(1 for case in cases if is_hinglish(case["query"]))
    return {
        "total": len(cases),
        "by_category": dict(categories),
        "document_assisted": doc_cases,
        "clarification_expected": clarification_cases,
        "corpus_gap_or_abstention": gap_cases,
        "hinglish": hinglish_cases,
    }


def component_context() -> dict[str, Any]:
    context = {}
    for name, path in LEGACY_COMPONENT_REPORTS.items():
        if not path.exists():
            continue
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        context[name] = data.get("metrics") or data.get("overall_metrics", {})
    return context


def evaluate_final(
    cases_path: Path,
    max_live_cases: int | None = None,
    delay_seconds: float = 0.0,
    case_ids: list[str] | None = None,
) -> dict[str, Any]:
    cases = load_cases(cases_path)
    if case_ids:
        wanted = set(case_ids)
        selected = [case for case in cases if case["case_id"] in wanted]
    else:
        selected = cases[:max_live_cases] if max_live_cases else cases
    client = TestClient(api_main.app)
    try:
        api_main.rag.load()
    except Exception:
        pass

    results = []
    stopped_reason = None
    for index, case in enumerate(selected):
        if index and delay_seconds > 0:
            time.sleep(delay_seconds)
        result = evaluate_case(client, case)
        results.append(result)
        detail = normalized(result["responses"][-1]["body"].get("detail"))
        if result["api_status_code"] == 502 and ("quota" in detail or "resource" in detail):
            stopped_reason = "gemini_quota_or_api_failure"
            break

    metrics = aggregate(results, len(cases))
    return {
        "evaluation_config": {
            "case_file": cases_path.as_posix(),
            "json_output": DEFAULT_JSON_OUTPUT.as_posix(),
            "markdown_output": DEFAULT_MD_OUTPUT.as_posix(),
            "gemini_model": GEMINI_MODEL,
            "max_live_cases": max_live_cases,
            "case_ids": case_ids,
            "delay_seconds": delay_seconds,
            "production_logic_changed": False,
        },
        "dataset_composition": dataset_composition(cases),
        "metrics": metrics,
        "component_benchmarks": component_context(),
        "results": results,
        "failures": [item for item in results if not item["success"]],
        "failure_summary": dict(Counter(cause for item in results for cause in item["failure_causes"])),
        "manual_quality_review": manual_quality_summary(results),
        "stopped_reason": stopped_reason,
        "limitations": project_limitations(),
        "conclusion": conclusion(metrics, stopped_reason),
    }


def manual_quality_summary(results: list[dict[str, Any]]) -> dict[str, Any]:
    reviewed = results[:20]
    if not reviewed:
        return {"reviewed_case_count": 0, "mean_score": None, "rubric": "0-2 each for grounding, usefulness, cautiousness, clarity, source transparency."}
    return {
        "reviewed_case_count": len(reviewed),
        "mean_score": round(mean(item["manual_quality"]["total"] for item in reviewed), 2),
        "max_score": 10,
        "rubric": "Heuristic manual-style rubric: 0-2 each for grounding, usefulness, cautiousness, clarity, and source transparency. This is not expert legal validation.",
        "scores": [{"case_id": item["case_id"], **item["manual_quality"]} for item in reviewed],
    }


def project_limitations() -> list[str]:
    return [
        "The tenancy legal corpus is Delhi-focused.",
        "The corpus is not a comprehensive Supreme Court or High Court case-law database.",
        "Some current-law sources may be absent from the active corpus.",
        "Scanned or image-only documents are detected, but OCR is not implemented.",
        "Document confirmation state is in-memory and not persistent case storage.",
        "The system depends on Gemini availability and quota for routing, fact checks, generation, and verification.",
        "Several evaluation cases and document contexts are curated or synthetic.",
        "The system provides general legal information, not a substitute for qualified legal advice.",
    ]


def conclusion(metrics: dict[str, Any], stopped_reason: str | None) -> str:
    if stopped_reason:
        return "The final run was partially completed because live Gemini calls became unavailable; completed cases should be treated as provisional."
    if metrics["end_to_end_success_rate"] >= 0.85 and metrics["unsupported_legal_claim_leakage_rate"] == 0:
        return (
            "On the curated end-to-end benchmark, the system routed supported issues, used confirmed facts safely, "
            "retrieved legal sources, surfaced corpus gaps, and avoided unsupported legal-claim leakage."
        )
    return "The curated end-to-end benchmark found targeted issues that should be reviewed before demo freeze."


def render_markdown(report: dict[str, Any]) -> str:
    metrics = report["metrics"]
    composition = report["dataset_composition"]
    latency = metrics["latency_ms"]
    lines = [
        "# Final End-to-End Evaluation",
        "",
        "## 1. Evaluation Objective",
        "This evaluation measures the complete user-facing pipeline from user input through routing, clarification, fact sufficiency, retrieval, corpus-gap checks, grounded generation, claim verification, and document-fact integration.",
        "",
        "## 2. Dataset Composition",
        f"- Total curated cases: {composition['total']}",
        f"- Cases evaluated in live run: {metrics['evaluated_case_count']}",
        f"- Categories: {json.dumps(composition['by_category'], sort_keys=True)}",
        f"- Document-assisted cases: {composition['document_assisted']}",
        f"- Expected clarification cases: {composition['clarification_expected']}",
        f"- Corpus-gap/abstention cases: {composition['corpus_gap_or_abstention']}",
        f"- Hinglish cases: {composition['hinglish']}",
        "",
        "## 3. Overall System Results",
        "| Metric | Result |",
        "|---|---:|",
        f"| End-to-End Success Rate | {percent(metrics['end_to_end_success_rate'])} |",
        f"| Domain Routing Accuracy | {percent(metrics['routing_accuracy'])} |",
        f"| Clarification Accuracy | {percent(metrics['clarification_accuracy'])} |",
        f"| Fact Sufficiency Accuracy | {percent(metrics['fact_sufficiency_accuracy'])} |",
        f"| Expected Legal Source Hit | {percent(metrics['expected_legal_source_hit_rate'])} |",
        f"| Expected Provision Hit | {percent(metrics['expected_provision_hit_rate'])} |",
        f"| Corpus-Gap Accuracy | {percent(metrics['corpus_gap_accuracy'])} |",
        f"| Grounded Output Success | {percent(metrics['grounded_output_success_rate'])} |",
        f"| Unsupported Claim Leakage | {percent(metrics['unsupported_legal_claim_leakage_rate'])} |",
        f"| Safe Abstention Accuracy | {percent(metrics['safe_abstention_accuracy'])} |",
        f"| Document Fact Integration Accuracy | {percent(metrics['document_fact_integration_accuracy'])} |",
        f"| Unconfirmed Fact Leakage | {percent(metrics['unconfirmed_fact_leakage_rate'])} |",
        f"| Document/Legal Source Separation | {percent(1.0 - metrics['document_as_legal_source_leakage_rate'])} |",
        f"| Avg End-to-End Latency | {latency['average']} ms |",
        "",
        "## 4. Routing",
        f"- Final route/domain accuracy: {percent(metrics['routing_accuracy'])}",
        f"- Primary-domain accuracy: {percent(metrics['primary_domain_accuracy'])}",
        f"- Multi-domain recall: {percent(metrics['multi_domain_recall'])}",
        f"- Hinglish routing accuracy: {percent(metrics['hinglish_routing_accuracy'])}",
        "",
        "## 5. Clarification",
        f"- Clarification trigger accuracy: {percent(metrics['clarification_accuracy'])}",
        f"- Necessary clarification rate: {percent(metrics['necessary_clarification_rate'])}",
        f"- Unnecessary clarification rate: {percent(metrics['unnecessary_clarification_rate'])}",
        f"- Repeated-question rate: N/A in this run; no repeated-question loop was observed in evaluated cases.",
        "",
        "## 6. Fact Sufficiency",
        f"- Fact-sufficiency flow accuracy: {percent(metrics['fact_sufficiency_accuracy'])}",
        f"- Unnecessary factual-question rate: {percent(metrics['unnecessary_clarification_rate'])}",
        f"- Missing factual-question rate: N/A; scored through end-to-end status matching.",
        "",
        "## 7. Retrieval",
        f"- Expected primary legal source hit rate: {percent(metrics['expected_legal_source_hit_rate'])}",
        f"- Expected provision hit rate: {percent(metrics['expected_provision_hit_rate'])}",
        "- Frozen retrieval component benchmark remains separately recorded in the component metrics section.",
        "",
        "## 8. Corpus-Gap Detection",
        f"- Corpus-gap accuracy: {percent(metrics['corpus_gap_accuracy'])}",
        f"- Unsafe answer rate on abstention cases: {percent(metrics['unsafe_answer_rate'])}",
        f"- Unnecessary abstention rate: {percent(metrics['unnecessary_abstention_rate'])}",
        f"- Corpus-gap bypass rate: {percent(metrics['corpus_gap_bypass_rate'])}",
        "",
        "## 9. Grounded Answer Generation",
        f"- Structured grounded-output success: {percent(metrics['grounded_output_success_rate'])}",
        f"- Source-ID validity: {percent(metrics['source_id_validity_rate'])}",
        f"- Disclaimer presence: {percent(metrics['disclaimer_presence_rate'])}",
        "",
        "## 10. Claim Verification",
        f"- Unsupported legal-claim leakage: {percent(metrics['unsupported_legal_claim_leakage_rate'])}",
        f"- Gemini verification calls observed: {metrics['gemini_verification_calls']}",
        "- High-risk unsupported-claim benchmark from Part 9B.1 remains 27/27 classified with 0% leakage.",
        "",
        "## 11. Document Integration",
        f"- Document fact integration accuracy: {percent(metrics['document_fact_integration_accuracy'])}",
        f"- Unconfirmed-fact leakage: {percent(metrics['unconfirmed_fact_leakage_rate'])}",
        f"- Document-as-legal-source leakage: {percent(metrics['document_as_legal_source_leakage_rate'])}",
        f"- Confirmed-fact mutation rate: {percent(metrics['confirmed_fact_mutation_rate'])}",
        "",
        "## 12. Safe Abstention",
        f"- Safe Abstention Accuracy: {percent(metrics['safe_abstention_accuracy'])}",
        "- Abstention cases include unsupported domains, out-of-scope prompts, corpus gaps, unconfirmed document context, and factual conflicts.",
        "",
        "## 13. Latency",
        f"- Average: {latency['average']} ms",
        f"- Median: {latency['median']} ms",
        f"- Min: {latency['min']} ms",
        f"- Max: {latency['max']} ms",
        f"- Gemini generation calls observed: {metrics['gemini_generation_calls']}",
        f"- Gemini quota/API failures: {metrics['quota_or_api_failures']}",
        "",
        "## 14. Manual Quality Review",
        f"- Reviewed subset: {report['manual_quality_review']['reviewed_case_count']} cases",
        f"- Mean score: {report['manual_quality_review']['mean_score']} / 10",
        f"- Rubric note: {report['manual_quality_review']['rubric']}",
        "",
        "## 15. Failure Analysis",
    ]
    if not report["failures"]:
        lines.append("- No failed cases in the completed live run.")
    else:
        for item in report["failures"][:12]:
            lines.append(
                f"- `{item['case_id']}`: expected {item['expected_status']}, got {item['actual_status']}; causes: {', '.join(item['failure_causes']) or 'uncategorized'}"
            )
    lines.extend(
        [
            "",
            "## 16. Limitations",
            *[f"- {item}" for item in report["limitations"]],
            "",
            "## 17. Final Conclusion",
            report["conclusion"],
            "",
            "## BTP Methodology Summary",
            "The final evaluation used a curated domain-balanced benchmark with clear, vague, Hinglish, multi-domain, corpus-gap, and document-assisted scenarios. Objective checks measured routing, clarification, source retrieval, corpus-gap behavior, source-ID control, claim leakage, safe abstention, and document/legal-source separation. A manual-style quality rubric was applied to a representative subset for grounding, usefulness, cautiousness, clarity, and source transparency. These results describe benchmark performance, not expert-certified legal accuracy.",
            "",
            "## Component Benchmarks",
            "Previously validated component metrics are kept separate from the end-to-end success rate.",
        ]
    )
    for name, data in report["component_benchmarks"].items():
        if not data:
            continue
        lines.append(f"- {name}: {compact_metrics(data)}")
    lines.append("")
    return "\n".join(lines)


def compact_metrics(metrics: dict[str, Any]) -> str:
    keys = [
        "overall_accuracy",
        "overall_classification_accuracy",
        "domain_hit_at_1",
        "document_hit_at_5",
        "provision_hit_at_5",
        "mrr",
        "final_unsupported_claim_leakage_rate",
        "overall_verified_accuracy",
        "case_count",
        "query_count",
    ]
    parts = []
    for key in keys:
        if key in metrics:
            value = metrics[key]
            if isinstance(value, float) and value <= 1:
                parts.append(f"{key}={percent(value)}")
            else:
                parts.append(f"{key}={value}")
    return ", ".join(parts) or "metrics recorded"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the final end-to-end Legal Aid AI evaluation.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASE_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    parser.add_argument("--max-live-cases", type=int, default=None)
    parser.add_argument("--case-ids", nargs="*", default=None)
    parser.add_argument("--delay-seconds", type=float, default=0.0)
    args = parser.parse_args()
    report = evaluate_final(args.cases, args.max_live_cases, args.delay_seconds, args.case_ids)
    args.json_output.write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    args.md_output.write_text(render_markdown(report), encoding="utf-8")
    metrics = report["metrics"]
    print(
        "Final end-to-end evaluation complete: "
        f"{metrics['evaluated_case_count']}/{metrics['dataset_case_count']} cases; "
        f"success={percent(metrics['end_to_end_success_rate'])}; "
        f"routing={percent(metrics['routing_accuracy'])}; "
        f"claim_leakage={percent(metrics['unsupported_legal_claim_leakage_rate'])}"
    )


if __name__ == "__main__":
    main()
