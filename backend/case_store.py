from __future__ import annotations

import json
import re
import sqlite3
import time
from pathlib import Path
from typing import Any

from config import BASE_DIR

DB_PATH = BASE_DIR / "legal_aid.db"
MAX_CASE_TITLE_CHARS = 80


def init_db(db_path: Path | None = None) -> None:
    path = Path(db_path or DB_PATH)
    path.parent.mkdir(parents=True, exist_ok=True)
    with connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS cases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                primary_domain TEXT,
                conversation_state_json TEXT,
                confirmed_document_context_json TEXT
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_id INTEGER NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('user', 'assistant')),
                content_json TEXT NOT NULL,
                created_at TEXT NOT NULL,
                sequence_number INTEGER NOT NULL,
                FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_case_sequence ON messages(case_id, sequence_number)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cases_updated ON cases(updated_at DESC)")


def connect(db_path: Path | None = None) -> sqlite3.Connection:
    conn = sqlite3.connect(Path(db_path or DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def create_case(
    first_message: str,
    primary_domain: str | None = None,
    conversation_state: dict[str, Any] | None = None,
    confirmed_document_context: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> int:
    init_db(db_path)
    now = utc_timestamp()
    title = generate_case_title(first_message, primary_domain)
    with connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO cases (
                title, created_at, updated_at, primary_domain,
                conversation_state_json, confirmed_document_context_json
            )
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                title,
                now,
                now,
                primary_domain,
                json_dumps(conversation_state),
                json_dumps(sanitize_value(confirmed_document_context)),
            ),
        )
        return int(cursor.lastrowid)


def get_case(case_id: int, db_path: Path | None = None) -> dict[str, Any] | None:
    init_db(db_path)
    with connect(db_path) as conn:
        row = conn.execute("SELECT * FROM cases WHERE id = ?", (case_id,)).fetchone()
    return case_row_to_dict(row) if row else None


VALID_CASE_DOMAINS = frozenset({"consumer", "cyber", "tenancy", "constitutional_public_authority"})


def list_cases(
    db_path: Path | None = None,
    limit: int | None = None,
    offset: int = 0,
    search: str | None = None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Offset-based pagination, added 2026-09-16: at 957 cases (this dev DB's current volume),
    the old unpaginated version fetched and rendered all of them on every My Cases page load --
    measured at ~1s to fully render and ~550ms click-to-response latency on a mid-list card in a
    live browser test, both clearly felt as UI lag. The backend query/payload itself was never
    the bottleneck (136KB, single-digit-ms SQL) -- rendering ~957 DOM cards was. `limit=None`
    keeps the old fetch-everything behavior for callers that want it (e.g. tests); the
    `/api/cases` endpoint in main.py always passes an explicit limit.

    `search` matches (case-insensitively) against the case title OR the case's first user
    message content -- cheap to include: one indexed-by-case_id EXISTS subquery against the
    messages table, well within SQLite's comfort zone at this row count. `domain` filters on
    primary_domain exactly (see VALID_CASE_DOMAINS for the values actually in use).
    """
    init_db(db_path)
    where_clauses: list[str] = []
    params: dict[str, Any] = {}
    if search and search.strip():
        where_clauses.append(
            "(cases.title LIKE :search_pattern ESCAPE '\\' OR EXISTS ("
            "SELECT 1 FROM messages WHERE messages.case_id = cases.id AND messages.role = 'user' "
            "AND messages.sequence_number = 1 AND messages.content_json LIKE :search_pattern ESCAPE '\\'"
            "))"
        )
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params["search_pattern"] = f"%{escaped}%"
    if domain:
        where_clauses.append("cases.primary_domain = :domain")
        params["domain"] = domain
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with connect(db_path) as conn:
        total = int(
            conn.execute(f"SELECT COUNT(*) FROM cases {where_sql}", params).fetchone()[0]  # noqa: S608
        )
        query = f"""
            SELECT cases.id, cases.title, cases.created_at, cases.updated_at, cases.primary_domain
            FROM cases
            {where_sql}
            ORDER BY cases.updated_at DESC, cases.id DESC
        """  # noqa: S608
        if limit is not None:
            query += " LIMIT :limit OFFSET :offset"
            params = {**params, "limit": limit, "offset": offset}
        rows = conn.execute(query, params).fetchall()

    items = [case_row_to_dict(row, include_json=False) for row in rows]
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": limit is not None and offset + len(items) < total,
    }


def rename_case(case_id: int, title: str, db_path: Path | None = None) -> dict[str, Any] | None:
    init_db(db_path)
    cleaned_title = normalize_case_title(title)
    now = utc_timestamp()
    with connect(db_path) as conn:
        existing = conn.execute("SELECT id FROM cases WHERE id = ?", (case_id,)).fetchone()
        if existing is None:
            return None
        conn.execute(
            "UPDATE cases SET title = ?, updated_at = ? WHERE id = ?",
            (cleaned_title, now, case_id),
        )
    return get_case(case_id, db_path)


def set_case_title_only(case_id: int, title: str, db_path: Path | None = None) -> bool:
    """Update ONLY the title column -- unlike rename_case(), does not touch updated_at (so the
    case does not jump to the top of the newest-first list) or anything else. For programmatic
    backfills (e.g. regenerating titles after a title-generation fix), not the user-facing
    rename action, which is expected to bump updated_at like any other edit."""
    init_db(db_path)
    cleaned_title = normalize_case_title(title)
    with connect(db_path) as conn:
        existing = conn.execute("SELECT id FROM cases WHERE id = ?", (case_id,)).fetchone()
        if existing is None:
            return False
        conn.execute("UPDATE cases SET title = ? WHERE id = ?", (cleaned_title, case_id))
    return True


def get_messages(case_id: int, db_path: Path | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, role, content_json, created_at, sequence_number
            FROM messages
            WHERE case_id = ?
            ORDER BY sequence_number ASC, id ASC
            """,
            (case_id,),
        ).fetchall()
    return [message_row_to_dict(row) for row in rows]


def delete_case(case_id: int, db_path: Path | None = None) -> bool:
    init_db(db_path)
    with connect(db_path) as conn:
        existing = conn.execute("SELECT id FROM cases WHERE id = ?", (case_id,)).fetchone()
        if existing is None:
            return False
        conn.execute("DELETE FROM messages WHERE case_id = ?", (case_id,))
        conn.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    return True


def delete_all_cases(db_path: Path | None = None) -> int:
    init_db(db_path)
    with connect(db_path) as conn:
        count = int(conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0])
        conn.execute("DELETE FROM messages")
        conn.execute("DELETE FROM cases")
    return count


def save_message(case_id: int, role: str, content: Any, db_path: Path | None = None) -> int:
    if role not in {"user", "assistant"}:
        raise ValueError("Message role must be user or assistant.")
    init_db(db_path)
    now = utc_timestamp()
    with connect(db_path) as conn:
        current = conn.execute(
            "SELECT COALESCE(MAX(sequence_number), 0) FROM messages WHERE case_id = ?",
            (case_id,),
        ).fetchone()[0]
        cursor = conn.execute(
            """
            INSERT INTO messages (case_id, role, content_json, created_at, sequence_number)
            VALUES (?, ?, ?, ?, ?)
            """,
            (case_id, role, json_dumps(sanitize_message_content(content)), now, int(current) + 1),
        )
        conn.execute("UPDATE cases SET updated_at = ? WHERE id = ?", (now, case_id))
        return int(cursor.lastrowid)


def update_case_metadata(
    case_id: int,
    primary_domain: str | None = None,
    conversation_state: dict[str, Any] | None = None,
    confirmed_document_context: dict[str, Any] | None = None,
    db_path: Path | None = None,
) -> None:
    init_db(db_path)
    now = utc_timestamp()
    with connect(db_path) as conn:
        conn.execute(
            """
            UPDATE cases
            SET updated_at = ?,
                primary_domain = COALESCE(?, primary_domain),
                conversation_state_json = COALESCE(?, conversation_state_json),
                confirmed_document_context_json = COALESCE(?, confirmed_document_context_json)
            WHERE id = ?
            """,
            (
                now,
                primary_domain,
                json_dumps(conversation_state) if conversation_state is not None else None,
                json_dumps(sanitize_value(confirmed_document_context)) if confirmed_document_context is not None else None,
                case_id,
            ),
        )


def should_create_case_for_response(question: str, response: dict[str, Any]) -> bool:
    if is_small_talk(question):
        return False
    routing = response.get("routing") or {}
    status = routing.get("status")
    if status == "out_of_scope":
        return False
    if status in {"classified", "unclear", "unsupported"}:
        return True
    if response.get("clarification") or response.get("answer"):
        return not response.get("technical_error")
    return False


def user_content_for_storage(message: str) -> dict[str, str]:
    return {"text": sanitize_text(message)}


def assistant_content_for_storage(response: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "answer",
        "sources",
        "confidence",
        "insufficient_context",
        "disclaimer",
        "clarification",
        "routing",
        "document_evidence_used",
        "confirmed_fact_context_id",
        "conversation_state_id",
        "conversation_state",
        "corpus_status",
        "limitations",
        "conversation",
        "technical_error",
    }
    return sanitize_value({key: value for key, value in response.items() if key in allowed})


def case_row_to_dict(row: sqlite3.Row, include_json: bool = True) -> dict[str, Any]:
    output = {
        "id": row["id"],
        "title": row["title"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "primary_domain": row["primary_domain"],
    }
    if include_json:
        output["conversation_state"] = json_loads(row["conversation_state_json"])
        output["confirmed_document_context"] = json_loads(row["confirmed_document_context_json"])
    return output


def message_row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    content = json_loads(row["content_json"])
    if row["role"] == "user" and isinstance(content, dict):
        content = content.get("text", "")
    return {
        "id": row["id"],
        "role": row["role"],
        "content": content,
        "created_at": row["created_at"],
        "sequence_number": row["sequence_number"],
    }


DOMAIN_FALLBACK_TITLE: dict[str, str] = {
    "consumer": "Consumer Legal Question",
    "cyber": "Cyber Legal Question",
    "tenancy": "Tenancy Legal Question",
    "constitutional_public_authority": "Public Authority Question",
}


def _title_from_message_words(message: str) -> str | None:
    """First several meaningful words of the (sanitized) message, title-cased -- e.g. "My
    landlord in Delhi cut off my electricity" -> "Landlord Delhi Cut Off Electricity". Returns
    None if the message has nothing usable (empty, or only short/stopword-length tokens)."""
    words = [word.title() for word in re.findall(r"[A-Za-z0-9]+", sanitize_text(message)) if len(word) > 2][:6]
    return " ".join(words) or None


def generate_case_title(message: str, primary_domain: str | None = None) -> str:
    """No LLM call is involved here -- title quality depends entirely on this deterministic
    logic, not on any live service being up. Fixed 2026-09-16: this used to fall back straight
    to a generic domain-name title (e.g. "Consumer Legal Question") whenever a message didn't
    match one of the ~7 hand-curated keyword patterns below, even though the word-extraction
    fallback (_title_from_message_words) almost always produces something more specific using
    the user's own words -- it was just never reached, because the domain-name checks ran first
    and returned before it got a chance. That's why some cases got a real, specific title and
    others didn't: it tracked which of a handful of keyword patterns happened to match, not
    message quality or a failing service. Priority now: curated keyword patterns (best quality,
    when they apply) -> word-extraction from the actual message (usually good, always available)
    -> generic domain-name (true last resort, only when the message has nothing usable at all,
    e.g. it's empty)."""
    text = sanitize_text(message).lower()
    if contains_any(text, ("instagram", "blocked", "never delivered", "not delivered")):
        return "Instagram Seller Non-Delivery" if "instagram" in text else "Seller Non-Delivery"
    if contains_any(text, ("defective", "refund", "replacement", "stopped working")):
        return "Defective Product Refund"
    if contains_any(text, ("electricity", "bijli", "supply")) and contains_any(text, ("landlord", "tenant", "rent")):
        return "Delhi Electricity Disconnection" if "delhi" in text else "Tenancy Electricity Dispute"
    if contains_any(text, ("security deposit", "deposit")):
        return "Security Deposit Dispute"
    if contains_any(text, ("rti", "reply", "response")):
        return "RTI No Response"
    if contains_any(text, ("identity", "password", "credentials", "account")):
        return "Cyber Identity Misuse"
    word_title = _title_from_message_words(message)
    if word_title:
        return word_title
    if primary_domain and primary_domain in DOMAIN_FALLBACK_TITLE:
        return DOMAIN_FALLBACK_TITLE[primary_domain]
    return "Legal Question"


def normalize_case_title(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", sanitize_text(title)).strip()
    if not cleaned:
        raise ValueError("A case title is required.")
    return cleaned[:MAX_CASE_TITLE_CHARS]


def sanitize_message_content(value: Any) -> Any:
    return sanitize_value(value)


def sanitize_value(value: Any) -> Any:
    if isinstance(value, str):
        return sanitize_text(value)
    if isinstance(value, list):
        return [sanitize_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): sanitize_value(item) for key, item in value.items()}
    return value


def luhn_valid(digits: str) -> bool:
    """Standard Luhn (mod 10) checksum. `digits` must be a string of only 0-9 characters."""
    total = 0
    for index, char in enumerate(reversed(digits)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


_CARD_NUMBER_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")


def _redact_card_number(match: re.Match) -> str:
    """Only redact a 13-19 digit run if it's also Luhn-valid.

    Fixed 2026-09-15: this previously redacted ANY 13-19 digit run unconditionally, with no
    check that it was even plausibly a card number -- an ordinary 13-digit epoch timestamp, a
    long order/reference number, or a phone number all matched and got permanently replaced with
    "[sensitive card number omitted]" at message-save time, with the original text unrecoverable
    (found in Phase 3 UI testing: "Reference: Phase3 debug 1789469159760" -> "Reference: Phase3
    debug [sensitive card number omitted]"). Luhn is the standard, well-understood way real card
    numbers are distinguished from arbitrary digit strings -- it's not a perfect filter (a
    Luhn-valid non-card 16-digit number could still false-positive; see
    tests/test_case_store.py's adversarial cases for what this does and doesn't catch), but it
    narrows the false-positive rate substantially without disabling the actual protection: known
    test card numbers (e.g. 4111111111111111) are still redacted.
    """
    digits_only = re.sub(r"[ -]", "", match.group(0))
    if not (13 <= len(digits_only) <= 19) or not luhn_valid(digits_only):
        return match.group(0)
    return "[sensitive card number omitted]"


def sanitize_text(text: str) -> str:
    cleaned = str(text or "")
    patterns = [
        (r"\b(?:otp|one time password)\s*(?:is|:)?\s*\d{4,8}\b", "OTP [sensitive information omitted]"),
        (r"\b(?:pin|password|cvv)\s*(?:is|:)?\s*\S+\b", "[sensitive information omitted]"),
        (r"\b\d{12}\b", "[sensitive identifier omitted]"),
        (r"(api[_ -]?key\s*(?:is|:)?\s*)\S+", r"\1[sensitive information omitted]"),
    ]
    for pattern, replacement in patterns:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.I)
    cleaned = _CARD_NUMBER_PATTERN.sub(_redact_card_number, cleaned)
    return cleaned


def is_small_talk(message: str) -> bool:
    text = re.sub(r"[^a-z0-9\s]+", " ", str(message or "").lower())
    text = re.sub(r"\s+", " ", text).strip()
    return text in {"thanks", "thank you", "thankyou", "ok", "okay", "got it", "understood", "hello", "hi", "hey"}


def contains_any(text: str, cues: tuple[str, ...]) -> bool:
    return any(cue in text for cue in cues)


def json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def json_loads(value: str | None) -> Any:
    if not value:
        return None
    return json.loads(value)


def utc_timestamp() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
