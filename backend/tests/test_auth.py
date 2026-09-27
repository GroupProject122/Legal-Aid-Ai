from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import auth
import case_store
import document_store
import main
from conftest import signed_in_client


@pytest.fixture
def temp_store(monkeypatch, tmp_path):
    monkeypatch.setattr(main.case_store, "DB_PATH", tmp_path / "legal_aid.db")
    monkeypatch.setattr(document_store, "UPLOAD_DIR", tmp_path / "user_uploads")
    document_store.init_db()
    auth.init_db()
    return tmp_path / "legal_aid.db"


def upload_txt(client: TestClient, name: str = "Receipt.txt", text: str = "Payment receipt text.") -> dict:
    response = client.post("/api/documents/extract", files={"file": (name, text.encode("utf-8"), "text/plain")})
    assert response.status_code == 200
    return response.json()


# --- Sign-up, login, logout ---


def test_signup_with_email_signs_in_and_me_returns_user(temp_store):
    client = TestClient(main.app)

    response = client.post("/api/auth/signup", json={"email": " Asha@Example.com ", "password": "long enough pw"})

    assert response.status_code == 200
    assert response.json()["user"]["email"] == "asha@example.com"
    assert "password_hash" not in response.json()["user"]
    assert client.get("/api/auth/me").json()["user"]["email"] == "asha@example.com"


def test_signup_with_phone_normalizes_number_and_login_accepts_other_formats(temp_store):
    client = TestClient(main.app)

    response = client.post("/api/auth/signup", json={"phone": "98765 43210", "password": "long enough pw"})

    assert response.status_code == 200
    assert response.json()["user"]["phone"] == "+919876543210"
    other = TestClient(main.app)
    assert other.post("/api/auth/login", json={"identifier": "+91-98765-43210", "password": "long enough pw"}).status_code == 200
    assert other.post("/api/auth/login", json={"identifier": "09876543210", "password": "long enough pw"}).status_code == 200


def test_signup_rejects_duplicates_short_passwords_and_missing_identifier(temp_store):
    client = TestClient(main.app)
    assert client.post("/api/auth/signup", json={"email": "a@example.com", "password": "long enough pw"}).status_code == 200

    duplicate = TestClient(main.app).post("/api/auth/signup", json={"email": "A@example.com", "password": "another pw!"})
    short = TestClient(main.app).post("/api/auth/signup", json={"email": "b@example.com", "password": "short"})
    missing = TestClient(main.app).post("/api/auth/signup", json={"password": "long enough pw"})
    bad_phone = TestClient(main.app).post("/api/auth/signup", json={"phone": "12345", "password": "long enough pw"})

    assert duplicate.status_code == 400
    assert "already exists" in duplicate.json()["detail"]
    assert short.status_code == 400
    assert missing.status_code == 400
    assert bad_phone.status_code == 400


def test_password_is_stored_hashed_not_plain(temp_store):
    auth.create_user(email="a@example.com", password="plain secret pw")

    with case_store.connect() as conn:
        stored = conn.execute("SELECT password_hash FROM users").fetchone()[0]

    assert "plain secret pw" not in stored
    assert stored.startswith("scrypt$")


def test_login_with_wrong_password_or_unknown_account_is_refused(temp_store):
    auth.create_user(email="a@example.com", password="long enough pw")
    client = TestClient(main.app)

    wrong = client.post("/api/auth/login", json={"identifier": "a@example.com", "password": "wrong password"})
    unknown = client.post("/api/auth/login", json={"identifier": "nobody@example.com", "password": "long enough pw"})

    assert wrong.status_code == 401
    assert unknown.status_code == 401
    # Same message either way, so the response does not reveal which accounts exist.
    assert wrong.json()["detail"] == unknown.json()["detail"]
    assert client.get("/api/auth/me").json()["user"] is None


def test_repeated_wrong_passwords_lock_the_account_temporarily(temp_store):
    auth.create_user(email="a@example.com", password="long enough pw")
    client = TestClient(main.app)
    for _ in range(auth.MAX_FAILED_LOGINS):
        client.post("/api/auth/login", json={"identifier": "a@example.com", "password": "wrong password"})

    locked = client.post("/api/auth/login", json={"identifier": "a@example.com", "password": "long enough pw"})

    assert locked.status_code == 429


