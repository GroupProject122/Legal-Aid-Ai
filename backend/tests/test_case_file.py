from __future__ import annotations

import io
import json
import logging
import shutil
import sqlite3
import sys
from pathlib import Path

import pytest
from docx import Document
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import case_file
import case_store
import complaint_drafter
import conversation_state
import evaluate_case_file
import main

CASES = {spec["id"]: spec for spec in evaluate_case_file.load_cases()}


def build(case_id: str, tmp_path: Path) -> dict:
    db = tmp_path / "legal_aid.db"
    stored_id = evaluate_case_file.seed_case(CASES[case_id], db)
    return case_file.build_case_file_context(case_file.load_case_for_export(stored_id, db))


def headings(docx_bytes: bytes) -> list[str]:
    return evaluate_case_file.docx_headings(docx_bytes)


@pytest.fixture
def api_db(monkeypatch, tmp_path):
    db = tmp_path / "legal_aid.db"
    monkeypatch.setattr(main.case_store, "DB_PATH", db)
    case_store.init_db()
    return db


# --- The five eval fixtures, end to end (seed -> context -> real DOCX) ---


@pytest.mark.parametrize("case_id", sorted(CASES))
def test_eval_fixture_passes_every_check(case_id):
    result = evaluate_case_file.evaluate_case(CASES[case_id])
    failed = [name for name, ok in result["checks"].items() if not ok]
    assert not failed, failed


# --- build_case_file_context ---


def test_consumer_receipt_document_facts_name_the_document(tmp_path):
    context = build("consumer_receipt_document", tmp_path)
    document_facts = [fact for fact in context["facts"] if "croma_receipt.pdf" in fact["label"]]
    assert {fact["text"] for fact in document_facts} >= {"Amount paid: Rs. 18,499", "Invoice date: 12 March 2026"}
    # The upload date is not presented as a date of the fact itself.
    assert all(fact["stated_on"] is None for fact in document_facts)
    assert [doc["name"] for doc in context["uploaded_documents"]] == ["croma_receipt.pdf"]
    assert [event["date_display"] for event in context["timeline"]] == ["12 March 2026", "20 March 2026"]


def test_user_facts_are_labelled_as_stated_by_you(tmp_path):
    context = build("consumer_receipt_document", tmp_path)
    user_facts = [fact for fact in context["facts"] if "document" not in fact["label"]]
    assert user_facts and all(fact["label"].startswith("As stated by you") for fact in user_facts)
    # Small talk ("thanks") is neither a fact nor in the conversation record.
    assert all(fact["text"] != "thanks" for fact in context["facts"])
    assert all(entry["question"] != "thanks" for entry in context["appendix"])


def test_correction_replaces_the_old_fact(tmp_path):
    context = build("cyber_correction", tmp_path)
    texts = [fact["text"] for fact in context["facts"]]
    assert "Sorry, actually it was 3 transactions, not 2." in texts
    assert not any("2 unauthorised transactions" in text for text in texts)
    correction = next(fact for fact in context["facts"] if "3 transactions" in fact["text"])
    assert correction["label"] == "As stated by you (your correction)"
    # The follow-up question is in the conversation record, not presented as a fact.
    assert not any("Can the bank refuse" in text for text in texts)
    assert any("Can the bank refuse" in entry["question"] for entry in context["appendix"])


def test_case_with_no_dated_facts_has_no_timeline_heading(tmp_path):
    context = build("tenancy_no_dates", tmp_path)
    assert context["timeline"] == []
    assert "timeline" not in context["sections"]
    docx_headings = headings(case_file.render_case_file_docx(context))
    assert "Timeline" not in docx_headings
    assert "Evidence checklist" not in docx_headings  # nothing to list, so no empty heading
    assert all(heading.strip() for heading in docx_headings)
    assert context["situation"]["label"] == "Your first message, as you wrote it"


def test_case_law_and_compiled_summary_are_labelled(tmp_path):
    context = build("consumer_case_law_and_summary", tmp_path)
    labels = {law["title"]: law["authority"] for law in context["laws"]}
    assert labels["Indian Medical Association v. V.P. Shantha, (1995) 6 SCC 651"] == "Case law (court judgment)"
    assert any(label == "Compiled summary — not the official text of the law" for title, label in labels.items() if "Greenwashing" in title)
    assert any(label == "Official guidance" for title, label in labels.items() if "Misleading Advertisements" in title)
    case_law = next(law for law in context["laws"] if "Shantha" in law["title"])
    assert case_law["provision"] == "(1995) 6 SCC 651"


