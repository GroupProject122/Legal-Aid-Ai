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

logger = logging.getLogger("legal_aid_ai.clarification")

REASON_CODES = {
    "domain_ambiguity",
    "event_ambiguity",
    "party_ambiguity",
    "transaction_context",
    "public_authority_context",
    "tenancy_context",
    "cyber_context",
    "consumer_context",
    "general_missing_context",
}
PROGRESS_VALUES = {"meaningful", "minimal", "none"}


@dataclass
class ClarificationTurn:
    question: str
    answer: str | None = None


@dataclass
class ClarificationState:
    state_id: str
    original_message: str
    accumulated_context: str
    router_status: str
    clarification_history: list[ClarificationTurn] = field(default_factory=list)
    no_progress_count: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            **asdict(self),
            "clarification_history": [asdict(item) for item in self.clarification_history],
        }


@dataclass
class ClarificationQuestion:
    question: str
    missing_information_type: str
    reason_code: str
    latency_ms: int | None = None
    provider: str = "gemini"
    generation_error: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProgressAssessment:
    progress: str
    should_continue: bool
    accumulated_context: str
    safe_exit: bool = False


CLARIFICATION_STATES: dict[str, ClarificationState] = {}

CLARIFICATION_PROMPT = """You help Legal Aid AI ask one clarification question before legal retrieval.
Do not answer the legal issue.
Do not cite laws.
Do not provide remedies or legal advice.
Ask exactly one concise question that helps identify the supported legal domain.

Supported domains are:
- consumer
- cyber
- tenancy
- constitutional_public_authority

Do not ask for jurisdiction, city, state, evidence, dates, exact amount, or desired remedy unless it is necessary only to identify the domain.
Match the user's language style when practical, including simple Hinglish.
Return only structured JSON.
"""

CLARIFICATION_SCHEMA = {
    "type": "object",
    "properties": {
        "question": {"type": "string"},
        "missing_information_type": {"type": "string"},
        "reason_code": {"type": "string", "enum": sorted(REASON_CODES)},
    },
    "required": ["question", "missing_information_type", "reason_code"],
}

BROAD_FALLBACK_QUESTION = "Briefly, who is involved and what happened?"


def start_clarification(original_message: str, route: domain_router.RouteDecision) -> tuple[ClarificationState, ClarificationQuestion]:
    state = ClarificationState(
        state_id=uuid.uuid4().hex,
        original_message=original_message.strip(),
        accumulated_context=original_message.strip(),
        router_status=route.status,
    )
    question = generate_clarification_question(state, route)
    state.clarification_history.append(ClarificationTurn(question=question.question))
    CLARIFICATION_STATES[state.state_id] = state
    return state, question


def get_state(state_id: str | None) -> ClarificationState | None:
    if not state_id:
        return None
    return CLARIFICATION_STATES.get(state_id)


def clear_state(state_id: str | None) -> None:
    if state_id:
        CLARIFICATION_STATES.pop(state_id, None)


def record_answer(state: ClarificationState, answer: str) -> ProgressAssessment:
    clean_answer = normalize_text(answer)
    if state.clarification_history:
        state.clarification_history[-1].answer = clean_answer

    progress = assess_clarification_progress(state, clean_answer)
    state.accumulated_context = progress.accumulated_context
    if progress.progress == "meaningful":
        state.no_progress_count = 0
    else:
        state.no_progress_count += 1
    return progress


def assess_clarification_progress(state: ClarificationState, latest_answer: str) -> ProgressAssessment:
    answer = normalize_text(latest_answer)
    if not answer or len(answer) < 4:
        return ProgressAssessment("none", True, state.accumulated_context)

    original_terms = content_terms(state.accumulated_context)
    answer_terms = content_terms(answer)
    new_terms = answer_terms - original_terms
    if len(new_terms) >= 2 or contains_domain_cue(answer):
        progress = "meaningful"
    elif len(new_terms) == 1:
        progress = "minimal"
    else:
        progress = "none"

    accumulated = combine_context(state.original_message, state.clarification_history, latest_answer)
    should_continue = progress in {"meaningful", "minimal"}
    safe_exit = progress != "meaningful" and state.no_progress_count >= 1
    if safe_exit:
        should_continue = False
    return ProgressAssessment(progress, should_continue, accumulated, safe_exit=safe_exit)


def generate_next_question(
    state: ClarificationState,
    route: domain_router.RouteDecision,
    progress: ProgressAssessment | None = None,
) -> ClarificationQuestion:
    if progress and progress.progress == "none":
        question = ClarificationQuestion(
            question=BROAD_FALLBACK_QUESTION,
            missing_information_type="general_context",
            reason_code="general_missing_context",
        )
    else:
        question = generate_clarification_question(state, route)
    question.question = avoid_repeated_question(question.question, state)
    state.clarification_history.append(ClarificationTurn(question=question.question))
    return question


