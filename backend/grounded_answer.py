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

logger = logging.getLogger("legal_aid_ai.grounded_answer")

CONFIDENCE_VALUES = {"low", "medium", "high"}


class GroundedAnswerError(Exception):
    pass


class GroundedAnswerConfigurationError(GroundedAnswerError):
    pass


@dataclass
class GroundedAnswerStats:
    latency_ms: int | None = None
    invalid_source_ids: list[str] | None = None
    provider: str = "gemini"


GROUNDED_ANSWER_SCHEMA = {
    "type": "object",
    "properties": {
        "issue_summary": {"type": "string"},
        "what_this_may_involve": {"type": "array", "items": {"type": "string"}},
        "possible_legal_position": {"type": "array", "items": {"type": "string"}},
        "suggested_next_steps": {"type": "array", "items": {"type": "string"}},
        "evidence_to_preserve": {"type": "array", "items": {"type": "string"}},
        "where_to_approach": {"type": "array", "items": {"type": "string"}},
        "limitations": {"type": "array", "items": {"type": "string"}},
        "source_chunk_ids": {"type": "array", "items": {"type": "string"}},
        "confidence": {"type": "string", "enum": sorted(CONFIDENCE_VALUES)},
        "insufficient_context": {"type": "boolean"},
        "disclaimer": {"type": "string"},
    },
    "required": [
        "issue_summary",
        "what_this_may_involve",
        "possible_legal_position",
        "suggested_next_steps",
        "evidence_to_preserve",
        "where_to_approach",
        "limitations",
        "source_chunk_ids",
        "confidence",
        "insufficient_context",
        "disclaimer",
    ],
}

GROUNDED_SYSTEM_PROMPT = """You are Legal Aid AI, an Indian legal-information assistant.
You must not answer from memory.
Use only the supplied USER FACTS and RETRIEVED LEGAL MATERIAL.
Never treat user facts as law.
Never treat legal extracts as proven facts.
Do not invent statutes, sections, rules, articles, cases, deadlines, fees, authorities, procedures, or remedies.
Do not guarantee outcomes, decide liability, or say the user will win.
Use cautious language: "may", "based on the facts provided", "the retrieved material indicates".
Avoid absolute certainty words such as "definitely" and "guaranteed", even when describing limitations.
If the retrieved legal material is insufficient, set insufficient_context to true and explain the limitation.
For ordinary defective-goods, refund, replacement, or non-delivery facts with no injury, physical harm, property damage, or consequential harm, do not discuss product liability merely because a product-liability chunk is present.
For multi-domain issues, use the retrieved material to preserve each supported aspect that is actually relevant, such as consumer remedy and cyber reporting, without inventing offences.
For RTI non-response issues, if retrieved Section 19 appeal material is available, present that appeal route distinctly from any Section 18 complaint material. Do not invent exact deadlines unless the supplied text states them.
Return only the required structured JSON.
Only include source_chunk_ids from the retrieved chunk IDs listed below.
Do not include markdown, bullets, numbering prefixes, or raw SVG/icon text inside strings.
"""


