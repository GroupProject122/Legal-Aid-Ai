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
import turn_memory

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

Decide from what the user means, not from punctuation or keywords. Users often type questions
without a question mark, in lowercase, in Hinglish, or as statements of need or confusion.
Return follow_up_question for anything that asks for help, information, explanation or guidance
about the active case, including: "i dont know how civil courts work", "tell me the process",
"what next", "how do i file it", "ab kya karu", "mujhe samajh nahi aaya", "i cant afford a lawyer",
and elliptical questions like "and the deposit". A message that both adds a fact and asks
something is follow_up_question.
Return additional_fact only when the user adds a fact about the case and is clearly not asking for anything.
Return correction only when the user replaces or corrects an earlier fact ("sorry, it was Rs. 45,000", "i meant water not electricity").
Return new_issue ONLY when the message clearly starts a different, unrelated legal problem. A new
detail, grievance or question about the same dispute, the same people, or the same property is NOT
a new issue ("the landlord also took my furniture, can i complain about that too" is follow_up_question).
When unsure between new_issue and anything else, do not choose new_issue: it discards the conversation.
Return acknowledgement or small_talk ONLY for messages that contain nothing but thanks, okay,
greetings or similar. If the message also asks or states anything ("ok but what about the deposit"),
it is not an acknowledgement. When unsure, choose follow_up_question: an acknowledgement gives the user no answer.
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


