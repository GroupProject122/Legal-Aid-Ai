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

import domain_router
from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger("legal_aid_ai.fact_sufficiency")

FACT_STATES: dict[str, "CaseContext"] = {}
ALLOWED_STATUSES = {"sufficient", "insufficient"}

FACT_PROMPT = """You are checking whether a classified Indian legal-information issue has enough facts for legal-source retrieval.
Do not answer the legal issue.
Do not cite laws.
Do not provide remedies or legal advice.
Do not decide liability.

Ask for at most ONE factual clarification only if the key event pattern is too vague for useful retrieval.
Avoid intake-form behavior. Do not ask for names, phone numbers, address, Aadhaar, passwords, OTPs, PINs, banking credentials, evidence lists, exact dates, exact amounts, desired remedy, state, city, or jurisdiction.

Domain expectations:
- consumer: enough if product/service issue and seller/provider behavior are broadly clear.
- cyber: enough if the digital incident is broadly clear, such as hacking, phishing, identity misuse, unauthorized access, or payment fraud.
- tenancy: enough if landlord/tenant relationship and dispute type are broadly clear. Do not ask state/city.
- constitutional_public_authority: enough if RTI, public authority action, legal aid, human rights, contempt, or fundamental-rights issue type is broadly clear.

Return only structured JSON.
"""

FACT_SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": sorted(ALLOWED_STATUSES)},
        "missing_facts": {"type": "array", "items": {"type": "string"}},
        "needs_fact_clarification": {"type": "boolean"},
        "question": {"type": "string"},
        "reason": {"type": "string"},
        "normalized_case_summary": {"type": "string"},
    },
    "required": [
        "status",
        "missing_facts",
        "needs_fact_clarification",
        "question",
        "reason",
        "normalized_case_summary",
    ],
}


@dataclass
class FactTurn:
    question: str
    answer: str | None = None


@dataclass
class CaseContext:
    state_id: str
    original_message: str
    domains: list[str]
    issue_summary: str | None
    facts: list[str] = field(default_factory=list)
    fact_clarification_history: list[FactTurn] = field(default_factory=list)
    no_progress_count: int = 0
    normalized_case_summary: str | None = None
    confirmed_fact_context_id: str | None = None
    document_fact_lines: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "fact_clarification_history": [asdict(item) for item in self.fact_clarification_history],
        }


@dataclass
class FactSufficiencyResult:
    status: str
    missing_facts: list[str]
    needs_fact_clarification: bool
    question: str | None
    reason: str | None
    normalized_case_summary: str | None
    latency_ms: int | None = None
    provider: str = "gemini"
    evaluation_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class FactProgress:
    progress: str
    should_continue: bool
    safe_exit: bool = False


def new_case_context(
    message: str,
    route: domain_router.RouteDecision,
    document_fact_lines: list[str] | None = None,
    confirmed_fact_context_id: str | None = None,
) -> CaseContext:
    fact_lines = [normalize_text(item) for item in document_fact_lines or [] if normalize_text(item)]
    return CaseContext(
        state_id=uuid.uuid4().hex,
        original_message=normalize_text(message),
        domains=list(route.domains),
        issue_summary=route.issue_summary,
        facts=[normalize_text(message), *fact_lines],
        normalized_case_summary=route.issue_summary,
        confirmed_fact_context_id=confirmed_fact_context_id,
        document_fact_lines=fact_lines,
    )


def get_state(state_id: str | None) -> CaseContext | None:
    if not state_id:
        return None
    return FACT_STATES.get(state_id)


def clear_state(state_id: str | None) -> None:
    if state_id:
        FACT_STATES.pop(state_id, None)