def generate_grounded_answer(
    original_message: str,
    normalized_case_summary: str,
    domains: list[str],
    chunks: list[Any],
    confirmed_case_facts: list[str] | None = None,
) -> dict[str, Any]:
    if not chunks:
        return insufficient_response("I do not have retrieved legal material to answer this reliably.")
    if is_too_vague_for_grounding(original_message, normalized_case_summary):
        return insufficient_response("I need a little more factual detail before I can connect your issue to the retrieved legal material reliably.")
    if has_obvious_source_gap(original_message, normalized_case_summary, chunks):
        return insufficient_response("The retrieved legal material does not contain enough support to answer this issue reliably.")
    if not GEMINI_API_KEY:
        raise GroundedAnswerConfigurationError("GEMINI_API_KEY is missing. Add it to backend/.env.")

    started = time.perf_counter()
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=build_grounded_prompt(original_message, normalized_case_summary, domains, chunks, confirmed_case_facts),
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=GROUNDED_ANSWER_SCHEMA,
            ),
        )
        parsed = json.loads(response.text or "{}")
        result = normalize_grounded_output(parsed, chunks)
        ensure_multi_domain_sources(result, chunks, domains)
        result["generation"] = asdict(
            GroundedAnswerStats(
                latency_ms=int((time.perf_counter() - started) * 1000),
                invalid_source_ids=result.pop("_invalid_source_ids", []),
            )
        )
        return result
    except GroundedAnswerConfigurationError:
        raise
    except (genai_errors.APIError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Gemini grounded answer failed: %s: %s", exc.__class__.__name__, str(exc))
        raise GroundedAnswerError("Gemini could not generate a grounded answer right now.") from exc


def build_grounded_prompt(
    original_message: str,
    normalized_case_summary: str,
    domains: list[str],
    chunks: list[Any],
    confirmed_case_facts: list[str] | None = None,
) -> str:
    legal_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        legal_blocks.append(
            f"CHUNK_ID: {chunk_id(chunk)}\n"
            f"DOCUMENT: {getattr(chunk, 'document_title', '')}\n"
            f"PROVISION: {provision_label(chunk) or 'Not identified'}\n"
            f"PAGE_RANGE: {page_range_label(chunk)}\n"
            f"TEXT:\n{compact_text(getattr(chunk, 'text', ''), 1800)}"
        )
    document_fact_block = "\n".join(f"- {clean_text(item)}" for item in confirmed_case_facts or [] if clean_text(item)) or "None"
    return (
        f"{GROUNDED_SYSTEM_PROMPT}\n\n"
        "USER FACTS:\n"
        f"- Original user message: {clean_text(original_message)}\n"
        f"- Normalized case summary: {clean_text(normalized_case_summary)}\n"
        f"- Routed domain(s): {', '.join(domains)}\n\n"
        "CONFIRMED CASE FACTS FROM USER DOCUMENTS:\n"
        f"{document_fact_block}\n\n"
        "RETRIEVED LEGAL MATERIAL:\n"
        + "\n\n".join(legal_blocks)
    )


def normalize_grounded_output(parsed: dict[str, Any], chunks: list[Any]) -> dict[str, Any]:
    valid_ids = {chunk_id(chunk): chunk for chunk in chunks}
    requested_ids = [clean_text(item) for item in parsed.get("source_chunk_ids", []) if clean_text(item)]
    accepted_ids = []
    invalid_ids = []
    for source_id in requested_ids:
        if source_id in valid_ids and source_id not in accepted_ids:
            accepted_ids.append(source_id)
        elif source_id not in valid_ids:
            invalid_ids.append(source_id)
    insufficient = bool(parsed.get("insufficient_context", False))
    if not accepted_ids and not insufficient:
        accepted_ids = [chunk_id(chunk) for chunk in chunks[:2]]

    answer = {
        "issue_summary": clean_text(parsed.get("issue_summary")) or "The retrieved legal material is not enough to summarize the issue reliably.",
        "what_this_may_involve": clean_list(parsed.get("what_this_may_involve"), 4),
        "possible_legal_position": clean_list(parsed.get("possible_legal_position"), 5),
        "suggested_next_steps": clean_list(parsed.get("suggested_next_steps"), 5),
        "evidence_to_preserve": clean_list(parsed.get("evidence_to_preserve"), 5),
        "where_to_approach": clean_list(parsed.get("where_to_approach"), 4),
        "limitations": clean_list(parsed.get("limitations"), 4),
    }
    answer["possible_rights"] = answer["possible_legal_position"]
    answer["next_steps"] = answer["suggested_next_steps"]
    confidence = clean_text(parsed.get("confidence")) or "medium"
    if confidence not in CONFIDENCE_VALUES:
        confidence = "medium"
    if insufficient:
        confidence = "low" if confidence == "high" else confidence
    return {
        "answer": answer,
        "sources": sources_from_ids(accepted_ids, valid_ids),
        "confidence": confidence,
        "insufficient_context": insufficient or not accepted_ids,
        "disclaimer": clean_text(parsed.get("disclaimer")) or DISCLAIMER,
        "source_chunk_ids": accepted_ids,
        "_invalid_source_ids": invalid_ids,
    }


def sources_from_ids(source_ids: list[str], chunks_by_id: dict[str, Any]) -> list[dict[str, Any]]:
    seen = set()
    sources = []
    for source_id in source_ids:
        chunk = chunks_by_id[source_id]
        key = (getattr(chunk, "document_title", ""), provision_label(chunk), getattr(chunk, "page", None))
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "document": getattr(chunk, "document_title", ""),
                "document_title": getattr(chunk, "document_title", ""),
                "source_file": getattr(chunk, "source", ""),
                "page": getattr(chunk, "page", None),
                "page_start": getattr(chunk, "page_start", None) or getattr(chunk, "page", None),
                "page_end": getattr(chunk, "page_end", None) or getattr(chunk, "page", None),
                "section": provision_label(chunk),
                "provision": provision_label(chunk),
                "chunk_id": source_id,
                "excerpt": short_excerpt(getattr(chunk, "text", "")),
            }
        )
    return sources


def ensure_multi_domain_sources(response: dict[str, Any], chunks: list[Any], domains: list[str]) -> None:
    desired_domains = []
    for domain in domains or []:
        if domain and domain not in desired_domains:
            desired_domains.append(domain)
    if len(desired_domains) < 2:
        return
    valid_chunks = {chunk_id(chunk): chunk for chunk in chunks}
    accepted = [source_id for source_id in response.get("source_chunk_ids", []) if source_id in valid_chunks]
    present_domains = {getattr(valid_chunks[source_id], "domain", None) for source_id in accepted}
    changed = False
    for domain in desired_domains:
        if domain in present_domains:
            continue
        candidate = next((chunk for chunk in chunks if getattr(chunk, "domain", None) == domain), None)
        if candidate is None:
            continue
        candidate_id = chunk_id(candidate)
        if candidate_id not in accepted:
            accepted.append(candidate_id)
            changed = True
    if not changed:
        return
    response["source_chunk_ids"] = accepted
    response["sources"] = sources_from_ids(accepted, valid_chunks)


