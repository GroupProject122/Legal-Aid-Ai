from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import backfill_case_titles
import case_store


def _make_generic_case(db, message: str, domain: str, title: str) -> int:
    """Create a case the normal way, then force its title back to a generic fallback -- mimics
    a case created before the title-generation fix (case_store.py, 2026-09-16)."""
    case_id = case_store.create_case(message, domain, db_path=db)
    case_store.save_message(case_id, "user", case_store.user_content_for_storage(message), db)
    case_store.set_case_title_only(case_id, title, db)
    return case_id


def test_find_generic_titled_case_ids_only_matches_generic_titles(tmp_path):
    db = tmp_path / "legal_aid.db"
    generic_id = _make_generic_case(db, "the building society is refusing my renovation", "tenancy", "Tenancy Legal Question")
    specific_id = case_store.create_case("defective phone refund refused", "consumer", db_path=db)

    ids = backfill_case_titles.find_generic_titled_case_ids(db)

    assert generic_id in ids
    assert specific_id not in ids


def test_backfill_updates_title_only_not_updated_at_or_messages(tmp_path):
    db = tmp_path / "legal_aid.db"
    message = "the building society is refusing to let me renovate my balcony"
    case_id = _make_generic_case(db, message, "tenancy", "Tenancy Legal Question")
    before = case_store.get_case(case_id, db)
    messages_before = case_store.get_messages(case_id, db)

    result = backfill_case_titles.backfill_case_titles(db)

    after = case_store.get_case(case_id, db)
    messages_after = case_store.get_messages(case_id, db)
    assert result["updated_count"] == 1
    assert result["changes"][0]["case_id"] == case_id
    assert result["changes"][0]["old_title"] == "Tenancy Legal Question"
    assert result["changes"][0]["new_title"] == after["title"]
    assert after["title"] != before["title"]
    assert after["title"] != "Tenancy Legal Question"
    # Nothing else changed.
    assert after["updated_at"] == before["updated_at"]
    assert after["primary_domain"] == before["primary_domain"]
    assert messages_after == messages_before


def test_backfill_dry_run_previews_without_writing(tmp_path):
    db = tmp_path / "legal_aid.db"
    case_id = _make_generic_case(db, "the building society is refusing my renovation", "tenancy", "Tenancy Legal Question")

    result = backfill_case_titles.backfill_case_titles(db, dry_run=True)

    assert result["dry_run"] is True
    assert result["updated_count"] == 1
    # Title on disk is untouched by a dry run.
    assert case_store.get_case(case_id, db)["title"] == "Tenancy Legal Question"


def test_backfill_leaves_case_unchanged_when_regeneration_is_still_generic(tmp_path):
    db = tmp_path / "legal_aid.db"
    case_id = case_store.create_case("hi", "tenancy", db_path=db)
    case_store.save_message(case_id, "user", case_store.user_content_for_storage(""), db)
    case_store.set_case_title_only(case_id, "Tenancy Legal Question", db)

    result = backfill_case_titles.backfill_case_titles(db)

    assert result["updated_count"] == 0
    assert any(item["case_id"] == case_id for item in result["unchanged"])
    assert case_store.get_case(case_id, db)["title"] == "Tenancy Legal Question"


def test_backfill_is_idempotent(tmp_path):
    db = tmp_path / "legal_aid.db"
    _make_generic_case(db, "the building society is refusing my renovation", "tenancy", "Tenancy Legal Question")

    first = backfill_case_titles.backfill_case_titles(db)
    second = backfill_case_titles.backfill_case_titles(db)

    assert first["updated_count"] == 1
    assert second["updated_count"] == 0
    assert backfill_case_titles.find_generic_titled_case_ids(db) == []
