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

logger = logging.getLogger("legal_aid_ai.conversation_state")

TURN_TYPES = {
    "new_issue",
    "follow_up_question",
    "additional_fact",
    "correction",
    "clarification_reply",
    "acknowledgement",
    "small_talk",
}
STATE_TTL_SECONDS = 60 * 60
MAX_FACTS = 12


@dataclass
class ActiveCaseState:
    conversation_state_id: str
    domains: list[str]
    primary_domain: str | None
    case_summary: str
    known_facts: list[str] = field(default_factory=list)
    confirmed_document_context_id: str | None = None
    last_user_intent: str | None = None
    last_issue_addressed: str | None = None
    clarification_state_id: str | None = None
    updated_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class TurnClassification:
    turn_type: str
    confidence: str
    reason: str | None = None
    updated_case_summary: str | None = None
    extracted_facts: list[str] = field(default_factory=list)
    corrected_facts: list[str] = field(default_factory=list)
    provider: str = "deterministic"
    latency_ms: int | None = None
    error: bool = False


ACTIVE_CASE_STATES: dict[str, ActiveCaseState] = {}

TURN_CLASSIFIER_PROMPT = """Classify the latest user message in an ongoing Indian legal-information consultation.
Do not answer the legal issue.
Do not cite law.
Use only the compact active case summary and latest user message.

Allowed turn_type values:
- new_issue
- follow_up_question
- additional_fact
- correction
- clarification_reply
- acknowledgement
- small_talk

Return correction only when the user replaces or corrects an earlier fact.
Return additional_fact when the user only adds a fact and is not asking a question.
Return follow_up_question when the message asks about the same legal issue or uses pronouns/context from the active case.
Return new_issue when the message clearly starts an unrelated legal issue.
Return acknowledgement or small_talk for thanks, okay, hello, or similar messages that should not run legal retrieval.
Return strict JSON only.
"""