def insufficient_response(message: str) -> dict[str, Any]:
    return {
        "answer": {
            "issue_summary": message,
            "what_this_may_involve": [],
            "possible_legal_position": [],
            "suggested_next_steps": [],
            "evidence_to_preserve": [],
            "where_to_approach": [],
            "limitations": [message],
        },
        "sources": [],
        "confidence": "low",
        "insufficient_context": True,
        "disclaimer": DISCLAIMER,
        "source_chunk_ids": [],
    }


def chunk_id(chunk: Any) -> str:
    value = getattr(chunk, "chunk_id", None)
    if value:
        return str(value)
    return f"{getattr(chunk, 'source', 'source')}__page_{getattr(chunk, 'page', 0)}"


def provision_label(chunk: Any) -> str | None:
    pairs = (
        ("section_number", "section_title", "Section"),
        ("article_number", "article_title", "Article"),
        ("rule_number", "rule_title", "Rule"),
        ("regulation_number", "regulation_title", "Regulation"),
    )
    for number_field, title_field, label in pairs:
        number = getattr(chunk, number_field, None)
        if number:
            title = getattr(chunk, title_field, None)
            return f"{label} {number}" + (f" — {title}" if title else "")
    return None


def page_range_label(chunk: Any) -> str:
    start = getattr(chunk, "page_start", None) or getattr(chunk, "page", None)
    end = getattr(chunk, "page_end", None) or start
    if start and end and start != end:
        return f"{start}-{end}"
    return str(start or "")


def clean_list(values: Any, limit: int) -> list[str]:
    if not isinstance(values, list):
        return []
    output = []
    seen = set()
    for value in values:
        text = clean_text(value)
        if not text or is_disclaimer_text(text):
            continue
        key = re.sub(r"[^a-z0-9]+", "", text.lower())
        if key in seen:
            continue
        seen.add(key)
        output.append(text)
        if len(output) >= limit:
            break
    return output


def clean_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"<svg\b[^>]*>.*?</svg>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\bsvg\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"^\s*(?:step\s*)?\d+\s*[\).:-]\s*", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def compact_text(text: str, max_chars: int) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rsplit(" ", 1)[0] + "..."


def short_excerpt(text: str, max_chars: int = 360) -> str:
    return compact_text(text, max_chars)


def is_disclaimer_text(text: str) -> bool:
    lowered = text.lower()
    return "legal information" in lowered and ("legal advice" in lowered or "qualified lawyer" in lowered)


def is_too_vague_for_grounding(original_message: str, normalized_case_summary: str) -> bool:
    text = f"{original_message} {normalized_case_summary}".lower()
    text = re.sub(r"[^a-z0-9\u0900-\u097f\s]+", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    vague_patterns = (
        r"\bconsumer complaint (karni|file|raise|banana|banani|complaint)\b",
        r"\bfile (a )?consumer complaint\b",
        r"\bmera cyber issue\b",
        r"\bcyber issue hai\b",
        r"\blandlord dispute hai\b",
        r"\bgovernment authority (ke against )?issue hai\b",
        r"\bmujhe notice mila\b",
        r"\bmere paise fas gaye\b",
    )
    event_cues = (
        "refund",
        "defect",
        "defective",
        "damaged",
        "not delivered",
        "hacked",
        "phishing",
        "fraud",
        "identity",
        "electricity",
        "evict",
        "deposit",
        "rti",
        "legal aid",
        "equality",
        "human rights",
        "contempt",
        "reply nahi",
        "block",
        "blocked",
        "payment",
    )
    if any(cue in text for cue in event_cues):
        return False
    return any(re.search(pattern, text) for pattern in vague_patterns)


def has_obvious_source_gap(original_message: str, normalized_case_summary: str, chunks: list[Any]) -> bool:
    text = f"{original_message} {normalized_case_summary}".lower()
    source_text = " ".join(
        f"{getattr(chunk, 'document_title', '')} {getattr(chunk, 'source', '')}"
        for chunk in chunks
    ).lower()
    unsupported_source_markers = {
        "income tax": ("income tax",),
        "divorce": ("divorce", "family court", "marriage"),
        "bail": ("bail",),
        "child custody": ("custody", "guardian"),
        "inheritance": ("succession", "inheritance"),
    }
    for cue, source_markers in unsupported_source_markers.items():
        if cue in text and not any(marker in source_text for marker in source_markers):
            return True
    return False
