from __future__ import annotations

import json
import logging
import time
from dataclasses import asdict, dataclass
from typing import Any

from google import genai
from google.genai import errors as genai_errors
from google.genai import types

from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger("legal_aid_ai.domain_router")

SUPPORTED_DOMAINS = {
    "consumer",
    "cyber",
    "tenancy",
    "constitutional_public_authority",
}
ALLOWED_STATUSES = {"classified", "unclear", "unsupported", "out_of_scope"}
ALLOWED_CONFIDENCE = {"low", "medium", "high"}


@dataclass
class RouteDecision:
    status: str
    domains: list[str]
    primary_domain: str | None
    confidence: str
    issue_summary: str | None
    needs_clarification: bool
    latency_ms: int | None = None
    provider: str = "gemini"
    routing_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


UNCLEAR_FALLBACK = RouteDecision(
    status="unclear",
    domains=[],
    primary_domain=None,
    confidence="low",
    issue_summary=None,
    needs_clarification=True,
    latency_ms=None,
)


ROUTER_PROMPT = """You are routing an Indian legal-information query.
Do not answer the legal issue.
Do not cite laws.
Do not provide remedies or next steps.
Do not decide liability.
Return only the required structured classification.

Supported domains are exactly:
- consumer
- cyber
- tenancy
- constitutional_public_authority

Use "classified" when the message can reasonably map to one or more supported domains.
Use "unclear" when it may be legal but is too vague to identify the supported domain.
Use "unsupported" when it is legal but outside the supported domains.
Use "out_of_scope" when it is clearly not a legal-information issue.

Multi-domain classification is allowed. If multiple domains apply, keep all plausible domains and choose one primary_domain.
Use cautious, factual issue summaries only. Do not say a law was violated or that the user has a valid case.
For primary_domain, return an empty string when there is no primary domain.
For issue_summary, return an empty string when no summary is appropriate.
"""

ROUTER_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": sorted(ALLOWED_STATUSES)},
        "domains": {"type": "array", "items": {"type": "string", "enum": sorted(SUPPORTED_DOMAINS)}},
        "primary_domain": {"type": "string"},
        "confidence": {"type": "string", "enum": sorted(ALLOWED_CONFIDENCE)},
        "issue_summary": {"type": "string"},
        "needs_clarification": {"type": "boolean"},
    },
    "required": ["status", "domains", "primary_domain", "confidence", "issue_summary", "needs_clarification"],
}