TURN_CLASSIFIER_SCHEMA = {
    "type": "object",
    "properties": {
        "turn_type": {"type": "string", "enum": sorted(TURN_TYPES)},
        "confidence": {"type": "string", "enum": ["high", "medium", "low"]},
        "reason": {"type": "string"},
        "updated_case_summary": {"type": "string"},
        "extracted_facts": {"type": "array", "items": {"type": "string"}},
        "corrected_facts": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["turn_type", "confidence", "reason", "updated_case_summary", "extracted_facts", "corrected_facts"],
}


def create_state(
    domains: list[str],
    primary_domain: str | None,
    case_summary: str,
    known_facts: list[str] | None = None,
    confirmed_document_context_id: str | None = None,
    last_user_intent: str | None = None,
    last_issue_addressed: str | None = None,
    clarification_state_id: str | None = None,
) -> ActiveCaseState:
    cleanup_expired_states()
    state = ActiveCaseState(
        conversation_state_id=uuid.uuid4().hex,
        domains=unique_clean(domains),
        primary_domain=primary_domain,
        case_summary=compact_text(case_summary, 420),
        known_facts=dedupe_facts(known_facts or []),
        confirmed_document_context_id=confirmed_document_context_id,
        last_user_intent=clean_text(last_user_intent),
        last_issue_addressed=clean_text(last_issue_addressed),
        clarification_state_id=clarification_state_id,
    )
    ACTIVE_CASE_STATES[state.conversation_state_id] = state
    return state


def get_state(state_id: str | None) -> ActiveCaseState | None:
    cleanup_expired_states()
    if not state_id:
        return None
    state = ACTIVE_CASE_STATES.get(state_id)
    if state:
        state.updated_at = time.time()
    return state


def restore_state(payload: dict[str, Any] | None) -> ActiveCaseState | None:
    if not payload:
        return None
    state_id = clean_text(payload.get("conversation_state_id")) or uuid.uuid4().hex
    state = ActiveCaseState(
        conversation_state_id=state_id,
        domains=unique_clean(payload.get("domains", [])),
        primary_domain=clean_text(payload.get("primary_domain")) or None,
        case_summary=compact_text(payload.get("case_summary", ""), 420),
        known_facts=dedupe_facts(payload.get("known_facts", [])),
        confirmed_document_context_id=clean_text(payload.get("confirmed_document_context_id")) or None,
        last_user_intent=clean_text(payload.get("last_user_intent")) or None,
        last_issue_addressed=clean_text(payload.get("last_issue_addressed")) or None,
        clarification_state_id=clean_text(payload.get("clarification_state_id")) or None,
        updated_at=time.time(),
    )
    ACTIVE_CASE_STATES[state.conversation_state_id] = state
    return state


def clear_state(state_id: str | None) -> None:
    if state_id:
        ACTIVE_CASE_STATES.pop(state_id, None)


def cleanup_expired_states(now: float | None = None) -> None:
    current = now or time.time()
    expired = [state_id for state_id, state in ACTIVE_CASE_STATES.items() if current - state.updated_at > STATE_TTL_SECONDS]
    for state_id in expired:
        ACTIVE_CASE_STATES.pop(state_id, None)


def classify_turn(message: str, state: ActiveCaseState) -> TurnClassification:
    deterministic = deterministic_turn_classification(message, state)
    if deterministic.confidence == "high" or not GEMINI_API_KEY:
        return deterministic

    started = time.perf_counter()
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=build_turn_prompt(message, state),
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=TURN_CLASSIFIER_SCHEMA,
            ),
        )
        parsed = json.loads(response.text or "{}")
        result = validate_turn_classification(parsed)
        result.latency_ms = int((time.perf_counter() - started) * 1000)
        result.provider = "gemini"
        return apply_turn_safety_overrides(message, state, result)
    except (genai_errors.APIError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Gemini turn classification failed safely: %s: %s", exc.__class__.__name__, str(exc))
        deterministic.error = True
        deterministic.latency_ms = int((time.perf_counter() - started) * 1000)
        return deterministic


def deterministic_turn_classification(message: str, state: ActiveCaseState) -> TurnClassification:
    text = clean_text(message)
    lowered = text.lower()
    if is_small_talk(lowered):
        turn_type = "acknowledgement" if contains_any(lowered, ("thanks", "thank you", "okay", "ok", "got it", "understood")) else "small_talk"
        return TurnClassification(turn_type, "high", "Conversational message that does not need legal retrieval.")
    if is_correction(lowered):
        corrected = [text]
        return TurnClassification("correction", "high", "User appears to correct an earlier fact.", corrected_facts=corrected)
    if clearly_new_issue(lowered, state):
        return TurnClassification("new_issue", "high", "Latest message appears unrelated to the active case.")
    if is_question_like(lowered):
        return TurnClassification("follow_up_question", "medium", "Likely asks about the active case.")
    if has_fact_content(lowered):
        return TurnClassification("additional_fact", "high", "User added a factual detail without asking a question.", extracted_facts=[text])
    if refers_to_existing_case(lowered):
        return TurnClassification("follow_up_question", "medium", "Likely refers to the active case.")
    return TurnClassification("follow_up_question", "low", "Ambiguous short message in an active legal consultation.")


def build_turn_prompt(message: str, state: ActiveCaseState) -> str:
    facts = "\n".join(f"- {fact}" for fact in state.known_facts[-8:]) or "None"
    return (
        f"{TURN_CLASSIFIER_PROMPT}\n\n"
        f"Active case summary:\n{state.case_summary}\n\n"
        f"Domains: {', '.join(state.domains)}\n"
        f"Last issue addressed: {state.last_issue_addressed or ''}\n"
        f"Known facts:\n{facts}\n\n"
        f"Latest user message:\n{clean_text(message)}"
    )


def validate_turn_classification(data: dict[str, Any]) -> TurnClassification:
    turn_type = data.get("turn_type")
    confidence = data.get("confidence")
    if turn_type not in TURN_TYPES:
        raise ValueError(f"Invalid turn_type: {turn_type}")
    if confidence not in {"high", "medium", "low"}:
        raise ValueError(f"Invalid confidence: {confidence}")
    return TurnClassification(
        turn_type=turn_type,
        confidence=confidence,
        reason=clean_text(data.get("reason")),
        updated_case_summary=clean_text(data.get("updated_case_summary")),
        extracted_facts=[clean_text(item) for item in data.get("extracted_facts", []) if clean_text(item)],
        corrected_facts=[clean_text(item) for item in data.get("corrected_facts", []) if clean_text(item)],
    )


def apply_turn_safety_overrides(message: str, state: ActiveCaseState, result: TurnClassification) -> TurnClassification:
    deterministic = deterministic_turn_classification(message, state)
    if deterministic.turn_type in {"small_talk", "acknowledgement", "correction", "new_issue"} and deterministic.confidence == "high":
        return deterministic
    return result


def apply_turn_to_state(state: ActiveCaseState, message: str, classification: TurnClassification) -> ActiveCaseState:
    text = clean_text(message)
    if classification.turn_type == "correction":
        facts = apply_correction(state.known_facts, text)
    elif classification.turn_type in {"follow_up_question", "additional_fact", "clarification_reply"}:
        additions = classification.extracted_facts or ([text] if classification.turn_type != "follow_up_question" else [])
        facts = dedupe_facts([*state.known_facts, *additions])
    else:
        facts = list(state.known_facts)
    state.known_facts = facts[-MAX_FACTS:]
    if classification.updated_case_summary:
        state.case_summary = compact_text(classification.updated_case_summary, 420)
    elif classification.turn_type in {"follow_up_question", "additional_fact", "clarification_reply", "correction"}:
        state.case_summary = build_updated_case_summary(state, text, classification.turn_type)
    state.last_user_intent = classification.turn_type
    state.updated_at = time.time()
    ACTIVE_CASE_STATES[state.conversation_state_id] = state
    return state


def replace_state_for_new_issue(
    old_state: ActiveCaseState,
    domains: list[str],
    primary_domain: str | None,
    case_summary: str,
    known_facts: list[str] | None = None,
    confirmed_document_context_id: str | None = None,
) -> ActiveCaseState:
    clear_state(old_state.conversation_state_id)
    return create_state(
        domains=domains,
        primary_domain=primary_domain,
        case_summary=case_summary,
        known_facts=known_facts,
        confirmed_document_context_id=confirmed_document_context_id,
        last_user_intent="new_issue",
        last_issue_addressed=case_summary,
    )


def pipeline_message(latest_message: str, state: ActiveCaseState, document_fact_lines: list[str] | None = None) -> str:
    facts = "\n".join(f"- {fact}" for fact in state.known_facts[-8:])
    document_facts = "\n".join(f"- {fact}" for fact in document_fact_lines or [])
    parts = [
        f"Current user question: {clean_text(latest_message)}",
        f"Active case summary: {state.case_summary}",
    ]
    if facts:
        parts.append(f"Known case facts:\n{facts}")
    if document_facts:
        parts.append(f"Confirmed document facts:\n{document_facts}")
    return "\n".join(parts)


def update_state_after_answer(
    state: ActiveCaseState,
    route: Any,
    case_summary: str,
    latest_message: str,
    confirmed_document_context_id: str | None = None,
) -> ActiveCaseState:
    state.domains = unique_clean(getattr(route, "domains", []) or state.domains)
    state.primary_domain = getattr(route, "primary_domain", None) or state.primary_domain
    state.case_summary = compact_text(case_summary or state.case_summary, 420)
    state.last_issue_addressed = clean_text(latest_message) or state.last_issue_addressed
    if confirmed_document_context_id:
        state.confirmed_document_context_id = confirmed_document_context_id
    if latest_message:
        state.known_facts = dedupe_facts([*state.known_facts, clean_text(latest_message)])[-MAX_FACTS:]
    state.updated_at = time.time()
    ACTIVE_CASE_STATES[state.conversation_state_id] = state
    return state


def acknowledgement_response(state: ActiveCaseState, message: str | None = None) -> dict[str, Any]:
    return {
        "answer": {
            "issue_summary": message or "You're welcome. You can ask a follow-up question if you'd like.",
            "possible_rights": [],
            "next_steps": [],
        },
        "sources": [],
        "confidence": "high",
        "insufficient_context": False,
        "conversation_state_id": state.conversation_state_id,
        "conversation": {"turn_type": state.last_user_intent or "acknowledgement"},
    }


def compact_state_payload(state: ActiveCaseState | None) -> dict[str, Any] | None:
    if state is None:
        return None
    return {
        "conversation_state_id": state.conversation_state_id,
        "domains": list(state.domains),
        "primary_domain": state.primary_domain,
        "case_summary": state.case_summary,
        "known_facts": list(state.known_facts[-MAX_FACTS:]),
        "known_fact_count": len(state.known_facts),
        "confirmed_document_context_id": state.confirmed_document_context_id,
        "last_user_intent": state.last_user_intent,
        "last_issue_addressed": state.last_issue_addressed,
        "clarification_state_id": state.clarification_state_id,
    }


def is_small_talk(lowered: str) -> bool:
    text = re.sub(r"[^a-z0-9\s]+", " ", lowered)
    text = re.sub(r"\s+", " ", text).strip()
    return text in {"thanks", "thank you", "thankyou", "ok", "okay", "got it", "understood", "hello", "hi", "hey"}


def is_correction(lowered: str) -> bool:
    return contains_any(lowered, ("sorry", "correction", "actually", "it was", "it is", "not rs", "not ₹", "instead"))


def clearly_new_issue(lowered: str, state: ActiveCaseState) -> bool:
    if contains_any(lowered, ("divorce", "bail", "income tax", "inheritance", "child custody")):
        return True
    previous = set(state.domains)
    cue_domains = {
        "consumer": contains_any(lowered, ("seller", "refund", "product", "order", "invoice", "defective")),
        "cyber": contains_any(lowered, ("instagram", "hacked", "phishing", "cyber", "online account", "blocked me")),
        "tenancy": contains_any(lowered, ("landlord", "tenant", "rent", "electricity", "deposit", "evict")),
        "constitutional_public_authority": contains_any(lowered, ("rti", "article", "legal aid", "public authority", "government")),
    }
    active_domains = {domain for domain, present in cue_domains.items() if present}
    return bool(active_domains and previous and active_domains.isdisjoint(previous) and not refers_to_existing_case(lowered))


def is_question_like(lowered: str) -> bool:
    return "?" in lowered or contains_any(lowered, ("what if", "can i", "can they", "can he", "what should", "what can", "does this", "is this", "should i", "kaise", "kya"))


def refers_to_existing_case(lowered: str) -> bool:
    return contains_any(lowered, ("he ", "him", "she ", "they", "this", "that", "it ", "same", "earlier", "above", "what if"))


def has_fact_content(lowered: str) -> bool:
    return len(content_terms(lowered)) >= 2 or bool(re.search(r"(?:rs\.?|₹)\s*[\d,]+", lowered, flags=re.I))


def apply_correction(facts: list[str], correction: str) -> list[str]:
    correction_amounts = normalized_amounts(correction)
    correction_dates = normalized_dates(correction)
    updated = []
    for fact in facts:
        if correction_amounts and normalized_amounts(fact):
            continue
        if correction_dates and normalized_dates(fact):
            continue
        updated.append(fact)
    updated.append(correction)
    return dedupe_facts(updated)


def build_updated_case_summary(state: ActiveCaseState, latest_message: str, turn_type: str) -> str:
    if turn_type == "correction":
        return compact_text(f"{state.case_summary} Corrected fact: {latest_message}", 420)
    if turn_type == "additional_fact":
        return compact_text(f"{state.case_summary} Additional fact: {latest_message}", 420)
    return compact_text(f"{state.case_summary} Follow-up: {latest_message}", 420)


def dedupe_facts(values: list[str]) -> list[str]:
    output = []
    seen = set()
    for value in values:
        cleaned = clean_text(value)
        if not cleaned:
            continue
        key = re.sub(r"[^a-z0-9]+", "", cleaned.lower())
        if key in seen:
            continue
        seen.add(key)
        output.append(cleaned)
    return output[-MAX_FACTS:]


def unique_clean(values: list[str]) -> list[str]:
    output = []
    for value in values:
        cleaned = clean_text(value)
        if cleaned and cleaned not in output:
            output.append(cleaned)
    return output


def normalized_amounts(text: str) -> set[str]:
    values = set()
    for match in re.findall(r"(?:rs\.?|inr|₹)\s*[\d,]+|\b\d{3,}(?:,\d{2,3})*\b", text or "", flags=re.I):
        digits = re.sub(r"\D", "", match)
        if digits:
            values.add(digits)
    return values


def normalized_dates(text: str) -> set[str]:
    dates = set()
    months = "january|february|march|april|may|june|july|august|september|october|november|december|jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
    for match in re.findall(rf"\b\d{{1,2}}\s+(?:{months})\s+\d{{4}}\b", text or "", flags=re.I):
        dates.add(re.sub(r"\s+", " ", match.lower()))
    for match in re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text or ""):
        dates.add(match)
    return dates


def content_terms(text: str) -> set[str]:
    stop = {"the", "and", "for", "with", "hai", "hain", "mera", "mere", "meri", "this", "that", "what", "can", "should", "legal"}
    return {token for token in re.findall(r"[a-zA-Z0-9]+", text.lower()) if token not in stop and len(token) > 2}


def contains_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(cue in text for cue in cues)


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def compact_text(text: str, max_chars: int) -> str:
    cleaned = clean_text(text)
    if len(cleaned) <= max_chars:
        return cleaned
    return cleaned[: max_chars - 1].rsplit(" ", 1)[0] + "..."
