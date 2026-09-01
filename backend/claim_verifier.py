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

from config import GEMINI_API_KEY, GEMINI_MODEL
import grounded_answer

logger = logging.getLogger("legal_aid_ai.claim_verifier")

SUPPORT_VALUES = {"supported", "partially_supported", "unsupported"}
LEGAL_CLAIM_FIELDS = (
    "what_this_may_involve",
    "possible_legal_position",
    "suggested_next_steps",
    "where_to_approach",
)
HIGH_RISK_TERMS = (
    "deadline",
    "limitation",
    "within",
    "days",
    "months",
    "years",
    "fee",
    "fine",
    "penalty",
    "punishable",
    "imprisonment",
    "commission",
    "court",
    "authority",
    "portal",
    "must",
    "always",
    "illegal",
    "entitled",
    "required",
    "shall",
)
GENERIC_NON_LEGAL_ACTIONS = (
    "preserve",
    "keep",
    "save",
    "collect",
    "document",
    "write down",
    "record",
)


@dataclass
class Claim:
    claim_id: str
    field: str
    text: str
    source_chunk_ids: list[str]
    high_risk: bool = False


VERIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "claim_id": {"type": "string"},
                    "support": {"type": "string", "enum": sorted(SUPPORT_VALUES)},
                    "supporting_chunk_ids": {"type": "array", "items": {"type": "string"}},
                    "reason": {"type": "string"},
                },
                "required": ["claim_id", "support", "supporting_chunk_ids", "reason"],
            },
        }
    },
    "required": ["claims"],
}

VERIFIER_PROMPT = """You verify whether generated legal-information claims are supported by the supplied retrieved source text.
You are not answering the user's legal problem.
Use ONLY the supplied source text.
Do not use outside knowledge.
Do not assume unstated facts.
Exact wording need not match if the meaning is clearly supported.
Return supported only when the source text clearly supports the claim.
Return partially_supported when the source supports only part of the claim or the claim adds an unsupported detail.
Return unsupported when the source text does not support the claim.
Do not repair or rewrite claims.
Return only structured JSON.
"""


def verify_and_sanitize_response(response: dict[str, Any], chunks: list[Any]) -> dict[str, Any]:
    valid_chunks = {grounded_answer.chunk_id(chunk): chunk for chunk in chunks}
    response_ids = [source_id for source_id in response.get("source_chunk_ids", []) if source_id in valid_chunks]
    claims = extract_claims(response, response_ids)
    deterministic_rejections = deterministic_invalid_claims(claims, valid_chunks)
    verifiable_claims = [claim for claim in claims if claim.claim_id not in deterministic_rejections]

    if not claims:
        response["verification"] = verification_stats("skipped", [], deterministic_rejections)
        return response

    if not GEMINI_API_KEY:
        return safe_verification_unavailable(response, claims, deterministic_rejections, "missing_api_key")

    started = time.perf_counter()
    try:
        results = call_gemini_verifier(verifiable_claims, valid_chunks)
        response = apply_verification_results(response, claims, results, deterministic_rejections)
        response["verification"]["latency_ms"] = int((time.perf_counter() - started) * 1000)
        response["verification"]["provider"] = "gemini"
        return response
    except (genai_errors.APIError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Gemini claim verification failed: %s: %s", exc.__class__.__name__, str(exc))
        return safe_verification_unavailable(response, claims, deterministic_rejections, exc.__class__.__name__)


def extract_claims(response: dict[str, Any], source_chunk_ids: list[str]) -> list[Claim]:
    answer = response.get("answer") or {}
    claims: list[Claim] = []
    counter = 1
    for field in LEGAL_CLAIM_FIELDS:
        values = answer.get(field) or []
        if not isinstance(values, list):
            continue
        for value in values:
            text = grounded_answer.clean_text(value)
            if not should_verify_claim(field, text):
                continue
            claims.append(
                Claim(
                    claim_id=f"claim_{counter:03d}",
                    field=field,
                    text=text,
                    source_chunk_ids=list(source_chunk_ids),
                    high_risk=is_high_risk_claim(text),
                )
            )
            counter += 1
    return claims


def should_verify_claim(field: str, text: str) -> bool:
    if not text:
        return False
    lowered = text.lower()
    if field == "suggested_next_steps" and lowered.startswith(GENERIC_NON_LEGAL_ACTIONS):
        return is_high_risk_claim(text)
    return True


def is_high_risk_claim(text: str) -> bool:
    lowered = text.lower()
    return any(re.search(rf"\b{re.escape(term)}\b", lowered) for term in HIGH_RISK_TERMS)


def deterministic_invalid_claims(claims: list[Claim], valid_chunks: dict[str, Any]) -> dict[str, str]:
    invalid = {}
    for claim in claims:
        if not claim.text:
            invalid[claim.claim_id] = "empty_claim"
        elif not claim.source_chunk_ids:
            invalid[claim.claim_id] = "no_source_chunk_ids"
        elif any(source_id not in valid_chunks for source_id in claim.source_chunk_ids):
            invalid[claim.claim_id] = "unknown_source_chunk_id"
        elif not any(grounded_answer.clean_text(getattr(valid_chunks[source_id], "text", "")) for source_id in claim.source_chunk_ids):
            invalid[claim.claim_id] = "empty_source_text"
    return invalid


def call_gemini_verifier(claims: list[Claim], chunks_by_id: dict[str, Any]) -> dict[str, dict[str, Any]]:
    if not claims:
        return {}
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=build_verification_prompt(claims, chunks_by_id),
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=VERIFICATION_SCHEMA,
        ),
    )
    parsed = json.loads(response.text or "{}")
    return normalize_verification_results(parsed, claims, chunks_by_id)


