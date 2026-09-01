from __future__ import annotations

import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import case_store
import main


def assistant_response(domain: str = "consumer") -> dict:
    return {
        "answer": {
            "issue_summary": "You said the seller refused a refund.",
            "possible_rights": ["The retrieved source may support a consumer remedy."],
            "next_steps": ["Keep the invoice if available."],
        },
        "sources": [{"document": "Consumer Protection Act, 2019", "page": 12, "section": "Section 39"}],
        "confidence": "medium",
        "insufficient_context": False,
        "disclaimer": "This is legal information, not professional legal advice.",
        "routing": {"status": "classified", "domains": [domain], "primary_domain": domain, "confidence": "high"},
        "conversation_state_id": "state_1",
        "conversation_state": {
            "conversation_state_id": "state_1",
            "domains": [domain],
            "primary_domain": domain,
            "case_summary": "Defective product refund dispute.",
            "known_facts": ["Seller refused refund."],
        },
    }


def test_database_initializes(tmp_path):
    db = tmp_path / "legal_aid.db"

    case_store.init_db(db)

    assert db.exists()


def test_create_case_and_unique_ids(tmp_path):
    db = tmp_path / "legal_aid.db"

    first = case_store.create_case("The seller refused refund for a defective phone.", "consumer", db_path=db)
    second = case_store.create_case("My landlord cut electricity.", "tenancy", db_path=db)

    assert first != second
    assert case_store.get_case(first, db)["title"] == "Defective Product Refund"


def test_save_user_and_assistant_messages_ordered_round_trip(tmp_path):
    db = tmp_path / "legal_aid.db"
    case_id = case_store.create_case("The seller refused refund.", "consumer", db_path=db)

    case_store.save_message(case_id, "user", case_store.user_content_for_storage("The seller refused refund."), db)
    case_store.save_message(case_id, "assistant", case_store.assistant_content_for_storage(assistant_response()), db)
    messages = case_store.get_messages(case_id, db)

    assert [message["role"] for message in messages] == ["user", "assistant"]
    assert messages[0]["content"] == "The seller refused refund."
    assert messages[1]["content"]["answer"]["issue_summary"].startswith("You said")
    assert messages[1]["content"]["sources"][0]["document"] == "Consumer Protection Act, 2019"


def test_updated_at_changes_and_cases_list_newest_first(tmp_path):
    db = tmp_path / "legal_aid.db"
    old_case = case_store.create_case("old consumer issue", "consumer", db_path=db)
    time.sleep(1.05)
    new_case = case_store.create_case("new tenancy issue", "tenancy", db_path=db)
    time.sleep(1.05)

    case_store.save_message(old_case, "user", {"text": "follow up"}, db)
    cases = case_store.list_cases(db)

    assert cases[0]["id"] == old_case
    assert {case["id"] for case in cases} == {old_case, new_case}


def test_open_case_returns_full_history(tmp_path):
    db = tmp_path / "legal_aid.db"
    case_id = case_store.create_case("RTI no response", "constitutional_public_authority", db_path=db)
    case_store.save_message(case_id, "user", {"text": "RTI no response"}, db)
    case_store.save_message(case_id, "assistant", assistant_response("constitutional_public_authority"), db)

    case = case_store.get_case(case_id, db)
    messages = case_store.get_messages(case_id, db)

    assert case["id"] == case_id
    assert len(messages) == 2
    assert messages[1]["content"]["routing"]["primary_domain"] == "constitutional_public_authority"


def test_delete_case_removes_case_and_messages(tmp_path):
    db = tmp_path / "legal_aid.db"
    case_id = case_store.create_case("The seller refused refund.", "consumer", db_path=db)
    case_store.save_message(case_id, "user", {"text": "The seller refused refund."}, db)
    case_store.save_message(case_id, "assistant", assistant_response(), db)

    deleted = case_store.delete_case(case_id, db)

    assert deleted is True
    assert case_store.get_case(case_id, db) is None
    assert case_store.get_messages(case_id, db) == []
    assert case_store.delete_case(case_id, db) is False


