"""Transcribes a short spoken legal question into plain Latin-letter text (English, Hinglish, or
a mix) for the Ask page's microphone input.

Privacy: the uploaded audio bytes are held in memory only, for the duration of one request --
never written to disk, never stored in any database. The transcript text itself is never logged;
only call-level metadata (byte size, latency, transcript length) is. Confirmed by
google-genai 1.43.0 + gemini-flash-lite-latest (the model this app already uses) accepting audio
input directly via types.Part.from_bytes(), tested 2026-10-28 against a real recording.

Why Latin letters only: Legal Aid AI's whole pipeline (routing, retrieval, the embedding model,
query_normalizer.py) is built around Hinglish written in Latin letters, never Devanagari. A
transcript in Devanagari would silently break every downstream step. The transcription prompt
asks for Latin letters only, but that's a request, not a guarantee -- query_normalizer.py already
showed Gemini isn't fully deterministic even at temperature=0, so this module backs the prompt
with a programmatic check: if the transcript comes back containing Devanagari characters, it is
retried ONCE with a more forceful prompt; if it's still Devanagari after that, transcription fails
safely rather than handing Devanagari text to a pipeline that can't handle it.
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
from config import GEMINI_API_KEY, GEMINI_MODEL, MAX_AUDIO_SIZE_MB

logger = logging.getLogger("legal_aid_ai.voice_transcription")

ALLOWED_AUDIO_MIME_TYPES = frozenset({
    "audio/wav", "audio/x-wav", "audio/wave",
    "audio/webm",
    "audio/mp4", "audio/x-m4a", "audio/m4a", "audio/aac",
    "audio/mpeg", "audio/mp3",
    "audio/ogg",
})

# U+0900-U+097F covers Devanagari, including the common vowel signs/matras and virama used in
# everyday Hindi -- enough to reliably flag a Devanagari transcript without a false-positive risk
# from Latin-letter Hinglish (which uses none of this range).
DEVANAGARI_PATTERN = re.compile(r"[ऀ-ॿ]")

TRANSCRIPTION_PROMPT = """Transcribe the speech in this audio.
The speaker may talk in English, Hindi, or a mix of both (Hinglish).
Rules:
- Write the transcript using ONLY English (Latin) letters, even for Hindi words. Do not use
  Devanagari script under any circumstances. Write Hindi words the way they sound in English
  letters (e.g. "mera", "nahi", "kar raha hai").
- Transcribe exactly what was said. Do not translate, summarize, answer, or add anything.
- If no speech is audible, or the audio is silent or unintelligible, return an empty transcript.
Return only strict structured JSON with this schema: {"transcript": "..."}
"""

DEVANAGARI_RETRY_PROMPT = TRANSCRIPTION_PROMPT + """
Your previous attempt at this used Devanagari script, which is not allowed. Transcribe the same
audio again, writing every word -- English or Hindi -- using ONLY English (Latin) letters. Write
Hindi words phonetically in English letters (e.g. "aapka", "nahi", "kar raha hai"). Do not output
a single Devanagari character.
"""

TRANSCRIPTION_SCHEMA = {
    "type": "object",
    "properties": {"transcript": {"type": "string"}},
    "required": ["transcript"],
}


class VoiceTranscriptionError(ValueError):
    """A problem with the request itself (bad format, empty or too-large audio) -- maps to 400."""


class VoiceServiceUnavailableError(RuntimeError):
    """Gemini itself failed to respond (timeout, API/quota error) -- maps to 503, distinct from a
    RuntimeError about the *content* of the result (no speech, still-Devanagari after retry),
    which maps to 422. The frontend uses this distinction to decide whether falling back to the
    browser's own speech recognition is worth trying (503: yes, our service is the problem;
    422: no, the recording itself didn't produce usable speech)."""


def max_audio_bytes() -> int:
    return MAX_AUDIO_SIZE_MB * 1024 * 1024


def is_allowed_mime_type(mime_type: str | None) -> bool:
    return bool(mime_type) and mime_type.lower().split(";")[0].strip() in ALLOWED_AUDIO_MIME_TYPES


def contains_devanagari(text: str) -> bool:
    return bool(DEVANAGARI_PATTERN.search(text or ""))


def _call_gemini(content: bytes, mime_type: str, prompt: str) -> str:
    client = genai.Client(api_key=GEMINI_API_KEY, http_options=gemini_http_options())
    response = client.models.generate_content(
        model=GEMINI_MODEL,
        contents=[
            types.Part.from_bytes(data=content, mime_type=mime_type),
            prompt,
        ],
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=TRANSCRIPTION_SCHEMA,
        ),
    )
    data = json.loads(response.text or "{}")
    return fact_sufficiency.normalize_text(data.get("transcript"))


def transcribe_audio(content: bytes, mime_type: str) -> str:
    """Return a Latin-letter transcript of `content`.

    Raises VoiceTranscriptionError for a request-shape problem (caller maps this to 400).
    Raises VoiceServiceUnavailableError if Gemini itself failed to respond (caller maps this to
    503 -- worth a client-side fallback). Raises RuntimeError if Gemini responded but the result
    wasn't usable -- no speech detected, or still Devanagari after one retry (caller maps this to
    422). Never returns a blank or Devanagari result.
    """
    if not content:
        raise VoiceTranscriptionError("No audio was received.")
    if len(content) > max_audio_bytes():
        raise VoiceTranscriptionError(f"Audio is too long. Maximum supported size is {MAX_AUDIO_SIZE_MB} MB.")
    if not is_allowed_mime_type(mime_type):
        raise VoiceTranscriptionError("Unsupported audio format.")
    if not GEMINI_API_KEY:
        raise VoiceServiceUnavailableError("Voice input is not configured right now. Please type your question instead.")

    clean_mime_type = mime_type.lower().split(";")[0].strip()
    started = time.perf_counter()
    retried_for_devanagari = False
    try:
        transcript = _call_gemini(content, clean_mime_type, TRANSCRIPTION_PROMPT)
        if transcript and contains_devanagari(transcript):
            retried_for_devanagari = True
            transcript = _call_gemini(content, clean_mime_type, DEVANAGARI_RETRY_PROMPT)
    except (genai_errors.APIError, TimeoutError, httpx.HTTPError) as exc:
        logger.warning("Voice transcription service call failed: %s: %s", exc.__class__.__name__, str(exc))
        raise VoiceServiceUnavailableError("Voice transcription is temporarily unavailable. Please try again or type your question.") from exc
    except (json.JSONDecodeError, ValueError, TypeError) as exc:
        logger.warning("Voice transcription returned an unusable response: %s: %s", exc.__class__.__name__, str(exc))
        raise RuntimeError("Could not transcribe that recording. Please try again or type your question.") from exc

    latency_ms = int((time.perf_counter() - started) * 1000)
    logger.info(
        "Voice transcription completed audio_bytes=%s mime_type=%s latency_ms=%s transcript_chars=%s retried_for_devanagari=%s",
        len(content), mime_type, latency_ms, len(transcript), retried_for_devanagari,
    )
    if not transcript:
        raise RuntimeError("No speech was detected in that recording. Please try again or type your question.")
    if contains_devanagari(transcript):
        logger.warning("Voice transcription still contained Devanagari after retry audio_bytes=%s mime_type=%s", len(content), mime_type)
        raise RuntimeError("Could not transcribe that into English letters. Please try again or type your question.")
    return transcript
