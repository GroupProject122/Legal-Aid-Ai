from __future__ import annotations

import json
import logging
import re
import time
from dataclasses import asdict, dataclass
from typing import Any

from google import genai
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger("legal_aid_ai.document_summarizer")

MAX_SINGLE_CALL_CHARS = 30000
MAX_TOTAL_CHARS = 90000
CHUNK_CHARS = 22000
MAX_CHUNKS = 4

SUMMARY_SCHEMA = {
    "type": "object",
    "properties": {"summary": {"type": "string"}},
    "required": ["summary"],
}

SUMMARY_PROMPT = """You are summarizing a user-provided legal or case-related document.
Rules:
- use ONLY the supplied document text
- do not use outside legal knowledge
- do not give legal advice
- do not determine whether any clause is valid, invalid, legal, illegal, enforceable or unfair
- do not invent missing facts
- do not infer unstated facts
- preserve important names, dates, amounts, obligations and terms where relevant
- do not reformat dates, amounts, document numbers, or identifiers; keep them as written
- omit or redact OTP, PIN, password, CVV, full card numbers, full bank credentials, and authentication credentials
- write in clear plain language for a non-lawyer
- produce one concise but sufficiently informative summary
- if the document text is unclear or incomplete, mention that briefly
- return only strict structured JSON with this schema: {"summary": "..."}
"""

LEGAL_CONCLUSION_PATTERNS = [
    r"\blegally valid\b",
    r"\blegally invalid\b",
    r"\billegal\b",
    r"\bunenforceable\b",
    r"\benforceable\b",
    r"\bunfair clause\b",
    r"\byou should file\b",
    r"\byou are entitled\b",
]

SENSITIVE_PATTERNS = [
    r"\b\d{4}\s?\d{4}\s?\d{4}\b",
    r"\b(?:\d[ -]?){13,19}\b",
    r"(?i)\b(?:otp|pin|cvv|password|passcode)\s*[:=-]?\s*\S+",
    r"(?i)\b(?:bank\s+password|netbanking\s+password|login\s+password)\s*[:=-]?\s*\S+",
]


@dataclass
class SummaryResult:
    status: str
    summary: str | None = None
    message: str | None = None
    model: str = GEMINI_MODEL
    gemini_calls: int = 0
    latency_ms: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def summarize_document(extraction: dict[str, Any]) -> dict[str, Any]:
    started = time.perf_counter()
    if extraction.get("status") == "ocr_required":
        return SummaryResult(
            status="ocr_required",
            message="This scanned document requires OCR before it can be summarized.",
            latency_ms=0,
        ).to_dict()

    text = redact_sensitive(clean_text(extraction.get("text", "")))
    if not text:
        return SummaryResult(
            status="no_extracted_text",
            message="No readable extracted text is available for summarization.",
            latency_ms=0,
        ).to_dict()
    if len(text) > MAX_TOTAL_CHARS:
        return SummaryResult(
            status="document_too_long_for_summary",
            message="This document is too long to summarize safely in this version.",
            latency_ms=0,
        ).to_dict()
    if not GEMINI_API_KEY:
        return SummaryResult(
            status="summary_unavailable",
            message="The document summary could not be generated right now.",
            latency_ms=0,
        ).to_dict()

    calls = 0
    try:
        if len(text) <= MAX_SINGLE_CALL_CHARS:
            parsed = call_gemini_summary(build_summary_prompt(text))
            calls = 1
            summary = normalize_summary(parsed)
        else:
            chunk_summaries = []
            for chunk in split_text(text, CHUNK_CHARS)[:MAX_CHUNKS]:
                parsed = call_gemini_summary(build_summary_prompt(chunk, chunk_mode=True))
                calls += 1
                chunk_summaries.append(normalize_summary(parsed))
            parsed = call_gemini_summary(build_summary_prompt("\n\n".join(chunk_summaries), synthesis_mode=True))
            calls += 1
            summary = normalize_summary(parsed)

        if contains_legal_conclusion(summary):
            raise ValueError("Summary contained legal-advice or validity language.")
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.info("Document summary generated status=success calls=%s latency_ms=%s", calls, latency_ms)
        return SummaryResult(status="success", summary=redact_sensitive(summary), gemini_calls=calls, latency_ms=latency_ms).to_dict()
    except Exception as exc:
        latency_ms = int((time.perf_counter() - started) * 1000)
        logger.warning("Document summary unavailable: %s latency_ms=%s", exc.__class__.__name__, latency_ms)
        return SummaryResult(
            status="summary_unavailable",
            message="The document summary could not be generated right now.",
            gemini_calls=calls,
            latency_ms=latency_ms,
        ).to_dict()


def call_gemini_summary(prompt: str) -> dict[str, Any]:
    client = genai.Client(api_key=GEMINI_API_KEY)
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            temperature=0.0,
            response_mime_type="application/json",
            response_schema=SUMMARY_SCHEMA,
        ),
    )
    return json.loads(response.text or "{}")


def build_summary_prompt(text: str, *, chunk_mode: bool = False, synthesis_mode: bool = False) -> str:
    mode = "Summarize this part of the document." if chunk_mode else "Summarize this document."
    if synthesis_mode:
        mode = "Combine these partial summaries into one document summary without adding new facts."
    return f"{SUMMARY_PROMPT}\n\nTASK: {mode}\n\nDOCUMENT TEXT:\n{text}"


def normalize_summary(parsed: dict[str, Any]) -> str:
    summary = clean_text(parsed.get("summary") if isinstance(parsed, dict) else "")
    if not summary:
        raise ValueError("Gemini returned an empty summary.")
    return summary


def split_text(text: str, size: int) -> list[str]:
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + size)
        if end < len(text):
            boundary = text.rfind("\n\n", start, end)
            if boundary > start + size // 2:
                end = boundary
        chunks.append(text[start:end].strip())
        start = end
    return [chunk for chunk in chunks if chunk]


def clean_text(value: Any) -> str:
    text = str(value or "").replace("\x00", " ")
    text = re.sub(r"[ \t\r\f\v]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def redact_sensitive(text: str) -> str:
    redacted = text
    for pattern in SENSITIVE_PATTERNS:
        redacted = re.sub(pattern, "[sensitive information omitted]", redacted)
    return redacted


def contains_legal_conclusion(summary: str) -> bool:
    lowered = summary.lower()
    return any(re.search(pattern, lowered) for pattern in LEGAL_CONCLUSION_PATTERNS)
