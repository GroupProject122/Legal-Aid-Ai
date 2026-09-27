from __future__ import annotations

import json
import re
import secrets
import sqlite3
from pathlib import Path
from typing import Any

import case_store
import document_extractor
import document_relevance
from config import BASE_DIR

UPLOAD_DIR = BASE_DIR / "user_uploads"


class DocumentStoreError(ValueError):
    pass


def init_db(db_path: Path | None = None) -> None:
    case_store.init_db(db_path)
    with case_store.connect(db_path) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                original_filename TEXT NOT NULL,
                display_filename TEXT NOT NULL,
                file_type TEXT NOT NULL,
                mime_type TEXT,
                size_bytes INTEGER NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                storage_path TEXT NOT NULL,
                extraction_status TEXT,
                extracted_text_json TEXT,
                confirmed_fact_context_json TEXT,
                case_id INTEGER,
                FOREIGN KEY(case_id) REFERENCES cases(id) ON DELETE SET NULL
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_updated ON documents(updated_at DESC)")
        ensure_document_columns(
            conn,
            {
                "summary_text": "TEXT",
                "summary_status": "TEXT",
                "summary_generated_at": "TEXT",
                "summary_model": "TEXT",
                # Owner, added when accounts were introduced; pre-existing rows are NULL until
                # auth.claim_unowned_data() assigns them to the admin account.
                "user_id": "INTEGER REFERENCES users(id)",
            },
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_documents_user ON documents(user_id, updated_at DESC)")
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def create_uploaded_document(
    *,
    original_filename: str,
    content: bytes,
    mime_type: str | None,
    extraction: dict[str, Any],
    case_id: int | None = None,
    db_path: Path | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    init_db(db_path)
    display_filename = safe_display_filename(original_filename)
    file_type = extraction.get("file_type") or document_extractor.detect_file_type(display_filename, content, mime_type)
    if file_type not in {"pdf", "docx", "txt"}:
        raise DocumentStoreError("Only PDF, DOCX, and TXT documents can be stored.")
    now = case_store.utc_timestamp()
    with case_store.connect(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO documents (
                original_filename, display_filename, file_type, mime_type, size_bytes,
                created_at, updated_at, storage_path, extraction_status,
                extracted_text_json, confirmed_fact_context_json, case_id, user_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                display_filename,
                display_filename,
                file_type,
                mime_type,
                len(content),
                now,
                now,
                "",
                extraction.get("status"),
                json_dumps(extraction_payload_for_storage(extraction)),
                None,
                case_id,
                user_id,
            ),
        )
        document_id = int(cursor.lastrowid)
        storage_path = storage_path_for(document_id, file_type)
        storage_path.write_bytes(content)
        conn.execute("UPDATE documents SET storage_path = ? WHERE id = ?", (str(storage_path), document_id))
    return require_document(document_id, db_path)


def list_documents(
    db_path: Path | None = None,
    limit: int | None = None,
    offset: int = 0,
    search: str | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    """Same limit/offset/{items, total, limit, offset, has_more} pagination convention as
    case_store.list_cases() -- reused deliberately rather than inventing a second pattern.
    `search` matches display_filename, case-insensitively. `limit=None` keeps the old
    fetch-everything behavior for callers that want it (e.g. tests)."""
    init_db(db_path)
    where_clauses: list[str] = []
    params: dict[str, Any] = {}
    if search and search.strip():
        where_clauses.append("display_filename LIKE :search_pattern ESCAPE '\\'")
        escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params["search_pattern"] = f"%{escaped}%"
    if user_id is not None:
        where_clauses.append("user_id = :user_id")
        params["user_id"] = user_id
    where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

    with case_store.connect(db_path) as conn:
        total = int(conn.execute(f"SELECT COUNT(*) FROM documents {where_sql}", params).fetchone()[0])  # noqa: S608
        query = f"""
            SELECT id, display_filename, file_type, mime_type, size_bytes, created_at, updated_at,
                   extraction_status, summary_status, summary_generated_at,
                   -- For the category colour: the area of law of the case this document was used
                   -- in (most recently updated case wins), else material to guess it from.
                   COALESCE(
                       (SELECT cases.primary_domain FROM case_documents
                        JOIN cases ON cases.id = case_documents.case_id
                        WHERE case_documents.document_id = documents.id AND cases.primary_domain IS NOT NULL
                        ORDER BY cases.updated_at DESC LIMIT 1),
                       (SELECT cases.primary_domain FROM cases WHERE cases.id = documents.case_id)
                   ) AS case_domain,
                   COALESCE(
                       json_extract(confirmed_fact_context_json, '$.confirmed_facts.document_type'),
                       json_extract(confirmed_fact_context_json, '$.document_type')
                   ) AS confirmed_document_type,
                   substr(json_extract(extracted_text_json, '$.text'), 1, 4000) AS text_sample
            FROM documents
            {where_sql}
            ORDER BY updated_at DESC, id DESC
        """  # noqa: S608
        if limit is not None:
            query += " LIMIT :limit OFFSET :offset"
            params = {**params, "limit": limit, "offset": offset}
        rows = conn.execute(query, params).fetchall()

    items = [with_category(row) for row in rows]
    linked_cases = cases_for_documents([item["id"] for item in items], db_path)
    for item in items:
        item["cases"] = linked_cases.get(item["id"], [])
    return {
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset,
        "has_more": limit is not None and offset + len(items) < total,
    }


CATEGORY_DOMAINS = {"consumer", "cyber", "tenancy", "constitutional_public_authority"}


def with_category(row: sqlite3.Row) -> dict[str, Any]:
    """List metadata plus `category` / `category_source`, so the Documents page can colour each
    document like My Cases colours each case. "case": the document was used in a case, and takes
    that case's area of law. "inferred": not used in any case yet, so the area is guessed from
    the document's name and text (document_relevance.document_category). None: neither says."""
    data = metadata_from_row(row)
    category, source = None, None
    if row["case_domain"] in CATEGORY_DOMAINS:
        category, source = row["case_domain"], "case"
    else:
        inferred = document_relevance.document_category(
            {
                "filename": row["display_filename"],
                "text_sample": row["text_sample"] or "",
                "document_type": row["confirmed_document_type"],
            }
        )
        if inferred:
            category, source = inferred, "inferred"
    data["category"] = category
    data["category_source"] = source
    return data


def get_document(document_id: int, db_path: Path | None = None, user_id: int | None = None) -> dict[str, Any] | None:
    """`user_id` restricts the lookup to that user's documents (another user's document is
    reported as not found); None = no owner filter, for maintenance code and store-level tests."""
    init_db(db_path)
    owner_sql, owner_params = case_store.owner_clause(user_id)
    with case_store.connect(db_path) as conn:
        row = conn.execute(f"SELECT * FROM documents WHERE id = ?{owner_sql}", (document_id, *owner_params)).fetchone()  # noqa: S608
    return row_to_document(row) if row else None


def require_document(document_id: int, db_path: Path | None = None, user_id: int | None = None) -> dict[str, Any]:
    document = get_document(document_id, db_path, user_id)
    if document is None:
        raise DocumentStoreError("Document not found.")
    return document


def rename_document(
    document_id: int,
    filename: str,
    db_path: Path | None = None,
    user_id: int | None = None,
) -> dict[str, Any]:
    document = require_document(document_id, db_path, user_id)
    new_name = safe_display_filename(filename)
    if document_extractor.extension_of(new_name) != f".{document['file_type']}":
        raise DocumentStoreError(f"Filename must keep the .{document['file_type']} extension.")
    now = case_store.utc_timestamp()
    with case_store.connect(db_path) as conn:
        conn.execute(
            "UPDATE documents SET display_filename = ?, updated_at = ? WHERE id = ?",
            (new_name, now, document_id),
        )
    return require_document(document_id, db_path)


def delete_document(document_id: int, db_path: Path | None = None, user_id: int | None = None) -> None:
    document = require_document(document_id, db_path, user_id)
    storage_path = safe_storage_path(document["storage_path"])
    context_id = (document.get("confirmed_fact_context") or {}).get("confirmed_fact_context_id")
    with case_store.connect(db_path) as conn:
        conn.execute("DELETE FROM case_documents WHERE document_id = ?", (document_id,))
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    if context_id:
        import document_facts

        document_facts.detach_confirmed_context(context_id)
    if storage_path.exists():
        storage_path.unlink()


def delete_all_documents(db_path: Path | None = None, user_id: int | None = None) -> int:
    """Mirrors case_store.delete_all_cases()'s bulk-delete pattern. Deliberately reuses
    delete_document() per row (rather than a single blind DELETE FROM documents) so every row's
    side effects -- detaching its confirmed_fact_context, unlinking its stored file from disk --
    still happen; a bare bulk DELETE would silently orphan every uploaded file on disk. Only the
    given user's documents when user_id is passed, which the API always does."""
    init_db(db_path)
    owner_sql, owner_params = case_store.owner_clause(user_id)
    with case_store.connect(db_path) as conn:
        ids = [row["id"] for row in conn.execute(f"SELECT id FROM documents WHERE 1 = 1{owner_sql}", owner_params).fetchall()]  # noqa: S608
    for document_id in ids:
        delete_document(document_id, db_path)
    return len(ids)


def link_document_to_case(
    case_id: int,
    document_id: int,
    db_path: Path | None = None,
    message_sequence: int | None = None,
) -> None:
    """Records that a document belongs to a case, and where in it: `message_sequence` is the
    user question the document came in with. A document uploaded inside an open chat comes
    before the question it is for, so by default that is the case's next message. Idempotent:
    the first link (and its position) is kept. Callers check that the case and the document
    have the same owner (main.py only passes ids already looked up for the user)."""
    init_db(db_path)
    if message_sequence is None:
        message_sequence = case_store.next_message_sequence(case_id, db_path)
    with case_store.connect(db_path) as conn:
        conn.execute(
            "INSERT OR IGNORE INTO case_documents (case_id, document_id, linked_at, message_sequence) VALUES (?, ?, ?, ?)",
            (case_id, document_id, case_store.utc_timestamp(), message_sequence),
        )


def cases_for_documents(document_ids: list[int], db_path: Path | None = None) -> dict[int, list[dict[str, Any]]]:
    """For each document id: the cases it was used in (most recently updated first), with the
    question it came in with, for the Documents page's "go to case" button."""
    if not document_ids:
        return {}
    placeholders = ",".join("?" for _ in document_ids)
    with case_store.connect(db_path) as conn:
        rows = conn.execute(
            f"""
            SELECT case_documents.document_id, cases.id AS case_id, cases.title, cases.primary_domain,
                   -- Links made before message_sequence existed: the last question asked before
                   -- the link, which is when those links were made (just after the turn was saved).
                   COALESCE(
                       case_documents.message_sequence,
                       (SELECT MAX(messages.sequence_number) FROM messages
                        WHERE messages.case_id = cases.id AND messages.role = 'user'
                          AND messages.created_at <= case_documents.linked_at),
                       (SELECT MIN(messages.sequence_number) FROM messages
                        WHERE messages.case_id = cases.id AND messages.role = 'user')
                   ) AS message_sequence,
                   cases.updated_at
            FROM case_documents JOIN cases ON cases.id = case_documents.case_id
            WHERE case_documents.document_id IN ({placeholders})
            UNION
            SELECT documents.id, cases.id, cases.title, cases.primary_domain, NULL, cases.updated_at
            FROM documents JOIN cases ON cases.id = documents.case_id
            WHERE documents.id IN ({placeholders})
              AND NOT EXISTS (SELECT 1 FROM case_documents
                              WHERE case_documents.document_id = documents.id AND case_documents.case_id = cases.id)
            """,  # noqa: S608 -- placeholders only
            [*document_ids, *document_ids],
        ).fetchall()
    output: dict[int, list[dict[str, Any]]] = {}
    for row in sorted(rows, key=lambda item: item["updated_at"] or "", reverse=True):
        output.setdefault(row["document_id"], []).append(
            {
                "case_id": row["case_id"],
                "title": row["title"],
                "primary_domain": row["primary_domain"],
                "message_sequence": row["message_sequence"],
            }
        )
    return output


def documents_with_confirmed_context(context_id: str, user_id: int, db_path: Path | None = None) -> list[int]:
    """Ids of the user's documents whose confirmed facts have this confirmed_fact_context_id --
    i.e. the document(s) behind facts attached to a chat."""
    if not context_id:
        return []
    init_db(db_path)
    with case_store.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id FROM documents
            WHERE user_id = ?
              AND confirmed_fact_context_json IS NOT NULL
              AND json_extract(confirmed_fact_context_json, '$.confirmed_fact_context_id') = ?
            """,
            (user_id, context_id),
        ).fetchall()
    return [row["id"] for row in rows]


def list_documents_for_relevance(user_id: int, db_path: Path | None = None) -> list[dict[str, Any]]:
    """Every document of the user with the bits document_relevance needs (metadata, confirmed
    document type, the start of the extracted text) and the ids of the cases it is linked to."""
    init_db(db_path)
    with case_store.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT * FROM documents WHERE user_id = ? ORDER BY updated_at DESC, id DESC",
            (user_id,),
        ).fetchall()
        links = conn.execute(
            """
            SELECT case_documents.document_id, case_documents.case_id FROM case_documents
            JOIN documents ON documents.id = case_documents.document_id
            WHERE documents.user_id = ?
            """,
            (user_id,),
        ).fetchall()
    case_ids: dict[int, set[int]] = {}
    for link in links:
        case_ids.setdefault(link["document_id"], set()).add(link["case_id"])
    output = []
    for row in rows:
        extraction = json_loads(row["extracted_text_json"]) or {}
        confirmed = json_loads(row["confirmed_fact_context_json"]) or {}
        data = metadata_from_row(row)
        data["document_type"] = (confirmed.get("confirmed_facts") or {}).get("document_type") or confirmed.get("document_type")
        data["text_sample"] = str(extraction.get("text") or "")[:4000]
        data["case_ids"] = case_ids.get(row["id"], set())
        output.append(data)
    return output


def update_confirmed_fact_context(
    document_id: int,
    confirmed_context: dict[str, Any],
    db_path: Path | None = None,
    user_id: int | None = None,
) -> None:
    require_document(document_id, db_path, user_id)
    now = case_store.utc_timestamp()
    with case_store.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE documents
            SET confirmed_fact_context_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (json_dumps(case_store.sanitize_value(confirmed_context)), now, document_id),
        )


def update_summary(
    document_id: int,
    *,
    summary_text: str | None,
    summary_status: str,
    summary_model: str | None = None,
    db_path: Path | None = None,
) -> dict[str, Any]:
    require_document(document_id, db_path)
    now = case_store.utc_timestamp()
    with case_store.connect(db_path) as conn:
        conn.execute(
            """
            UPDATE documents
            SET summary_text = ?, summary_status = ?, summary_generated_at = ?,
                summary_model = ?, updated_at = ?
            WHERE id = ?
            """,
            (summary_text, summary_status, now if summary_text else None, summary_model, now, document_id),
        )
    return require_document(document_id, db_path)


def ensure_document_columns(conn: sqlite3.Connection, columns: dict[str, str]) -> None:
    existing = {row["name"] for row in conn.execute("PRAGMA table_info(documents)").fetchall()}
    for name, definition in columns.items():
        if name not in existing:
            conn.execute(f"ALTER TABLE documents ADD COLUMN {name} {definition}")


def safe_storage_path(value: str) -> Path:
    path = Path(value)
    upload_root = UPLOAD_DIR.resolve()
    resolved = path.resolve()
    if upload_root not in resolved.parents:
        raise DocumentStoreError("Stored document path is invalid.")
    return resolved


def storage_path_for(document_id: int, file_type: str) -> Path:
    suffix = secrets.token_hex(4)
    return UPLOAD_DIR / f"doc_{document_id}_{suffix}.{file_type}"


def safe_display_filename(filename: str) -> str:
    name = document_extractor.safe_filename(filename)
    name = re.sub(r"[\x00-\x1f]+", "", name).strip()
    name = re.sub(r"\s+", " ", name)
    name = re.sub(r"[^A-Za-z0-9 ._()\\-]", "_", name)
    if not name or name in {".", ".."}:
        raise DocumentStoreError("A valid filename is required.")
    extension = document_extractor.extension_of(name)
    if extension not in document_extractor.SUPPORTED_EXTENSIONS:
        raise DocumentStoreError("Only PDF, DOCX, and TXT filenames are supported.")
    return name[:160]


def extraction_payload_for_storage(extraction: dict[str, Any]) -> dict[str, Any]:
    return case_store.sanitize_value(
        {
            "status": extraction.get("status"),
            "filename": extraction.get("filename"),
            "file_type": extraction.get("file_type"),
            "size_bytes": extraction.get("size_bytes"),
            "page_count": extraction.get("page_count"),
            "character_count": extraction.get("character_count"),
            "text": extraction.get("text", ""),
            "pages": extraction.get("pages", []),
            "warnings": extraction.get("warnings", []),
            "processing_time_ms": extraction.get("processing_time_ms"),
        }
    )


def metadata_from_row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "filename": row["display_filename"],
        "file_type": row["file_type"],
        "mime_type": row["mime_type"],
        "size_bytes": row["size_bytes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
            "extraction_status": row["extraction_status"],
            "summary_status": row["summary_status"] if "summary_status" in row.keys() else None,
            "summary_generated_at": row["summary_generated_at"] if "summary_generated_at" in row.keys() else None,
        }


def row_to_document(row: sqlite3.Row) -> dict[str, Any]:
    data = metadata_from_row(row)
    data.update(
        {
            "original_filename": row["original_filename"],
            "storage_path": row["storage_path"],
            "extraction": json_loads(row["extracted_text_json"]) or {},
            "confirmed_fact_context": json_loads(row["confirmed_fact_context_json"]),
            "case_id": row["case_id"],
            "summary_text": row["summary_text"] if "summary_text" in row.keys() else None,
            "summary_status": row["summary_status"] if "summary_status" in row.keys() else None,
            "summary_generated_at": row["summary_generated_at"] if "summary_generated_at" in row.keys() else None,
            "summary_model": row["summary_model"] if "summary_model" in row.keys() else None,
        }
    )
    return data


def json_dumps(value: Any) -> str | None:
    if value is None:
        return None
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def json_loads(value: str | None) -> Any:
    if not value:
        return None
    return json.loads(value)
