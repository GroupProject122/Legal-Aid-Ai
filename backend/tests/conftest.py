from __future__ import annotations

import hashlib
import sqlite3
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import case_store
import conversation_state
import document_store
import turn_memory

# Resolved once, at import -- before any fixture redirects case_store.DB_PATH -- so the guard below
# always knows where the developer's real database is.
REAL_DB_PATH = Path(case_store.DB_PATH).resolve()
REAL_UPLOAD_DIR = Path(document_store.UPLOAD_DIR).resolve()


@pytest.fixture(scope="session", autouse=True)
def refuse_real_database():
    """Any attempt to open the real backend/legal_aid.db during the test run raises instead.

    Added 2026-10-28: tests calling /api/ask without redirecting case_store.DB_PATH used to write
    real cases -- 11 per full run, 330 in one day -- into the developer's database. A redirect
    alone (isolated_app_storage below) can be bypassed by code that captured the path earlier;
    this makes the mistake fail loudly instead of silently writing. It checks the path being
    opened rather than whether the file changed, so a dev server writing to the same database
    during a test run cannot trigger it."""
    real_connect = sqlite3.connect

    def guarded_connect(database, *args, **kwargs):
        if str(database) != ":memory:" and Path(database).resolve() == REAL_DB_PATH:
            raise RuntimeError(
                f"A test tried to open the real database {REAL_DB_PATH}. Tests must use a temporary "
                "database (tests/conftest.py's isolated_app_storage sets one up for every test)."
            )
        return real_connect(database, *args, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(sqlite3, "connect", guarded_connect)
        yield


@pytest.fixture(autouse=True)
def isolated_app_storage(tmp_path, monkeypatch):
    """Every test gets its own empty app database (cases, messages, documents, accounts and
    sessions all live in case_store.DB_PATH) and its own upload folder. Tests that set their own
    temp paths still can; they simply override these."""
    monkeypatch.setattr(case_store, "DB_PATH", tmp_path / "legal_aid.db")
    monkeypatch.setattr(document_store, "UPLOAD_DIR", tmp_path / "user_uploads")


def fake_embed(texts: list[str]) -> np.ndarray:
    """Deterministic bag-of-words vectors: identical texts score 1.0, texts sharing words score
    in between. Stands in for the sentence-transformer so tests never load the model."""
    vectors = np.zeros((len(texts), 64), dtype="float32")
    for row, text in enumerate(texts):
        for word in text.lower().split():
            vectors[row, int(hashlib.md5(word.encode()).hexdigest(), 16) % 64] += 1.0
        norm = np.linalg.norm(vectors[row])
        if norm:
            vectors[row] /= norm
    return vectors


@pytest.fixture(autouse=True)
def isolated_turn_memory(tmp_path, monkeypatch):
    """Every test gets its own empty correction memory and a fake embedder, and the turn
    classifier starts with Gemini off (a test that needs it sets GEMINI_API_KEY and mocks the
    client). Without this, a real backend/.env key would make classify_turn call Gemini and
    write to the real legal_aid.db during tests."""
    monkeypatch.setattr(turn_memory, "DB_PATH", tmp_path / "turn_memory_test.db")
    monkeypatch.setattr(turn_memory, "ENABLED", True)
    turn_memory.set_embedder(fake_embed)
    monkeypatch.setattr(conversation_state, "GEMINI_API_KEY", "")
    yield
    turn_memory.set_embedder(None)


def signed_in_client(email: str = "user@example.com", password: str = "correct horse battery"):
    """A TestClient signed in as a freshly created account -> (client, user_id). The session
    cookie is kept by the client, so every later request is made as this user. The caller must
    already have pointed case_store.DB_PATH at a temp database."""
    from fastapi.testclient import TestClient

    import main

    client = TestClient(main.app)
    response = client.post("/api/auth/signup", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return client, response.json()["user"]["id"]


@pytest.fixture(autouse=True)
def reset_login_lockouts():
    import auth

    auth._failed_logins.clear()
    yield
    auth._failed_logins.clear()