def test_logout_ends_the_session(temp_store):
    client, _user_id = signed_in_client()

    assert client.post("/api/auth/logout").status_code == 200

    assert client.get("/api/auth/me").json()["user"] is None
    assert client.get("/api/cases").status_code == 401


def test_session_cookie_is_http_only(temp_store):
    client = TestClient(main.app)

    response = client.post("/api/auth/signup", json={"email": "a@example.com", "password": "long enough pw"})

    cookie_header = response.headers["set-cookie"].lower()
    assert "httponly" in cookie_header
    assert "samesite=lax" in cookie_header


def test_password_change_signs_out_existing_sessions(temp_store):
    client, user_id = signed_in_client()

    auth.set_password(user_id, "a brand new password")

    assert client.get("/api/auth/me").json()["user"] is None


# --- Guests ---


def test_guest_cannot_reach_cases_or_documents(temp_store):
    client = TestClient(main.app)

    assert client.get("/api/cases").status_code == 401
    assert client.get("/api/cases/1").status_code == 401
    assert client.delete("/api/cases").status_code == 401
    assert client.get("/api/documents").status_code == 401
    assert client.get("/api/documents/1/file").status_code == 401
    assert client.delete("/api/documents").status_code == 401


def test_guest_question_is_answered_but_not_saved(monkeypatch, temp_store):
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _text, **_kw: main.domain_router.RouteDecision(
        status="classified",
        domains=["consumer"],
        primary_domain="consumer",
        confidence="high",
        issue_summary="Mock consumer issue.",
        needs_clarification=False,
    ))
    monkeypatch.setattr(main, "handle_classified_issue", lambda *_a, **_kw: {"answer": {"issue_summary": "x"}, "sources": []})
    client = TestClient(main.app)

    response = client.post("/api/ask", json={"question": "The seller refused refund."})

    assert response.status_code == 200
    assert "case_id" not in response.json()
    assert case_store.list_cases()["total"] == 0


def test_guest_cannot_continue_a_saved_case(temp_store):
    _owner, owner_id = signed_in_client()
    case_id = case_store.create_case("The seller refused refund.", "consumer", user_id=owner_id)

    response = TestClient(main.app).post("/api/ask", json={"question": "and then?", "case_id": case_id})

    assert response.status_code == 401


def test_guest_upload_is_read_but_not_stored(temp_store):
    data = upload_txt(TestClient(main.app))

    assert data["text"] == "Payment receipt text."
    assert "document_id" not in data
    assert document_store.list_documents()["total"] == 0


# --- Separation between accounts ---


def test_users_only_see_and_change_their_own_cases(temp_store):
    alice, alice_id = signed_in_client("alice@example.com")
    bob, _bob_id = signed_in_client("bob@example.com")
    alice_case = case_store.create_case("The seller refused refund.", "consumer", user_id=alice_id)
    case_store.save_message(alice_case, "user", {"text": "The seller refused refund."})

    assert bob.get("/api/cases").json()["total"] == 0
    assert bob.get(f"/api/cases/{alice_case}").status_code == 404
    assert bob.patch(f"/api/cases/{alice_case}/rename", json={"title": "Mine now"}).status_code == 404
    assert bob.delete(f"/api/cases/{alice_case}").status_code == 404
    assert bob.post("/api/ask", json={"question": "follow up", "case_id": alice_case}).status_code == 404
    assert bob.delete("/api/cases").json()["deleted_count"] == 0

    assert alice.get("/api/cases").json()["total"] == 1
    assert alice.get(f"/api/cases/{alice_case}").json()["case"]["title"] == "Defective Product Refund"


def test_new_cases_from_ask_belong_to_the_asker(monkeypatch, temp_store):
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _text, **_kw: main.domain_router.RouteDecision(
        status="classified",
        domains=["consumer"],
        primary_domain="consumer",
        confidence="high",
        issue_summary="Mock consumer issue.",
        needs_clarification=False,
    ))
    monkeypatch.setattr(main, "handle_classified_issue", lambda *_a, **_kw: {"answer": {"issue_summary": "x"}, "sources": []})
    alice, _alice_id = signed_in_client("alice@example.com")
    bob, _bob_id = signed_in_client("bob@example.com")

    case_id = alice.post("/api/ask", json={"question": "The seller refused refund."}).json()["case_id"]

    assert alice.get("/api/cases").json()["total"] == 1
    assert bob.get("/api/cases").json()["total"] == 0
    assert bob.get(f"/api/cases/{case_id}").status_code == 404


