from __future__ import annotations

import json
import logging
import re
import time
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger("legal_aid_ai.document_facts")

DOCUMENT_TYPES = {
    "rent_agreement",
    "invoice_or_receipt",
    "legal_notice",
    "complaint",
    "transaction_record",
    "correspondence",
    "other",
    "unknown",
}
CONFIDENCE_VALUES = {"high", "medium", "low"}
FACT_CATEGORIES = [
    "parties",
    "dates",
    "amounts",
    "identifiers",
    "locations",
    "important_terms",
    "events",
    "notices_or_demands",
    "other_facts",
    "uncertain_items",
]
MAX_DOCUMENT_TEXT_CHARS = 18000
MAX_EXCERPT_CHARS = 220


class DocumentFactError(Exception):
    pass


@dataclass
class FactExtractionStats:
    provider: str = "gemini"
    model: str = GEMINI_MODEL
    latency_ms: int | None = None
    redacted_sensitive_items: int = 0


@dataclass
class ConfirmedFacts:
    status: str
    fact_extraction_id: str
    confirmed_facts: dict[str, Any]
    confirmed_fact_context_id: str | None = None
    source: str = "user_document"

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


FACT_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "label": {"type": "string"},
        "value": {"type": "string"},
        "source_page": {"type": "integer"},
        "source_excerpt": {"type": "string"},
        "confidence": {"type": "string", "enum": sorted(CONFIDENCE_VALUES)},
    },
    "required": ["label", "value", "source_page", "source_excerpt", "confidence"],
}

DOCUMENT_FACT_SCHEMA = {
    "type": "object",
    "properties": {
        "document_type": {"type": "string", "enum": sorted(DOCUMENT_TYPES)},
        "document_summary": {"type": "string"},
        **{category: {"type": "array", "items": FACT_ITEM_SCHEMA} for category in FACT_CATEGORIES},
        "warnings": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["document_type", "document_summary", *FACT_CATEGORIES, "warnings"],
}

FACT_EXTRACTION_PROMPT = """You extract factual information from a user-provided document.
Use only the supplied document text.
Extract facts, not legal conclusions.
Do not give legal advice, cite law, identify remedies, or decide who is right.
Do not infer unstated facts or fill gaps from memory.
Preserve dates, amounts, identifiers, and names exactly as written unless sensitive.
Omit or replace Aadhaar, OTP, PIN, passwords, CVV, full bank/card numbers, and credentials with [sensitive information omitted].
Every substantive fact should include a short source excerpt and page number when available; use 0 if page number is unavailable.
Put ambiguous or uncertain interpretations in uncertain_items, not confirmed fact categories.
Return only strict structured JSON.
"""

FACT_STORE: dict[str, dict[str, Any]] = {}
CONFIRMED_FACT_CONTEXTS: dict[str, dict[str, Any]] = {}


def extract_facts_from_extraction(extraction: dict[str, Any]) -> dict[str, Any]:
    if not extraction_text(extraction):
        return unavailable_response(extraction, "No extracted text is available for fact extraction.")
    if not GEMINI_API_KEY:
        return unavailable_response(extraction, "Gemini fact extraction is not configured.")

    started = time.perf_counter()
    try:
        parsed = call_gemini_fact_extraction(extraction)
        facts, redacted_count = normalize_fact_output(parsed, extraction)
        stats = FactExtractionStats(latency_ms=int((time.perf_counter() - started) * 1000), redacted_sensitive_items=redacted_count)
        extraction_id = store_pending_facts(facts)
        logger.info(
            "Document fact extraction completed type=%s fact_count=%s latency_ms=%s",
            facts["document_type"],
            count_fact_items(facts),
            stats.latency_ms,
        )
        return {
            "status": "success",
            "fact_extraction_id": extraction_id,
            "confirmation_required": True,
            "facts": facts,
            "warnings": facts.get("warnings", []),
            "extraction": asdict(stats),
        }
    except Exception as exc:
        logger.warning("Document fact extraction unavailable: %s: %s", exc.__class__.__name__, safe_error_message(exc))
        return unavailable_response(extraction, "Fact extraction is unavailable right now. You can still review the extracted text.")


def call_gemini_fact_extraction(extraction: dict[str, Any]) -> dict[str, Any]:
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=build_fact_prompt(extraction),
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=DOCUMENT_FACT_SCHEMA,
        ),
    )
    return json.loads(response.text or "{}")


