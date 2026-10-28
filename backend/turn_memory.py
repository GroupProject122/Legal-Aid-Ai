"""Correction memory for follow-up turn classification.

When the keyword rules' first guess about a follow-up message ("is this a question, a new fact,
a new problem, or just thanks?") is overruled by Gemini, the disagreement is recorded here. Past
corrections are then reused in two ways:

- as reference examples in Gemini's prompt, chosen by similarity to the new message (pending
  and approved records -- low risk, Gemini still decides);
- as a shortcut that skips the Gemini call entirely, but ONLY for a near-duplicate of a record a
  person has approved -- because Gemini is not always right, and an unreviewed label reused
  without a check would repeat its mistakes indefinitely.

Records are reviewed with `python review_turn_corrections.py`.

Kept deliberately separate from the legal corpus: its own table in legal_aid.db, its own
embeddings, never in vectorstore/. Mixing user phrasing into the legal index would pull
"i dont know how civil courts work" into legal retrieval in place of statutes.

Privacy: only the short follow-up message is stored, never the case story, and only after
redaction (phone numbers, e-mail addresses, card / Aadhaar / long account numbers, OTP / PIN /
password values). Names cannot be reliably detected by pattern and are NOT removed, which is one
reason records are capped at MAX_MESSAGE_CHARS. Pending and rejected records are deleted after
RETENTION_DAYS; approved ones are kept because they are in active use.
"""
from __future__ import annotations

import logging
import os
import re
import sqlite3
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

import numpy as np

import redaction
from config import BASE_DIR

logger = logging.getLogger("legal_aid_ai.turn_memory")

DB_PATH = BASE_DIR / "legal_aid.db"
ENABLED = os.getenv("TURN_MEMORY_ENABLED", "true").strip().lower() not in {"0", "false", "no", "off"}

MAX_MESSAGE_CHARS = 300
RETENTION_DAYS = 90
EXAMPLE_COUNT = 4
EXAMPLE_MIN_SIMILARITY = 0.55
# Cosine similarity (MiniLM, normalised) at which an APPROVED record is treated as the same
# message and its label used without calling Gemini. High on purpose: "the rent is 15000" and
# "the rent is 18000 not 15000" are similar but are a fact and a correction.
SHORTCUT_MIN_SIMILARITY = 0.93

TURN_TYPES = {
    "new_issue", "follow_up_question", "additional_fact", "correction",
    "clarification_reply", "acknowledgement", "small_talk",
}
# What each label makes the app do -- recorded alongside the label, since "the kind of response
# it requires" is what the correction is ultimately about.
RESPONSE_ACTION = {
    "follow_up_question": "answer_with_context",
    "additional_fact": "update_case_and_answer",
    "correction": "correct_case_and_answer",
    "clarification_reply": "answer_with_context",
    "new_issue": "start_new_case",
    "acknowledgement": "acknowledge_only",
    "small_talk": "acknowledge_only",
}
STATUSES = {"pending", "approved", "rejected"}

REDACTIONS = [
    (re.compile(r"(?i)\b(?:otp|pin|cvv|password|passcode|upi pin)\s*(?:is|:|=|-)?\s*\S+"), "[secret removed]"),
    (re.compile(r"(?i)\b[\w.+-]+@[\w-]+\.[\w.-]+\b"), "[email removed]"),
    (re.compile(r"(?i)\b[\w.-]+@(?:ok|y|ax|ib|ic|upi|paytm|ybl|apl|axl|ibl|sbi|hdfcbank|icici)\w*\b"), "[upi id removed]"),
    (re.compile(r"(?<!\d)(?:\+?91[\s-]?)?[6-9]\d{4}[\s-]?\d{5}(?!\d)"), "[phone removed]"),
    (re.compile(r"(?<!\d)\d{4}\s?\d{4}\s?\d{4}(?!\d)"), "[id number removed]"),
    (re.compile(r"(?<!\d)\d{9,18}(?!\d)"), "[account number removed]"),
]

