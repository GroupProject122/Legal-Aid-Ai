from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

import faiss
import numpy as np
from google import genai
from google.genai import errors as genai_errors
from google.genai import types
from sentence_transformers import SentenceTransformer

import grounded_answer
import claim_verifier
import source_text
from config import (
    DISCLAIMER,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    GEMINI_API_KEY,
    GEMINI_MODEL,
    INDEX_PATH,
    LLM_PROVIDER,
    MAX_QUESTION_CHARS,
    METADATA_PATH,
    TOP_K,
)

logger = logging.getLogger("legal_aid_ai.rag")


class RAGError(Exception):
    status_code = 500


class VectorStoreMissingError(RAGError):
    status_code = 503


class VectorStoreIncompatibleError(RAGError):
    status_code = 503


class ConfigurationError(RAGError):
    status_code = 503


class LLMError(RAGError):
    status_code = 502


@dataclass
class RetrievedChunk:
    text: str
    source: str
    document_title: str
    page: int
    score: float
    rerank_score: float = 0.0
    domain: str | None = None
    retrieval_priority: str | None = None
    authority_level: str | None = None
    status: str | None = None
    document_type: str | None = None
    chapter: str | None = None
    section_number: str | None = None
    section_title: str | None = None
    rule_number: str | None = None
    rule_title: str | None = None
    chunk_id: str | None = None
    article_number: str | None = None
    article_title: str | None = None
    regulation_number: str | None = None
    regulation_title: str | None = None
    guideline_number: str | None = None
    guideline_title: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    # Case-law fields. Carried through so downstream code can act on them rather than relying on
    # the warning text embedded in the chunk body: good_law in particular is a safety signal
    # (see enforce_good_law_warning), and it was being dropped here at retrieval time.
    paragraph_number: str | None = None
    case_name: str | None = None
    citation: str | None = None
    court: str | None = None
    good_law: Any | None = None


CONSUMER_KEYWORDS = {
    "consumer", "seller", "refund", "replacement", "replace", "repair", "defective",
    "defect", "product", "goods", "service", "services", "invoice", "warranty",
    "guarantee", "online", "ecommerce", "e-commerce", "purchase", "bought",
    "shop", "merchant", "complaint", "damaged", "order", "price", "payment",
    "phone", "mobile", "faulty", "broken",
}

OFF_TOPIC_KEYWORDS = {
    "landlord", "tenant", "rent", "deposit", "instagram", "hacked", "weather",
    "python", "code", "criminal", "fir", "murder", "medical", "doctor",
}

SUBSTANTIVE_LEGAL_KEYWORDS = {
    "consumer rights", "right to", "defect", "defective", "deficiency",
    "product liability", "liable", "compensation", "refund", "replacement",
    "repair", "redressal", "complaint", "district commission", "unfair trade",
    "manufacturer", "product seller", "express warranty", "manufacturing defect",
}

ADMINISTRATIVE_KEYWORDS = {
    "salary", "allowance", "appointment", "meeting", "minutes", "form", "fee payable",
    "accounts", "budget", "annual report", "selection committee", "vacancy",
    "mediator", "settlement report", "settlement", "recording such settlement",
}

