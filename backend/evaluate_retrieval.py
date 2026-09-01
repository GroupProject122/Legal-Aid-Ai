from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from config import BASE_DIR, METADATA_PATH, TOP_K
from rag import LegalRAG, final_rerank_score, retrieval_debug_info, select_relevant_chunks

EVAL_DIR = BASE_DIR / "eval"
DEFAULT_QUERY_PATH = EVAL_DIR / "retrieval_queries.json"
DEFAULT_JSON_OUTPUT = EVAL_DIR / "retrieval_evaluation.json"
DEFAULT_MD_OUTPUT = EVAL_DIR / "retrieval_evaluation.md"
RAW_CANDIDATE_K = 10
METRIC_TOP_K = 10

SUPPORTING_DOCUMENT_TYPES = {
    "supporting_criminal_law",
    "supporting_criminal_procedure",
    "supporting_property_law",
    "supporting_document_registration_law",
    "procedural_user_guide",
}


def load_query_set(path: Path = DEFAULT_QUERY_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_vectorstore_metadata(path: Path = METADATA_PATH) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def text_snippet(text: str, limit: int = 220) -> str:
    return re.sub(r"\s+", " ", text or "").strip()[:limit]


def provision_number(record: dict[str, Any]) -> str | None:
    for field in (
        "section_number",
        "article_number",
        "rule_number",
        "regulation_number",
        "guideline_number",
        "heading_number",
        "provision_number",
    ):
        value = record.get(field)
        if value:
            return str(value)
    return None


def provision_title(record: dict[str, Any]) -> str | None:
    for field in (
        "section_title",
        "article_title",
        "rule_title",
        "regulation_title",
        "guideline_title",
        "heading_title",
        "provision_title",
    ):
        value = record.get(field)
        if value:
            return str(value)
    return None


def metadata_lookup(chunks: list[dict[str, Any]]) -> dict[tuple[str, int, str], dict[str, Any]]:
    lookup = {}
    for chunk in chunks:
        source = chunk.get("source") or chunk.get("source_file")
        page = int(chunk.get("page") or 0)
        lookup[(source, page, chunk.get("text") or "")] = chunk
    return lookup


def metadata_for_retrieved(retrieved, lookup: dict[tuple[str, int, str], dict[str, Any]]) -> dict[str, Any]:
    return lookup.get((retrieved.source, retrieved.page, retrieved.text), {})


def serialize_result(rank: int, retrieved, metadata: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": rank,
        "similarity_score": round(retrieved.score, 4),
        "rerank_score": round(retrieved.rerank_score or final_rerank_score("", retrieved), 4),
        "chunk_id": metadata.get("chunk_id"),
        "domain": metadata.get("domain"),
        "document_title": metadata.get("document_title") or retrieved.document_title,
        "structure_type": metadata.get("structure_type"),
        "provision_number": provision_number(metadata),
        "provision_title": provision_title(metadata),
        "source_file": metadata.get("source_file") or retrieved.source,
        "retrieval_priority": metadata.get("retrieval_priority"),
        "authority_level": metadata.get("authority_level"),
        "document_type": metadata.get("document_type"),
        "page": metadata.get("page") or retrieved.page,
        "snippet": text_snippet(retrieved.text),
    }


def ranked_results_for_query(engine: LegalRAG, query: str, lookup: dict[tuple[str, int, str], dict[str, Any]]) -> dict[str, Any]:
    candidates = engine.retrieve_candidates(query, candidate_k=RAW_CANDIDATE_K)
    for candidate in candidates:
        candidate.rerank_score = final_rerank_score(query, candidate)
    ranked = sorted(candidates, key=lambda item: (item.rerank_score, item.score), reverse=True)
    selected = select_relevant_chunks(list(candidates), question=query, top_k=TOP_K)
    return {
        "domain_signals": retrieval_debug_info(query),
        "raw_candidates_top10": [
            {
                **serialize_result(index, candidate, metadata_for_retrieved(candidate, lookup)),
                "domain_debug": retrieval_debug_info(query, candidate),
            }
            for index, candidate in enumerate(candidates[:RAW_CANDIDATE_K], start=1)
        ],
        "reranked_top10": [
            {
                **serialize_result(index, candidate, metadata_for_retrieved(candidate, lookup)),
                "domain_debug": retrieval_debug_info(query, candidate),
            }
            for index, candidate in enumerate(ranked[:METRIC_TOP_K], start=1)
        ],
        "selected_by_current_retrieve": [
            {
                **serialize_result(index, candidate, metadata_for_retrieved(candidate, lookup)),
                "domain_debug": retrieval_debug_info(query, candidate),
            }
            for index, candidate in enumerate(selected, start=1)
        ],
    }


def result_matches_domain(result: dict[str, Any], expected_domains: list[str]) -> bool:
    return result.get("domain") in set(expected_domains or [])


def result_matches_document(result: dict[str, Any], query_case: dict[str, Any]) -> bool:
    expected_docs = set(query_case.get("expected_primary_documents") or [])
    expected_sources = set(query_case.get("expected_primary_sources") or [])
    return result.get("document_title") in expected_docs or result.get("source_file") in expected_sources


def result_matches_provision(result: dict[str, Any], query_case: dict[str, Any]) -> bool:
    expected = {str(item) for item in query_case.get("expected_provision_numbers") or []}
    if not expected:
        return False
    return str(result.get("provision_number") or "") in expected


def hit_at(results: list[dict[str, Any]], predicate, k: int) -> bool:
    return any(predicate(result) for result in results[:k])


def reciprocal_rank(results: list[dict[str, Any]], predicate) -> float:
    for index, result in enumerate(results, start=1):
        if predicate(result):
            return 1.0 / index
    return 0.0


def classify_failure(query_case: dict[str, Any], results: list[dict[str, Any]]) -> list[str]:
    reasons = []
    expected_domains = query_case.get("expected_domain") or []
    top = results[0] if results else {}
    if not results:
        return ["no_results"]
    if expected_domains and top.get("domain") not in expected_domains:
        reasons.append("off-domain semantic similarity")
    if any(result.get("document_type") in SUPPORTING_DOCUMENT_TYPES for result in results[:3]):
        if not hit_at(results, lambda item: result_matches_document(item, query_case), 3):
            reasons.append("broad supporting statute outranking primary source")
    if not hit_at(results, lambda item: result_matches_document(item, query_case), 5):
        if len((query_case.get("query") or "").split()) <= 4:
            reasons.append("generic/common wording")
        else:
            reasons.append("expected primary document absent from Top 5")
    if query_case.get("expected_provision_numbers") and not hit_at(results, lambda item: result_matches_provision(item, query_case), 5):
        reasons.append("expected provision absent from Top 5")
    if len({(r.get("source_file"), r.get("provision_number")) for r in results[:5]}) < min(3, len(results[:5])):
        reasons.append("duplicate/adjacent chunks")
    if not reasons:
        reasons.append("expected label may be too strict")
    return reasons


def evaluate_single_domain(case: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    expected_domains = case.get("expected_domain") or []
    domain_predicate = lambda item: result_matches_domain(item, expected_domains)
    document_predicate = lambda item: result_matches_document(item, case)
    provision_expected = bool(case.get("expected_provision_numbers"))
    provision_predicate = lambda item: result_matches_provision(item, case)
    top5 = results[:5]
    metrics = {
        "domain_hit_at_1": hit_at(results, domain_predicate, 1),
        "domain_hit_at_3": hit_at(results, domain_predicate, 3),
        "document_hit_at_1": hit_at(results, document_predicate, 1),
        "document_hit_at_3": hit_at(results, document_predicate, 3),
        "document_hit_at_5": hit_at(results, document_predicate, 5),
        "provision_hit_at_5": hit_at(results, provision_predicate, 5) if provision_expected else None,
        "document_mrr": reciprocal_rank(results, document_predicate),
        "off_domain_top5_count": sum(not result_matches_domain(result, expected_domains) for result in top5),
    }
    return {
        "metrics": metrics,
        "failure_reasons": [] if metrics["document_hit_at_5"] and metrics["domain_hit_at_3"] else classify_failure(case, results),
    }


def aggregate_metrics(cases: list[dict[str, Any]]) -> dict[str, Any]:
    count = len(cases) or 1
    provision_cases = [case for case in cases if case["evaluation"]["metrics"]["provision_hit_at_5"] is not None]

    def average_bool(field: str) -> float:
        return round(sum(1 for case in cases if case["evaluation"]["metrics"][field]) / count, 3)

    return {
        "query_count": len(cases),
        "domain_hit_at_1": average_bool("domain_hit_at_1"),
        "domain_hit_at_3": average_bool("domain_hit_at_3"),
        "document_hit_at_1": average_bool("document_hit_at_1"),
        "document_hit_at_3": average_bool("document_hit_at_3"),
        "document_hit_at_5": average_bool("document_hit_at_5"),
        "provision_hit_at_5": (
            round(
                sum(1 for case in provision_cases if case["evaluation"]["metrics"]["provision_hit_at_5"])
                / len(provision_cases),
                3,
            )
            if provision_cases
            else None
        ),
        "provision_query_count": len(provision_cases),
        "mrr": round(sum(case["evaluation"]["metrics"]["document_mrr"] for case in cases) / count, 3),
        "average_off_domain_top5_count": round(
            sum(case["evaluation"]["metrics"]["off_domain_top5_count"] for case in cases) / count,
            3,
        ),
    }


def domain_breakdown(cases: list[dict[str, Any]]) -> dict[str, Any]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for case in cases:
        domain = (case.get("expected_domain") or ["unknown"])[0]
        grouped[domain].append(case)
    return {domain: aggregate_metrics(items) for domain, items in sorted(grouped.items())}


def analyze_cross_domain(case: dict[str, Any], results: list[dict[str, Any]]) -> dict[str, Any]:
    expected = set(case.get("expected_domains") or [])
    top5_domains = {result.get("domain") for result in results[:5]}
    top10_domains = {result.get("domain") for result in results[:10]}
    return {
        "expected_domains": sorted(expected),
        "top5_domains": sorted(domain for domain in top5_domains if domain),
        "top10_domains": sorted(domain for domain in top10_domains if domain),
        "all_expected_in_top5": expected.issubset(top5_domains),
        "all_expected_in_top10": expected.issubset(top10_domains),
    }


def supporting_vs_primary_findings(cases: list[dict[str, Any]]) -> list[dict[str, Any]]:
    findings = []
    for case in cases:
        results = case["results"]["reranked_top10"]
        first_primary_rank = next(
            (result["rank"] for result in results if result_matches_document(result, case)),
            None,
        )
        first_supporting = next(
            (result for result in results if result.get("document_type") in SUPPORTING_DOCUMENT_TYPES),
            None,
        )
        if first_supporting and (first_primary_rank is None or first_supporting["rank"] < first_primary_rank):
            findings.append(
                {
                    "query_id": case["id"],
                    "query": case["query"],
                    "supporting_rank": first_supporting["rank"],
                    "supporting_source": first_supporting["source_file"],
                    "supporting_document_type": first_supporting["document_type"],
                    "first_primary_rank": first_primary_rank,
                }
            )
    return findings


def major_failure_patterns(cases: list[dict[str, Any]]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for case in cases:
        for reason in case["evaluation"]["failure_reasons"]:
            counter[reason] += 1
    return dict(counter.most_common())


def run_evaluation(query_path: Path = DEFAULT_QUERY_PATH) -> dict[str, Any]:
    query_set = load_query_set(query_path)
    metadata = load_vectorstore_metadata()
    engine = LegalRAG()
    engine.load()
    lookup = metadata_lookup(metadata.get("chunks", []))

    single_results = []
    for case in query_set.get("single_domain_queries", []):
        retrieved = ranked_results_for_query(engine, case["query"], lookup)
        evaluation = evaluate_single_domain(case, retrieved["reranked_top10"])
        single_results.append({**case, "results": retrieved, "evaluation": evaluation})

    cross_results = []
    for case in query_set.get("cross_domain_queries", []):
        retrieved = ranked_results_for_query(engine, case["query"], lookup)
        cross_results.append({**case, "results": retrieved, "analysis": analyze_cross_domain(case, retrieved["reranked_top10"])})

    non_legal_results = []
    for case in query_set.get("non_legal_queries", []):
        retrieved = ranked_results_for_query(engine, case["query"], lookup)
        non_legal_results.append({**case, "results": retrieved})

    cyber_case = next((case for case in single_results if case["query"] == "cyber fraud online payment"), None)
    return {
        "evaluation_config": {
            "query_file": query_path.as_posix(),
            "metadata_path": METADATA_PATH.as_posix(),
            "embedding_model": metadata.get("embedding_model"),
            "embedding_dimension": metadata.get("embedding_dimension"),
            "faiss_index_type": metadata.get("faiss_index_type"),
            "raw_candidate_k": RAW_CANDIDATE_K,
            "metric_top_k": METRIC_TOP_K,
            "uses_existing_retrieval_query_expansion": True,
            "uses_existing_reranking": True,
            "uses_existing_duplicate_suppression_for_selected_results": True,
            "gemini_called": False,
        },
        "dataset_summary": {
            "single_domain_queries": len(single_results),
            "cross_domain_queries": len(cross_results),
            "non_legal_queries": len(non_legal_results),
            "total_queries": len(single_results) + len(cross_results) + len(non_legal_results),
        },
        "overall_metrics": aggregate_metrics(single_results),
        "domain_breakdown": domain_breakdown(single_results),
        "query_results": single_results,
        "failures": [
            {
                "query_id": case["id"],
                "query": case["query"],
                "expected_domain": case.get("expected_domain"),
                "failure_reasons": case["evaluation"]["failure_reasons"],
                "top_result": case["results"]["reranked_top10"][0] if case["results"]["reranked_top10"] else None,
            }
            for case in single_results
            if case["evaluation"]["failure_reasons"]
        ],
        "failure_patterns": major_failure_patterns(single_results),
        "cyber_specific_analysis": {
            "cyber_fraud_online_payment": cyber_case,
            "cyber_domain_metrics": domain_breakdown(single_results).get("cyber"),
        },
        "supporting_vs_primary_analysis": supporting_vs_primary_findings(single_results),
        "cross_domain_analysis": cross_results,
        "non_legal_queries": non_legal_results,
    }


def pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{value * 100:.1f}%"


def render_markdown(report: dict[str, Any]) -> str:
    overall = report["overall_metrics"]
    domain_metrics = report["domain_breakdown"]
    failures = report["failures"][:8]
    supporting = report["supporting_vs_primary_analysis"][:8]
    cyber_case = report["cyber_specific_analysis"]["cyber_fraud_online_payment"]
    non_legal = report["non_legal_queries"]
    cross = report["cross_domain_analysis"]

    best_domain = max(domain_metrics.items(), key=lambda item: item[1]["document_hit_at_5"])[0]
    weakest_domain = min(domain_metrics.items(), key=lambda item: item[1]["document_hit_at_5"])[0]
    lines = [
        "# Retrieval Evaluation",
        "",
        "## Overall Metrics",
        f"- Single-domain queries: {overall['query_count']}",
        f"- Domain Hit@1: {pct(overall['domain_hit_at_1'])}",
        f"- Domain Hit@3: {pct(overall['domain_hit_at_3'])}",
        f"- Document Hit@1: {pct(overall['document_hit_at_1'])}",
        f"- Document Hit@3: {pct(overall['document_hit_at_3'])}",
        f"- Document Hit@5: {pct(overall['document_hit_at_5'])}",
        f"- Provision Hit@5: {pct(overall['provision_hit_at_5'])} over {overall['provision_query_count']} provision-labelled queries",
        f"- MRR: {overall['mrr']}",
        f"- Average off-domain Top-5 count: {overall['average_off_domain_top5_count']}",
        "",
        "## Domain-wise Performance",
    ]
    for domain, metrics in domain_metrics.items():
        lines.append(
            f"- {domain}: Domain Hit@1 {pct(metrics['domain_hit_at_1'])}, "
            f"Document Hit@5 {pct(metrics['document_hit_at_5'])}, MRR {metrics['mrr']}, "
            f"Avg off-domain Top-5 {metrics['average_off_domain_top5_count']}"
        )
    lines.extend([
        "",
        "## Strong Examples",
    ])
    for case in report["query_results"]:
        metrics = case["evaluation"]["metrics"]
        if metrics["domain_hit_at_1"] and metrics["document_hit_at_1"]:
            top = case["results"]["reranked_top10"][0]
            lines.append(f"- `{case['query']}` -> `{top['source_file']}` ({top['structure_type']} {top.get('provision_number') or ''})")
        if len(lines) > 28:
            break
    lines.extend(["", "## Failure Examples"])
    if not failures:
        lines.append("- No clear failures under the current labels.")
    else:
        for item in failures:
            top = item["top_result"] or {}
            lines.append(
                f"- `{item['query']}`: {', '.join(item['failure_reasons'])}; "
                f"top result `{top.get('source_file')}`"
            )
    lines.extend(["", "## Cyber Retrieval Analysis"])
    if cyber_case:
        top_results = cyber_case["results"]["reranked_top10"][:5]
        lines.append("- `cyber fraud online payment` Top 5:")
        for result in top_results:
            lines.append(
                f"  - rank {result['rank']}: `{result['source_file']}` "
                f"domain `{result['domain']}`, score {result['similarity_score']}, rerank {result['rerank_score']}"
            )
    lines.extend(["", "## Supporting vs Primary Source Issues"])
    if not supporting:
        lines.append("- No supporting-only source outranked expected primary documents under this test set.")
    else:
        for item in supporting:
            lines.append(
                f"- `{item['query']}`: supporting `{item['supporting_source']}` at rank {item['supporting_rank']} "
                f"before first primary rank {item['first_primary_rank']}"
            )
    lines.extend(["", "## Cross-Domain Queries"])
    for item in cross:
        analysis = item["analysis"]
        lines.append(
            f"- `{item['query']}`: expected {analysis['expected_domains']}; "
            f"Top5 {analysis['top5_domains']}; Top10 {analysis['top10_domains']}"
        )
    lines.extend(["", "## Non-Legal Queries"])
    for item in non_legal:
        top = item["results"]["reranked_top10"][0] if item["results"]["reranked_top10"] else {}
        lines.append(f"- `{item['query']}` -> top result `{top.get('source_file')}` domain `{top.get('domain')}`")
    lines.extend([
        "",
        "## Recommended Next Improvements",
        f"- Best-performing domain by Document Hit@5: `{best_domain}`.",
        f"- Weakest-performing domain by Document Hit@5: `{weakest_domain}`.",
        "- Review remaining document-level misses before adding heavier retrieval methods.",
        "- Consider targeted query-intent handling or domain routing only after comparing this report with earlier baselines.",
        "",
    ])
    return "\n".join(lines)


def write_reports(report: dict[str, Any], json_path: Path, md_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(report), encoding="utf-8")


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description="Evaluate current Legal Aid AI retrieval quality.")
    parser.add_argument("--queries", type=Path, default=DEFAULT_QUERY_PATH)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON_OUTPUT)
    parser.add_argument("--md-output", type=Path, default=DEFAULT_MD_OUTPUT)
    args = parser.parse_args(argv)
    report = run_evaluation(args.queries)
    write_reports(report, args.json_output, args.md_output)
    overall = report["overall_metrics"]
    print(
        "Retrieval evaluation complete: "
        f"{report['dataset_summary']['total_queries']} queries; "
        f"Domain Hit@1={pct(overall['domain_hit_at_1'])}; "
        f"Document Hit@5={pct(overall['document_hit_at_5'])}; "
        f"MRR={overall['mrr']}"
    )
    print(f"Wrote {args.json_output}")
    print(f"Wrote {args.md_output}")
    return report


if __name__ == "__main__":
    main()
