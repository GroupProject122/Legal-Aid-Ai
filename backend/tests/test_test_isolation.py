"""Tests must never write to the developer's real backend/legal_aid.db (see tests/conftest.py).
Before 2026-10-28, tests calling /api/ask without redirecting case_store.DB_PATH wrote 11 real
cases per full run into it."""
from __future__ import annotations

import sqlite3

import pytest
from conftest import REAL_DB_PATH

import case_store
import document_store


def test_code_that_sets_no_path_writes_to_a_temp_database():
    # Exactly what the leaking tests did: create a case without pointing DB_PATH anywhere.
    case_id = case_store.create_case("landlord cut electricity", "tenancy")
    assert case_store.get_case(case_id)["title"]
    assert case_store.DB_PATH.resolve() != REAL_DB_PATH
    assert REAL_DB_PATH.parent not in case_store.DB_PATH.resolve().parents


def test_uploads_go_to_a_temp_folder():
    assert REAL_DB_PATH.parent / "user_uploads" != document_store.UPLOAD_DIR.resolve()


def test_opening_the_real_database_fails_loudly():
    with pytest.raises(RuntimeError, match="real database"):
        sqlite3.connect(REAL_DB_PATH)
    with pytest.raises(RuntimeError, match="real database"):
        case_store.connect(REAL_DB_PATH)