def build_fact_prompt(extraction: dict[str, Any]) -> str:
    pages = extraction.get("pages") or []
    if pages:
        blocks = []
        total = 0
        for page in pages:
            page_text = clean_text(page.get("text", ""))
            if not page_text:
                continue
            block = f"PAGE {page.get('page_number')}:\n{page_text}"
            if total + len(block) > MAX_DOCUMENT_TEXT_CHARS:
                break
            blocks.append(block)
            total += len(block)
        document_text = "\n\n".join(blocks)
    else:
        document_text = clean_text(extraction.get("text", ""))[:MAX_DOCUMENT_TEXT_CHARS]
    return (
        f"{FACT_EXTRACTION_PROMPT}\n\n"
        f"FILENAME: {clean_text(extraction.get('filename'))}\n"
        f"FILE_TYPE: {clean_text(extraction.get('file_type'))}\n"
        f"EXTRACTION_WARNINGS: {json.dumps(extraction.get('warnings', []), ensure_ascii=False)}\n\n"
        f"DOCUMENT TEXT:\n{document_text}"
    )


def normalize_fact_output(parsed: dict[str, Any], extraction: dict[str, Any]) -> tuple[dict[str, Any], int]:
    document_type = clean_text(parsed.get("document_type")) or infer_document_type(extraction)
    if document_type not in DOCUMENT_TYPES:
        document_type = "unknown"
    facts: dict[str, Any] = {
        "document_type": document_type,
        "document_summary": clean_text(parsed.get("document_summary")) or default_summary(document_type),
    }
    redacted_count = 0
    for category in FACT_CATEGORIES:
        normalized_items = []
        for item in parsed.get(category, []) or []:
            normalized, redacted = normalize_fact_item(item)
            redacted_count += redacted
            if normalized:
                normalized_items.append(normalized)
        facts[category] = dedupe_items(normalized_items)
    warnings = [clean_text(item) for item in parsed.get("warnings", []) if clean_text(item)]
    facts["warnings"] = dedupe_strings(warnings)
    apply_document_type_guardrails(facts, extraction)
    apply_uncertainty_guardrails(facts, extraction)
    return facts, redacted_count


def normalize_fact_item(item: dict[str, Any]) -> tuple[dict[str, Any] | None, int]:
    if not isinstance(item, dict):
        return None, 0
    label = clean_text(item.get("label")) or "fact"
    value, value_redactions = redact_sensitive(clean_text(item.get("value")))
    excerpt, excerpt_redactions = redact_sensitive(compact_excerpt(item.get("source_excerpt", "")))
    if not value:
        return None, value_redactions + excerpt_redactions
    confidence = clean_text(item.get("confidence")) or "medium"
    if confidence not in CONFIDENCE_VALUES:
        confidence = "medium"
    source_page = item.get("source_page")
    if not isinstance(source_page, int) or source_page <= 0:
        source_page = None
    return (
        {
            "label": label,
            "value": value,
            "source_page": source_page,
            "source_excerpt": excerpt,
            "confidence": confidence,
        },
        value_redactions + excerpt_redactions,
    )


def confirm_facts(fact_extraction_id: str, confirmed_facts: dict[str, Any]) -> ConfirmedFacts:
    if fact_extraction_id not in FACT_STORE:
        raise DocumentFactError("Fact extraction session was not found or has expired.")
    sanitized = sanitize_confirmed_facts(confirmed_facts)
    FACT_STORE[fact_extraction_id] = sanitized
    context_id = uuid.uuid4().hex
    CONFIRMED_FACT_CONTEXTS[context_id] = {
        "confirmed_fact_context_id": context_id,
        "source": "user_document",
        "status": "confirmed",
        "document_type": sanitized.get("document_type", "unknown"),
        "confirmed_facts": sanitized,
        "document_provenance": document_provenance(sanitized),
    }
    return ConfirmedFacts(
        status="confirmed",
        fact_extraction_id=fact_extraction_id,
        confirmed_facts=sanitized,
        confirmed_fact_context_id=context_id,
    )


def get_pending_facts(fact_extraction_id: str) -> dict[str, Any] | None:
    return FACT_STORE.get(fact_extraction_id)


def get_confirmed_context(context_id: str | None) -> dict[str, Any] | None:
    if not context_id:
        return None
    return CONFIRMED_FACT_CONTEXTS.get(context_id)


def detach_confirmed_context(context_id: str | None) -> bool:
    if not context_id:
        return False
    return CONFIRMED_FACT_CONTEXTS.pop(context_id, None) is not None