DOMAIN_SIGNAL_CUES = {
    "consumer": {
        "defective product": 0.45,
        "defective goods": 0.45,
        "refund": 0.32,
        "replacement": 0.3,
        "replace": 0.25,
        "warranty": 0.28,
        "seller": 0.28,
        "ecommerce order": 0.35,
        "e-commerce order": 0.35,
        "misleading advertisement": 0.45,
        "dark pattern": 0.45,
        "service deficiency": 0.4,
        "deficiency": 0.24,
        "product liability": 0.45,
        "consumer complaint": 0.42,
        "consumer commission": 0.4,
        "direct selling": 0.42,
        "damaged goods": 0.35,
        "faulty product": 0.35,
        "instagram seller": 0.34,
        "online seller took payment": 0.38,
        "never delivered": 0.28,
    },
    "cyber": {
        "hacked": 0.42,
        "hacking": 0.42,
        "phishing": 0.45,
        "cyber fraud": 0.55,
        "cybercrime": 0.5,
        "cyber crime": 0.5,
        "otp fraud": 0.48,
        "unauthorized access": 0.5,
        "account hacked": 0.55,
        "used my login details": 0.48,
        "used my credentials": 0.48,
        "used my personal details": 0.38,
        "access account without permission": 0.45,
        "access my online account": 0.4,
        "logged in as me": 0.45,
        "pretended to be me online": 0.48,
        "account credentials": 0.48,
        "social media hacked": 0.55,
        "social media": 0.28,
        "instagram": 0.28,
        "blocked me": 0.18,
        "took payment and blocked": 0.35,
        "blocked after payment": 0.34,
        "disappeared after payment": 0.36,
        "fake seller": 0.3,
        "identity theft": 0.5,
        "malware": 0.42,
        "password stolen": 0.45,
        "online scam": 0.42,
        "digital fraud": 0.5,
        "upi fraud": 0.5,
        "fraudulent transaction": 0.45,
        "data breach": 0.45,
        "private data": 0.35,
        "intermediary": 0.38,
        "unlawful content": 0.34,
        "grievance officer": 0.35,
        "report online cybercrime": 0.55,
    },
    "tenancy": {
        "landlord": 0.42,
        "tenant": 0.4,
        "rent": 0.32,
        "eviction": 0.42,
        "security deposit": 0.45,
        "lease": 0.34,
        "rent agreement": 0.45,
        "electricity cut": 0.45,
        "cut electricity": 0.45,
        "essential supply": 0.48,
        "premises": 0.3,
        "rented property": 0.36,
    },
    "constitutional_public_authority": {
        "article 14": 0.5,
        "article 19": 0.5,
        "article 21": 0.5,
        "fundamental right": 0.45,
        "equality": 0.4,
        "freedom of speech": 0.5,
        "rti": 0.5,
        "right to information": 0.5,
        "public authority": 0.45,
        "legal aid": 0.42,
        "free lawyer": 0.4,
        "human rights": 0.45,
        "custodial abuse": 0.45,
        "contempt of court": 0.45,
        "disobeyed court order": 0.45,
        "court order was deliberately disobeyed": 0.45,
        "government authority": 0.38,
        "personal liberty": 0.42,
        "government office": 0.32,
    },
}
GENERIC_DOMAIN_TERMS = {"online", "payment", "money", "complaint", "account", "issue", "problem"}
DOMAIN_SIGNAL_THRESHOLD = 0.25
DOMAIN_SIGNAL_CLOSE_DELTA = 0.16
DOMAIN_PRIMARY_BOOST = 0.20
DOMAIN_SECONDARY_BOOST = 0.10
DOMAIN_MISMATCH_PENALTY = 0.12
# HISTORY (2026-09-14/15): the cybercrime_portal_citizen_manual_latest.pdf retrieval drift went
# through four escalating rounds across two days, in this order -- read as a record of what was
# tried and why each step alone was insufficient, not a single clean design:
#   1. ACCEPT: originally logged here as an accepted, not-fixed limitation, relying only on the
#      baseline weights immediately below (still the general-purpose priority/authority signal,
#      applied to every document regardless of query type). Insufficient: raw semantic similarity
#      for plain-language citizen queries was strong enough to survive these baseline penalties.
#   2. STRENGTHEN SCORING: added PROCEDURAL_GUIDE_SUBSTANTIVE_PENALTY (in authority_level_boost()
#      and relevance_gate_score() below) -- a much larger, query-conditional penalty for
#      procedural manuals on substantive (non-procedural-intent) queries specifically. Verified
#      effective wherever the target statute was already a raw-FAISS candidate -- but insufficient
#      on its own: several substantive cyber queries never fetched IT Act s.66C as a candidate at
#      all (raw-FAISS rank 41-61, outside the then-current candidate_k=40), so no scoring change
#      could surface a document that was never in the pool.
#   3. WIDEN CANDIDATES: added the cyber-specific candidate_k=100 branch in
#      production_candidate_k() below, specifically to close the gap step 2 exposed. This is what
#      actually got IT Act into the top 5 for most tested substantive queries. Also extended step
#      2's penalty to retrieval_priority=medium (not just low) after confirming
#      npci_upi_procedural_guidelines.pdf shares the same crowding risk. Side effect found: the
#      wider pool let one document (DPDP Act 2023) monopolize every selected slot on one query
#      ("someone shared private data online"), pushing out a second expected document (IT Act
#      2000) that the narrower pool had included.
#   4. DIVERSITY CAP: added DOCUMENT_DIVERSITY_CAP=2 to select_relevant_chunks() (below), fixing
#      step 3's side effect directly -- confirmed it restores IT Act 2000 for that query without
#      regressing the three queries step 3 had just fixed ("cyber fraud online payment", "phishing
#      link stole my money", "someone hacked my social media account").
# Also found, NOT fixed (recorded in CHANGELOG.md's known-limitations callout instead): some
# plainly cyber/payment-fraud phrasings (e.g. "rights after online payment fraud") get a zero
# score from detect_domain_signals() for every domain, so they never reach the cyber-specific
# candidate_k branch above at all -- a separate, upstream cue-coverage gap, not something steps
# 1-4 could address.
# Net effect verified this session: single-domain Document Hit@5 88.9%->94.4%, MRR 0.813->0.857;
# cyber domain Document Hit@5 66.7%->88.9%, MRR 0.404->0.615 (all in eval/retrieval_evaluation.md).
RETRIEVAL_PRIORITY_WEIGHTS = {
    "high": 0.045,
    "medium": 0.02,
    "low": -0.015,
}
AUTHORITY_LEVEL_WEIGHTS = {
    "primary": 0.035,
    "official_guidance": 0.018,
    "procedural_guide": -0.012,
}
SUPPORTING_ONLY_PENALTY = 0.04
REFERENCE_ONLY_PENALTY = 0.035
PROCEDURAL_QUERY_MANUAL_BOOST = 0.06
PROCEDURAL_GUIDE_SUBSTANTIVE_PENALTY = 0.20
# Same shape of problem as the procedural-manual penalty above, found when judgments were first
# ingested (2026-09-24). Case law carries authority_level=primary -- correct, a Supreme Court
# judgment is primary authority -- so it competes directly with statutes, and a judgment
# discussing a topic at length can outrank the provision that actually states the obligation.
# The concrete regression: eval query cyber_05 "intermediary failed to remove unlawful content"
# returned Mrs X v. Union of India at rerank 0.9263, displacing the IT Intermediary Guidelines
# Rules that carry the takedown duty. Smaller than the procedural penalty (0.20) because case law
# is genuinely more authoritative than a citizen manual: the aim is to seat judgments alongside
# the governing provision rather than ahead of it, not to suppress them.
CASE_LAW_SUBSTANTIVE_PENALTY = 0.18
# Mirrors corpus_gap.case_law_query. Duplicated rather than imported because corpus_gap imports
# rag (it builds RetrievedChunk), so importing back would be circular.
CASE_LAW_QUERY_TERMS = (
    "supreme court held",
    "high court held",
    "what did the supreme court",
    "what did the high court",
    "held in",
    "judgment in",
    "judgement in",
    "case law",
    "precedent",
    "ratio",
    " vs ",
    " v. ",
)
PROCEDURAL_QUERY_TERMS = {
    "report",
    "reporting",
    "portal",
    "file",
    "filing",
    "register",
    "submit",
    "how do i",
    "where can i",
}
PUBLIC_AUTHORITY_INTENT_CUES = {
    "rti": {
        "rti": 0.55,
        "right to information": 0.55,
        "information request": 0.38,
        "public information officer": 0.48,
        "pio": 0.42,
        "information denied": 0.42,
        "refusing information": 0.42,
        "refused information": 0.42,
        "refused to give information": 0.45,
        "rti application": 0.55,
        "no reply to rti": 0.55,
        "appeal under rti": 0.5,
        "government office for records": 0.32,
    },
    "fundamental_rights": {
        "article 14": 0.55,
        "article 19": 0.55,
        "article 21": 0.55,
        "equality": 0.42,
        "freedom of speech": 0.55,
        "personal liberty": 0.5,
        "fundamental right": 0.5,
        "constitutional right": 0.45,
        "discrimination by government": 0.5,
        "government discriminated": 0.45,
        "discriminated": 0.36,
        "state action": 0.38,
        "treated me unfairly": 0.32,
        "government authority treated": 0.32,
    },
    "legal_aid": {
        "free legal aid": 0.55,
        "free lawyer": 0.5,
        "legal services authority": 0.5,
        "legal aid eligibility": 0.55,
        "nalsa": 0.5,
        "dlsa": 0.48,
        "slsa": 0.48,
        "legal aid": 0.42,
    },
    "human_rights": {
        "human rights complaint": 0.55,
        "human rights": 0.48,
        "nhrc": 0.5,
        "state human rights commission": 0.5,
        "custodial abuse": 0.55,
        "rights violation by public authority": 0.5,
        "public authority treated me unfairly": 0.32,
        "government authority treated me unfairly": 0.3,
    },
    "contempt": {
        "contempt of court": 0.55,
        "disobeyed court order": 0.55,
        "court order was deliberately disobeyed": 0.55,
        "scandalising court": 0.48,
        "scandalizing court": 0.48,
        "court contempt": 0.55,
    },
}
PUBLIC_AUTHORITY_INTENT_THRESHOLD = 0.25
PUBLIC_AUTHORITY_INTENT_CLOSE_DELTA = 0.14
PUBLIC_AUTHORITY_INTENT_PRIMARY_BOOST = 0.13
PUBLIC_AUTHORITY_INTENT_SECONDARY_BOOST = 0.06
PUBLIC_AUTHORITY_INTENT_EXPANSIONS = {
    "rti": "right to information public information officer information request records appeal under RTI",
    "fundamental_rights": "constitution fundamental rights article equality freedom speech personal liberty state action",
    "legal_aid": "legal services authority free legal aid free lawyer eligibility NALSA DLSA SLSA",
    "human_rights": "human rights commission NHRC public authority rights violation complaint custodial abuse",
    "contempt": "contempt of court disobeyed court order scandalising court",
}
CREDENTIAL_MISUSE_CUES = (
    "identity theft",
    "password",
    "login details",
    "credentials",
    "account credentials",
    "personal details",
    "logged in as me",
    "pretended to be me",
    "access my online account",
    "access account without permission",
    "used my account",
)
PRODUCT_LIABILITY_CUES = (
    "product liability",
    "injury",
    "injured",
    "harm",
    "physical harm",
    "damage caused",
    "exploded",
    "fire",
    "unsafe product",
    "defective product caused",
)
NO_PRODUCT_LIABILITY_CUES = (
    "no one was injured",
    "no one injured",
    "no injury",
    "not injured",
    "no physical harm",
    "no harm",
    "no property damage",
    "only seeking refund",
    "only want refund",
    "only seeking replacement",
    "only want replacement",
    "simply defective",
    "just defective",
    "stopped working",
    "not working",
)
ORDINARY_CONSUMER_REMEDY_CUES = (
    "refund",
    "replacement",
    "replace",
    "repair",
    "not delivered",
    "never delivered",
    "non-delivery",
    "seller not responding",
    "refusing refund",
    "defective",
    "faulty",
)
MULTI_DOMAIN_TRANSACTION_CUES = (
    "blocked after payment",
    "took payment and blocked",
    "disappeared after payment",
    "online seller took payment",
    "social media seller",
    "instagram seller",
    "fake seller",
    "never delivered",
)
RTI_NO_RESPONSE_CUES = (
    "no reply",
    "no response",
    "did not receive any reply",
    "did not receive a reply",
    "did not receive any response",
    "pio did not reply",
    "pio did not respond",
    "rti unanswered",
    "information not received",
)
FUNDAMENTAL_RIGHTS_SPECIFIC_EXPANSIONS = (
    (("article 14", "equality"), "article 14 equality before law equal protection laws"),
    (("article 19", "freedom of speech", "speech restriction"), "article 19 freedom of speech expression"),
    (("article 21", "right to life", "personal liberty"), "article 21 protection of life personal liberty"),
)

MIN_RELEVANCE_SCORE = 0.30
LOW_CONFIDENCE_RELEVANCE_SCORE = 0.22
RELEVANCE_WINDOW = 0.14
MAX_CONTEXT_CHUNKS = 4
# See the per-document diversity cap comment in select_relevant_chunks() for why this exists and
# how 2 was chosen.
DOCUMENT_DIVERSITY_CAP = 2
MAX_SOURCE_CARDS = 4


def validate_question(question: str) -> str:
    cleaned = (question or "").strip()
    if not cleaned:
        raise ValueError("Question is required.")
    if len(cleaned) > MAX_QUESTION_CHARS:
        raise ValueError(f"Question is too long. Please keep it under {MAX_QUESTION_CHARS} characters.")
    return cleaned


def is_consumer_law_question(question: str) -> bool:
    words = set(re.findall(r"[a-zA-Z][a-zA-Z-]+", question.lower()))
    if words & CONSUMER_KEYWORDS:
        return True
    return not bool(words & OFF_TOPIC_KEYWORDS) and "consumer" in question.lower()


