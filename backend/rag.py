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
    chapter: str | None = None
    section_number: str | None = None
    section_title: str | None = None
    rule_number: str | None = None
    rule_title: str | None = None


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

MIN_RELEVANCE_SCORE = 0.30
LOW_CONFIDENCE_RELEVANCE_SCORE = 0.22
RELEVANCE_WINDOW = 0.14
MAX_CONTEXT_CHUNKS = 4
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
    product_problem_terms = {
        "defective", "defect", "damaged", "broken", "faulty", "stopped working",
        "refund", "replacement", "replace", "repair", "warranty", "seller",
        "phone", "mobile", "goods", "product", "online",
    }
    if any(term in lowered for term in product_problem_terms):
        return (
            f"{question} defective product goods seller refund repair replacement warranty "
            "consumer rights product liability complaint redressal"
        )
    return question


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
                    chapter=item.get("chapter"),
                    section_number=item.get("section_number"),
                    section_title=item.get("section_title"),
                    rule_number=item.get("rule_number"),
                    rule_title=item.get("rule_title"),
                )
            )
        return candidates

    def retrieve(self, question: str, top_k: int = TOP_K) -> list[RetrievedChunk]:
        candidates = self.retrieve_candidates(question, candidate_k=max(top_k * 2, 12))
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

    def answer(self, question: str) -> dict[str, Any]:
        question = validate_question(question)
        if not is_consumer_law_question(question):
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
            return gemini_grounded_response(question, chunks)

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
            boost += 0.06

    if any(term in query for term in ("replace", "replacement")):
        if "replace the goods" in text or "free from any defect" in text:
            boost += 0.14

    if "seller" in query:
        if "liability of product sellers" in title or "product seller" in text:
            boost += 0.12

    if any(term in query for term in ("defect", "defective", "damaged", "stopped working", "faulty", "broken")):
        if "defect" in text or "defective" in text:
            boost += 0.06
        if "definitions" in title and "defect" in text:
            boost += 0.09
        if "product liability" in text:
            boost += 0.06
        if "exceptions to product liability" in title and not any(term in query for term in ("exception", "defence", "defense")):
            boost -= 0.20

    if any(term in query for term in ("mean", "meaning", "define", "definition")):
        if "definitions" in title or "(10)" in text and "defect" in text:
            boost += 0.16

    return min(boost, 0.22)


def final_rerank_score(question: str, chunk: RetrievedChunk) -> float:
    return chunk.score + legal_substance_boost(chunk) + lexical_overlap_score(question, chunk) + query_intent_boost(question, chunk)


def select_relevant_chunks(candidates: list[RetrievedChunk], question: str, top_k: int = TOP_K) -> list[RetrievedChunk]:
    if not candidates:
        return []
    max_score = max(chunk.score for chunk in candidates)
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
    selected: list[RetrievedChunk] = []
    for chunk in ranked:
        if chunk.score < threshold:
            continue
        if is_near_duplicate(chunk, selected):
            continue
        selected.append(chunk)
        if len(selected) >= min(top_k, MAX_CONTEXT_CHUNKS):
            break
    return selected


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
    system_prompt = """You are Legal Aid AI, an informational assistant for Indian consumer law.

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
