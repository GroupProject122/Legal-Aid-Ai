"""One-time (but safely re-runnable) backfill: regenerate titles for saved cases currently
carrying a generic domain-name fallback title ("Consumer Legal Question", "Cyber Legal
Question", "Tenancy Legal Question", "Public Authority Question", "Legal Question"), using the
fixed generate_case_title() logic (2026-09-16 -- see case_store.py's docstring on that function
for what changed and why some cases ended up generic in the first place).

Regenerates each case's title from its own first user message (the same input title generation
originally used), via case_store.generate_case_title(). Only the `title` column is touched, via
case_store.set_case_title_only() -- never message content, routing state, or updated_at (so
backfilled cases do not jump to the top of the newest-first My Cases list).

Note on input fidelity: titles were originally generated from the RAW question text (before
storage-time sanitization). This backfill only has access to the STORED (already sanitized)
first message, since the raw original was never persisted. In the ordinary case this makes no
difference -- generate_case_title()'s keyword matching operates on ordinary words, not the kind
of content sanitize_text() redacts -- but is worth knowing if a backfilled title ever looks
slightly different from what live case creation would produce for the same raw input today.

Safe to re-run: a case is only counted "updated" if regeneration produces something other than
its current (generic) title; cases where regeneration still lands on a generic title (e.g. an
empty or near-empty first message) are left untouched and reported separately, not silently
skipped.

Usage:
    python backfill_case_titles.py                  # runs for real, writes the log
    python backfill_case_titles.py --dry-run         # preview only, no writes
    python backfill_case_titles.py --log-output PATH # override the log file location
"""
from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import case_store
from config import BASE_DIR

logger = logging.getLogger("legal_aid_ai.backfill_case_titles")

GENERIC_FALLBACK_TITLES: frozenset[str] = frozenset(case_store.DOMAIN_FALLBACK_TITLE.values()) | {"Legal Question"}
DEFAULT_LOG_PATH = BASE_DIR / "eval" / "case_title_backfill_log.json"


def find_generic_titled_case_ids(db_path: Path | None = None) -> list[int]:
    case_store.init_db(db_path)
    with case_store.connect(db_path) as conn:
        placeholders = ",".join("?" for _ in GENERIC_FALLBACK_TITLES)
        rows = conn.execute(
            f"SELECT id FROM cases WHERE title IN ({placeholders}) ORDER BY id",  # noqa: S608 -- static placeholders only
            tuple(GENERIC_FALLBACK_TITLES),
        ).fetchall()
    return [row["id"] for row in rows]


def first_user_message_text(case_id: int, db_path: Path | None = None) -> str | None:
    messages = case_store.get_messages(case_id, db_path)
    for message in messages:
        if message["role"] == "user" and isinstance(message["content"], str):
            return message["content"]
    return None


def backfill_case_titles(db_path: Path | None = None, dry_run: bool = False) -> dict[str, Any]:
    candidate_ids = find_generic_titled_case_ids(db_path)
    changes: list[dict[str, Any]] = []
    unchanged: list[dict[str, Any]] = []

    for case_id in candidate_ids:
        case = case_store.get_case(case_id, db_path)
        if case is None:
            continue  # deleted between listing and processing -- nothing to backfill
        message_text = first_user_message_text(case_id, db_path)
        if not message_text:
            unchanged.append({"case_id": case_id, "reason": "no usable first user message"})
            continue
        new_title = case_store.generate_case_title(message_text, case["primary_domain"])
        if new_title == case["title"]:
            unchanged.append({"case_id": case_id, "reason": "regeneration still produced a generic title"})
            continue
        changes.append(
            {
                "case_id": case_id,
                "primary_domain": case["primary_domain"],
                "old_title": case["title"],
                "new_title": new_title,
            }
        )
        if not dry_run:
            case_store.set_case_title_only(case_id, new_title, db_path)

    return {
        "dry_run": dry_run,
        "candidate_count": len(candidate_ids),
        "updated_count": len(changes),
        "unchanged_count": len(unchanged),
        "changes": changes,
        "unchanged": unchanged,
    }


def main(argv: list[str] | None = None) -> dict[str, Any]:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without writing them.")
    parser.add_argument("--log-output", type=Path, default=DEFAULT_LOG_PATH)
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    result = backfill_case_titles(dry_run=args.dry_run)

    for change in result["changes"]:
        logger.info(
            "case_id=%s domain=%s: %r -> %r",
            change["case_id"],
            change["primary_domain"],
            change["old_title"],
            change["new_title"],
        )
    for item in result["unchanged"]:
        logger.info("case_id=%s left unchanged: %s", item["case_id"], item["reason"])

    args.log_output.parent.mkdir(parents=True, exist_ok=True)
    args.log_output.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    logger.info(
        "%sBackfill complete: %s/%s candidate cases updated, %s left unchanged. Log written to %s",
        "[DRY RUN] " if args.dry_run else "",
        result["updated_count"],
        result["candidate_count"],
        result["unchanged_count"],
        args.log_output,
    )
    return result


if __name__ == "__main__":
    main()
