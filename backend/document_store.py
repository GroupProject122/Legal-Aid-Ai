from __future__ import annotations

import json
import re
import secrets
import sqlite3
from pathlib import Path
from typing import Any

import case_store
import document_extractor
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
            },
        )
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def create_uploaded_document(
    *,
    original_filename: str,
    content: bytes,
    mime_type: str | None,
    extraction: dict[str, Any],
    case_id: int | None = None,
    db_path: Path | None = None,
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
                extracted_text_json, confirmed_fact_context_json, case_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )
        document_id = int(cursor.lastrowid)
        storage_path = storage_path_for(document_id, file_type)
        storage_path.write_bytes(content)
        conn.execute("UPDATE documents SET storage_path = ? WHERE id = ?", (str(storage_path), document_id))
    return require_document(document_id, db_path)


def list_documents(db_path: Path | None = None) -> list[dict[str, Any]]:
    init_db(db_path)
    with case_store.connect(db_path) as conn:
        rows = conn.execute(
            """
            SELECT id, display_filename, file_type, mime_type, size_bytes, created_at, updated_at,
                   extraction_status, summary_status, summary_generated_at
            FROM documents
            ORDER BY updated_at DESC, id DESC
            """
        ).fetchall()
    return [metadata_from_row(row) for row in rows]


def get_document(document_id: int, db_path: Path | None = None) -> dict[str, Any] | None:
    init_db(db_path)
    with case_store.connect(db_path) as conn:
        row = conn.execute("SELECT * FROM documents WHERE id = ?", (document_id,)).fetchone()
    return row_to_document(row) if row else None


def require_document(document_id: int, db_path: Path | None = None) -> dict[str, Any]:
    document = get_document(document_id, db_path)
    if document is None:
        raise DocumentStoreError("Document not found.")
    return document


def rename_document(document_id: int, filename: str, db_path: Path | None = None) -> dict[str, Any]:
    document = require_document(document_id, db_path)
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


def delete_document(document_id: int, db_path: Path | None = None) -> None:
    document = require_document(document_id, db_path)
    storage_path = safe_storage_path(document["storage_path"])
    context_id = (document.get("confirmed_fact_context") or {}).get("confirmed_fact_context_id")
    with case_store.connect(db_path) as conn:
        conn.execute("DELETE FROM documents WHERE id = ?", (document_id,))
    if context_id:
        import document_facts

        document_facts.detach_confirmed_context(context_id)
    if storage_path.exists():
        storage_path.unlink()


def update_confirmed_fact_context(
    document_id: int,
    confirmed_context: dict[str, Any],
    db_path: Path | None = None,
) -> None:
    require_document(document_id, db_path)
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