def test_otp_and_other_secrets_are_redacted(tmp_path):
    context = build("cyber_otp_redaction", tmp_path)
    dumped = json.dumps(context, ensure_ascii=False)
    for secret in ("482913", "2345 6789 0123", "Sunrise@2026", "4111 1111 1111 1111", "1 2 3 4 5 6"):
        assert secret not in dumped
    assert "OTP [sensitive information omitted]" in dumped
    text = evaluate_case_file.docx_text(case_file.render_case_file_docx(context))
    assert "482913" not in text and "& bank help" in text  # escaped, not dropped


def test_sources_deduplicated_by_document_and_provision(tmp_path):
    # Two different chunks of Delhi Rent Control Act Section 45, both verified -> one entry.
    context = build("tenancy_no_dates", tmp_path)
    assert len(context["laws"]) == 1
    assert context["laws"][0]["provision"].startswith("Section 45")


def test_unverified_and_unrecorded_sources_are_excluded(tmp_path):
    receipt = build("consumer_receipt_document", tmp_path / "a")
    assert "consumer_consumer_protection_act_2019__chunk_0003" not in {law["chunk_id"] for law in receipt["laws"]}
    assert any("passed the app's source check" in note for note in receipt["notes"])
    legacy = build("consumer_case_law_and_summary", tmp_path / "b")
    assert "consumer_consumer_protection_act_2019__chunk_0052" not in {law["chunk_id"] for law in legacy["laws"]}
    assert any("saved before the app began recording" in note for note in legacy["notes"])


def test_case_without_answers_is_refused():
    with pytest.raises(case_file.CaseFileError):
        case_file.build_case_file_context({"title": "x", "messages": [{"role": "user", "content": "hello", "created_at": None}]}, manifest={})


def test_explicit_dates_never_estimates():
    assert case_file.explicit_dates("last week, in March 2026, on 5/3/26") == []
    assert case_file.explicit_dates("on 31 February 2026") == []
    dates = [date.isoformat() for date, _ in case_file.explicit_dates("paid on 5th March 2026, notice 05/04/2026, hearing 2026-06-01")]
    assert dates == ["2026-03-05", "2026-04-05", "2026-06-01"]


def test_filename_is_safe():
    import datetime

    name = case_file.case_file_filename('Seller "Refund" / ../etc & बिजली', datetime.date(2026, 10, 28), "pdf")
    assert name == "case-file-seller-refund-etc-2026-10-28.pdf"
    assert case_file.case_file_filename("", datetime.date(2026, 10, 28), "docx") == "case-file-case-2026-10-28.docx"


# --- Supporting changes in existing modules ---


def test_apply_correction_replaces_explicitly_negated_count():
    facts = ["There were 2 unauthorised transactions.", "I paid 2 times at the counter.", "Rs 500 was lost"]
    updated = conversation_state.apply_correction(facts, "actually it was 3 transactions, not 2")
    assert "There were 2 unauthorised transactions." not in updated
    assert "I paid 2 times at the counter." in updated  # different noun -> untouched
    assert conversation_state.apply_correction(["two transactions"], "not two but three transactions") == ["not two but three transactions"]


def test_assistant_storage_keeps_only_compact_verification():
    stored = case_store.assistant_content_for_storage(
        {
            "answer": {"issue_summary": "x"},
            "sources": [],
            "verification": {
                "status": "verified",
                "claims": [{"text": "a long claim"}],
                "results": [
                    {"support": "supported", "supporting_chunk_ids": ["a", "b"]},
                    {"support": "partially_supported", "supporting_chunk_ids": ["b", "c"]},
                    {"support": "unsupported", "supporting_chunk_ids": ["d"]},
                ],
            },
        }
    )
    assert stored["verification"] == {"status": "verified", "verified_source_chunk_ids": ["a", "b", "c"]}
    unavailable = case_store.compact_verification_for_storage({"status": "unavailable", "results": [{"support": "supported", "supporting_chunk_ids": ["a"]}]})
    assert unavailable == {"status": "unavailable", "verified_source_chunk_ids": []}


def test_is_answer_content_excludes_acknowledgements_and_clarifications():
    assert case_store.is_answer_content({"answer": {"issue_summary": "x", "where_to_approach": ["y"]}, "sources": []})
    assert not case_store.is_answer_content({"answer": {"issue_summary": "Got it", "possible_rights": [], "next_steps": []}, "sources": []})
    assert not case_store.is_answer_content({"answer": {"issue_summary": "x", "next_steps": ["Which city?"]}, "clarification": {"needed": True}})
    assert not case_store.is_answer_content({"answer": {"issue_summary": "x", "suggested_next_steps": ["y"]}, "technical_error": True})