def route_issue(message: str, conversation_context: list[dict[str, str]] | None = None) -> RouteDecision:
    if not GEMINI_API_KEY:
        logger.warning("Gemini router skipped because GEMINI_API_KEY is not configured.")
        return UNCLEAR_FALLBACK

    prompt = build_router_prompt(message, conversation_context)
    started = time.perf_counter()
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=ROUTER_SCHEMA,
            ),
        )
        parsed = json.loads(response.text or "{}")
        decision = validate_route_decision(parsed)
        decision = apply_router_safety_overrides(message, decision)
        decision.latency_ms = int((time.perf_counter() - started) * 1000)
        return decision
    except (genai_errors.APIError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Gemini routing failed safely: %s: %s", exc.__class__.__name__, str(exc))
        fallback = RouteDecision(**UNCLEAR_FALLBACK.to_dict())
        fallback.latency_ms = int((time.perf_counter() - started) * 1000)
        fallback.routing_error = True
        return fallback


def build_router_prompt(message: str, conversation_context: list[dict[str, str]] | None = None) -> str:
    context_lines = []
    for item in conversation_context or []:
        role = item.get("role", "user")
        content = item.get("content", "")
        if content:
            context_lines.append(f"{role}: {content}")
    context = "\n".join(context_lines[-4:])
    context_block = f"\nRecent conversation context:\n{context}\n" if context else ""
    return f"{ROUTER_PROMPT}{context_block}\nUser message:\n{message}"


def validate_route_decision(data: dict[str, Any]) -> RouteDecision:
    status = data.get("status")
    domains = data.get("domains")
    primary_domain = data.get("primary_domain")
    confidence = data.get("confidence")
    issue_summary = data.get("issue_summary")
    needs_clarification = data.get("needs_clarification")
    if primary_domain == "":
        primary_domain = None
    if issue_summary == "":
        issue_summary = None

    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid router status: {status}")
    if confidence not in ALLOWED_CONFIDENCE:
        raise ValueError(f"Invalid router confidence: {confidence}")
    if not isinstance(domains, list):
        raise ValueError("Router domains must be a list.")
    unique_domains = []
    for domain in domains:
        if domain not in SUPPORTED_DOMAINS:
            raise ValueError(f"Invalid router domain: {domain}")
        if domain not in unique_domains:
            unique_domains.append(domain)
    if primary_domain is not None and primary_domain not in unique_domains:
        raise ValueError("Router primary_domain must be one of domains.")
    if not isinstance(needs_clarification, bool):
        raise ValueError("Router needs_clarification must be boolean.")
    if issue_summary is not None and not isinstance(issue_summary, str):
        raise ValueError("Router issue_summary must be string or null.")

    if status == "classified":
        if not unique_domains:
            raise ValueError("Classified router decision requires at least one domain.")
        if primary_domain is None:
            raise ValueError("Classified router decision requires primary_domain.")
        if not issue_summary or not issue_summary.strip():
            raise ValueError("Classified router decision requires issue_summary.")
        needs_clarification = False
    elif status == "unclear":
        unique_domains = []
        primary_domain = None
        needs_clarification = True
        confidence = "low"
        issue_summary = issue_summary.strip() if isinstance(issue_summary, str) and issue_summary.strip() else None
    else:
        unique_domains = []
        primary_domain = None
        needs_clarification = False
        issue_summary = issue_summary.strip() if isinstance(issue_summary, str) and issue_summary.strip() else None

    return RouteDecision(
        status=status,
        domains=unique_domains,
        primary_domain=primary_domain,
        confidence=confidence,
        issue_summary=issue_summary.strip() if isinstance(issue_summary, str) else None,
        needs_clarification=needs_clarification,
    )


def apply_router_safety_overrides(message: str, decision: RouteDecision) -> RouteDecision:
    text = message.lower()
    if contains_any(text, UNSUPPORTED_LEGAL_CUES):
        return RouteDecision(
            status="unsupported",
            domains=[],
            primary_domain=None,
            confidence="high",
            issue_summary="The issue appears legal, but outside the currently supported Legal Aid AI corpus.",
            needs_clarification=False,
        )
    cue_domains = domains_from_supported_cues(text)
    if decision.status == "classified" and looks_too_vague_for_classification(text) and not has_specific_supported_action(text):
        return RouteDecision(
            status="unclear",
            domains=[],
            primary_domain=None,
            confidence="low",
            issue_summary="The message may describe a legal issue, but more context is needed to identify the supported area.",
            needs_clarification=True,
        )
    if decision.status == "unclear" and cue_domains and has_specific_supported_action(text):
        domains = sorted(cue_domains)
        return RouteDecision(
            status="classified",
            domains=domains,
            primary_domain=domains[0],
            confidence="medium",
            issue_summary="The message contains enough context to identify the supported legal area.",
            needs_clarification=False,
        )
    if decision.status == "classified" and cue_domains:
        merged_domains = list(decision.domains)
        for domain in sorted(cue_domains):
            if domain not in merged_domains:
                merged_domains.append(domain)
        if merged_domains != decision.domains:
            decision.domains = merged_domains
            if decision.primary_domain not in merged_domains:
                decision.primary_domain = merged_domains[0]
    return decision


UNSUPPORTED_LEGAL_CUES = (
    "divorce",
    "child custody",
    "inheritance",
    "bail",
    "income tax",
    "shareholder",
    "corporate dispute",
)

SUPPORTED_DOMAIN_CUES = {
    "consumer": (
        "seller",
        "defective",
        "product",
        "refund",
        "replacement",
        "warranty",
        "ecommerce",
        "e-commerce",
        "direct selling",
        "misleading advertisement",
        "dark pattern",
    ),
    "cyber": (
        "hack",
        "hacked",
        "phishing",
        "otp",
        "upi fraud",
        "cyber",
        "instagram",
        "unauthorized transaction",
        "identity theft",
        "data breach",
        "fake account",
        "personal details",
        "private data",
        "blocked me",
        "block kar",
    ),
    "tenancy": (
        "landlord",
        "tenant",
        "rent",
        "eviction",
        "security deposit",
        "electricity cut",
        "essential supply",
        "lease",
    ),
    "constitutional_public_authority": (
        "rti",
        "right to information",
        "free legal aid",
        "free lawyer",
        "legal services authority",
        "human rights",
        "fundamental right",
        "article 14",
        "article 19",
        "article 21",
        "contempt of court",
        "discriminate",
    ),
}

VAGUE_LEGAL_PATTERNS = (
    "paise fas",
    "paise chale gaye",
    "refund issue",
    "account problem",
    "misusing my details",
    "deposit nahi",
    "government office problem",
    "help chahiye",
    "online paise",
    "trouble kar",
    "court matter",
    "notice mila",
    "matter hai",
    "galat hua",
)


def explicit_supported_domain_count(text: str) -> int:
    return len(domains_from_supported_cues(text))


def domains_from_supported_cues(text: str) -> set[str]:
    return {domain for domain, cues in SUPPORTED_DOMAIN_CUES.items() if contains_any(text, cues)}


def looks_too_vague_for_classification(text: str) -> bool:
    return contains_any(text, VAGUE_LEGAL_PATTERNS)


def has_specific_supported_action(text: str) -> bool:
    specific_patterns = (
        "seller refund",
        "defective product",
        "product defective",
        "replace nahi",
        "phishing",
        "hack",
        "hacked",
        "otp",
        "upi fraud",
        "unauthorized transaction",
        "fake account",
        "personal details",
        "instagram seller",
        "block kar",
        "electricity cut",
        "security deposit",
        "evict",
        "eviction",
        "rti",
        "right to information",
        "free legal aid",
        "free lawyer",
        "legal aid",
        "discriminate",
        "human rights",
    )
    return contains_any(text, specific_patterns)


def contains_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(cue in text for cue in cues)


def fallback_unclear_decision() -> RouteDecision:
    return RouteDecision(**UNCLEAR_FALLBACK.to_dict())
