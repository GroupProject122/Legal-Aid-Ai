from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from config import DISCLAIMER, GEMINI_API_KEY, GEMINI_MODEL
import grounded_answer

logger = logging.getLogger("legal_aid_ai.corpus_gap")

STATUSES = {"sufficient", "limited", "insufficient"}
REASON_CODES = {
    "no_relevant_source",
    "weak_retrieval",
    "missing_primary_authority",
    "jurisdiction_not_covered",
    "domain_not_fully_covered",
    "missing_current_law",
    "source_conflict",
    "fact_law_mismatch",
    "supporting_sources_only",
    "case_law_not_in_corpus",
    "verification_removed_core_claims",
}


@dataclass
class CorpusGapResult:
    status: str
    reason_codes: list[str]
    summary: str
    allow_grounded_answer: bool
    require_limitation: bool = False
    suggest_professional_help: bool = False
    source: str = "deterministic"
    latency_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


CORPUS_GAP_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": sorted(STATUSES)},
        "reason_codes": {"type": "array", "items": {"type": "string"}},
        "summary": {"type": "string"},
        "allow_grounded_answer": {"type": "boolean"},
        "require_limitation": {"type": "boolean"},
        "suggest_professional_help": {"type": "boolean"},
    },
    "required": [
        "status",
        "reason_codes",
        "summary",
        "allow_grounded_answer",
        "require_limitation",
        "suggest_professional_help",
    ],
}

CORPUS_SCOPE = """Current Legal Aid AI corpus scope:
- consumer: Consumer Protection Act, consumer rules/regulations, e-commerce, direct selling, misleading ads, dark patterns.
- cyber: Information Technology Act, Intermediary Rules, DPDP Rules 2025, cybercrime portal user guide, and limited supporting criminal-law material. Standalone DPDP Act 2023 and CERT-In Directions 2022 are not currently in the corpus.
- tenancy: Delhi-focused tenancy pilot with Delhi rent-control material and supporting property/registration statutes. Non-Delhi tenancy disputes are not reliably covered.
- constitutional_public_authority: Constitution, RTI, Legal Services Authorities, Human Rights, and Contempt sources. Comprehensive case law is not included.
"""

CORPUS_GAP_PROMPT = """You assess whether supplied retrieved legal material is sufficient for a grounded legal-information answer.
Do not answer the legal issue.
Do not cite new law.
Do not use outside legal knowledge.
Use only the issue summary, routed domains, corpus scope, and retrieved source snippets.
Return sufficient if the sources are enough for a useful grounded answer.
Return limited if useful material exists but coverage is materially incomplete.
Return insufficient if the corpus/retrieved evidence cannot support a reliable answer.
Return only structured JSON.
"""


def pre_generation_check(issue_summary: str, domains: list[str], chunks: list[Any]) -> CorpusGapResult:
    deterministic = deterministic_pre_check(issue_summary, domains, chunks)
    if deterministic.status != "limited" or deterministic.reason_codes:
        return deterministic
    ambiguous = should_use_gemini_for_ambiguity(issue_summary, domains, chunks)
    if not ambiguous:
        return deterministic
    gemini_result = gemini_gap_assessment(issue_summary, domains, chunks)
    return gemini_result or deterministic