# --- API ---


def test_list_cases_reports_has_answers(api_db):
    answered = evaluate_case_file.seed_case(CASES["tenancy_no_dates"], api_db)
    unanswered = case_store.create_case("My landlord is harassing me", "tenancy")
    case_store.save_message(unanswered, "user", {"text": "My landlord is harassing me"})
    items = {item["id"]: item for item in TestClient(main.app).get("/api/cases").json()["items"]}
    assert items[answered]["has_answers"] is True
    assert items[unanswered]["has_answers"] is False


def test_api_docx_download(api_db):
    case_id = evaluate_case_file.seed_case(CASES["consumer_receipt_document"], api_db)
    response = TestClient(main.app).get(f"/api/cases/{case_id}/case-file.docx")
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats-officedocument.wordprocessingml.document")
    assert response.headers["cache-control"] == "no-store"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith('attachment; filename="case-file-defective-product-refund-')
    assert disposition.endswith('.docx"')
    document = Document(io.BytesIO(response.content))
    assert any(paragraph.text == "Facts as stated by you" for paragraph in document.paragraphs)


def test_api_missing_case_returns_same_404_as_open_case(api_db):
    client = TestClient(main.app)
    expected = client.get("/api/cases/9999")
    for suffix in ("case-file.pdf", "case-file.docx"):
        response = client.get(f"/api/cases/9999/{suffix}")
        assert response.status_code == expected.status_code == 404
        assert response.json() == expected.json()


def test_api_case_without_answers_returns_409(api_db):
    case_id = case_store.create_case("hello there, my landlord", "tenancy")
    case_store.save_message(case_id, "user", {"text": "hello there, my landlord"})
    response = TestClient(main.app).get(f"/api/cases/{case_id}/case-file.docx")
    assert response.status_code == 409
    assert "no answers yet" in response.json()["detail"]


def test_api_pdf_without_libreoffice_returns_503_pointing_to_docx(api_db, monkeypatch):
    case_id = evaluate_case_file.seed_case(CASES["tenancy_no_dates"], api_db)
    monkeypatch.setattr(complaint_drafter.shutil, "which", lambda _name: None)
    response = TestClient(main.app).get(f"/api/cases/{case_id}/case-file.pdf")
    assert response.status_code == 503
    assert "Word (.docx)" in response.json()["detail"]


@pytest.mark.skipif(not (shutil.which("soffice") or shutil.which("libreoffice")), reason="LibreOffice not installed")
def test_api_pdf_download_with_libreoffice(api_db):
    case_id = evaluate_case_file.seed_case(CASES["cyber_otp_redaction"], api_db)
    response = TestClient(main.app).get(f"/api/cases/{case_id}/case-file.pdf")
    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def _snapshot(paths: list[Path]) -> dict[str, float]:
    snapshot = {}
    for root in paths:
        if not root.exists():
            continue
        for path in [root, *root.rglob("*")]:
            if "__pycache__" not in path.parts:
                snapshot[str(path)] = path.stat().st_mtime
    return snapshot


def _db_state(db: Path) -> list:
    with sqlite3.connect(db) as conn:
        return [
            conn.execute("SELECT id, title, updated_at, conversation_state_json FROM cases ORDER BY id").fetchall(),
            conn.execute("SELECT COUNT(*) FROM messages").fetchone(),
            conn.execute("SELECT COUNT(*), MAX(updated_at) FROM documents").fetchone(),
        ]


def test_export_writes_nothing_to_disk_or_db_and_logs_no_content(api_db, tmp_path, caplog):
    case_id = evaluate_case_file.seed_case(CASES["consumer_receipt_document"], api_db)
    backend_dir = Path(case_file.__file__).resolve().parent
    watched = [tmp_path, backend_dir / "templates", backend_dir / "user_uploads", backend_dir / "eval"]
    before_files, before_db = _snapshot(watched), _db_state(api_db)
    top_level_before = {p.name for p in backend_dir.iterdir()}

    caplog.set_level(logging.DEBUG)
    response = TestClient(main.app).get(f"/api/cases/{case_id}/case-file.docx")
    assert response.status_code == 200

    assert _snapshot(watched) == before_files
    assert {p.name for p in backend_dir.iterdir()} == top_level_before
    assert _db_state(api_db) == before_db
    logged = caplog.text
    for fragment in ("stopped working", "Croma", "18,499", "written complaint", "croma_receipt.pdf", "Defective Product Refund"):
        assert fragment not in logged
    assert f"case_id={case_id}" in logged