def test_delete_all_cases_removes_all_cases_and_messages(tmp_path):
    db = tmp_path / "legal_aid.db"
    first = case_store.create_case("The seller refused refund.", "consumer", db_path=db)
    second = case_store.create_case("My landlord cut electricity.", "tenancy", db_path=db)
    case_store.save_message(first, "user", {"text": "The seller refused refund."}, db)
    case_store.save_message(second, "assistant", assistant_response("tenancy"), db)

    deleted_count = case_store.delete_all_cases(db)

    assert deleted_count == 2
    assert case_store.list_cases(db) == []
    assert case_store.get_messages(first, db) == []
    assert case_store.get_messages(second, db) == []


def test_rename_case_updates_title_and_timestamp(tmp_path):
    db = tmp_path / "legal_aid.db"
    case_id = case_store.create_case("The seller refused refund.", "consumer", db_path=db)
    original = case_store.get_case(case_id, db)
    time.sleep(1.05)

    renamed = case_store.rename_case(case_id, "  Phone Refund Dispute  ", db)

    assert renamed is not None
    assert renamed["title"] == "Phone Refund Dispute"
    assert renamed["updated_at"] > original["updated_at"]
    assert case_store.list_cases(db)[0]["title"] == "Phone Refund Dispute"


def test_rename_case_rejects_blank_title(tmp_path):
    db = tmp_path / "legal_aid.db"
    case_id = case_store.create_case("The seller refused refund.", "consumer", db_path=db)

    try:
        case_store.rename_case(case_id, "   ", db)
    except ValueError as exc:
        assert "title" in str(exc).lower()
    else:
        raise AssertionError("Blank case title should be rejected.")


def test_rename_missing_case_returns_none(tmp_path):
    db = tmp_path / "legal_aid.db"

    assert case_store.rename_case(999, "Updated Case", db) is None


def test_small_talk_alone_should_not_create_case():
    assert case_store.should_create_case_for_response("thanks", assistant_response()) is False


def test_structured_assistant_json_survives_round_trip(tmp_path):
    db = tmp_path / "legal_aid.db"
    case_id = case_store.create_case("consumer issue", "consumer", db_path=db)
    response = assistant_response()

    case_store.save_message(case_id, "assistant", case_store.assistant_content_for_storage(response), db)
    stored = case_store.get_messages(case_id, db)[0]["content"]

    assert stored["answer"]["next_steps"] == ["Keep the invoice if available."]
    assert stored["conversation_state"]["known_facts"] == ["Seller refused refund."]


def test_sensitive_values_are_redacted_before_storage(tmp_path):
    db = tmp_path / "legal_aid.db"
    case_id = case_store.create_case("cyber issue", "cyber", db_path=db)

    case_store.save_message(case_id, "user", case_store.user_content_for_storage("My password is hunter2 and OTP is 123456"), db)

    stored = case_store.get_messages(case_id, db)[0]["content"]
    assert "hunter2" not in stored
    assert "123456" not in stored