_embedder: Callable[[list[str]], np.ndarray] | None = None


def set_embedder(embedder: Callable[[list[str]], np.ndarray] | None) -> None:
    """Tests inject a small fake embedder so they never load the sentence-transformer model."""
    global _embedder
    _embedder = embedder


def embed(texts: list[str]) -> np.ndarray:
    if _embedder is not None:
        return np.asarray(_embedder(texts), dtype="float32")
    import rag  # deferred: the model is already loaded by the running app; tests never get here

    return rag.embed_texts(texts)


def redact(message: str) -> str:
    text = re.sub(r"\s+", " ", str(message or "")).strip()
    text = redaction.redact_card_number(text, "[card number removed]")
    for pattern, placeholder in REDACTIONS:
        text = pattern.sub(placeholder, text)
    return text[:MAX_MESSAGE_CHARS]


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS turn_corrections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            message TEXT NOT NULL,
            domains TEXT NOT NULL,
            rule_label TEXT NOT NULL,
            model_label TEXT NOT NULL,
            final_label TEXT NOT NULL,
            response_action TEXT NOT NULL,
            reason TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            seen_count INTEGER NOT NULL DEFAULT 1,
            reviewer_note TEXT,
            embedding BLOB
        )
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_turn_corrections_status ON turn_corrections(status)")
    return conn


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def purge_expired(conn: sqlite3.Connection, days: int = RETENTION_DAYS) -> int:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")
    cursor = conn.execute(
        "DELETE FROM turn_corrections WHERE status IN ('pending', 'rejected') AND updated_at < ?",
        (cutoff,),
    )
    return cursor.rowcount


def record_correction(
    message: str,
    domains: list[str],
    rule_label: str,
    model_label: str,
    reason: str | None = None,
    db_path: Path | None = None,
) -> int | None:
    """Store one rules-vs-Gemini disagreement as a pending correction. A repeat of an identical
    redacted message with the same labels bumps seen_count instead of adding a row, so the review
    queue shows how often a phrasing occurs. Never raises: a failure here must not break an answer."""
    if not ENABLED or rule_label == model_label or model_label not in TURN_TYPES:
        return None
    text = redact(message)
    if not text:
        return None
    try:
        vector = embed([text])[0].astype("float32").tobytes()
        with connect(db_path) as conn:
            purge_expired(conn)
            existing = conn.execute(
                "SELECT id FROM turn_corrections WHERE message = ? AND rule_label = ? AND model_label = ?",
                (text, rule_label, model_label),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE turn_corrections SET seen_count = seen_count + 1, updated_at = ? WHERE id = ?",
                    (now_iso(), existing["id"]),
                )
                return int(existing["id"])
            cursor = conn.execute(
                """
                INSERT INTO turn_corrections (
                    created_at, updated_at, message, domains, rule_label, model_label, final_label,
                    response_action, reason, status, embedding
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?)
                """,
                (
                    now_iso(), now_iso(), text, ",".join(domains or []), rule_label, model_label, model_label,
                    RESPONSE_ACTION.get(model_label, ""), (reason or "")[:300], vector,
                ),
            )
            return int(cursor.lastrowid)
    except Exception as exc:  # noqa: BLE001 -- recording is best-effort by design
        logger.warning("Could not record turn correction: %s: %s", exc.__class__.__name__, str(exc))
        return None


def _nearest(message: str, statuses: tuple[str, ...], db_path: Path | None = None) -> list[tuple[float, sqlite3.Row]]:
    text = redact(message)
    placeholders = ",".join("?" for _ in statuses)
    with connect(db_path) as conn:
        rows = conn.execute(
            f"SELECT * FROM turn_corrections WHERE status IN ({placeholders}) AND embedding IS NOT NULL",
            statuses,
        ).fetchall()
    if not rows or not text:
        return []
    query = embed([text])[0]
    matrix = np.stack([np.frombuffer(row["embedding"], dtype="float32") for row in rows])
    scores = matrix @ query
    order = np.argsort(-scores)
    return [(float(scores[index]), rows[index]) for index in order]