def post_generation_check(response: dict[str, Any], pre_result: CorpusGapResult) -> CorpusGapResult:
    if response.get("insufficient_context") is True:
        return CorpusGapResult(
            status="insufficient",
            reason_codes=merge_reason_codes(pre_result.reason_codes, ["no_relevant_source"]),
            summary="The generated answer itself indicates that the retrieved material is insufficient.",
            allow_grounded_answer=False,
            require_limitation=True,
            suggest_professional_help=True,
            source="post_generation",
        )
    verification = response.get("verification") or {}
    claim_count = int(verification.get("claim_count") or 0)
    removed = int(verification.get("removed_claim_count") or 0)
    verified = int(verification.get("verified_claim_count") or 0)
    partial = int(verification.get("partially_supported_claim_count") or 0)
    if claim_count and removed >= claim_count and verified == 0 and partial == 0:
        return CorpusGapResult(
            status="insufficient",
            reason_codes=merge_reason_codes(pre_result.reason_codes, ["verification_removed_core_claims"]),
            summary="Claim verification removed the substantive legal claims, so the corpus support is not enough for a reliable answer.",
            allow_grounded_answer=False,
            require_limitation=True,
            suggest_professional_help=True,
            source="post_verification",
        )
    if claim_count and removed / claim_count >= 0.5:
        return CorpusGapResult(
            status="limited",
            reason_codes=merge_reason_codes(pre_result.reason_codes, ["verification_removed_core_claims"]),
            summary="Some generated points were not clearly supported by the retrieved sources, so the answer should be treated as limited.",
            allow_grounded_answer=True,
            require_limitation=True,
            suggest_professional_help=pre_result.suggest_professional_help,
            source="post_verification",
        )
    return pre_result


def deterministic_pre_check(issue_summary: str, domains: list[str], chunks: list[Any]) -> CorpusGapResult:
    text = normalize(issue_summary)
    if not chunks:
        return result("insufficient", ["no_relevant_source"], "No relevant legal source was retrieved.", False, True, True)
    if explicit_non_delhi_tenancy(text, domains):
        return result(
            "insufficient",
            ["jurisdiction_not_covered"],
            "The tenancy corpus is currently Delhi-focused, so it cannot reliably answer this non-Delhi tenancy issue.",
            False,
            True,
            True,
        )
    if case_law_query(text):
        return result(
            "insufficient",
            ["case_law_not_in_corpus"],
            "The current corpus does not include comprehensive case-law material for this specific case-law question.",
            False,
            True,
            True,
        )
    if unsupported_legal_gap_query(text, chunks):
        return result(
            "insufficient",
            ["domain_not_fully_covered", "missing_primary_authority"],
            "The current corpus does not contain the primary legal source needed for this issue.",
            False,
            True,
            True,
        )
    if missing_current_law_query(text, chunks):
        return result(
            "limited",
            ["missing_current_law", "domain_not_fully_covered"],
            "Some useful cyber material is available, but a source that may be material to this issue is not present in the current corpus.",
            True,
            True,
            True,
        )
    domain_match_count = sum(1 for chunk in chunks if getattr(chunk, "domain", None) in set(domains))
    top_score = max(float(getattr(chunk, "rerank_score", None) or getattr(chunk, "score", 0.0) or 0.0) for chunk in chunks)
    primary_count = sum(1 for chunk in chunks if is_primary_source(chunk))
    supporting_count = sum(1 for chunk in chunks if is_supporting_only(chunk))
    if domain_match_count == 0:
        return result("insufficient", ["fact_law_mismatch"], "Retrieved sources do not match the routed legal domain.", False, True, True)
    if top_score < 0.34 and primary_count == 0:
        return result("insufficient", ["weak_retrieval", "missing_primary_authority"], "Only weak, non-primary legal material was retrieved.", False, True, True)
    if primary_count == 0 and supporting_count:
        return result("limited", ["supporting_sources_only", "missing_primary_authority"], "Only supporting or procedural sources were retrieved.", True, True, False)
    if top_score < 0.42:
        return result("limited", ["weak_retrieval"], "The retrieved material appears relevant but not especially strong.", True, True, False)
    return result("sufficient", [], "The retrieved corpus material appears sufficient for a grounded answer.", True, False, False)


def apply_gap_to_response(response: dict[str, Any], gap: CorpusGapResult) -> dict[str, Any]:
    response["corpus_gap"] = gap.to_dict()
    response["corpus_status"] = gap.status
    if gap.status == "limited" and gap.summary:
        answer = response.setdefault("answer", {})
        limitations = list(answer.get("limitations") or [])
        limitations.insert(0, gap.summary)
        answer["limitations"] = grounded_answer.clean_list(limitations, 5)
    if gap.suggest_professional_help:
        answer = response.setdefault("answer", {})
        steps = list(answer.get("suggested_next_steps") or answer.get("next_steps") or [])
        steps.append("Consider checking an official source or speaking with a qualified legal professional for this gap.")
        answer["suggested_next_steps"] = grounded_answer.clean_list(steps, 5)
        answer["next_steps"] = answer["suggested_next_steps"]
    return response


