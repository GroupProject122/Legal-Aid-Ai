"""Rewrites a Hinglish (or mixed Hindi/English, written in Latin letters) legal question into
plain English, for retrieval only.

Why this exists: EMBEDDING_MODEL (all-MiniLM-L6-v2) is an English-only sentence embedding model,
and the legal corpus itself is entirely English-language documents. A Hinglish question like
"mera Instagram hack ho gaya" was previously sent to rag.retrieve() exactly as typed -- confirmed
2026-10-28 by comparing retrieval for that exact query against its English equivalent "my
Instagram account was hacked": the Hinglish version's top (and only) result was Bharatiya Nyaya
Sanhita Section 330 ("House-trespass and house-breaking", retrieval_priority="low",
status="supporting_only" -- a vector-similarity false positive), while the English version
correctly retrieved IT Act Section 66C ("Identity theft"). This module exists to close that gap
by normalizing the query sent to retrieval ONLY -- never the text shown to the user, stored in
the case, or checked by corpus_gap's raw-text keyword gates or the claim verifier.
"""
from __future__ import annotations

import json
import logging
import re
import time

import httpx
from google import genai
from google.genai import errors as genai_errors
from google.genai import types

import fact_sufficiency
from gemini_http import gemini_http_options
from config import GEMINI_API_KEY, GEMINI_MODEL

logger = logging.getLogger("legal_aid_ai.query_normalizer")

# A broad, non-exhaustive set of common Hinglish function/connector words -- common enough that a
# genuinely Hinglish or mixed question is very likely to contain at least one, while plain English
# legal questions essentially never do (none of these are real English words on their own).
# Deliberately a flat "any match" check rather than a weighted/ratio score: it's cheap, has no
# false-negative risk worth worrying about in practice (missing a rewrite just means retrieval
# stays as good as it was before this module existed, not worse), and false positives (an English
# question that happens to contain one of these as a substring of an unrelated word) are avoided
# by matching whole tokens only, not substrings.
HINGLISH_MARKER_WORDS = frozenset({
    "hai", "hain", "nahi", "nahin", "kya", "mera", "meri", "mere", "mujhe", "mujhko", "humko",
    "hamara", "hamari", "tumhara", "aapka", "paise", "paisa", "rupaye", "kar", "karu", "karna",
    "karni", "karo", "kiya", "kiye", "ki", "raha", "rahi", "rahe", "diya", "diye", "di", "gaya",
    "gayi", "gaye", "wapas", "chahiye", "hua", "hui", "hue", "tha", "thi", "liya", "liye",
    "bhi", "ke", "ka", "se", "ko", "pe", "hoga", "hogi", "honge", "ab", "abhi",
    "kaise", "kyun", "kyu", "kahan", "kab", "kaun", "kitna", "kitni", "bata", "batao", "madad",
    "shikayat", "maalik", "makaan", "kiraya", "paas", "milega", "milegi", "nikal",
    "karvana", "karwana", "banta", "banti",
    # "the" and "par" deliberately excluded -- both are real, common English words (the; par
    # value/on par with) and including them caused false positives on plain English legal
    # questions during testing (e.g. "What is a consumer under the Consumer Protection Act?").
})

NORMALIZER_PROMPT = """You are rewriting a user's legal question so it can be searched against
English-language Indian legal documents.
The user may have written in English, Hindi written in English letters (Hinglish), or a mix.
Rewrite it as a short, plain English legal-search query.
Rules:
- Keep every fact, amount, date, party, and place exactly as given -- do not drop or change any of them.
- Do not add any fact, assumption, or detail that was not in the original text.
- Do not answer the question, give legal advice, or cite any law.
- Do not translate proper names of people or places -- keep them as written.
- Return only strict structured JSON with this schema: {"english_query": "..."}
"""

NORMALIZER_SCHEMA = {
    "type": "object",
    "properties": {"english_query": {"type": "string"}},
    "required": ["english_query"],
}


def looks_like_plain_english(text: str) -> bool:
    """Cheap, deterministic, no-API-call check: does this text contain any common Hinglish
    marker word (as a whole token, not a substring)? If not, it's treated as already-English and
    the Gemini rewrite is skipped entirely -- most questions asked of this app are already plain
    English, and this keeps that common case free and instant."""
    tokens = set(re.findall(r"[a-zA-Z]+", text.lower()))
    return tokens.isdisjoint(HINGLISH_MARKER_WORDS)


def english_retrieval_query(text: str) -> str:
    """Return an English version of `text` suitable for embedding-based retrieval against the
    corpus. Used ONLY for the string passed to rag.retrieve() -- callers must keep using the
    original `text` for everything else (the stored case, the chat transcript, corpus_gap's
    raw-text checks, the claim verifier). Never raises and never blocks -- falls back to the
    original text on any failure, missing API key, or empty/unusable result, since a missed
    normalization is far better than a blocked answer."""
    if not text or looks_like_plain_english(text):
        return text
    if not GEMINI_API_KEY:
        return text

    started = time.perf_counter()
    try:
        client = genai.Client(api_key=GEMINI_API_KEY, http_options=gemini_http_options())
        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=f"{NORMALIZER_PROMPT}\n\nUser's question: {text}",
            config=types.GenerateContentConfig(
                temperature=0,
                response_mime_type="application/json",
                response_schema=NORMALIZER_SCHEMA,
            ),
        )
        data = json.loads(response.text or "{}")
        english_query = fact_sufficiency.normalize_text(data.get("english_query"))
        latency_ms = int((time.perf_counter() - started) * 1000)
        if not english_query:
            logger.debug("Query normalization returned an empty result latency_ms=%s, falling back to original.", latency_ms)
            return text
        logger.debug(
            "Query normalized original=%r english=%r latency_ms=%s",
            fact_sufficiency.sanitize_user_fact(text),
            fact_sufficiency.sanitize_user_fact(english_query),
            latency_ms,
        )
        return english_query
    except (genai_errors.APIError, TimeoutError, httpx.HTTPError, RuntimeError, json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Query normalization failed safely, using original text: %s: %s", exc.__class__.__name__, str(exc))
        return text