def similar_examples(message: str, limit: int = EXAMPLE_COUNT, db_path: Path | None = None) -> list[dict[str, str]]:
    """Past corrections most similar to `message`, as prompt examples. Approved records are
    preferred over pending ones at equal relevance. Never raises."""
    if not ENABLED:
        return []
    try:
        ranked = _nearest(message, ("approved", "pending"), db_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read turn corrections: %s: %s", exc.__class__.__name__, str(exc))
        return []
    ranked = [(score + (0.02 if row["status"] == "approved" else 0.0), row) for score, row in ranked if score >= EXAMPLE_MIN_SIMILARITY]
    ranked.sort(key=lambda item: -item[0])
    return [{"message": row["message"], "turn_type": row["final_label"]} for _score, row in ranked[:limit]]


def shortcut_label(message: str, db_path: Path | None = None) -> str | None:
    """The label of an APPROVED correction that is a near-duplicate of `message`, else None.
    Pending records never qualify: skipping Gemini is only safe on a human-checked label."""
    if not ENABLED:
        return None
    try:
        ranked = _nearest(message, ("approved",), db_path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("Could not read turn corrections: %s: %s", exc.__class__.__name__, str(exc))
        return None
    if ranked and ranked[0][0] >= SHORTCUT_MIN_SIMILARITY:
        return ranked[0][1]["final_label"]
    return None


# --- review operations (used by review_turn_corrections.py) ---------------------------------


def list_corrections(status: str | None = "pending", db_path: Path | None = None) -> list[dict[str, Any]]:
    with connect(db_path) as conn:
        purge_expired(conn)
        if status:
            rows = conn.execute("SELECT * FROM turn_corrections WHERE status = ? ORDER BY seen_count DESC, id", (status,)).fetchall()
        else:
            rows = conn.execute("SELECT * FROM turn_corrections ORDER BY id").fetchall()
    return [{key: row[key] for key in row.keys() if key != "embedding"} for row in rows]


def review(correction_id: int, status: str, label: str | None = None, note: str | None = None, db_path: Path | None = None) -> bool:
    """Approve or reject a record, optionally fixing its label (when Gemini got it wrong too)."""
    if status not in STATUSES:
        raise ValueError(f"status must be one of {sorted(STATUSES)}")
    if label is not None and label not in TURN_TYPES:
        raise ValueError(f"label must be one of {sorted(TURN_TYPES)}")
    with connect(db_path) as conn:
        row = conn.execute("SELECT final_label FROM turn_corrections WHERE id = ?", (correction_id,)).fetchone()
        if not row:
            return False
        final = label or row["final_label"]
        conn.execute(
            "UPDATE turn_corrections SET status = ?, final_label = ?, response_action = ?, reviewer_note = ?, updated_at = ? WHERE id = ?",
            (status, final, RESPONSE_ACTION.get(final, ""), note, now_iso(), correction_id),
        )
    return True


def delete(correction_id: int, db_path: Path | None = None) -> bool:
    with connect(db_path) as conn:
        return conn.execute("DELETE FROM turn_corrections WHERE id = ?", (correction_id,)).rowcount > 0


def stats(db_path: Path | None = None) -> dict[str, Any]:
    with connect(db_path) as conn:
        by_status = {row["status"]: row["n"] for row in conn.execute("SELECT status, COUNT(*) n FROM turn_corrections GROUP BY status")}
        pairs = [
            {"rule_label": row["rule_label"], "model_label": row["model_label"], "count": row["n"]}
            for row in conn.execute(
                "SELECT rule_label, model_label, SUM(seen_count) n FROM turn_corrections GROUP BY rule_label, model_label ORDER BY n DESC"
            )
        ]
    return {"by_status": by_status, "rule_to_model": pairs, "checked_at": time.strftime("%Y-%m-%d %H:%M")}