def retrieval_query(question: str) -> str:
    lowered = question.lower()
    signals = detect_domain_signals(question)
    consumer_score = signals["scores"]["consumer"]
    cyber_score = signals["scores"]["cyber"]
    product_problem_terms = {
        "defective", "defect", "damaged", "broken", "faulty", "stopped working",
        "refund", "replacement", "replace", "repair", "warranty", "seller",
        "goods", "product",
    }
    if consumer_score >= DOMAIN_SIGNAL_THRESHOLD and cyber_score >= DOMAIN_SIGNAL_THRESHOLD:
        return (
            f"{question} consumer complaint refund non-delivery seller online marketplace "
            "consumer remedy return price replacement cyber fraud online scam report cybercrime "
            "payment blocked account deceptive seller"
        )
    if is_product_liability_query(question):
        return (
            f"{question} defective product injury harm product liability manufacturer seller "
            "consumer complaint compensation redressal"
        )
    if consumer_score >= DOMAIN_SIGNAL_THRESHOLD and consumer_score >= cyber_score and any(term in lowered for term in product_problem_terms):
        return (
            f"{question} defective product goods seller refund repair replacement warranty "
            "consumer complaint remedy redressal return price replace goods"
        )
    if is_credential_misuse_query(question):
        return f"{question} identity theft password credentials electronic signature Section 66C account access"
    intents = detect_public_authority_intents(question)
    has_public_authority_intent = bool(intents["primary_intents"] or intents["secondary_intents"])
    if "constitutional_public_authority" in signals["primary_domains"] or (not signals["primary_domains"] and has_public_authority_intent):
        expansions = public_authority_intent_expansions(question, intents)
        if expansions:
            return f"{question} {' '.join(expansions)}"
    return question


def is_credential_misuse_query(question: str) -> bool:
    lowered = question.lower()
    if not contains_any(lowered, CREDENTIAL_MISUSE_CUES):
        return False
    return contains_any(lowered, ("account", "online", "login", "password", "credentials", "personal details", "identity", "pretended"))


def is_product_liability_query(question: str) -> bool:
    lowered = question.lower()
    if contains_any(lowered, NO_PRODUCT_LIABILITY_CUES) and not contains_any(
        lowered,
        ("caused injury", "caused harm", "caused damage", "property was damaged", "injured me", "hurt me"),
    ):
        return False
    return contains_any(lowered, PRODUCT_LIABILITY_CUES)


def is_ordinary_consumer_remedy_query(question: str) -> bool:
    lowered = question.lower()
    return contains_any(lowered, ORDINARY_CONSUMER_REMEDY_CUES) and not is_product_liability_query(question)


def should_suppress_product_liability_for_query(question: str) -> bool:
    lowered = question.lower()
    return (
        contains_any(lowered, NO_PRODUCT_LIABILITY_CUES)
        or is_ordinary_consumer_remedy_query(question)
        or contains_any(lowered, ("never delivered", "not delivered", "non-delivery", "no delivery"))
        or is_online_seller_blocked_payment_query(question)
    ) and not is_product_liability_query(question)


def is_product_liability_chunk(chunk: RetrievedChunk) -> bool:
    title = f"{chunk.section_title or ''} {chunk.rule_title or ''}".lower()
    section = str(chunk.section_number or "").strip()
    if chunk.domain == "consumer" and section in {"82", "83", "84", "85", "86", "87"}:
        return True
    return "product liability" in title or "liability of product" in title


def is_rti_no_response_query(question: str) -> bool:
    lowered = question.lower()
    return ("rti" in lowered or "right to information" in lowered) and contains_any(lowered, RTI_NO_RESPONSE_CUES)


def is_online_seller_blocked_payment_query(question: str) -> bool:
    lowered = question.lower()
    return (
        contains_any(lowered, MULTI_DOMAIN_TRANSACTION_CUES)
        or ("seller" in lowered and "blocked" in lowered and "payment" in lowered)
        or ("seller" in lowered and "blocked" in lowered and "paid" in lowered)
    )


def detect_domain_signals(query: str) -> dict[str, Any]:
    lowered = re.sub(r"\s+", " ", query.lower()).strip()
    scores = {domain: 0.0 for domain in DOMAIN_SIGNAL_CUES}
    for domain, cues in DOMAIN_SIGNAL_CUES.items():
        for cue, weight in cues.items():
            if contains_query_cue(lowered, cue):
                scores[domain] += weight

    words = set(re.findall(r"[a-zA-Z][a-zA-Z-]+", lowered))
    if words <= GENERIC_DOMAIN_TERMS:
        scores = {domain: min(score, 0.12) for domain, score in scores.items()}

    capped_scores = {domain: min(score, 1.0) for domain, score in scores.items()}
    max_score = max(capped_scores.values()) if capped_scores else 0.0
    primary_domains = [
        domain
        for domain, score in capped_scores.items()
        if score >= DOMAIN_SIGNAL_THRESHOLD and max_score - score <= DOMAIN_SIGNAL_CLOSE_DELTA
    ]
    secondary_domains = [
        domain
        for domain, score in capped_scores.items()
        if score >= DOMAIN_SIGNAL_THRESHOLD and domain not in primary_domains
    ]
    return {
        "scores": capped_scores,
        "primary_domains": primary_domains,
        "secondary_domains": secondary_domains,
    }


def production_candidate_k(question: str, top_k: int = TOP_K) -> int:
    """The candidate_k LegalRAG.retrieve() actually uses in production. Factored out (2026-09-14)
    so evaluate_retrieval.py can call this directly instead of keeping its own hardcoded
    RAW_CANDIDATE_K constant that silently drifts out of sync with this logic -- which is exactly
    what happened before this refactor: that script's own candidate window was narrower than
    production's, so its metrics couldn't reflect fixes made to this function (see
    eval/retrieval_evaluation.md's history for that finding)."""
    signals = detect_domain_signals(question)
    domain_count = len(signals["primary_domains"] + signals["secondary_domains"])
    if domain_count > 1:
        # Multi-domain/ambiguous: keep the window tight-ish to limit cross-domain noise reaching
        # the reranker.
        return max(top_k * 8, 40)
    if domain_count == 1:
        single_domain = (signals["primary_domains"] + signals["secondary_domains"])[0]
        if single_domain == "cyber":
            # Cyber-specific, added 2026-09-14 (step 3 of the cyber-manual escalation -- see
            # PROCEDURAL_GUIDE_SUBSTANTIVE_PENALTY above for steps 1-2): the general single-domain
            # candidate_k=40 below still wasn't enough for cyber. Its low/medium-priority
            # procedural manuals (cybercrime_portal_citizen_manual_latest.pdf and siblings)
            # dominate raw semantic similarity so strongly for plain-language substantive queries
            # that IT Act s.66C's raw-FAISS candidate rank was 41, 44, and 61 (out of the full
            # corpus) across three tested substantive phrasings -- all outside candidate_k=40,
            # meaning the statute was never fetched as a candidate at all, so no amount of
            # down-weighting in authority_level_boost()/relevance_gate_score() could surface it.
            # 100 covers the worst case found (61) with ~40 of margin, not just barely. If a
            # future query needs more, re-check raw-FAISS rank empirically rather than guessing --
            # see eval/retrieval_evaluation.md for the methodology.
            return max(top_k * 20, 100)
        # Single, unambiguous domain (non-cyber): widen the window. There's less cross-domain
        # noise risk here, so it's safe to look deeper. Found via manual_02_delhi_electricity: a
        # correct provision (Delhi Rent Control Act, 1958 s.45, essential-supply cutoff) was
        # ranking ~30th in raw FAISS similarity for a plainly-phrased "landlord disconnected
        # electricity" query -- outside the old candidate_k=12 window -- so it never reached
        # select_relevant_chunks' query_intent_boost, which does correctly boost this query's
        # intent once a chunk is in the pool. See eval/manual_regression_evaluation.md.
        return max(top_k * 6, 40)
    # No clear domain signal at all: not the same as a confidently single-domain query, so don't
    # widen -- keep the original tight default.
    return max(top_k * 2, 12)


def detect_public_authority_intents(query: str) -> dict[str, Any]:
    lowered = re.sub(r"\s+", " ", query.lower()).strip()
    scores = {intent: 0.0 for intent in PUBLIC_AUTHORITY_INTENT_CUES}
    for intent, cues in PUBLIC_AUTHORITY_INTENT_CUES.items():
        for cue, weight in cues.items():
            if contains_query_cue(lowered, cue):
                scores[intent] += weight
    capped_scores = {intent: min(score, 1.0) for intent, score in scores.items()}
    max_score = max(capped_scores.values()) if capped_scores else 0.0
    primary_intents = [
        intent
        for intent, score in capped_scores.items()
        if score >= PUBLIC_AUTHORITY_INTENT_THRESHOLD and max_score - score <= PUBLIC_AUTHORITY_INTENT_CLOSE_DELTA
    ]
    secondary_intents = [
        intent
        for intent, score in capped_scores.items()
        if score >= PUBLIC_AUTHORITY_INTENT_THRESHOLD and intent not in primary_intents
    ]
    return {
        "scores": capped_scores,
        "primary_intents": primary_intents,
        "secondary_intents": secondary_intents,
    }