def start_fact_check(
    message: str,
    route: domain_router.RouteDecision,
    document_fact_lines: list[str] | None = None,
    confirmed_fact_context_id: str | None = None,
) -> tuple[CaseContext, FactSufficiencyResult]:
    context = new_case_context(message, route, document_fact_lines, confirmed_fact_context_id)
    result = assess_fact_sufficiency(context)
    if result.needs_fact_clarification and result.question:
        context.fact_clarification_history.append(FactTurn(question=result.question))
        FACT_STATES[context.state_id] = context
    return context, result


def record_fact_answer(context: CaseContext, answer: str) -> FactProgress:
    clean_answer = sanitize_user_fact(answer)
    if context.fact_clarification_history:
        context.fact_clarification_history[-1].answer = clean_answer
    previous_terms = content_terms(" ".join(context.facts))
    answer_terms = content_terms(clean_answer)
    new_terms = answer_terms - previous_terms
    if len(new_terms) >= 2 or has_specific_fact_cue(clean_answer, context.domains):
        progress = "meaningful"
    elif len(new_terms) == 1:
        progress = "minimal"
    else:
        progress = "none"
    if progress == "meaningful":
        context.no_progress_count = 0
    else:
        context.no_progress_count += 1
    if clean_answer:
        context.facts.append(clean_answer)
    safe_exit = progress != "meaningful" and context.no_progress_count >= 2
    return FactProgress(progress=progress, should_continue=not safe_exit, safe_exit=safe_exit)


def continue_fact_check(context: CaseContext, answer: str) -> tuple[FactProgress, FactSufficiencyResult]:
    progress = record_fact_answer(context, answer)
    context.normalized_case_summary = build_case_summary(context)
    if progress.safe_exit:
        return progress, insufficient_result(
            "More factual detail is needed before Legal Aid AI can retrieve useful legal sources.",
            "Please briefly describe what happened.",
        )
    result = assess_fact_sufficiency(context)
    if result.needs_fact_clarification and result.question:
        result.question = avoid_repeated_question(result.question, context)
        context.fact_clarification_history.append(FactTurn(question=result.question))
        FACT_STATES[context.state_id] = context
    return progress, result