def test_api_open_case_round_trip_with_temp_db(monkeypatch, tmp_path):
    db = tmp_path / "legal_aid.db"
    monkeypatch.setattr(main.case_store, "DB_PATH", db)
    main.case_store.init_db()
    client = TestClient(main.app)
    case_id = main.case_store.create_case(
        "The seller refused refund.",
        "consumer",
        conversation_state=assistant_response()["conversation_state"],
    )
    main.case_store.save_message(case_id, "user", {"text": "The seller refused refund."})
    main.case_store.save_message(case_id, "assistant", assistant_response())

    response = client.get(f"/api/cases/{case_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["case"]["id"] == case_id
    assert [message["role"] for message in data["messages"]] == ["user", "assistant"]


def test_api_delete_case_removes_history(monkeypatch, tmp_path):
    db = tmp_path / "legal_aid.db"
    monkeypatch.setattr(main.case_store, "DB_PATH", db)
    main.case_store.init_db()
    client = TestClient(main.app)
    case_id = main.case_store.create_case("The seller refused refund.", "consumer")
    main.case_store.save_message(case_id, "user", {"text": "The seller refused refund."})
    main.case_store.save_message(case_id, "assistant", assistant_response())

    response = client.delete(f"/api/cases/{case_id}")

    assert response.status_code == 200
    assert client.get(f"/api/cases/{case_id}").status_code == 404
    assert client.delete(f"/api/cases/{case_id}").status_code == 404


def test_api_delete_all_cases_removes_every_saved_case(monkeypatch, tmp_path):
    db = tmp_path / "legal_aid.db"
    monkeypatch.setattr(main.case_store, "DB_PATH", db)
    main.case_store.init_db()
    client = TestClient(main.app)
    first = main.case_store.create_case("The seller refused refund.", "consumer")
    second = main.case_store.create_case("My landlord cut electricity.", "tenancy")
    main.case_store.save_message(first, "user", {"text": "The seller refused refund."})
    main.case_store.save_message(second, "assistant", assistant_response("tenancy"))

    response = client.delete("/api/cases")

    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2
    assert client.get("/api/cases").json() == []
    assert client.get(f"/api/cases/{first}").status_code == 404
    assert client.get(f"/api/cases/{second}").status_code == 404


def test_api_rename_case_updates_title(monkeypatch, tmp_path):
    db = tmp_path / "legal_aid.db"
    monkeypatch.setattr(main.case_store, "DB_PATH", db)
    main.case_store.init_db()
    client = TestClient(main.app)
    case_id = main.case_store.create_case("The seller refused refund.", "consumer")

    response = client.patch(f"/api/cases/{case_id}/rename", json={"title": "Phone Refund Dispute"})

    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Phone Refund Dispute"
    assert client.get(f"/api/cases/{case_id}").json()["case"]["title"] == "Phone Refund Dispute"


def test_api_rename_case_rejects_blank_title(monkeypatch, tmp_path):
    db = tmp_path / "legal_aid.db"
    monkeypatch.setattr(main.case_store, "DB_PATH", db)
    main.case_store.init_db()
    client = TestClient(main.app)
    case_id = main.case_store.create_case("The seller refused refund.", "consumer")

    response = client.patch(f"/api/cases/{case_id}/rename", json={"title": "   "})

    assert response.status_code == 400


def test_api_ask_creates_case_and_appends_follow_up(monkeypatch, tmp_path):
    db = tmp_path / "legal_aid.db"
    monkeypatch.setattr(main.case_store, "DB_PATH", db)
    main.case_store.init_db()
    client = TestClient(main.app)
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _text: main.domain_router.RouteDecision(
        status="classified",
        domains=["consumer"],
        primary_domain="consumer",
        confidence="high",
        issue_summary="Mock consumer issue.",
        needs_clarification=False,
    ))

    def fake_classified(*_args, **_kwargs):
        return assistant_response()

    monkeypatch.setattr(main, "handle_classified_issue", fake_classified)

    first = client.post("/api/ask", json={"question": "The seller refused refund."})
    assert first.status_code == 200
    case_id = first.json()["case_id"]

    second = client.post("/api/ask", json={"question": "I paid by UPI.", "case_id": case_id})
    assert second.status_code == 200
    assert second.json()["case_id"] == case_id
    stored = client.get(f"/api/cases/{case_id}").json()["messages"]

    assert [message["role"] for message in stored] == ["user", "assistant", "user", "assistant"]
    assert stored[2]["content"] == "I paid by UPI."


def test_api_small_talk_alone_does_not_create_case(monkeypatch, tmp_path):
    db = tmp_path / "legal_aid.db"
    monkeypatch.setattr(main.case_store, "DB_PATH", db)
    main.case_store.init_db()
    client = TestClient(main.app)

    response = client.post("/api/ask", json={"question": "thanks"})

    assert response.status_code == 200
    assert "case_id" not in response.json()
    assert client.get("/api/cases").json() == []


def test_new_question_does_not_delete_old_case(tmp_path):
    db = tmp_path / "legal_aid.db"
    old_case = case_store.create_case("The seller refused refund.", "consumer", db_path=db)
    new_case = case_store.create_case("My landlord cut electricity.", "tenancy", db_path=db)

    assert case_store.get_case(old_case, db) is not None
    assert case_store.get_case(new_case, db) is not None
