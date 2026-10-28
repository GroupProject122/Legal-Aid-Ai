from __future__ import annotations

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import case_store
import document_relevance
import document_store
import main
from conftest import signed_in_client


@pytest.fixture
def temp_store(monkeypatch, tmp_path):
    monkeypatch.setattr(main.case_store, "DB_PATH", tmp_path / "legal_aid.db")
    monkeypatch.setattr(document_store, "UPLOAD_DIR", tmp_path / "user_uploads")
    document_store.init_db()


@pytest.fixture
def classified_answers(monkeypatch):
    """/api/ask answers every question as a classified consumer issue without calling a model."""
    monkeypatch.setattr(main.domain_router, "route_issue", lambda _text, **_kw: main.domain_router.RouteDecision(
        status="classified",
        domains=["consumer"],
        primary_domain="consumer",
        confidence="high",
        issue_summary="Mock consumer issue.",
        needs_clarification=False,
    ))
    monkeypatch.setattr(
        main,
        "handle_classified_issue",
        lambda *_a, **_kw: {"answer": {"issue_summary": "x"}, "sources": [], "routing": {"primary_domain": "consumer"}},
    )


def upload(client: TestClient, name: str, text: str, case_id: int | None = None) -> int:
    response = client.post(
        "/api/documents/extract",
        files={"file": (name, text.encode("utf-8"), "text/plain")},
        data={"case_id": str(case_id)} if case_id is not None else None,
    )
    assert response.status_code == 200, response.text
    return response.json()["document_id"]


def case_documents(client: TestClient, case_id: int) -> dict:
    response = client.get(f"/api/cases/{case_id}/documents")
    assert response.status_code == 200, response.text
    return response.json()


# --- Documents in this case ---


def test_upload_inside_a_chat_is_listed_in_that_case_only(temp_store):
    client, user_id = signed_in_client()
    this_case = case_store.create_case("Seller refused refund for my phone.", "consumer", user_id=user_id)
    other_case = case_store.create_case("Landlord kept my deposit.", "tenancy", user_id=user_id)

    document_id = upload(client, "Phone invoice.txt", "Tax invoice for phone", case_id=this_case)

    assert [d["id"] for d in case_documents(client, this_case)["documents"]] == [document_id]
    assert case_documents(client, other_case)["documents"] == []


def test_documents_uploaded_before_the_first_question_are_linked_when_the_case_is_created(temp_store, classified_answers):
    client, _user_id = signed_in_client()
    document_id = upload(client, "Receipt.txt", "Payment receipt")

    response = client.post("/api/ask", json={"question": "The seller refused a refund.", "document_ids": [document_id]})

    case_id = response.json()["case_id"]
    assert [d["id"] for d in case_documents(client, case_id)["documents"]] == [document_id]


def test_document_whose_confirmed_facts_are_used_is_linked(temp_store, classified_answers, monkeypatch):
    client, user_id = signed_in_client()
    document_id = upload(client, "Invoice.txt", "Invoice total Rs. 20,000")
    context = {"confirmed_fact_context_id": "ctx123", "confirmed_facts": {"document_type": "invoice_or_receipt"}}
    document_store.update_confirmed_fact_context(document_id, context)
    monkeypatch.setattr(main, "load_confirmed_document_context", lambda context_id: context if context_id == "ctx123" else None)

    response = client.post("/api/ask", json={"question": "The seller refused a refund.", "confirmed_fact_context_id": "ctx123"})

    case_id = response.json()["case_id"]
    assert [d["id"] for d in case_documents(client, case_id)["documents"]] == [document_id]


def test_another_users_document_ids_are_never_linked(temp_store, classified_answers):
    alice, _alice_id = signed_in_client("alice@example.com")
    bob, _bob_id = signed_in_client("bob@example.com")
    alice_document = upload(alice, "Receipt.txt", "Payment receipt")

    case_id = bob.post("/api/ask", json={"question": "The seller refused a refund.", "document_ids": [alice_document]}).json()["case_id"]

    assert case_documents(bob, case_id)["documents"] == []


def test_cannot_upload_into_or_read_another_users_case(temp_store):
    _alice, alice_id = signed_in_client("alice@example.com")
    bob, _bob_id = signed_in_client("bob@example.com")
    alice_case = case_store.create_case("Seller refused refund.", "consumer", user_id=alice_id)

    rejected = bob.post(
        "/api/documents/extract",
        files={"file": ("x.txt", b"text", "text/plain")},
        data={"case_id": str(alice_case)},
    )

    assert rejected.status_code == 404
    assert document_store.list_documents()["total"] == 0
    assert bob.get(f"/api/cases/{alice_case}/documents").status_code == 404


def test_deleting_a_document_or_case_removes_its_links(temp_store):
    client, user_id = signed_in_client()
    case_id = case_store.create_case("Seller refused refund.", "consumer", user_id=user_id)
    first = upload(client, "Invoice.txt", "invoice", case_id=case_id)
    upload(client, "Receipt.txt", "receipt", case_id=case_id)

    client.delete(f"/api/documents/{first}")
    assert len(case_documents(client, case_id)["documents"]) == 1

    client.delete(f"/api/cases/{case_id}")
    with case_store.connect() as conn:
        assert conn.execute("SELECT COUNT(*) FROM case_documents").fetchone()[0] == 0