def assess_fact_sufficiency(context: CaseContext) -> FactSufficiencyResult:
    deterministic = deterministic_fact_result(context)
    if deterministic.status == "sufficient" or not GEMINI_API_KEY:
        return deterministic

    started = time.perf_counter()
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=build_fact_prompt(context),
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=FACT_SCHEMA,
            ),
        )
        data = json.loads(response.text or "{}")
        result = validate_fact_result(data)
        result = apply_fact_safety_overrides(context, result)
        result.latency_ms = int((time.perf_counter() - started) * 1000)
        return result
    except (genai_errors.APIError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Gemini fact-sufficiency check failed safely: %s: %s", exc.__class__.__name__, str(exc))
        fallback = deterministic if deterministic.needs_fact_clarification else fallback_insufficient(context)
        fallback.latency_ms = int((time.perf_counter() - started) * 1000)
        fallback.evaluation_error = True
        return fallback


def build_fact_prompt(context: CaseContext) -> str:
    history = "\n".join(
        f"Q: {turn.question}\nA: {turn.answer or ''}".strip()
        for turn in context.fact_clarification_history[-3:]
    )
    return (
        f"{FACT_PROMPT}\n"
        f"Supported domains already classified: {', '.join(context.domains)}\n"
        f"Issue summary: {context.issue_summary or ''}\n"
        f"Known user facts:\n- " + "\n- ".join(context.facts) + "\n\n"
        f"Prior fact clarification:\n{history or 'None'}"
    )


def validate_fact_result(data: dict[str, Any]) -> FactSufficiencyResult:
    status = data.get("status")
    missing = data.get("missing_facts") or []
    needs = data.get("needs_fact_clarification")
    question = normalize_text(data.get("question")) or None
    reason = normalize_text(data.get("reason")) or None
    summary = normalize_text(data.get("normalized_case_summary")) or None

    if status not in ALLOWED_STATUSES:
        raise ValueError(f"Invalid fact-sufficiency status: {status}")
    if not isinstance(missing, list):
        raise ValueError("missing_facts must be a list.")
    if not isinstance(needs, bool):
        raise ValueError("needs_fact_clarification must be boolean.")
    missing = [normalize_text(item) for item in missing if normalize_text(item)]
    if status == "sufficient":
        needs = False
        question = None
        missing = []
    else:
        needs = True
        if not question:
            raise ValueError("Insufficient fact result requires a question.")
    result = FactSufficiencyResult(status, missing, needs, question, reason, summary)
    if result.question and (asks_for_jurisdiction(result.question) or asks_for_sensitive_info(result.question)):
        raise ValueError("Unsafe fact clarification question.")
    return result


def deterministic_fact_result(context: CaseContext) -> FactSufficiencyResult:
    text = " ".join([context.original_message, *context.facts, context.issue_summary or ""]).lower()
    user_text = " ".join([context.original_message, *context.facts]).lower()
    domains = set(context.domains)
    if not context.fact_clarification_history and is_too_generic(user_text, domains):
        return fallback_insufficient(context)
    if has_specific_fact_cue(text, domains):
        summary = build_case_summary(context)
        return FactSufficiencyResult(
            status="sufficient",
            missing_facts=[],
            needs_fact_clarification=False,
            question=None,
            reason=None,
            normalized_case_summary=summary,
            provider="deterministic",
        )
    if is_too_generic(user_text, domains):
        return fallback_insufficient(context)
    return fallback_insufficient(context)


def apply_fact_safety_overrides(context: CaseContext, result: FactSufficiencyResult) -> FactSufficiencyResult:
    deterministic = deterministic_fact_result(context)
    if deterministic.status == "sufficient":
        return deterministic
    if result.question and (asks_for_jurisdiction(result.question) or asks_for_sensitive_info(result.question)):
        return fallback_insufficient(context)
    return result


def fallback_insufficient(context: CaseContext) -> FactSufficiencyResult:
    text = " ".join([context.original_message, *context.facts]).lower()
    domains = set(context.domains)
    if "consumer" in domains:
        question = "What happened with the product or service?"
        missing = ["specific product or service issue"]
    elif "cyber" in domains:
        question = "What happened — account hacking, payment fraud, identity misuse, or something else?"
        missing = ["specific digital incident"]
    elif "tenancy" in domains:
        question = "What is the dispute about — eviction, rent, deposit, or power/water supply?"
        missing = ["specific landlord-tenant dispute"]
    elif "constitutional_public_authority" in domains:
        question = "What did the public authority do or refuse to do?"
        missing = ["specific public-authority action"]
    elif any(word in text for word in ("payment", "paise", "money")):
        question = "What happened with the payment?"
        missing = ["payment context"]
    else:
        question = "Please briefly describe what happened."
        missing = ["basic event details"]
    return insufficient_result(question, question, missing)


def insufficient_result(reason: str, question: str, missing_facts: list[str] | None = None) -> FactSufficiencyResult:
    return FactSufficiencyResult(
        status="insufficient",
        missing_facts=missing_facts or ["basic event details"],
        needs_fact_clarification=True,
        question=question,
        reason=reason,
        normalized_case_summary=None,
        provider="deterministic",
    )


def build_case_summary(context: CaseContext) -> str:
    facts = [sanitize_user_fact(item) for item in context.facts if sanitize_user_fact(item)]
    combined = " ".join(facts)
    combined = re.sub(r"\s+", " ", combined).strip()
    if len(combined) > 280:
        combined = combined[:277].rsplit(" ", 1)[0] + "..."
    return combined or context.issue_summary or context.original_message


def retrieval_query(context: CaseContext, result: FactSufficiencyResult | None = None) -> str:
    return normalize_text((result.normalized_case_summary if result else None) or context.normalized_case_summary or build_case_summary(context))


def avoid_repeated_question(question: str, context: CaseContext) -> str:
    normalized = normalize_text(question).lower()
    previous = {normalize_text(turn.question).lower() for turn in context.fact_clarification_history}
    if normalized in previous:
        return "Please briefly describe what happened."
    return question


def is_too_generic(text: str, domains: set[str]) -> bool:
    generic_patterns = (
        "consumer complaint karni hai",
        "consumer issue",
        "consumer issue hai",
        "cyber issue",
        "mera cyber issue",
        "landlord dispute hai",
        "rent matter hai",
        "government authority ke against issue",
        "government authority ke against issue hai",
        "public authority problem",
        "public authority issue",
        "legal aid issue",
        "complaint karni hai",
    )
    if any(pattern in text for pattern in generic_patterns):
        return True
    if "consumer" in domains and not contains_any(text, CONSUMER_FACT_CUES):
        return True
    if "cyber" in domains and not contains_any(text, CYBER_FACT_CUES):
        return True
    if "tenancy" in domains and not contains_any(text, TENANCY_FACT_CUES):
        return True
    if "constitutional_public_authority" in domains and not contains_any(text, PUBLIC_FACT_CUES):
        return True
    return False


def has_specific_fact_cue(text: str, domains: set[str] | list[str]) -> bool:
    domain_set = set(domains)
    lowered = text.lower()
    return (
        ("consumer" in domain_set and contains_any(lowered, CONSUMER_FACT_CUES))
        or ("cyber" in domain_set and contains_any(lowered, CYBER_FACT_CUES))
        or ("tenancy" in domain_set and contains_any(lowered, TENANCY_FACT_CUES))
        or ("constitutional_public_authority" in domain_set and contains_any(lowered, PUBLIC_FACT_CUES))
    )


CONSUMER_FACT_CUES = (
    "defective",
    "damaged",
    "not delivered",
    "refund",
    "replace",
    "replacement",
    "warranty",
    "seller",
    "service deficiency",
    "service provider",
    "service complete",
    "service not complete",
    "service incomplete",
    "misleading advertisement",
    "dark pattern",
    "direct selling",
)
CYBER_FACT_CUES = (
    "hack",
    "hacked",
    "phishing",
    "otp",
    "upi fraud",
    "unauthorized",
    "identity",
    "fake account",
    "personal details",
    "data breach",
    "fraudulent transaction",
)
TENANCY_FACT_CUES = (
    "evict",
    "eviction",
    "rent",
    "deposit",
    "electricity",
    "water",
    "essential supply",
    "agreement",
)
PUBLIC_FACT_CUES = (
    "rti",
    "right to information",
    "reply nahi",
    "free legal aid",
    "free lawyer",
    "legal aid",
    "discriminate",
    "equality",
    "article",
    "human rights",
    "contempt",
    "court order",
    "public authority",
    "government authority",
)


def sanitize_user_fact(value: Any) -> str:
    text = normalize_text(value)
    text = re.sub(r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[redacted Aadhaar-like number]", text)
    text = re.sub(r"\b(otp|pin|password)\s*(?:is|hai|:)?\s*\S+", r"\1 [redacted]", text, flags=re.I)
    return text


def content_terms(text: str) -> set[str]:
    stop = {"hai", "hain", "mere", "mera", "meri", "mujhe", "bas", "kya", "the", "and", "for", "with", "issue", "matter", "legal"}
    return {token for token in re.findall(r"[a-zA-Z0-9]+", text.lower()) if token not in stop and len(token) > 2}


def asks_for_jurisdiction(question: str) -> bool:
    lowered = question.lower()
    return any(phrase in lowered for phrase in ("which state", "which city", "what city", "state/city", "jurisdiction", "property located", "kis state", "kaunse state", "sheher"))


def asks_for_sensitive_info(question: str) -> bool:
    lowered = question.lower()
    return any(word in lowered for word in ("password", "otp", "pin", "aadhaar", "aadhar", "card number", "cvv", "bank credentials"))


def contains_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(cue in text for cue in cues)


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()