def abstention_response(gap: CorpusGapResult) -> dict[str, Any]:
    next_steps = ["Try asking with a narrower issue or check an official source that covers this legal area."]
    if gap.suggest_professional_help:
        next_steps.append("Consider speaking with a qualified legal professional before relying on this corpus for the issue.")
    return {
        "answer": {
            "issue_summary": gap.summary,
            "what_this_may_involve": [],
            "possible_legal_position": [],
            "suggested_next_steps": next_steps,
            "evidence_to_preserve": [],
            "where_to_approach": [],
            "limitations": [gap.summary],
            "possible_rights": [],
            "next_steps": next_steps,
        },
        "sources": [],
        "confidence": "low",
        "insufficient_context": True,
        "disclaimer": DISCLAIMER,
        "source_chunk_ids": [],
        "corpus_status": gap.status,
        "corpus_gap": gap.to_dict(),
    }


def gemini_gap_assessment(issue_summary: str, domains: list[str], chunks: list[Any]) -> CorpusGapResult | None:
    if not GEMINI_API_KEY:
        return None
    started = time.perf_counter()
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=build_gap_prompt(issue_summary, domains, chunks),
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
                response_schema=CORPUS_GAP_SCHEMA,
            ),
        )
        parsed = json.loads(response.text or "{}")
        return normalize_gap_result(parsed, source="gemini", latency_ms=int((time.perf_counter() - started) * 1000))
    except (genai_errors.APIError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Gemini corpus-gap assessment failed: %s: %s", exc.__class__.__name__, str(exc))
        return None


def build_gap_prompt(issue_summary: str, domains: list[str], chunks: list[Any]) -> str:
    snippets = []
    for chunk in chunks[:5]:
        snippets.append(
            {
                "chunk_id": grounded_answer.chunk_id(chunk),
                "domain": getattr(chunk, "domain", None),
                "document_title": getattr(chunk, "document_title", None),
                "authority_level": getattr(chunk, "authority_level", None),
                "status": getattr(chunk, "status", None),
                "score": round(float(getattr(chunk, "rerank_score", None) or getattr(chunk, "score", 0.0) or 0.0), 4),
                "snippet": grounded_answer.compact_text(getattr(chunk, "text", ""), 500),
            }
        )
    return (
        f"{CORPUS_GAP_PROMPT}\n\n"
        f"{CORPUS_SCOPE}\n\n"
        f"ISSUE SUMMARY: {issue_summary}\n"
        f"ROUTED DOMAINS: {', '.join(domains)}\n"
        f"RETRIEVED SOURCES:\n{json.dumps(snippets, ensure_ascii=False, indent=2)}"
    )


def normalize_gap_result(parsed: dict[str, Any], source: str, latency_ms: int | None = None) -> CorpusGapResult:
    status = grounded_answer.clean_text(parsed.get("status"))
    if status not in STATUSES:
        status = "limited"
    reasons = [
        grounded_answer.clean_text(reason)
        for reason in parsed.get("reason_codes", [])
        if grounded_answer.clean_text(reason) in REASON_CODES
    ]
    allow = bool(parsed.get("allow_grounded_answer", status != "insufficient"))
    return CorpusGapResult(
        status=status,
        reason_codes=reasons,
        summary=grounded_answer.clean_text(parsed.get("summary")) or default_summary(status),
        allow_grounded_answer=allow and status != "insufficient",
        require_limitation=bool(parsed.get("require_limitation", status != "sufficient")),
        suggest_professional_help=bool(parsed.get("suggest_professional_help", status == "insufficient")),
        source=source,
        latency_ms=latency_ms,
    )


def result(status: str, reasons: list[str], summary: str, allow: bool, limitation: bool, professional: bool) -> CorpusGapResult:
    return CorpusGapResult(
        status=status,
        reason_codes=[reason for reason in reasons if reason in REASON_CODES],
        summary=summary,
        allow_grounded_answer=allow,
        require_limitation=limitation,
        suggest_professional_help=professional,
    )


def default_summary(status: str) -> str:
    if status == "insufficient":
        return "The current corpus does not contain enough reliable material to answer this issue."
    if status == "limited":
        return "The current corpus contains some relevant material, but coverage is limited."
    return "The current corpus contains enough relevant material for a grounded response."


def merge_reason_codes(existing: list[str], extra: list[str]) -> list[str]:
    merged = []
    for reason in existing + extra:
        if reason in REASON_CODES and reason not in merged:
            merged.append(reason)
    return merged


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").lower()).strip()


def explicit_non_delhi_tenancy(text: str, domains: list[str]) -> bool:
    if "tenancy" not in domains:
        return False
    non_delhi_places = ("mumbai", "maharashtra", "haryana", "gurgaon", "gurugram", "noida", "uttar pradesh", "up ", "bangalore", "bengaluru", "karnataka")
    return any(place in f"{text} " for place in non_delhi_places)


def case_law_query(text: str) -> bool:
    case_terms = (
        "supreme court held",
        "high court held",
        "what did the supreme court",
        "what did the high court",
        "held in",
        "judgment in",
        "judgement in",
        "precedent",
        " vs ",
        " v. ",
        " v ",
    )
    if "case law on" in text:
        return True
    return any(term in text for term in case_terms)


def missing_current_law_query(text: str, chunks: list[Any]) -> bool:
    asks_cert = "cert-in" in text or "cert in" in text or "incident reporting direction" in text
    asks_dpdp_act = "dpdp act" in text or "digital personal data protection act" in text
    source_text = " ".join(f"{getattr(chunk, 'document_title', '')} {getattr(chunk, 'source', '')}" for chunk in chunks).lower()
    has_cert_directions = "cert-in direction" in source_text or "cert in direction" in source_text or "incident reporting direction" in source_text
    if asks_cert and not has_cert_directions:
        return True
    if asks_dpdp_act and "digital personal data protection act" not in source_text:
        return True
    return False


def unsupported_legal_gap_query(text: str, chunks: list[Any]) -> bool:
    unsupported_source_terms = {
        "income tax": ("income tax", "tax law"),
        "tax law": ("income tax", "tax law"),
        "gst": ("goods and services tax", "gst"),
    }
    source_text = " ".join(f"{getattr(chunk, 'document_title', '')} {getattr(chunk, 'source', '')}" for chunk in chunks).lower()
    for cue, source_terms in unsupported_source_terms.items():
        if cue in text and not any(term in source_text for term in source_terms):
            return True
    return False


def is_primary_source(chunk: Any) -> bool:
    return (getattr(chunk, "authority_level", "") or "").lower() == "primary" and not is_supporting_only(chunk)


def is_supporting_only(chunk: Any) -> bool:
    status = (getattr(chunk, "status", "") or "").lower()
    document_type = (getattr(chunk, "document_type", "") or "").lower()
    authority = (getattr(chunk, "authority_level", "") or "").lower()
    return status in {"supporting_only", "reference_only"} or document_type.startswith("supporting_") or authority == "procedural_guide"


def should_use_gemini_for_ambiguity(issue_summary: str, domains: list[str], chunks: list[Any]) -> bool:
    text = normalize(issue_summary)
    if not chunks or explicit_non_delhi_tenancy(text, domains) or case_law_query(text):
        return False
    top_score = max(float(getattr(chunk, "rerank_score", None) or getattr(chunk, "score", 0.0) or 0.0) for chunk in chunks)
    return 0.34 <= top_score <= 0.48