# --- May also be relevant ---


def test_suggestions_match_the_case_area_and_include_identity_proof(temp_store):
    client, user_id = signed_in_client()
    tenancy_case = case_store.create_case("Landlord kept my security deposit.", "tenancy", user_id=user_id)
    rent = upload(client, "Rent Agreement.txt", "This rent agreement is between the licensor and licensee")
    aadhaar = upload(client, "aadhaar_card.txt", "Government of India Aadhaar")
    invoice = upload(client, "Phone invoice.txt", "Tax invoice")

    suggestions = case_documents(client, tenancy_case)["suggestions"]

    ids = [s["id"] for s in suggestions]
    assert ids == [rent, aadhaar]  # area-specific first, then identity proof; the invoice is not relevant
    assert invoice not in ids
    assert suggestions[0]["relevance_label"] == "Rent agreement"
    assert suggestions[1]["relevance_label"] == "Identity proof"


def test_documents_already_in_the_case_are_not_suggested_again(temp_store):
    client, user_id = signed_in_client()
    case_id = case_store.create_case("Seller refused refund.", "consumer", user_id=user_id)
    in_case = upload(client, "Invoice.txt", "Tax invoice", case_id=case_id)
    elsewhere = upload(client, "Receipt.txt", "Payment receipt")

    body = case_documents(client, case_id)

    assert [d["id"] for d in body["documents"]] == [in_case]
    assert [s["id"] for s in body["suggestions"]] == [elsewhere]


def test_suggestions_only_come_from_the_users_own_documents(temp_store):
    alice, _alice_id = signed_in_client("alice@example.com")
    bob, bob_id = signed_in_client("bob@example.com")
    upload(alice, "aadhaar.txt", "Aadhaar")
    bob_case = case_store.create_case("Seller refused refund.", "consumer", user_id=bob_id)

    assert case_documents(bob, bob_case)["suggestions"] == []


@pytest.mark.parametrize(
    ("filename", "text", "expected"),
    [
        ("electricity-bill-march.pdf", "", "address_proof"),
        ("scan.pdf", "Unique Identification Authority of India (UIDAI) Aadhaar", "identity_proof"),
        ("statement.pdf", "UPI transaction UTR 123456", "transaction_record"),
        ("fir_copy.pdf", "", "police_or_cyber_report"),
        ("letter.pdf", "Application under the Right to Information Act", "government_record"),
    ],
)
def test_document_kinds_from_filename_and_text(filename, text, expected):
    kinds = document_relevance.document_kinds({"filename": filename, "text_sample": text})
    assert expected in [kind.key for kind in kinds]


def test_confirmed_document_type_counts_even_without_keywords():
    kinds = document_relevance.document_kinds({"filename": "scan1.pdf", "text_sample": "", "document_type": "rent_agreement"})
    assert [kind.key for kind in kinds] == ["rent_agreement"]


def test_documents_from_another_area_are_not_suggested_through_a_generic_kind():
    documents = [
        {"id": 1, "filename": "legal_notice_to_landlord.docx", "text_sample": "Legal notice. Refund of security deposit under the rent agreement", "case_ids": set()},
        {"id": 2, "filename": "cybercrime_ack.pdf", "text_sample": "cybercrime.gov.in acknowledgement. UTR 624811093301", "case_ids": set()},
        {"id": 3, "filename": "bank_statement.pdf", "text_sample": "Bank statement", "case_ids": set()},
    ]

    consumer = document_relevance.suggest_documents(documents, case_id=99, case_domains=["consumer"])
    public_authority = document_relevance.suggest_documents(documents, case_id=99, case_domains=["constitutional_public_authority"])

    assert [s["id"] for s in consumer] == [3]
    assert public_authority == []


def test_identity_and_address_proof_are_not_crowded_out():
    invoices = [{"id": i, "filename": f"invoice{i}.pdf", "text_sample": "Tax invoice", "case_ids": set()} for i in range(1, 8)]
    proofs = [
        {"id": 100, "filename": "aadhaar.pdf", "text_sample": "Aadhaar", "case_ids": set()},
        {"id": 101, "filename": "electricity bill.pdf", "text_sample": "", "case_ids": set()},
    ]

    suggestions = document_relevance.suggest_documents(invoices + proofs, case_id=99, case_domains=["consumer"])

    assert [s["id"] for s in suggestions] == [1, 2, 3, 100, 101]


def test_postal_order_and_paid_by_upi_are_not_purchases_or_bank_records():
    rti = document_relevance.document_kinds({"filename": "rti.docx", "text_sample": "Fee paid by Indian Postal Order No. 45F 667812"})
    rent = document_relevance.document_kinds({"filename": "rent receipts.pdf", "text_sample": "January Rs. 25,000 paid by UPI. Monthly rent"})
    assert "invoice_or_receipt" not in [kind.key for kind in rti]
    assert [kind.key for kind in rent] == ["rent_payment"]


def test_unrelated_words_do_not_match():
    # "pan" inside another word, "fir" inside "first", "upi" inside "cupid": no false kinds.
    kinds = document_relevance.document_kinds({"filename": "notes.txt", "text_sample": "the first cupid panorama"})
    assert kinds == []