def build_verification_prompt(claims: list[Claim], chunks_by_id: dict[str, Any]) -> str:
    source_ids = []
    for claim in claims:
        for source_id in claim.source_chunk_ids:
            if source_id not in source_ids:
                source_ids.append(source_id)
    source_blocks = []
    for source_id in source_ids:
        chunk = chunks_by_id[source_id]
        source_blocks.append(
            f"CHUNK_ID: {source_id}\n"
            f"DOCUMENT: {getattr(chunk, 'document_title', '')}\n"
            f"PROVISION: {grounded_answer.provision_label(chunk) or 'Not identified'}\n"
            f"TEXT:\n{grounded_answer.compact_text(getattr(chunk, 'text', ''), 1600)}"
        )
    claim_blocks = [
        {
            "claim_id": claim.claim_id,
            "text": claim.text,
            "candidate_source_chunk_ids": claim.source_chunk_ids,
        }
        for claim in claims
    ]
    return (
        f"{VERIFIER_PROMPT}\n\n"
        "RETRIEVED SOURCE TEXT:\n"
        + "\n\n".join(source_blocks)
        + "\n\nCLAIMS TO VERIFY:\n"
        + json.dumps(claim_blocks, ensure_ascii=False, indent=2)
    )


def normalize_verification_results(
    parsed: dict[str, Any],
    claims: list[Claim],
    chunks_by_id: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    claim_ids = {claim.claim_id for claim in claims}
    valid_ids = set(chunks_by_id)
    results: dict[str, dict[str, Any]] = {}
    for item in parsed.get("claims", []):
        claim_id = grounded_answer.clean_text(item.get("claim_id"))
        if claim_id not in claim_ids:
            continue
        support = grounded_answer.clean_text(item.get("support"))
        if support not in SUPPORT_VALUES:
            support = "unsupported"
        supporting_ids = []
        for source_id in item.get("supporting_chunk_ids", []):
            source_id = grounded_answer.clean_text(source_id)
            if source_id in valid_ids and source_id not in supporting_ids:
                supporting_ids.append(source_id)
        if support in {"supported", "partially_supported"} and not supporting_ids:
            support = "unsupported"
        results[claim_id] = {
            "claim_id": claim_id,
            "support": support,
            "supporting_chunk_ids": supporting_ids,
            "reason": grounded_answer.clean_text(item.get("reason"))[:280],
        }
    for claim in claims:
        results.setdefault(
            claim.claim_id,
            {
                "claim_id": claim.claim_id,
                "support": "unsupported",
                "supporting_chunk_ids": [],
                "reason": "Verifier did not return a result for this claim.",
            },
        )
    return results


def apply_verification_results(
    response: dict[str, Any],
    claims: list[Claim],
    results: dict[str, dict[str, Any]],
    deterministic_rejections: dict[str, str],
) -> dict[str, Any]:
    claim_by_text_and_field = {(claim.field, claim.text): claim for claim in claims}
    answer = response.get("answer") or {}
    removed: list[dict[str, str]] = []
    partial: list[dict[str, str]] = []
    for field in LEGAL_CLAIM_FIELDS:
        new_values = []
        for value in answer.get(field, []) or []:
            text = grounded_answer.clean_text(value)
            claim = claim_by_text_and_field.get((field, text))
            if claim is None:
                new_values.append(value)
                continue
            result = results.get(claim.claim_id, {"support": "unsupported", "reason": "Not verified."})
            support = "unsupported" if claim.claim_id in deterministic_rejections else result["support"]
            if support == "supported":
                new_values.append(text)
            elif support == "partially_supported":
                partial.append({"claim_id": claim.claim_id, "field": field, "text": text})
                new_values.append(natural_partial_claim(text))
            else:
                removed.append({"claim_id": claim.claim_id, "field": field, "text": text})
        answer[field] = new_values
    append_verification_limitations(answer, removed, partial)
    answer["possible_rights"] = answer.get("possible_legal_position", [])
    answer["next_steps"] = answer.get("suggested_next_steps", [])
    response["answer"] = answer
    response["verification"] = verification_stats("verified", claims, deterministic_rejections, results, removed, partial)
    return response


def append_verification_limitations(answer: dict[str, Any], removed: list[dict[str, str]], partial: list[dict[str, str]]) -> None:
    limitations = list(answer.get("limitations") or [])
    if removed and not any("available sources do not clearly establish" in item.lower() for item in limitations):
        limitations.append("The available sources do not clearly establish every possible procedural detail.")
    answer["limitations"] = grounded_answer.clean_list(limitations, 5)


def natural_partial_claim(text: str) -> str:
    cleaned = grounded_answer.clean_text(text)
    return re.sub(r"^(you must|you should|you can|you may)\b", "You may", cleaned, flags=re.I)


def safe_verification_unavailable(
    response: dict[str, Any],
    claims: list[Claim],
    deterministic_rejections: dict[str, str],
    reason: str,
) -> dict[str, Any]:
    answer = response.get("answer") or {}
    removed: list[dict[str, str]] = []
    for field in LEGAL_CLAIM_FIELDS:
        kept = []
        for value in answer.get(field, []) or []:
            text = grounded_answer.clean_text(value)
            claim = next((item for item in claims if item.field == field and item.text == text), None)
            if claim and claim.claim_id in deterministic_rejections:
                removed.append({"claim_id": claim.claim_id, "field": field, "text": text})
                continue
            if claim and claim.high_risk and not is_narrowly_traceable_claim(claim, response):
                removed.append({"claim_id": claim.claim_id, "field": field, "text": text})
                continue
            kept.append(text)
        answer[field] = kept
    limitations = list(answer.get("limitations") or [])
    if removed:
        limitations.append("Some procedural details are omitted because they could not be reliably verified from the available sources.")
    answer["limitations"] = grounded_answer.clean_list(limitations, 5)
    answer["possible_rights"] = answer.get("possible_legal_position", [])
    answer["next_steps"] = answer.get("suggested_next_steps", [])
    response["answer"] = answer
    response["verification"] = verification_stats("unavailable", claims, deterministic_rejections, removed=removed)
    response["verification"]["failure_reason"] = reason
    return response


def is_narrowly_traceable_claim(claim: Claim, response: dict[str, Any]) -> bool:
    if not claim.source_chunk_ids:
        return False
    lowered = claim.text.lower()
    if contains_high_risk_detail(lowered):
        return False
    if not re.search(r"\b(section|rule|article)\s+\d+[a-z]?\b", lowered):
        return False
    if len(re.findall(r"[a-zA-Z][a-zA-Z-]{3,}", lowered)) > 28:
        return False
    return True


def contains_high_risk_detail(lowered: str) -> bool:
    return bool(
        re.search(r"\b\d+\s*(day|days|month|months|year|years|rupees|rs\.?|inr)\b", lowered)
        or re.search(r"\b(fine|penalty|imprisonment|guaranteed|always|definitely|illegal|entitled)\b", lowered)
    )


def verification_stats(
    status: str,
    claims: list[Claim],
    deterministic_rejections: dict[str, str],
    results: dict[str, dict[str, Any]] | None = None,
    removed: list[dict[str, str]] | None = None,
    partial: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    results = results or {}
    removed = removed or []
    partial = partial or []
    return {
        "status": status,
        "verified_claim_count": sum(1 for item in results.values() if item.get("support") == "supported"),
        "partially_supported_claim_count": sum(1 for item in results.values() if item.get("support") == "partially_supported"),
        "unsupported_claim_count": sum(1 for item in results.values() if item.get("support") == "unsupported") + len(deterministic_rejections),
        "claim_count": len(claims),
        "deterministic_rejections": deterministic_rejections,
        "removed_claim_count": len(removed),
        "qualified_claim_count": len(partial),
        "claims": [asdict(claim) for claim in claims],
        "results": list(results.values()),
    }
