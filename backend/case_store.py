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


def list_cases(db_path: Path | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    with connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, title, created_at, updated_at, primary_domain
            FROM cases
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()
    return [case_row_to_dict(row, include_json=False) for row in rows]


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


def generate_case_title(message: str, primary_domain: str | None = None) -> str:
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
    if primary_domain == "consumer":
        return "Consumer Legal Question"
    if primary_domain == "cyber":
        return "Cyber Legal Question"
    if primary_domain == "tenancy":
        return "Tenancy Legal Question"
    if primary_domain == "constitutional_public_authority":
        return "Public Authority Question"
    words = [word.title() for word in re.findall(r"[A-Za-z0-9]+", sanitize_text(message)) if len(word) > 2][:6]
    return " ".join(words) or "Legal Question"


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


def sanitize_text(text: str) -> str:
    cleaned = str(text or "")
    patterns = [
        (r"\b(?:otp|one time password)\s*(?:is|:)?\s*\d{4,8}\b", "OTP [sensitive information omitted]"),
        (r"\b(?:pin|password|cvv)\s*(?:is|:)?\s*\S+\b", "[sensitive information omitted]"),
        (r"\b\d{12}\b", "[sensitive identifier omitted]"),
        (r"\b(?:\d[ -]?){13,19}\b", "[sensitive card number omitted]"),
        (r"(api[_ -]?key\s*(?:is|:)?\s*)\S+", r"\1[sensitive information omitted]"),
    ]
    for pattern, replacement in patterns:
        cleaned = re.sub(pattern, replacement, cleaned, flags=re.I)
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