def classify_turn(
    message: str,
    state: ActiveCaseState,
    use_memory: bool = True,
    record_corrections: bool = True,
) -> TurnClassification:
    """Keyword rules make a first guess; Gemini makes the decision.

    The rules alone decide only pure acknowledgements / greetings ("thanks", "ok", "hi"), which
    are exact-vocabulary matches that cannot really be misread -- and everything when Gemini is
    unavailable, as a fallback. For every other message the rules' guess is passed to Gemini as
    an explicitly fallible hint, together with similar past messages Gemini has already sorted
    (turn_memory). An approved past correction that is a near-duplicate of this message is used
    directly, without a Gemini call. When Gemini disagrees with the rules, the disagreement is
    recorded (redacted, pending human review) so it can be reused as an example next time.

    use_memory / record_corrections exist so evaluation can score the classifier reproducibly,
    without reading from or writing to the correction memory."""
    deterministic = deterministic_turn_classification(message, state)
    if deterministic.confidence == "high":
        return deterministic

    if use_memory:
        remembered = turn_memory.shortcut_label(message)
        if remembered:
            result = TurnClassification(
                remembered,
                "high",
                "Matches a reviewed past correction of a near-identical message.",
                extracted_facts=[clean_text(message)] if remembered == "additional_fact" else [],
                corrected_facts=[clean_text(message)] if remembered == "correction" else [],
                provider="memory",
            )
            return apply_turn_safety_overrides(message, state, result)

    if not GEMINI_API_KEY:
        return deterministic

    examples = turn_memory.similar_examples(message) if use_memory else []
    started = time.perf_counter()
    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=build_turn_prompt(message, state, rule_hint=deterministic, examples=examples),
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
        result = apply_turn_safety_overrides(message, state, result)
    except (genai_errors.APIError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Gemini turn classification failed safely: %s: %s", exc.__class__.__name__, str(exc))
        deterministic.error = True
        deterministic.latency_ms = int((time.perf_counter() - started) * 1000)
        return deterministic

    if record_corrections and result.turn_type != deterministic.turn_type:
        turn_memory.record_correction(
            message=message,
            domains=state.domains,
            rule_label=deterministic.turn_type,
            model_label=result.turn_type,
            reason=result.reason,
        )
    return result


# Pure acknowledgement / greeting vocabulary. A message made only of these words is the one case
# the rules decide alone; one extra word ("ok but what about the deposit") sends it to Gemini.
ACKNOWLEDGEMENT_WORDS = {
    "thanks", "thank", "thankyou", "thx", "ty", "you", "so", "very", "much", "a", "lot", "ok", "okay",
    "okk", "k", "got", "it", "understood", "great", "cool", "fine", "noted", "alright", "sure", "nice",
    "perfect", "this", "that", "helps", "helped", "helpful", "shukriya", "dhanyavad", "theek", "hai",
}
GREETING_WORDS = {"hello", "hi", "hey", "hii", "namaste", "good", "morning", "evening", "afternoon"}

# Question cues for messages typed without a "?". Checked as whole words/phrases.
QUESTION_START_RE = re.compile(
    r"^(?:(?:so|and|but|ok|okay|thanks|sorry)[\s,]+)*"
    r"(?:how|what|why|where|when|who|whom|whose|which|is|are|am|can|could|should|would|will|do|does|did|may|shall|was|were)\b"
)
QUESTION_PHRASE_RE = re.compile(
    r"\b(?:what if|what about|what next|now what|and if|tell me|explain|help me|guide me|advise|"
    r"i (?:do ?n[o']?t|dont) (?:know|understand)|(?:do ?n[o']?t|dont) understand|not sure|no idea|confused|"
    r"i (?:want|need|would like) to know|is that (?:right|correct|true)|is it (?:legal|allowed|possible)|"
    r"can i|can they|can he|can she|can you|should i|do i|what should|what can|"
    r"kya|kaise|kab|kahan|kyun|kyon|kitna|kitne|kaun|karu|karun|karoon|samajh nahi|ya nahi|batao|bataiye)\b"
)
CORRECTION_RE = re.compile(
    r"^(?:sorry|correction|actually|no wait|wait|oops|my bad)\b|\bi meant\b|\binstead\b|"
    r"\bnot\s+(?:rs\.?\s*|inr\s*|₹\s*)?[\d,]{2,}|\b(?:it|that) was\b[^.?!]*\bnot\b"
)
NEW_ISSUE_MARKERS = ("separately", "different problem", "different issue", "another problem", "another issue", "unrelated", "new problem", "new issue", "on another note")
OUT_OF_SCOPE_NEW_ISSUE_CUES = ("divorce", "bail", "income tax", "inheritance", "child custody", "salary", "employer", "maintenance from my husband")


def deterministic_turn_classification(message: str, state: ActiveCaseState) -> TurnClassification:
    """The keyword first guess. Only pure acknowledgements/greetings come back with "high"
    confidence (decided without Gemini); every other label is a hint for Gemini, and the
    fallback answer when Gemini is unavailable. Ordered so the costly mistakes are the hardest to
    make: a question is recognised before a correction ("actually can i just stop paying rent"),
    and anything unrecognised defaults to a follow-up question, never to an acknowledgement."""
    text = clean_text(message)
    lowered = text.lower()
    if is_small_talk(lowered):
        turn_type = "small_talk" if is_greeting_only(lowered) else "acknowledgement"
        return TurnClassification(turn_type, "high", "Conversational message that does not need legal retrieval.")
    if clearly_new_issue(lowered, state):
        return TurnClassification("new_issue", "medium", "Latest message appears unrelated to the active case.")
    if is_question_like(lowered):
        return TurnClassification("follow_up_question", "medium", "Likely asks about the active case.")
    if is_correction(lowered):
        return TurnClassification("correction", "medium", "User appears to correct an earlier fact.", corrected_facts=[text])
    if has_fact_content(lowered):
        return TurnClassification("additional_fact", "medium", "Reads as a factual statement without a recognised question cue.", extracted_facts=[text])
    return TurnClassification("follow_up_question", "low", "Ambiguous short message in an active legal consultation.")


def build_turn_prompt(
    message: str,
    state: ActiveCaseState,
    rule_hint: TurnClassification | None = None,
    examples: list[dict[str, str]] | None = None,
) -> str:
    facts = "\n".join(f"- {fact}" for fact in state.known_facts[-8:]) or "None"
    parts = [
        TURN_CLASSIFIER_PROMPT,
        "",
        f"Active case summary:\n{state.case_summary}",
        "",
        f"Domains: {', '.join(state.domains)}",
        f"Last issue addressed: {state.last_issue_addressed or ''}",
        f"Known facts:\n{facts}",
    ]
    if examples:
        lines = "\n".join(f'- "{item["message"]}" -> {item["turn_type"]}' for item in examples)
        parts.extend(["", f"Similar past messages and their correct turn_type (for reference):\n{lines}"])
    if rule_hint is not None:
        parts.extend([
            "",
            "Keyword-rule pre-classification (a HINT that may be wrong -- verify it against the message's meaning):",
            f"turn_type={rule_hint.turn_type}; reason: {rule_hint.reason}",
            "These rules only look for punctuation and keywords. They often mislabel questions typed "
            "without a question mark as additional_fact, and can mistake phrases like \"it is\" or "
            "\"actually\" for corrections. Overrule the hint whenever the message means something else.",
        ])
    parts.extend(["", f"Latest user message:\n{clean_text(message)}"])
    return "\n".join(parts)


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
    """Guards against the two mistakes that hurt the user, whoever made them:
    - swallowing a question: an acknowledgement / small-talk label is only kept when the message
      is nothing but acknowledgement or greeting words; otherwise it becomes a follow-up question.
    - wiping the conversation: new_issue is not accepted for a message that points back at the
      current case ("also", "that", "he", "they"...) unless it carries an explicit new-topic
      marker ("separately", "unrelated") or an out-of-scope topic cue."""
    lowered = clean_text(message).lower()
    if result.turn_type in {"acknowledgement", "small_talk"} and not is_small_talk(lowered):
        return TurnClassification(
            "follow_up_question", "medium", "Overrode an acknowledgement label: the message says more than thanks/ok.",
            provider=result.provider, latency_ms=result.latency_ms,
        )
    if (
        result.turn_type == "new_issue"
        and refers_to_existing_case(lowered)
        and not contains_any(lowered, NEW_ISSUE_MARKERS)
        and not contains_any(lowered, OUT_OF_SCOPE_NEW_ISSUE_CUES)
        and not other_domain_cues(lowered, state)
    ):
        return TurnClassification(
            "follow_up_question", "medium", "Overrode a new-issue label: the message refers back to the current case.",
            provider=result.provider, latency_ms=result.latency_ms,
        )
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
        f"{PIPELINE_QUESTION_PREFIX}{clean_text(latest_message)}",
        f"Active case summary: {state.case_summary}",
    ]
    if facts:
        parts.append(f"Known case facts:\n{facts}")
    if document_facts:
        parts.append(f"Confirmed document facts:\n{document_facts}")
    return "\n".join(parts)