def require_confirmed_context(context_id: str | None) -> dict[str, Any]:
    context = get_confirmed_context(context_id)
    if not context or context.get("status") != "confirmed":
        raise DocumentFactError("Confirmed document fact context was not found or has expired.")
    return context


def store_pending_facts(facts: dict[str, Any]) -> str:
    extraction_id = uuid.uuid4().hex
    FACT_STORE[extraction_id] = facts
    return extraction_id


def confirmed_fact_lines(context: dict[str, Any] | None, max_items: int = 12) -> list[str]:
    if not context:
        return []
    facts = context.get("confirmed_facts", {})
    lines = []
    document_type = clean_text(facts.get("document_type"))
    if document_type:
        lines.append(f"Document type confirmed by user: {document_type.replace('_', ' ')}")
    for category in FACT_CATEGORIES:
        if category == "uncertain_items":
            continue
        for item in facts.get(category, []) or []:
            label = clean_text(item.get("label")).replace("_", " ")
            value = clean_text(item.get("value"))
            if value:
                lines.append(f"{label}: {value}")
            if len(lines) >= max_items:
                return lines
    return lines


def combined_question_with_confirmed_facts(question: str, context: dict[str, Any] | None) -> str:
    lines = confirmed_fact_lines(context, max_items=10)
    if not lines:
        return clean_text(question)
    return clean_text(
        "USER QUESTION: "
        + clean_text(question)
        + " CONFIRMED DOCUMENT FACTS: "
        + "; ".join(lines)
    )


