from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import case_store
import document_store
import main
from conftest import signed_in_client
from config import DOCUMENTS_DIR, INDEX_PATH, METADATA_PATH


def configure_temp_store(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(main.case_store, "DB_PATH", tmp_path / "legal_aid.db")
    monkeypatch.setattr(document_store, "UPLOAD_DIR", tmp_path / "user_uploads")
    document_store.init_db()


def upload_txt(client: TestClient, name: str = "Receipt.txt", text: str = "Payment receipt text.") -> dict:
    response = client.post(
        "/api/documents/extract",
        files={"file": (name, text.encode("utf-8"), "text/plain")},
    )
    assert response.status_code == 200
    return response.json()


def test_documents_table_initializes(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)

    with case_store.connect() as conn:
        row = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='documents'").fetchone()

    assert row["name"] == "documents"


def test_upload_creates_document_row_and_physical_file(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()

    data = upload_txt(client)
    document = document_store.require_document(data["document_id"])

    assert document["filename"] == "Receipt.txt"
    assert Path(document["storage_path"]).exists()
    assert document["extraction"]["text"] == "Payment receipt text."


def test_get_documents_lists_newest_first(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    first = upload_txt(client, "First.txt", "first document")
    second = upload_txt(client, "Second.txt", "second document")

    response = client.get("/api/documents")

    assert response.status_code == 200
    body = response.json()
    ids = [item["id"] for item in body["items"]]
    assert ids == [second["document_id"], first["document_id"]]
    assert "extraction" not in body["items"][0]
    assert body["total"] == 2


def test_get_single_document_and_file_serving(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    uploaded = upload_txt(client, "Evidence.txt", "evidence text")

    detail = client.get(f"/api/documents/{uploaded['document_id']}")
    file_response = client.get(f"/api/documents/{uploaded['document_id']}/file")

    assert detail.status_code == 200
    assert detail.json()["extraction"]["text"] == "evidence text"
    assert file_response.status_code == 200
    assert file_response.text == "evidence text"


def test_rename_updates_display_filename_and_preserves_extension(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    uploaded = upload_txt(client, "Old.txt", "rename text")

    response = client.patch(
        f"/api/documents/{uploaded['document_id']}/rename",
        json={"filename": "Phone Purchase Receipt.txt"},
    )

    assert response.status_code == 200
    assert response.json()["filename"] == "Phone Purchase Receipt.txt"
    assert document_store.require_document(uploaded["document_id"])["file_type"] == "txt"


def test_invalid_rename_rejected(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    uploaded = upload_txt(client, "Old.txt", "rename text")

    response = client.patch(
        f"/api/documents/{uploaded['document_id']}/rename",
        json={"filename": "../bad.exe"},
    )

    assert response.status_code == 400


def test_delete_removes_db_row_and_physical_file(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    uploaded = upload_txt(client, "DeleteMe.txt", "delete text")
    storage_path = Path(document_store.require_document(uploaded["document_id"])["storage_path"])

    response = client.delete(f"/api/documents/{uploaded['document_id']}")

    assert response.status_code == 200
    assert document_store.get_document(uploaded["document_id"]) is None
    assert not storage_path.exists()


def test_missing_document_returns_404(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()

    assert client.get("/api/documents/999").status_code == 404
    assert client.get("/api/documents/999/file").status_code == 404
    assert client.delete("/api/documents/999").status_code == 404


def test_path_traversal_is_not_served(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    document_id = document_store.create_uploaded_document(
        original_filename="Safe.txt",
        content=b"safe",
        mime_type="text/plain",
        extraction={"status": "success", "file_type": "txt", "text": "safe", "character_count": 4},
        user_id=user_id,
    )["id"]
    with case_store.connect() as conn:
        conn.execute("UPDATE documents SET storage_path = ? WHERE id = ?", ("/etc/passwd", document_id))

    response = client.get(f"/api/documents/{document_id}/file")

    assert response.status_code == 404


def test_existing_extraction_endpoint_still_returns_schema(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()

    data = upload_txt(client, "Simple.txt", "simple document text")

    assert data["status"] == "success"
    assert data["file_type"] == "txt"
    assert data["document_id"]


def test_confirmed_fact_context_can_be_persisted(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    uploaded = upload_txt(client, "Facts.txt", "Invoice number 123 and amount Rs. 500.")

    payload = {
        "document_type": "invoice_or_receipt",
        "document_summary": "Synthetic invoice facts.",
        "parties": [],
        "dates": [],
        "amounts": [{"label": "amount", "value": "Rs. 500", "source_page": None, "source_excerpt": "amount Rs. 500", "confidence": "high"}],
        "identifiers": [],
        "locations": [],
        "important_terms": [],
        "events": [],
        "notices_or_demands": [],
        "other_facts": [],
        "uncertain_items": [],
        "warnings": [],
    }
    extraction_id = main.document_facts.store_pending_facts(payload)

    response = client.post(
        "/api/documents/confirm-facts",
        json={"fact_extraction_id": extraction_id, "confirmed_facts": payload, "document_id": uploaded["document_id"]},
    )

    assert response.status_code == 200
    document = document_store.require_document(uploaded["document_id"])
    assert document["confirmed_fact_context"]["status"] == "confirmed"


def test_delete_detaches_confirmed_fact_context(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    uploaded = upload_txt(client, "Facts.txt", "amount Rs. 500.")
    payload = {
        "document_type": "invoice_or_receipt",
        "document_summary": "Synthetic invoice facts.",
        "parties": [],
        "dates": [],
        "amounts": [{"label": "amount", "value": "Rs. 500", "source_page": None, "source_excerpt": "amount Rs. 500", "confidence": "high"}],
        "identifiers": [],
        "locations": [],
        "important_terms": [],
        "events": [],
        "notices_or_demands": [],
        "other_facts": [],
        "uncertain_items": [],
        "warnings": [],
    }
    extraction_id = main.document_facts.store_pending_facts(payload)
    confirmed = client.post(
        "/api/documents/confirm-facts",
        json={"fact_extraction_id": extraction_id, "confirmed_facts": payload, "document_id": uploaded["document_id"]},
    ).json()

    client.delete(f"/api/documents/{uploaded['document_id']}")

    assert main.document_facts.get_confirmed_context(confirmed["confirmed_fact_context_id"]) is None


def test_document_never_enters_legal_corpus_or_faiss(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    tracked_paths = [DOCUMENTS_DIR / "corpus_manifest.json", INDEX_PATH, METADATA_PATH]
    before = {path: path.stat().st_mtime_ns for path in tracked_paths if path.exists()}

    upload_txt(client, "Evidence.txt", "This is user evidence, not law.")

    after = {path: path.stat().st_mtime_ns for path in tracked_paths if path.exists()}
    assert after == before


# --- Pagination, search, bulk delete (added 2026-09-16, same convention as My Cases) ---


def test_list_documents_paginates_with_limit_and_offset(tmp_path):
    db = tmp_path / "legal_aid.db"
    ids = []
    for i in range(5):
        document = document_store.create_uploaded_document(
            original_filename=f"doc{i}.txt",
            content=f"text {i}".encode("utf-8"),
            mime_type="text/plain",
            extraction={"status": "success", "file_type": "txt", "text": f"text {i}"},
            db_path=db,
        )
        ids.append(document["id"])
    expected_order = list(reversed(ids))

    page1 = document_store.list_documents(db, limit=2, offset=0)
    page2 = document_store.list_documents(db, limit=2, offset=2)
    page3 = document_store.list_documents(db, limit=2, offset=4)

    assert [d["id"] for d in page1["items"]] == expected_order[0:2]
    assert [d["id"] for d in page2["items"]] == expected_order[2:4]
    assert [d["id"] for d in page3["items"]] == expected_order[4:5]
    assert page1["total"] == page2["total"] == page3["total"] == 5
    assert page1["has_more"] is True
    assert page3["has_more"] is False


def test_list_documents_search_matches_filename_case_insensitively(tmp_path):
    db = tmp_path / "legal_aid.db"
    document_store.create_uploaded_document(
        original_filename="Rental Agreement.txt",
        content=b"rental text",
        mime_type="text/plain",
        extraction={"status": "success", "file_type": "txt", "text": "rental text"},
        db_path=db,
    )
    document_store.create_uploaded_document(
        original_filename="Invoice.txt",
        content=b"invoice text",
        mime_type="text/plain",
        extraction={"status": "success", "file_type": "txt", "text": "invoice text"},
        db_path=db,
    )

    result = document_store.list_documents(db, search="RENTAL")

    assert result["total"] == 1
    assert "Rental" in result["items"][0]["filename"]


def test_list_documents_without_limit_returns_everything(tmp_path):
    db = tmp_path / "legal_aid.db"
    for i in range(3):
        document_store.create_uploaded_document(
            original_filename=f"doc{i}.txt",
            content=f"text {i}".encode("utf-8"),
            mime_type="text/plain",
            extraction={"status": "success", "file_type": "txt", "text": f"text {i}"},
            db_path=db,
        )
    result = document_store.list_documents(db)
    assert len(result["items"]) == 3
    assert result["total"] == 3


def test_size_bytes_is_present_in_listed_documents(tmp_path):
    db = tmp_path / "legal_aid.db"
    content = b"twenty two byte text!"
    document_store.create_uploaded_document(
        original_filename="Sized.txt",
        content=content,
        mime_type="text/plain",
        extraction={"status": "success", "file_type": "txt", "text": "twenty two byte text!"},
        db_path=db,
    )
    result = document_store.list_documents(db)
    assert result["items"][0]["size_bytes"] == len(content)


def test_delete_all_documents_removes_rows_and_physical_files(tmp_path):
    db = tmp_path / "legal_aid.db"
    monkeypatch_upload_dir = tmp_path / "user_uploads"
    import document_store as ds

    original_upload_dir = ds.UPLOAD_DIR
    ds.UPLOAD_DIR = monkeypatch_upload_dir
    try:
        documents = [
            ds.create_uploaded_document(
                original_filename=f"doc{i}.txt",
                content=f"text {i}".encode("utf-8"),
                mime_type="text/plain",
                extraction={"status": "success", "file_type": "txt", "text": f"text {i}"},
                db_path=db,
            )
            for i in range(3)
        ]
        storage_paths = [Path(d["storage_path"]) for d in documents]
        assert all(path.exists() for path in storage_paths)

        deleted_count = ds.delete_all_documents(db)

        assert deleted_count == 3
        assert ds.list_documents(db)["items"] == []
        assert all(not path.exists() for path in storage_paths)
    finally:
        ds.UPLOAD_DIR = original_upload_dir


def test_api_list_documents_paginates(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    for i in range(3):
        upload_txt(client, f"doc{i}.txt", f"text {i}")

    response = client.get("/api/documents", params={"limit": 2, "offset": 0})

    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["total"] == 3
    assert body["has_more"] is True


def test_api_list_documents_search_param(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    upload_txt(client, "Rental Agreement.txt", "rental text")
    upload_txt(client, "Invoice.txt", "invoice text")

    response = client.get("/api/documents", params={"search": "rental"})

    assert response.status_code == 200
    assert response.json()["total"] == 1


def test_api_delete_all_documents(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    upload_txt(client, "doc1.txt", "text 1")
    upload_txt(client, "doc2.txt", "text 2")

    response = client.delete("/api/documents")

    assert response.status_code == 200
    assert response.json()["deleted_count"] == 2
    assert client.get("/api/documents").json()["items"] == []


def test_documents_are_categorised_like_cases(monkeypatch, tmp_path):
    # The Documents page colours each document by legal area, like My Cases. A document used in
    # a case takes that case's area; an unused one gets a guess from its name and text; one that
    # points at no single area (identity proof, bank statement) gets none.
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    invoice = upload_txt(client, "invoice.txt", "Tax invoice for a refrigerator.")["document_id"]
    rent = upload_txt(client, "rent_agreement.txt", "This lease agreement is between the lessor and the tenant.")["document_id"]
    statement = upload_txt(client, "bank_statement.txt", "Account statement, amount debited.")["document_id"]
    used = upload_txt(client, "notes.txt", "Notes about the landlord.")["document_id"]
    case_id = case_store.create_case("my landlord cut the electricity", "tenancy", user_id=user_id)
    document_store.link_document_to_case(case_id, used)

    items = {item["id"]: item for item in client.get("/api/documents").json()["items"]}

    assert (items[invoice]["category"], items[invoice]["category_source"]) == ("consumer", "inferred")
    assert (items[rent]["category"], items[rent]["category_source"]) == ("tenancy", "inferred")
    assert (items[statement]["category"], items[statement]["category_source"]) == (None, None)
    assert (items[used]["category"], items[used]["category_source"]) == ("tenancy", "case")


def test_documents_list_the_case_and_question_they_came_in_with(monkeypatch, tmp_path):
    # The Documents page's "Go to case" button opens a document's case at the question it was
    # added with. Uploaded inside an open chat: the question asked next. Linked when a turn is
    # saved: that turn's question. Never used in a case: no cases.
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    case_id = case_store.create_case("landlord cut electricity", "tenancy", user_id=user_id)
    case_store.save_message(case_id, "user", "landlord cut electricity")      # 1
    case_store.save_message(case_id, "assistant", {"answer": {}})             # 2
    in_chat = client.post(
        "/api/documents/extract",
        data={"case_id": str(case_id)},
        files={"file": ("rent_receipt.txt", b"Rent receipt for June.", "text/plain")},
    ).json()["document_id"]
    with_turn = upload_txt(client, "notice.txt", "Notice from landlord.")["document_id"]
    document_store.link_document_to_case(case_id, with_turn, message_sequence=1)
    unused = upload_txt(client, "id_card.txt", "Identity card.")["document_id"]

    items = {item["id"]: item for item in client.get("/api/documents").json()["items"]}

    assert items[in_chat]["cases"] == [
        {"case_id": case_id, "title": items[in_chat]["cases"][0]["title"], "primary_domain": "tenancy", "message_sequence": 3}
    ]
    assert items[with_turn]["cases"][0]["message_sequence"] == 1
    assert items[unused]["cases"] == []


def test_legacy_link_without_position_points_at_last_question_before_it(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client, user_id = signed_in_client()
    case_id = case_store.create_case("seller refused refund", "consumer", user_id=user_id)
    case_store.save_message(case_id, "user", "seller refused refund")
    case_store.save_message(case_id, "assistant", {"answer": {}})
    document_id = upload_txt(client, "invoice.txt", "Tax invoice.")["document_id"]
    with case_store.connect() as conn:
        conn.execute(
            "INSERT INTO case_documents (case_id, document_id, linked_at, message_sequence) VALUES (?, ?, ?, NULL)",
            (case_id, document_id, "2999-01-01T00:00:00Z"),
        )

    item = next(item for item in client.get("/api/documents").json()["items"] if item["id"] == document_id)

    assert item["cases"][0]["message_sequence"] == 1