PIPELINE_QUESTION_PREFIX = "Current user question: "


def split_pipeline_message(text: str) -> tuple[str, str] | None:
    """Undo pipeline_message(): return (latest user question, case background), or None when
    `text` is not a pipeline message. Lets the answer writer reply to the question the user just
    asked instead of treating the whole case as the thing to answer."""
    if not text or not text.startswith(PIPELINE_QUESTION_PREFIX):
        return None
    first_line, _, rest = text.partition("\n")
    question = first_line[len(PIPELINE_QUESTION_PREFIX):].strip()
    return (question, rest.strip()) if question else None


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


def small_talk_words(lowered: str) -> list[str]:
    text = re.sub(r"[^a-z0-9\s]+", " ", lowered)
    return text.split()


def is_small_talk(lowered: str) -> bool:
    """True only when every word is acknowledgement/greeting vocabulary ("ok thank you so much",
    "thank you this helps", "hi"). The previous exact-phrase list missed "ok thank you so much"
    and "understood thanks", which then fell through to being treated as case facts."""
    words = small_talk_words(lowered)
    return bool(words) and len(words) <= 8 and all(word in ACKNOWLEDGEMENT_WORDS | GREETING_WORDS for word in words)


def is_greeting_only(lowered: str) -> bool:
    words = small_talk_words(lowered)
    return bool(words) and all(word in GREETING_WORDS for word in words)


def is_correction(lowered: str) -> bool:
    """Explicit correction phrasing only. Bare "it is" / "it was" used to count, which turned
    ordinary facts ("they said it is my fault", "it is still not fixed") into corrections."""
    return bool(CORRECTION_RE.search(lowered))


DOMAIN_CUE_RES = {
    "consumer": re.compile(r"\b(?:seller|refunds?|products?|orders?|invoice|defective)\b"),
    "cyber": re.compile(r"\b(?:instagram|hacked|phishing|cyber|online account|blocked me)\b"),
    "tenancy": re.compile(r"\b(?:landlord|tenants?|rent|rented|electricity|deposit|evict(?:ed|ion)?)\b"),
    "constitutional_public_authority": re.compile(r"\b(?:rti|article|legal aid|public authority|government)\b"),
}


def other_domain_cues(lowered: str, state: ActiveCaseState) -> set[str]:
    """Legal areas the message mentions that the current case is NOT about -- the signal that a
    message is a different problem even when it says "also" ("my RTI application also got no
    reply" during a consumer case)."""
    cued = {domain for domain, pattern in DOMAIN_CUE_RES.items() if pattern.search(lowered)}
    previous = set(state.domains)
    return cued if (cued and previous and cued.isdisjoint(previous)) else set()


def clearly_new_issue(lowered: str, state: ActiveCaseState) -> bool:
    if contains_any(lowered, NEW_ISSUE_MARKERS) or contains_any(lowered, OUT_OF_SCOPE_NEW_ISSUE_CUES):
        return True
    return bool(other_domain_cues(lowered, state)) and not refers_back_to_people(lowered)


def refers_back_to_people(lowered: str) -> bool:
    """Pronouns / back-references strong enough to tie a message mentioning another legal area
    to the current case ("can I report him online" in a seller dispute). Deliberately excludes
    "also"/"too", which join a second problem as often as they extend the first."""
    return bool(re.search(r"\b(?:he|him|his|she|her|they|them|their|same|earlier|above)\b", lowered)) or "what if" in lowered


def is_question_like(lowered: str) -> bool:
    """A "?" is not required: users type questions as statements ("tell me the process",
    "i dont know how civil courts work"), without punctuation ("how do i file it"), or in
    Hinglish ("ab kya karu"). Also checks after a comma, so "thanks, and what if they ignore
    the notice" is recognised."""
    if "?" in lowered:
        return True
    clauses = [clause.strip() for clause in re.split(r"[,;.!]", lowered) if clause.strip()]
    return any(QUESTION_START_RE.search(clause) for clause in clauses) or bool(QUESTION_PHRASE_RE.search(lowered))


def refers_to_existing_case(lowered: str) -> bool:
    return bool(re.search(r"\b(?:he|him|his|she|her|they|them|their|this|that|it|same|earlier|above|also|too|again|still)\b", lowered)) or "what if" in lowered


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