def contains_query_cue(normalized_query: str, cue: str) -> bool:
    normalized_cue = re.sub(r"\s+", " ", cue.lower()).strip()
    if not normalized_cue:
        return False
    prefix = r"(?<![a-z0-9])" if normalized_cue[0].isalnum() else ""
    suffix = r"(?![a-z0-9])" if normalized_cue[-1].isalnum() else ""
    return bool(re.search(f"{prefix}{re.escape(normalized_cue)}{suffix}", normalized_query))


def contains_any(text: str, cues: tuple[str, ...]) -> bool:
    normalized_text = re.sub(r"\s+", " ", text.lower()).strip()
    return any(contains_query_cue(normalized_text, cue) for cue in cues)


def public_authority_intent_expansions(question: str, intents: dict[str, Any]) -> list[str]:
    query = re.sub(r"\s+", " ", question.lower()).strip()
    expansions: list[str] = []
    for intent in intents["primary_intents"] + intents["secondary_intents"]:
        if intent == "fundamental_rights":
            specific = [
                expansion
                for cues, expansion in FUNDAMENTAL_RIGHTS_SPECIFIC_EXPANSIONS
                if any(contains_query_cue(query, cue) for cue in cues)
            ]
            expansions.extend(specific or [PUBLIC_AUTHORITY_INTENT_EXPANSIONS[intent]])
        elif intent in PUBLIC_AUTHORITY_INTENT_EXPANSIONS:
            expansions.append(PUBLIC_AUTHORITY_INTENT_EXPANSIONS[intent])
    return expansions


@lru_cache(maxsize=2)
def get_sentence_transformer(model_name: str = EMBEDDING_MODEL) -> SentenceTransformer:
    logger.info("Loading SentenceTransformer embedding model: %s", model_name)
    return SentenceTransformer(model_name)


def sentence_transformer_embed_texts(texts: list[str], model_name: str = EMBEDDING_MODEL) -> np.ndarray:
    model = get_sentence_transformer(model_name)
    vectors = model.encode(
        texts,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype="float32")


def embed_texts(texts: list[str], provider: str | None = None) -> np.ndarray:
    selected = (provider or EMBEDDING_PROVIDER).lower()
    if selected in {"local", "sentence-transformers", "sentence_transformers"}:
        return sentence_transformer_embed_texts(texts)
    raise ConfigurationError(f"Unsupported embedding provider: {selected}")


def _load_metadata() -> dict[str, Any]:
    if not INDEX_PATH.exists() or not METADATA_PATH.exists():
        raise VectorStoreMissingError("Vector store is missing. Run `python ingest.py` inside backend first.")
    with METADATA_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