def document_evidence_payload(context: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not context:
        return []
    facts = context.get("confirmed_facts", {})
    evidence = []
    for category in FACT_CATEGORIES:
        if category == "uncertain_items":
            continue
        for item in facts.get(category, []) or []:
            value = clean_text(item.get("value"))
            if not value:
                continue
            evidence.append(
                {
                    "label": clean_text(item.get("label")) or "fact",
                    "value": value,
                    "source_page": item.get("source_page"),
                    "source_excerpt": clean_text(item.get("source_excerpt")),
                    "confidence": clean_text(item.get("confidence")) or "medium",
                    "document_type": facts.get("document_type", "unknown"),
                    "source": "user_document",
                }
            )
    return evidence[:12]


def document_provenance(facts: dict[str, Any]) -> dict[str, Any]:
    pages = sorted(
        {
            item.get("source_page")
            for category in FACT_CATEGORIES
            for item in facts.get(category, []) or []
            if isinstance(item.get("source_page"), int)
        }
    )
    return {"source": "user_document", "document_type": facts.get("document_type", "unknown"), "pages": pages}


def confirmed_values(context: dict[str, Any] | None, categories: set[str] | None = None) -> list[str]:
    if not context:
        return []
    facts = context.get("confirmed_facts", {})
    values = []
    for category in FACT_CATEGORIES:
        if categories and category not in categories:
            continue
        for item in facts.get(category, []) or []:
            value = clean_text(item.get("value"))
            if value:
                values.append(value)
    return values


def sanitize_confirmed_facts(facts: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(facts, dict):
        raise DocumentFactError("Confirmed facts must be a structured object.")
    sanitized = {
        "document_type": clean_text(facts.get("document_type")) if clean_text(facts.get("document_type")) in DOCUMENT_TYPES else "unknown",
        "document_summary": clean_text(facts.get("document_summary")),
    }
    for category in FACT_CATEGORIES:
        items = []
        for item in facts.get(category, []) or []:
            normalized, _redacted = normalize_fact_item(item)
            if normalized:
                items.append(normalized)
        sanitized[category] = dedupe_items(items)
    sanitized["warnings"] = dedupe_strings([clean_text(item) for item in facts.get("warnings", []) if clean_text(item)])
    return sanitized


def unavailable_response(extraction: dict[str, Any], message: str) -> dict[str, Any]:
    return {
        "status": "fact_extraction_unavailable",
        "fact_extraction_id": None,
        "confirmation_required": False,
        "facts": {
            "document_type": infer_document_type(extraction),
            "document_summary": "",
            **{category: [] for category in FACT_CATEGORIES},
            "warnings": [message],
        },
        "warnings": [message],
        "extraction": {"provider": "gemini", "model": GEMINI_MODEL, "latency_ms": None, "redacted_sensitive_items": 0},
    }


def infer_document_type(extraction: dict[str, Any]) -> str:
    text = clean_text(f"{extraction.get('filename', '')} {extraction.get('text', '')[:1000]}").lower()
    if "rent agreement" in text or "lease agreement" in text:
        return "rent_agreement"
    if "invoice" in text or "receipt" in text or "order no" in text:
        return "invoice_or_receipt"
    if "legal notice" in text or "notice" in text:
        return "legal_notice"
    if "complaint" in text:
        return "complaint"
    if "transaction" in text or "utr" in text or "payment" in text:
        return "transaction_record"
    if "dear " in text or "email" in text:
        return "correspondence"
    return "unknown"


def apply_document_type_guardrails(facts: dict[str, Any], extraction: dict[str, Any]) -> None:
    text = clean_text(f"{extraction.get('filename', '')} {extraction.get('text', '')[:1500]}").lower()
    if "legal notice" in text or re.search(r"\bnotice dated\b", text):
        facts["document_type"] = "legal_notice"
        return
    if "rti application" in text or "consumer complaint" in text or "complaint draft" in text:
        facts["document_type"] = "complaint"
        return
    if "rent agreement" in text or "lease agreement" in text:
        facts["document_type"] = "rent_agreement"
        return
    if "transaction receipt" in text:
        facts["document_type"] = "transaction_record"
        return
    if text.startswith("statement:") and ("without permission" in text or "unknown device" in text):
        facts["document_type"] = "other"
        return
    if "invoice" in text or "receipt" in text:
        facts["document_type"] = "invoice_or_receipt"
        return
    if is_sparse_or_role_unclear(text):
        facts["document_type"] = "unknown"


def apply_uncertainty_guardrails(facts: dict[str, Any], extraction: dict[str, Any]) -> None:
    text = clean_text(extraction.get("text", "")).lower()
    uncertain = list(facts.get("uncertain_items", []) or [])
    if ("role unclear" in text or "no role is stated" in text or "only two signatures" in text) and not any(
        "role" in item.get("label", "").lower() or "role" in item.get("value", "").lower()
        for item in uncertain
    ):
        uncertain.append(
            {
                "label": "party_role",
                "value": "Party roles are not clearly stated in the document.",
                "source_page": 1,
                "source_excerpt": compact_excerpt(extraction.get("text", "")),
                "confidence": "low",
            }
        )
    if len(text) < 60 and "issue" in text and not uncertain:
        uncertain.append(
            {
                "label": "document_context",
                "value": "The document mentions an issue but gives limited context.",
                "source_page": 1,
                "source_excerpt": compact_excerpt(extraction.get("text", "")),
                "confidence": "low",
            }
        )
    facts["uncertain_items"] = dedupe_items(uncertain)


def is_sparse_or_role_unclear(text: str) -> bool:
    return len(text) < 90 or "no role is stated" in text or "only two signatures" in text


def extraction_text(extraction: dict[str, Any]) -> str:
    return clean_text(extraction.get("text", ""))


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def compact_excerpt(value: Any) -> str:
    text = clean_text(value)
    return text[:MAX_EXCERPT_CHARS].strip()


def dedupe_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    deduped = []
    for item in items:
        key = (item["label"].lower(), item["value"].lower())
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def dedupe_strings(items: list[str]) -> list[str]:
    seen = set()
    deduped = []
    for item in items:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(item)
    return deduped


def redact_sensitive(text: str) -> tuple[str, int]:
    redactions = 0
    patterns = [
        r"\b\d{4}\s?\d{4}\s?\d{4}\b",
        r"\b(?:\d[ -]?){13,19}\b",
        r"(?i)\b(?:otp|pin|cvv|password|passcode)\s*[:=-]?\s*\S+",
    ]
    redacted = text
    for pattern in patterns:
        redacted, count = re.subn(pattern, "[sensitive information omitted]", redacted)
        redactions += count
    return redacted, redactions


def count_fact_items(facts: dict[str, Any]) -> int:
    return sum(len(facts.get(category, []) or []) for category in FACT_CATEGORIES)


def default_summary(document_type: str) -> str:
    if document_type == "unknown":
        return "This appears to be a user-provided document with extractable text."
    return f"This appears to be a {document_type.replace('_', ' ')} document."


def safe_error_message(exc: Exception) -> str:
    if isinstance(exc, (genai_errors.APIError, TimeoutError, json.JSONDecodeError, ValueError, TypeError)):
        return str(exc)[:160]
    return "Fact extraction failed."