def test_users_only_see_and_change_their_own_documents(temp_store):
    alice, _alice_id = signed_in_client("alice@example.com")
    bob, _bob_id = signed_in_client("bob@example.com")
    document_id = upload_txt(alice)["document_id"]

    assert bob.get("/api/documents").json()["total"] == 0
    assert bob.get(f"/api/documents/{document_id}").status_code == 404
    assert bob.get(f"/api/documents/{document_id}/file").status_code == 404
    assert bob.get(f"/api/documents/{document_id}/summary").status_code == 404
    assert bob.post(f"/api/documents/{document_id}/summarize").status_code == 404
    assert bob.patch(f"/api/documents/{document_id}/rename", json={"filename": "x.txt"}).status_code == 400
    assert bob.delete(f"/api/documents/{document_id}").status_code == 404
    assert bob.post(
        "/api/documents/confirm-facts",
        json={"fact_extraction_id": "unknown", "confirmed_facts": {}, "document_id": document_id},
    ).status_code == 404
    assert bob.delete("/api/documents").json()["deleted_count"] == 0

    assert alice.get("/api/documents").json()["total"] == 1
    assert alice.get(f"/api/documents/{document_id}").json()["filename"] == "Receipt.txt"


# --- Data saved before accounts existed ---


def test_existing_data_is_given_to_admin_and_nothing_is_deleted(temp_store):
    old_case = case_store.create_case("The seller refused refund.", "consumer")
    case_store.save_message(old_case, "user", {"text": "The seller refused refund."})
    old_document = document_store.create_uploaded_document(
        original_filename="Old.txt",
        content=b"old",
        mime_type="text/plain",
        extraction={"status": "success", "file_type": "txt", "text": "old"},
    )["id"]

    claimed = auth.claim_unowned_data()

    assert claimed == {"cases": 1, "documents": 1}
    admin = auth.ensure_admin()
    assert admin["is_admin"] == 1
    assert case_store.get_case(old_case, user_id=admin["id"]) is not None
    assert len(case_store.get_messages(old_case)) == 1
    assert document_store.get_document(old_document, user_id=admin["id"]) is not None
    # Running it again changes nothing and creates no second admin.
    assert auth.claim_unowned_data() == {"cases": 0, "documents": 0}
    with case_store.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM users WHERE is_admin = 1").fetchone()[0] == 1


def test_admin_can_sign_in_and_see_the_existing_data(monkeypatch, temp_store):
    monkeypatch.setenv("LEGAL_AID_ADMIN_PASSWORD", "admin password 123")
    case_store.create_case("The seller refused refund.", "consumer")
    auth.claim_unowned_data()
    client = TestClient(main.app)

    response = client.post("/api/auth/login", json={"identifier": auth.ADMIN_EMAIL, "password": "admin password 123"})

    assert response.status_code == 200
    assert response.json()["user"]["is_admin"] is True
    assert client.get("/api/cases").json()["total"] == 1
    # Other accounts still see nothing of the admin's data.
    other, _other_id = signed_in_client()
    assert other.get("/api/cases").json()["total"] == 0


def test_database_from_before_accounts_is_migrated(monkeypatch, tmp_path):
    """A legal_aid.db created by the pre-accounts code (no user_id columns) keeps its rows."""
    db = tmp_path / "legal_aid.db"
    with sqlite3.connect(db) as conn:
        conn.execute(
            """CREATE TABLE cases (id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL,
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL, primary_domain TEXT,
            conversation_state_json TEXT, confirmed_document_context_json TEXT)"""
        )
        conn.execute(
            "INSERT INTO cases (title, created_at, updated_at, primary_domain) VALUES ('Old Case', 't', 't', 'consumer')"
        )
    monkeypatch.setattr(main.case_store, "DB_PATH", db)
    monkeypatch.setattr(document_store, "UPLOAD_DIR", tmp_path / "user_uploads")

    auth.claim_unowned_data()

    admin = auth.ensure_admin()
    cases = case_store.list_cases(user_id=admin["id"])
    assert [case["title"] for case in cases["items"]] == ["Old Case"]