def generate_clarification_question(
    state: ClarificationState,
    route: domain_router.RouteDecision,
) -> ClarificationQuestion:
    started = time.perf_counter()
    if not GEMINI_API_KEY:
        return fallback_question(state)

    try:
        client = genai.Client(api_key=GEMINI_API_KEY)
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=build_clarification_prompt(state, route),
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=CLARIFICATION_SCHEMA,
            ),
        )
        data = json.loads(response.text or "{}")
        question = validate_clarification_question(data)
        question.latency_ms = int((time.perf_counter() - started) * 1000)
        return question
    except (genai_errors.APIError, TimeoutError, RuntimeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Gemini clarification failed safely: %s: %s", exc.__class__.__name__, str(exc))
        question = fallback_question(state)
        question.latency_ms = int((time.perf_counter() - started) * 1000)
        question.generation_error = True
        return question


def build_clarification_prompt(state: ClarificationState, route: domain_router.RouteDecision) -> str:
    history = "\n".join(
        f"Q: {turn.question}\nA: {turn.answer or ''}".strip()
        for turn in state.clarification_history[-3:]
    )
    return (
        f"{CLARIFICATION_PROMPT}\n"
        f"Original user message:\n{state.original_message}\n\n"
        f"Accumulated context:\n{state.accumulated_context}\n\n"
        f"Router status: {route.status}\n"
        f"Router issue summary: {route.issue_summary or ''}\n"
        f"Previous clarification history:\n{history or 'None'}"
    )


def validate_clarification_question(data: dict[str, Any]) -> ClarificationQuestion:
    question = normalize_text(data.get("question"))
    missing_type = normalize_text(data.get("missing_information_type")) or "general_context"
    reason = data.get("reason_code")
    if not question:
        raise ValueError("Clarification question is required.")
    if "?" not in question and not question.endswith("hai"):
        question = f"{question}?"
    if reason not in REASON_CODES:
        raise ValueError(f"Invalid clarification reason_code: {reason}")
    if asks_for_jurisdiction(question):
        raise ValueError("Clarification question must not ask for jurisdiction yet.")
    return ClarificationQuestion(question=question, missing_information_type=missing_type, reason_code=reason)


def fallback_question(state: ClarificationState) -> ClarificationQuestion:
    text = state.accumulated_context.lower()
    if any(word in text for word in ("paise", "money", "payment", "refund")):
        question = "Paise kis context mein fase hain — seller/payment, cyber fraud, landlord, ya kisi aur matter mein?"
        reason = "transaction_context"
    elif "notice" in text:
        question = "Notice kis taraf se mila hai — landlord, government authority, court/police, company/seller, ya kisi aur se?"
        reason = "party_ambiguity"
    elif any(word in text for word in ("troubling", "trouble", "pareshan")):
        question = "Kaun trouble kar raha hai aur kya kar raha hai?"
        reason = "party_ambiguity"
    else:
        question = BROAD_FALLBACK_QUESTION
        reason = "general_missing_context"
    return ClarificationQuestion(question=avoid_repeated_question(question, state), missing_information_type="context", reason_code=reason)


def combine_context(original_message: str, history: list[ClarificationTurn], latest_answer: str | None = None) -> str:
    parts = [f"Original issue: {normalize_text(original_message)}"]
    for turn in history:
        if turn.answer:
            parts.append(f"Clarification answer: {normalize_text(turn.answer)}")
    if latest_answer and (not history or history[-1].answer != normalize_text(latest_answer)):
        parts.append(f"Clarification answer: {normalize_text(latest_answer)}")
    return " ".join(part for part in parts if part.strip())


def avoid_repeated_question(question: str, state: ClarificationState) -> str:
    normalized = normalize_text(question).lower()
    previous = {normalize_text(turn.question).lower() for turn in state.clarification_history}
    if normalized in previous:
        return BROAD_FALLBACK_QUESTION
    return question


def contains_domain_cue(text: str) -> bool:
    lowered = text.lower()
    cues = (
        "seller",
        "refund",
        "product",
        "landlord",
        "tenant",
        "rent",
        "hack",
        "phishing",
        "instagram",
        "cyber",
        "rti",
        "government",
        "legal aid",
        "divorce",
        "bail",
        "weather",
        "python",
    )
    return any(cue in lowered for cue in cues)


def content_terms(text: str) -> set[str]:
    stop = {
        "hai",
        "hain",
        "mere",
        "mera",
        "meri",
        "mujhe",
        "bas",
        "kya",
        "the",
        "and",
        "for",
        "with",
        "issue",
        "matter",
        "legal",
    }
    return {token for token in re.findall(r"[a-zA-Z0-9]+", text.lower()) if token not in stop and len(token) > 2}


def normalize_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def asks_for_jurisdiction(question: str) -> bool:
    lowered = question.lower()
    return any(phrase in lowered for phrase in ("which state", "which city", "what city", "property location", "kis state", "kaunse state"))