class LegalRAG:
    def __init__(self) -> None:
        self.index: faiss.Index | None = None
        self.metadata: dict[str, Any] | None = None
        self.chunks: list[dict[str, Any]] = []

    def load(self) -> None:
        metadata = _load_metadata()
        self.index = faiss.read_index(str(INDEX_PATH))
        self.metadata = metadata
        self.chunks = metadata.get("chunks", [])
        provider = metadata.get("embedding_provider")
        model = metadata.get("embedding_model")
        expected_provider = EMBEDDING_PROVIDER
        expected_model = EMBEDDING_MODEL
        if provider != expected_provider or model != expected_model:
            self.index = None
            self.metadata = None
            self.chunks = []
            raise VectorStoreIncompatibleError(
                "Vector store was built with a different embedding provider/model. "
                "Delete backend/vectorstore or rerun `python ingest.py` to rebuild it."
            )
        logger.info("Vector store loaded with %s chunks", len(self.chunks))

    @property
    def loaded(self) -> bool:
        return self.index is not None and bool(self.chunks)

    def retrieve_candidates(self, question: str, candidate_k: int | None = None) -> list[RetrievedChunk]:
        if not self.loaded or self.index is None or self.metadata is None:
            self.load()
        provider = self.metadata.get("embedding_provider", EMBEDDING_PROVIDER)
        query_vector = embed_texts([retrieval_query(question)], provider=provider)
        candidate_k = min(len(self.chunks), candidate_k or max(TOP_K * 2, 12))
        scores, indexes = self.index.search(query_vector, candidate_k)
        candidates: list[RetrievedChunk] = []
        for score, idx in zip(scores[0], indexes[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            item = self.chunks[idx]
            candidates.append(
                RetrievedChunk(
                    text=item["text"],
                    source=item["source"],
                    document_title=item.get("document_title") or item["source"],
                    page=int(item["page"]),
                    score=float(score),
                    chunk_id=item.get("chunk_id"),
                    domain=item.get("domain"),
                    retrieval_priority=item.get("retrieval_priority"),
                    authority_level=item.get("authority_level"),
                    status=item.get("status"),
                    document_type=item.get("document_type"),
                    chapter=item.get("chapter"),
                    section_number=item.get("section_number"),
                    section_title=item.get("section_title"),
                    rule_number=item.get("rule_number"),
                    rule_title=item.get("rule_title"),
                    article_number=item.get("article_number"),
                    article_title=item.get("article_title"),
                    regulation_number=item.get("regulation_number"),
                    regulation_title=item.get("regulation_title"),
                    guideline_number=item.get("guideline_number"),
                    guideline_title=item.get("guideline_title"),
                    page_start=item.get("page_start"),
                    page_end=item.get("page_end"),
                    paragraph_number=item.get("paragraph_number"),
                    case_name=item.get("case_name"),
                    citation=item.get("citation"),
                    court=item.get("court"),
                    good_law=item.get("good_law"),
                )
            )
        return candidates

    def retrieve(self, question: str, top_k: int = TOP_K) -> list[RetrievedChunk]:
        candidate_k = production_candidate_k(question, top_k)
        candidates = self.retrieve_candidates(question, candidate_k=candidate_k)
        results = select_relevant_chunks(candidates, question=question, top_k=top_k)
        logger.info(
            "Retrieved %s strong chunks from %s candidates for query=%r. Final sources=%s",
            len(results),
            len(candidates),
            question[:160],
            [
                {
                    "document": chunk.document_title,
                    "page": chunk.page,
                    "section": source_section_label(chunk),
                    "faiss": round(chunk.score, 4),
                    "rerank": round(chunk.rerank_score, 4),
                }
                for chunk in results
            ],
        )
        return results

    def answer(self, question: str, skip_scope_check: bool = False) -> dict[str, Any]:
        question = validate_question(question)
        if not skip_scope_check and not is_consumer_law_question(question):
            return insufficient_response(
                "This version of Legal Aid AI currently supports consumer-law questions only."
            )

        chunks = self.retrieve(question)
        if not chunks:
            return insufficient_response(
                "I don’t have enough information in the available legal sources to answer this reliably."
            )

        if LLM_PROVIDER == "local":
            return local_grounded_response(question, chunks)

        if LLM_PROVIDER == "gemini":
            if not GEMINI_API_KEY:
                raise ConfigurationError("GEMINI_API_KEY is missing. Add it to backend/.env or set LLM_PROVIDER=local for development tests.")
            try:
                answer = grounded_answer.generate_grounded_answer(
                    original_message=question,
                    normalized_case_summary=question,
                    domains=sorted({chunk.domain for chunk in chunks if chunk.domain}),
                    chunks=chunks,
                )
                return claim_verifier.verify_and_sanitize_response(answer, chunks)
            except grounded_answer.GroundedAnswerConfigurationError as exc:
                raise ConfigurationError(str(exc)) from exc
            except grounded_answer.GroundedAnswerError as exc:
                raise LLMError(str(exc)) from exc

        raise ConfigurationError(f"Unsupported LLM provider: {LLM_PROVIDER}")


def insufficient_response(message: str) -> dict[str, Any]:
    return {
        "answer": {
            "issue_summary": message,
            "possible_rights": [],
            "next_steps": [
                "Try providing more details if your question relates to an Indian consumer issue.",
                "For complex or urgent issues, consult a qualified legal professional.",
            ],
        },
        "sources": [],
        "confidence": "low",
        "insufficient_context": True,
        "disclaimer": DISCLAIMER,
    }


def short_excerpt(text: str, max_chars: int = 320) -> str:
    compact = re.sub(r"\s+", " ", text).strip()
    lowered = compact.lower()
    anchors = [
        "replace the goods", "defect", "defective", "product liability", "liable",
        "refund", "replacement", "repair", "redressal", "consumer", "complaint",
        "express warranty",
    ]
    positions = [lowered.find(anchor) for anchor in anchors if lowered.find(anchor) >= 0]
    if positions:
        start = max(0, min(positions) - 80)
        if start > 0:
            sentence_start = max(compact.rfind(". ", 0, start), compact.rfind("; ", 0, start))
            start = sentence_start + 2 if sentence_start >= 0 else start
        excerpt = compact[start : start + max_chars].strip()
        if len(excerpt) >= max_chars:
            excerpt = excerpt[: max_chars - 1].rsplit(" ", 1)[0] + "..."
        return excerpt
    if len(compact) <= max_chars:
        return compact
    return compact[: max_chars - 1].rsplit(" ", 1)[0] + "..."


def normalized_fingerprint(text: str) -> set[str]:
    words = re.findall(r"[a-zA-Z][a-zA-Z-]{3,}", text.lower())
    return set(words)


def source_section_label(chunk: RetrievedChunk) -> str | None:
    if chunk.rule_number:
        title = f" — {chunk.rule_title}" if chunk.rule_title else ""
        return f"Rule {chunk.rule_number}{title}"
    if chunk.section_number:
        title = f" — {chunk.section_title}" if chunk.section_title else ""
        return f"Section {chunk.section_number}{title}"
    return identify_section(chunk.text)


def chunk_section_key(chunk: RetrievedChunk) -> tuple[str, str | None, str | None, int]:
    return (
        chunk.document_title,
        chunk.section_number or chunk.rule_number,
        chunk.section_title or chunk.rule_title,
        chunk.page,
    )


def is_near_duplicate(chunk: RetrievedChunk, selected: list[RetrievedChunk]) -> bool:
    candidate_words = normalized_fingerprint(chunk.text[:900])
    if not candidate_words:
        return False
    for existing in selected:
        if chunk_section_key(chunk) == chunk_section_key(existing):
            return True
        if (
            "rules" in chunk.document_title.lower()
            and "consumer protection act" in existing.document_title.lower()
            and (chunk.rule_number or chunk.section_number)
            and (chunk.rule_number or chunk.section_number) == (existing.section_number or existing.rule_number)
        ):
            return True
        if (
            chunk.document_title == existing.document_title
            and (chunk.section_number or chunk.rule_number)
            and (chunk.section_number or chunk.rule_number) == (existing.section_number or existing.rule_number)
        ):
            return True
        existing_words = normalized_fingerprint(existing.text[:900])
        overlap = len(candidate_words & existing_words)
        union = len(candidate_words | existing_words) or 1
        if overlap / union > 0.72:
            return True
    return False


def query_terms(question: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-zA-Z][a-zA-Z-]{2,}", retrieval_query(question).lower())
        if word not in {"the", "and", "for", "with", "that", "this", "from", "into"}
    }


def lexical_overlap_score(question: str, chunk: RetrievedChunk) -> float:
    terms = query_terms(question)
    if not terms:
        return 0.0
    text_words = normalized_fingerprint(f"{chunk.text} {chunk.section_title or ''} {chunk.rule_title or ''}")
    overlap = len(terms & text_words)
    return min(0.12, (overlap / len(terms)) * 0.18)


def legal_substance_boost(chunk: RetrievedChunk) -> float:
    text = f"{chunk.text} {chunk.section_title or ''} {chunk.rule_title or ''}"
    lowered = text.lower()
    keyword_boost = sum(0.018 for keyword in SUBSTANTIVE_LEGAL_KEYWORDS if keyword in lowered)
    penalty = sum(0.018 for keyword in ADMINISTRATIVE_KEYWORDS if keyword in lowered)
    doc_preference = 0.0
    if "consumer protection act" in chunk.document_title.lower():
        doc_preference += 0.08
    if "rules" in chunk.document_title.lower():
        penalty += 0.09
        if not (chunk.rule_number or chunk.section_number):
            penalty += 0.05
    title = f"{chunk.section_title or ''} {chunk.rule_title or ''}".lower()
    title_boost = 0.0
    if any(keyword in title for keyword in ("defect", "liability", "seller", "manufacturer", "findings", "redressal")):
        title_boost += 0.06
    return min(keyword_boost, 0.10) + doc_preference + title_boost - min(penalty, 0.14)


def query_intent_boost(question: str, chunk: RetrievedChunk) -> float:
    query = question.lower()
    text = chunk.text.lower()
    title = f"{chunk.section_title or ''} {chunk.rule_title or ''}".lower()
    boost = 0.0

    if any(term in query for term in ("refund", "return", "money back")):
        if any(term in text for term in ("return to the complainant the price", "return the price", "charges paid")):
            boost += 0.12
        if "findings of district commission" in title:
            boost += 0.10

    if any(term in query for term in ("replace", "replacement")):
        if "replace the goods" in text or "free from any defect" in text:
            boost += 0.14

    if "seller" in query and not is_ordinary_consumer_remedy_query(question):
        if "liability of product sellers" in title or "product seller" in text:
            boost += 0.12

    if any(term in query for term in ("defect", "defective", "damaged", "stopped working", "faulty", "broken")):
        if "defect" in text or "defective" in text:
            boost += 0.06
        if "definitions" in title and "defect" in text:
            boost += 0.09
        if "product liability" in text and is_product_liability_query(question):
            boost += 0.06
        if "exceptions to product liability" in title and not any(term in query for term in ("exception", "defence", "defense")):
            boost -= 0.20

    if is_ordinary_consumer_remedy_query(question):
        if "findings of district commission" in title:
            boost += 0.12
        if any(term in text for term in ("return to the complainant the price", "replace the goods", "remove the defect")):
            boost += 0.10
        if "product liability action" in title or "liability of product" in title:
            boost -= 0.18

    if should_suppress_product_liability_for_query(question) and is_product_liability_chunk(chunk):
        boost -= 0.26

    if is_credential_misuse_query(question):
        if "66c" in title or "identity theft" in title:
            boost += 0.20
        elif "identity theft" in text or "password" in text:
            boost += 0.12

    if is_rti_no_response_query(question) and chunk.domain == "constitutional_public_authority":
        if str(chunk.section_number or "").strip() == "19" or "appeal" in title:
            boost += 0.14
        elif str(chunk.section_number or "").strip() == "18" or "information commissions" in title:
            boost -= 0.04
        elif str(chunk.section_number or "").strip() == "20" or "penalties" in title:
            boost -= 0.08

    if is_online_seller_blocked_payment_query(question) and chunk.domain == "cyber":
        if chunk.document_type == "procedural_user_guide" or "cybercrime reporting portal" in chunk.document_title.lower():
            boost += 0.10
        elif chunk.status == "supporting_only":
            boost -= 0.06

    if chunk.domain == "tenancy" and contains_any(query, ("electricity", "bijli", "essential supply", "water supply")):
        if "essential supply" in title or "cutting off or withholding essential supply" in title:
            boost += 0.18
        elif "eviction" in title or "standard rent" in title:
            boost -= 0.05

    if any(term in query for term in ("mean", "meaning", "define", "definition")):
        if "definitions" in title or "(10)" in text and "defect" in text:
            boost += 0.16

    return max(-0.32, min(boost, 0.28))


def domain_signal_boost(question: str, chunk: RetrievedChunk) -> float:
    signals = detect_domain_signals(question)
    domain = chunk.domain
    if not domain:
        return 0.0
    if domain in signals["primary_domains"]:
        return DOMAIN_PRIMARY_BOOST * signals["scores"].get(domain, 0.0)
    if domain in signals["secondary_domains"]:
        return DOMAIN_SECONDARY_BOOST * signals["scores"].get(domain, 0.0)
    if signals["primary_domains"]:
        return -DOMAIN_MISMATCH_PENALTY * max(signals["scores"].values())
    return 0.0


def domain_debug_info(question: str, chunk: RetrievedChunk | None = None) -> dict[str, Any]:
    signals = detect_domain_signals(question)
    debug = {
        "scores": signals["scores"],
        "primary_domains": signals["primary_domains"],
        "secondary_domains": signals["secondary_domains"],
    }
    if chunk is not None:
        debug["chunk_domain"] = chunk.domain
        debug["domain_boost"] = round(domain_signal_boost(question, chunk), 4)
        debug["priority_boost"] = round(retrieval_priority_boost(chunk), 4)
        debug["authority_boost"] = round(authority_level_boost(question, chunk), 4)
        debug["supporting_status_boost"] = round(supporting_status_boost(question, chunk), 4)
        debug["source_role_boost"] = round(source_role_boost(question, chunk), 4)
    return debug


def retrieval_priority_boost(chunk: RetrievedChunk) -> float:
    priority = (chunk.retrieval_priority or "").lower()
    return RETRIEVAL_PRIORITY_WEIGHTS.get(priority, 0.0)


def authority_level_boost(question: str, chunk: RetrievedChunk) -> float:
    authority = (chunk.authority_level or "").lower()
    boost = AUTHORITY_LEVEL_WEIGHTS.get(authority, 0.0)
    is_procedural_manual = authority == "procedural_guide" and chunk.document_type == "procedural_user_guide"
    if is_procedural_manual and is_procedural_query(question):
        boost += PROCEDURAL_QUERY_MANUAL_BOOST
    elif is_procedural_manual and (chunk.retrieval_priority or "").lower() in ("low", "medium"):
        # Strengthened down-weighting, added 2026-09-14, extended 2026-09-14: procedural manuals
        # (authority_level=procedural_guide + document_type=procedural_user_guide) with
        # retrieval_priority=low OR medium (currently cybercrime_portal_citizen_manual_latest.pdf,
        # national_cybercrime_reporting_portal_user_manual_2019.pdf,
        # sanchar_saathi_ceir_user_manual.pdf [low], and npci_upi_procedural_guidelines.pdf
        # [medium] -- see corpus_manifest.json for the current set; any future document tagged the
        # same way inherits this automatically) have plain, citizen-facing language with raw
        # semantic similarity strong enough to crowd statutory sources (e.g. IT Act, DPDP Act) out
        # of the top 5 on substantive legal questions, despite the baseline
        # AUTHORITY_LEVEL_WEIGHTS/RETRIEVAL_PRIORITY_WEIGHTS penalties above (see the KNOWN
        # LIMITATION comment near those weights -- this replaces the "accept as-is" decision
        # recorded there). Originally scoped to retrieval_priority=low only; widened to include
        # medium the same day after confirming npci_upi_procedural_guidelines.pdf (medium
        # priority) shares the identical procedural_guide/procedural_user_guide shape and the same
        # crowding risk for substantive UPI/payment-fraud queries. This additional penalty applies
        # only when is_procedural_query(question) is False, reusing that same
        # procedural-vs-substantive signal the boost above already uses, so genuinely procedural
        # queries ("how do I report this", "where do I file a complaint") are untouched and these
        # manuals still rank well for them. Magnitude (0.20) was tuned empirically against
        # eval/retrieval_evaluation.md's cyber queries: it's enough to surface statutory content
        # into the top 5 on substantive phrasings without fully suppressing the manual (it still
        # co-occurs in the top 5 for most substantive queries, per the "alongside or ahead of, not
        # crowded out" goal) or affecting procedural-intent queries at all. Note: this alone isn't
        # sufficient for every substantive query -- see the cyber-specific candidate_k branch in
        # LegalRAG.retrieve() below for the companion candidate-pool-depth fix this required (a
        # down-weighted chunk still has to be fetched as a candidate before this can act on it).
        boost -= PROCEDURAL_GUIDE_SUBSTANTIVE_PENALTY
    boost -= case_law_substantive_penalty(question, chunk)
    return boost


def is_procedural_query(question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in PROCEDURAL_QUERY_TERMS)


def is_case_law_query(question: str) -> bool:
    lowered = question.lower()
    return any(term in lowered for term in CASE_LAW_QUERY_TERMS)


def case_law_substantive_penalty(question: str, chunk: RetrievedChunk) -> float:
    """Down-weight a judgment on a question that is not asking about case law.

    Someone asking what an intermediary must do needs the rule that imposes the duty; a judgment
    applying that rule is useful context but should not displace it. When the question is itself
    about case law ("what did the Supreme Court hold in..."), no penalty applies and judgments
    rank on their merits."""
    if (chunk.document_type or "").lower() != "case_law":
        return 0.0
    if is_case_law_query(question):
        return 0.0
    return CASE_LAW_SUBSTANTIVE_PENALTY


def supporting_status_boost(question: str, chunk: RetrievedChunk) -> float:
    status = (chunk.status or "").lower()
    document_type = (chunk.document_type or "").lower()
    if status == "supporting_only" or document_type.startswith("supporting_"):
        return -SUPPORTING_ONLY_PENALTY
    if status == "reference_only":
        if is_procedural_query(question) and document_type == "procedural_user_guide":
            return 0.0
        return -REFERENCE_ONLY_PENALTY
    return 0.0


def source_role_boost(question: str, chunk: RetrievedChunk) -> float:
    return (
        retrieval_priority_boost(chunk)
        + authority_level_boost(question, chunk)
        + supporting_status_boost(question, chunk)
    )


def public_authority_intent_for_chunk(chunk: RetrievedChunk) -> str | None:
    source = (chunk.source or "").lower()
    title = (chunk.document_title or "").lower()
    haystack = f"{source} {title}"
    if "right_to_information_act" in source or "right to information act" in title:
        return "rti"
    if "constitution_of_india" in source or "constitution of india" in title:
        return "fundamental_rights"
    if "legal_services_authorities_act" in source or "legal services authorities act" in title:
        return "legal_aid"
    if "protection_of_human_rights_act" in source or "protection of human rights act" in title:
        return "human_rights"
    if "contempt_of_courts_act" in source or "contempt of courts act" in title:
        return "contempt"
    if "human rights" in haystack:
        return "human_rights"
    return None


def public_authority_intent_boost(question: str, chunk: RetrievedChunk) -> float:
    signals = detect_domain_signals(question)
    plausible_public_authority = (
        "constitutional_public_authority" in signals["primary_domains"]
        or "constitutional_public_authority" in signals["secondary_domains"]
        or chunk.domain == "constitutional_public_authority"
    )
    if not plausible_public_authority or chunk.domain != "constitutional_public_authority":
        return 0.0
    chunk_intent = public_authority_intent_for_chunk(chunk)
    if not chunk_intent:
        return 0.0
    intents = detect_public_authority_intents(question)
    if chunk_intent in intents["primary_intents"]:
        return PUBLIC_AUTHORITY_INTENT_PRIMARY_BOOST * intents["scores"].get(chunk_intent, 0.0)
    if chunk_intent in intents["secondary_intents"]:
        return PUBLIC_AUTHORITY_INTENT_SECONDARY_BOOST * intents["scores"].get(chunk_intent, 0.0)
    return 0.0


def retrieval_debug_info(question: str, chunk: RetrievedChunk | None = None) -> dict[str, Any]:
    debug = domain_debug_info(question, chunk)
    debug["public_authority_intents"] = detect_public_authority_intents(question)
    if chunk is not None:
        debug["public_authority_chunk_intent"] = public_authority_intent_for_chunk(chunk)
        debug["public_authority_intent_boost"] = round(public_authority_intent_boost(question, chunk), 4)
        debug["credential_misuse_boost"] = round(query_intent_boost(question, chunk), 4)
        debug["final_rerank_score"] = round(final_rerank_score(question, chunk), 4)
    return debug


TITLE_SUBJECT_MATCH_BOOST = 0.25
TITLE_SUBJECT_RE = re.compile(r"\(([^)]{3,60})\)")


def title_subject_match_boost(question: str, chunk: RetrievedChunk) -> float:
    """Boost the instrument whose title names the specific subject the question is about.

    Indian subordinate legislation distinguishes itself in parentheses -- Consumer Protection
    (Direct Selling) Rules, 2021 against Consumer Protection (E-Commerce) Rules, 2020 -- and
    everything outside the parentheses is shared with the parent Act. Semantic similarity alone
    therefore favours the parent Act, which repeats general language the query also uses, over
    the specific Rules that actually govern. Eval query consumer_06 ("direct selling company
    refusing refund") returned the Consumer Protection Act and E-Commerce Rules while the Direct
    Selling Rules did not make the candidate pool at all, despite the query naming its subject
    outright. Matching on the parenthetical is narrow on purpose: it only fires when the question
    contains the phrase that distinguishes this instrument from its siblings."""
    title = chunk.document_title or ""
    lowered_question = question.lower()
    for subject in TITLE_SUBJECT_RE.findall(title):
        subject = subject.strip().lower()
        # Hyphens and spacing vary between the title and how a person types it
        # ("E-Commerce" vs "e commerce"), so compare on a normalised form.
        normalised_subject = re.sub(r"[^a-z0-9]+", " ", subject).strip()
        normalised_question = re.sub(r"[^a-z0-9]+", " ", lowered_question)
        if len(normalised_subject) >= 4 and normalised_subject in normalised_question:
            return TITLE_SUBJECT_MATCH_BOOST
    return 0.0


def final_rerank_score(question: str, chunk: RetrievedChunk) -> float:
    return (
        chunk.score
        + legal_substance_boost(chunk)
        + lexical_overlap_score(question, chunk)
        + query_intent_boost(question, chunk)
        + domain_signal_boost(question, chunk)
        + source_role_boost(question, chunk)
        + public_authority_intent_boost(question, chunk)
        + title_subject_match_boost(question, chunk)
    )


def relevance_gate_score(question: str, chunk: RetrievedChunk) -> float:
    """Raw-score-derived value used only for select_relevant_chunks' admission threshold, not
    for display/eval/MRR purposes (those keep reading chunk.score directly). A low/medium-
    priority procedural manual can have a raw score so far above every other candidate's that
    max_score - RELEVANCE_WINDOW anchors the window above every statutory chunk, excluding them
    from admission entirely regardless of any rerank_score down-weighting -- rerank only reorders
    candidates that already cleared this gate. Applies the same
    PROCEDURAL_GUIDE_SUBSTANTIVE_PENALTY / is_procedural_query(question) signal used in
    authority_level_boost so the down-weighting is consistent between ranking and admission,
    without building separate classification logic for the two."""
    score = chunk.score
    authority = (chunk.authority_level or "").lower()
    is_procedural_manual = authority == "procedural_guide" and chunk.document_type == "procedural_user_guide"
    if (
        is_procedural_manual
        and (chunk.retrieval_priority or "").lower() in ("low", "medium")
        and not is_procedural_query(question)
    ):
        score -= PROCEDURAL_GUIDE_SUBSTANTIVE_PENALTY
    # Applied at the admission gate as well as in ranking, for the reason in this docstring: a
    # rerank-only penalty cannot rescue a statutory chunk that the raw-score window already
    # excluded from admission.
    score -= case_law_substantive_penalty(question, chunk)
    # Same reasoning in the other direction: the instrument the question actually names has to
    # clear admission before any rerank boost can order it.
    score += title_subject_match_boost(question, chunk)
    return score


def select_relevant_chunks(candidates: list[RetrievedChunk], question: str, top_k: int = TOP_K) -> list[RetrievedChunk]:
    if not candidates:
        return []
    max_score = max(relevance_gate_score(question, chunk) for chunk in candidates)
    threshold = max(MIN_RELEVANCE_SCORE, max_score - RELEVANCE_WINDOW)
    if max_score < MIN_RELEVANCE_SCORE:
        threshold = max(LOW_CONFIDENCE_RELEVANCE_SCORE, max_score - 0.08)
    for chunk in candidates:
        chunk.rerank_score = final_rerank_score(question, chunk)
    ranked = sorted(
        candidates,
        key=lambda chunk: (chunk.rerank_score, chunk.score),
        reverse=True,
    )
    ranked = demote_context_suppressed_product_liability(question, ranked, top_k)
    ranked = balance_multi_domain_candidates(question, ranked)
    target = min(top_k, MAX_CONTEXT_CHUNKS)
    selected: list[RetrievedChunk] = []
    doc_counts: dict[str, int] = {}
    capped_out: list[RetrievedChunk] = []
    for chunk in ranked:
        if relevance_gate_score(question, chunk) < threshold:
            continue
        if is_near_duplicate(chunk, selected):
            continue
        # Per-document diversity cap, added 2026-09-15: a wide candidate pool (see
        # production_candidate_k()'s cyber-specific widening) can let one document with many
        # similar chunks fill every selected slot, pushing out a second, equally relevant
        # document entirely. Found via "someone shared private data online": Digital Personal
        # Data Protection Act, 2023 chunks filled all 4 slots, losing The Information Technology
        # Act, 2000 coverage that a narrower pool had included. DOCUMENT_DIVERSITY_CAP=2 (tuned
        # against that case plus the three queries the wider candidate pool had just fixed --
        # "cyber fraud online payment", "phishing link stole my money", "someone hacked my social
        # media account" -- confirmed it restores the lost document without regressing any of
        # the three) means at most 2 of the selected slots can come from the same source
        # document; the rest of this loop still ranks by rerank_score as before. If the capped
        # pool doesn't fill every slot (too few distinct relevant documents survived the
        # threshold), the fallback below backfills from what the cap skipped, so this never
        # returns fewer chunks than an uncapped selection would have.
        source_key = chunk.source or chunk.document_title
        if doc_counts.get(source_key, 0) >= DOCUMENT_DIVERSITY_CAP:
            capped_out.append(chunk)
            continue
        selected.append(chunk)
        doc_counts[source_key] = doc_counts.get(source_key, 0) + 1
        if len(selected) >= target:
            break
    if len(selected) < target:
        for chunk in capped_out:
            if is_near_duplicate(chunk, selected):
                continue
            selected.append(chunk)
            if len(selected) >= target:
                break
    selected = ensure_multi_domain_selection(question, selected, ranked, threshold, top_k)
    return selected


def demote_context_suppressed_product_liability(
    question: str, ranked: list[RetrievedChunk], top_k: int = TOP_K
) -> list[RetrievedChunk]:
    if not should_suppress_product_liability_for_query(question):
        return ranked
    suppressed = [chunk for chunk in ranked if is_product_liability_chunk(chunk)]
    if not suppressed:
        return ranked
    preferred = [chunk for chunk in ranked if not is_product_liability_chunk(chunk)]
    if len(preferred) >= min(top_k, MAX_CONTEXT_CHUNKS):
        return preferred + suppressed
    return ranked


def ensure_multi_domain_selection(
    question: str,
    selected: list[RetrievedChunk],
    ranked: list[RetrievedChunk],
    threshold: float,
    top_k: int = TOP_K,
) -> list[RetrievedChunk]:
    signals = detect_domain_signals(question)
    desired_domains = signals["primary_domains"] + signals["secondary_domains"]
    if len(desired_domains) < 2:
        return selected
    selected_domains = {chunk.domain for chunk in selected}
    if set(desired_domains).issubset(selected_domains):
        return selected
    max_slots = min(top_k, MAX_CONTEXT_CHUNKS)
    output = list(selected)
    for domain in desired_domains:
        if domain in {chunk.domain for chunk in output}:
            continue
        candidate = next(
            (
                chunk
                for chunk in ranked
                if chunk.domain == domain
                and chunk.score >= threshold
                and not is_near_duplicate(chunk, output)
            ),
            None,
        )
        if not candidate:
            continue
        if len(output) >= max_slots:
            domain_counts = {item.domain: sum(1 for chunk in output if chunk.domain == item.domain) for item in output}
            replaceable_indexes = [
                index
                for index, item in enumerate(output)
                if item.domain not in desired_domains or domain_counts.get(item.domain, 0) > 1
            ]
            if not replaceable_indexes:
                continue
            replace_index = min(replaceable_indexes, key=lambda index: output[index].rerank_score)
            output[replace_index] = candidate
        else:
            output.append(candidate)
    return sorted(output, key=lambda chunk: (chunk.rerank_score, chunk.score), reverse=True)


def balance_multi_domain_candidates(question: str, ranked: list[RetrievedChunk]) -> list[RetrievedChunk]:
    signals = detect_domain_signals(question)
    desired_domains = signals["primary_domains"] + signals["secondary_domains"]
    if len(desired_domains) < 2:
        return ranked
    max_score = max((chunk.rerank_score for chunk in ranked), default=0.0)
    promoted: list[RetrievedChunk] = []
    for domain in desired_domains:
        if any(chunk.domain == domain for chunk in ranked[:MAX_CONTEXT_CHUNKS]):
            continue
        candidate = next(
            (
                chunk
                for chunk in ranked
                if chunk.domain == domain
                and chunk.rerank_score >= max_score - 0.26
                and chunk.score >= LOW_CONFIDENCE_RELEVANCE_SCORE
            ),
            None,
        )
        if candidate:
            promoted.append(candidate)
    if not promoted:
        return ranked
    remaining = [chunk for chunk in ranked if chunk not in promoted]
    insert_at = min(2, len(remaining))
    return remaining[:insert_at] + promoted + remaining[insert_at:]


def identify_section(text: str) -> str | None:
    patterns = [
        r"\b[Ss]ection\s+([0-9]+[A-Za-z]?(?:\([0-9A-Za-z]+\))*)",
        r"\b[Rr]ule\s+([0-9]+[A-Za-z]?(?:\([0-9A-Za-z]+\))*)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text[:600])
        if match:
            label = "Rule" if "rule" in match.group(0).lower() else "Section"
            return f"{label} {match.group(1)}"
    return None


def source_payload(chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
    seen: set[tuple[str, int]] = set()
    sources: list[dict[str, Any]] = []
    for chunk in sorted(chunks, key=lambda item: item.rerank_score or item.score, reverse=True):
        key = (chunk.document_title, chunk.page)
        if key in seen:
            continue
        seen.add(key)
        sources.append(
            {
                "document": chunk.document_title,
                "source_file": chunk.source,
                "page": chunk.page,
                "section": source_section_label(chunk),
                "excerpt": short_excerpt(chunk.text),
                "full_text": source_text.readable_source_text(chunk.text),
                "relevance": round(chunk.score, 4),
                "rerank_score": round(chunk.rerank_score or chunk.score, 4),
            }
        )
        if len(sources) >= MAX_SOURCE_CARDS:
            break
    return sources


def strip_markdown(text: str) -> str:
    text = re.sub(r"\*\*(.*?)\*\*", r"\1", text)
    text = re.sub(r"__(.*?)__", r"\1", text)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"^\s*[-*•]\s+", "", text)
    return text


def clean_structured_text(value: Any) -> str:
    text = str(value or "")
    text = re.sub(r"<svg\\b[^>]*>.*?</svg>", " ", text, flags=re.IGNORECASE | re.DOTALL)
    text = re.sub(r"\bsvg\b", " ", text, flags=re.IGNORECASE)
    text = strip_markdown(text)
    text = re.sub(r"^\s*(?:step\s*)?\d+\s*[\).:-]\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*(?:step\s*)?\d+\s+", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def contains_disclaimer(text: str) -> bool:
    lowered = text.lower()
    return "legal information" in lowered and "professional legal advice" in lowered


def normalize_text_list(values: Any, limit: int) -> list[str]:
    if not isinstance(values, list):
        return []
    seen: set[str] = set()
    cleaned_values: list[str] = []
    for value in values:
        cleaned = clean_structured_text(value)
        cleaned = re.sub(r"\s+when supported by (?:the )?(?:retrieved )?context\.?", ".", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+based on (?:the )?(?:available )?(?:information|context)\.?", ".", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+provided\.$", ".", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned or contains_disclaimer(cleaned):
            continue
        key = re.sub(r"[^a-z0-9]+", "", cleaned.lower())
        if key in seen:
            continue
        seen.add(key)
        cleaned_values.append(cleaned)
        if len(cleaned_values) >= limit:
            break
    return cleaned_values


def normalize_rag_response(parsed: dict[str, Any], chunks: list[RetrievedChunk]) -> dict[str, Any]:
    answer = parsed.get("answer") if isinstance(parsed.get("answer"), dict) else {}
    issue_summary = clean_structured_text(answer.get("issue_summary"))
    if contains_disclaimer(issue_summary):
        issue_summary = "The available legal sources do not contain enough information to answer this reliably."

    normalized = {
        "answer": {
            "issue_summary": issue_summary or "The available legal sources do not contain enough information to answer this reliably.",
            "possible_rights": normalize_text_list(answer.get("possible_rights"), limit=4),
            "next_steps": normalize_text_list(answer.get("next_steps"), limit=5),
        },
        "sources": source_payload(chunks),
        "confidence": clean_structured_text(parsed.get("confidence")) or "medium",
        "insufficient_context": bool(parsed.get("insufficient_context", False)),
        "disclaimer": DISCLAIMER,
    }
    if normalized["confidence"] not in {"low", "medium", "high"}:
        normalized["confidence"] = "medium"
    if not chunks or len(normalized["sources"]) == 0:
        normalized["insufficient_context"] = True
        normalized["confidence"] = "low"
    return normalized


def raise_classified_gemini_error(exc: Exception) -> None:
    error_class = f"{exc.__class__.__module__}.{exc.__class__.__name__}"
    message = str(exc)
    lower_message = message.lower()
    logger.error("Gemini generation failed: %s: %s", error_class, message)

    if "api key" in lower_message and any(term in lower_message for term in ("invalid", "expired", "not valid")):
        raise ConfigurationError("Gemini authentication failed. Check GEMINI_API_KEY.") from exc

    if any(term in lower_message for term in ("permission_denied", "permission denied", "403")):
        raise ConfigurationError("Gemini permission denied. Check that the API key has access to the Gemini API.") from exc

    if any(term in lower_message for term in ("not_found", "not found", "no longer available", "model")) and "404" in lower_message:
        raise ConfigurationError(
            f"Configured Gemini model '{GEMINI_MODEL}' is unavailable for this API key. "
            "Set GEMINI_MODEL to an accessible model such as gemini-flash-lite-latest."
        ) from exc

    if any(term in lower_message for term in ("quota", "rate limit", "resource_exhausted", "429")):
        raise LLMError("Gemini quota or rate limit was exceeded. Please try again later or check your quota.") from exc

    if any(term in lower_message for term in ("unavailable", "overloaded", "high demand", "503")):
        raise LLMError("Gemini is temporarily unavailable or under high demand. Please try again shortly.") from exc

    if any(term in lower_message for term in ("invalid_argument", "schema", "400")):
        raise LLMError("Gemini rejected the structured-output request. Check the response schema and prompt.") from exc

    raise LLMError("Gemini could not generate an answer right now. Please check the API key, quota, model, or try again.") from exc


def local_grounded_response(question: str, chunks: list[RetrievedChunk]) -> dict[str, Any]:
    context = " ".join(chunk.text for chunk in chunks[:2]).lower()
    possible_rights = [
        "The retrieved legal sources indicate that the issue may relate to goods or services supplied to a consumer.",
        "Depending on the facts and the provisions that apply, remedies may include repair, replacement, refund, compensation, or another appropriate relief.",
    ]
    if "defect" in context or "defective" in question.lower() or "damaged" in question.lower():
        possible_rights[0] = "The retrieved legal sources include consumer-law material about defective goods and consumer remedies."

    return normalize_rag_response({
        "answer": {
            "issue_summary": "Based on the information provided, this appears to involve an Indian consumer-law issue connected to goods or services and the seller's response.",
            "possible_rights": possible_rights,
            "next_steps": [
                "Keep the invoice, payment proof, product details, and seller communication.",
                "Send the seller a clear written request explaining the defect or problem and the remedy you are asking for.",
                "If the issue remains unresolved, consider using the consumer complaint process after checking the applicable provisions and facts.",
            ],
        },
        "confidence": "medium",
        "insufficient_context": False,
    }, chunks)


def gemini_grounded_response(question: str, chunks: list[RetrievedChunk]) -> dict[str, Any]:
    context_blocks = []
    for index, chunk in enumerate(chunks, start=1):
        context_blocks.append(
            f"[Source {index}] Document: {chunk.document_title}\n"
            f"File: {chunk.source}\nPage: {chunk.page}\nText:\n{chunk.text}"
        )
    context = "\n\n".join(context_blocks)
    client = genai.Client(api_key=GEMINI_API_KEY)
    system_prompt = """You are Legal Aid AI, an informational assistant for Indian legal information.

You must answer the user's question using ONLY the legal source text supplied in the retrieved context.
Do not use unsupported general legal knowledge to make legal claims.
Do not invent Acts, sections, rules, judgments, deadlines, fees, procedures, authorities, or remedies.
If the available context does not provide enough information to answer reliably, say clearly that the available legal sources do not contain enough information.
Explain legal information in simple language suitable for a non-lawyer.
Do not state that the user definitely has a valid legal case.
Use cautious phrasing such as "may apply", "based on the information provided", and "the retrieved provisions indicate".

Write the response in these practical sections:
- issue_summary: a concise explanation of what the situation may involve.
- possible_rights: only rights or remedies directly supported by the retrieved context.
- next_steps: concrete layperson actions, such as keeping invoices/payment proof/warranty/seller communication, sending a written request for repair/replacement/refund when supported by the context, or considering the consumer redressal mechanism when supported by the context.

Do not give vague steps such as "review the legal provisions", "consider the provided provisions", or "consult the law".
Do not write phrases like "when supported by the context" or "based on the context" in the final user-facing answer.
If the retrieved context does not support a specific practical step, omit that step instead of making it vague.
Do not include markdown formatting, bold markers, bullets, or numbering inside any string.
Do not prefix steps with "1.", "1)", or "Step 1:".
Do not include the disclaimer in issue_summary, possible_rights, or next_steps. The backend adds the disclaimer separately.
Do not include raw SVG text or icon labels.

Return only valid JSON with this exact shape:
{
  "answer": {
    "issue_summary": "string",
    "possible_rights": ["string"],
    "next_steps": ["string"]
  },
  "confidence": "low|medium|high",
  "insufficient_context": false
}
"""
    schema = {
        "type": "object",
        "properties": {
            "answer": {
                "type": "object",
                "properties": {
                    "issue_summary": {"type": "string"},
                    "possible_rights": {"type": "array", "items": {"type": "string"}},
                    "next_steps": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["issue_summary", "possible_rights", "next_steps"],
            },
            "confidence": {"type": "string", "enum": ["low", "medium", "high"]},
            "insufficient_context": {"type": "boolean"},
        },
        "required": ["answer", "confidence", "insufficient_context"],
    }
    try:
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{system_prompt}\n\nRetrieved context:\n{context}\n\nUser question:\n{question}",
            config=types.GenerateContentConfig(
                temperature=0.2,
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        content = response.text or "{}"
        parsed = json.loads(content)
    except (genai_errors.APIError, TimeoutError, RuntimeError) as exc:
        raise_classified_gemini_error(exc)
    except (json.JSONDecodeError, KeyError, TypeError) as exc:
        logger.exception("Gemini returned malformed JSON")
        raise LLMError("Gemini returned an unexpected response format. Please try again.") from exc

    return normalize_rag_response(parsed, chunks)


rag = LegalRAG()
