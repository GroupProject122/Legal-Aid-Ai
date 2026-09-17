from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import case_store
import document_store
import document_summarizer
import main
import redaction
from config import DOCUMENTS_DIR, INDEX_PATH, METADATA_PATH


def configure_temp_store(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setattr(main.case_store, "DB_PATH", tmp_path / "legal_aid.db")
    monkeypatch.setattr(document_store, "UPLOAD_DIR", tmp_path / "user_uploads")
    document_store.init_db()


def create_txt_document(text: str, *, status: str = "success", name: str = "Agreement.txt") -> dict:
    return document_store.create_uploaded_document(
        original_filename=name,
        content=text.encode("utf-8"),
        mime_type="text/plain",
        extraction={
            "status": status,
            "filename": name,
            "file_type": "txt",
            "size_bytes": len(text.encode("utf-8")),
            "character_count": len(text),
            "text": text,
            "pages": [],
            "warnings": [],
        },
    )


def test_document_with_extracted_text_can_be_summarized(monkeypatch):
    monkeypatch.setattr(document_summarizer, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        document_summarizer,
        "call_gemini_summary",
        lambda _prompt: {"summary": "This document records rent of Rs. 25,000 and a security deposit of Rs. 50,000."},
    )

    result = document_summarizer.summarize_document(
        {"status": "success", "text": "Monthly rent is Rs. 25,000. Security deposit is Rs. 50,000."}
    )

    assert result["status"] == "success"
    assert set(result).issuperset({"summary", "status"})
    assert "Rs. 25,000" in result["summary"]


def test_cached_summary_prevents_second_gemini_call(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    document = create_txt_document("Invoice amount Rs. 20,000.")
    calls = {"count": 0}

    def fake_summarize(_extraction):
        calls["count"] += 1
        return {"status": "success", "summary": "This invoice records an amount of Rs. 20,000.", "model": "test", "gemini_calls": 1}

    monkeypatch.setattr(main.document_summarizer, "summarize_document", fake_summarize)
    client = TestClient(main.app)

    first = client.post(f"/api/documents/{document['id']}/summarize")
    second = client.post(f"/api/documents/{document['id']}/summarize")

    assert first.status_code == 200
    assert first.json()["cached"] is False
    assert second.status_code == 200
    assert second.json()["cached"] is True
    assert calls["count"] == 1


def test_nonexistent_document_summary_returns_404(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    client = TestClient(main.app)

    assert client.post("/api/documents/999/summarize").status_code == 404
    assert client.get("/api/documents/999/summary").status_code == 404


def test_empty_extracted_text_is_rejected(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    document = create_txt_document("", status="failed")
    client = TestClient(main.app)

    response = client.post(f"/api/documents/{document['id']}/summarize")

    assert response.status_code == 200
    assert response.json()["status"] == "no_extracted_text"
    assert response.json()["summary"] is None


def test_scanned_ocr_required_document_is_not_summarized(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    document = create_txt_document("", status="ocr_required", name="Scanned.txt")
    with case_store.connect() as conn:
        extraction = document["extraction"] | {"status": "ocr_required", "text": ""}
        conn.execute(
            "UPDATE documents SET extraction_status = ?, extracted_text_json = ? WHERE id = ?",
            ("ocr_required", document_store.json_dumps(extraction), document["id"]),
        )
    client = TestClient(main.app)

    response = client.post(f"/api/documents/{document['id']}/summarize")

    assert response.status_code == 200
    assert response.json()["status"] == "ocr_required"
    assert "OCR" in response.json()["message"]


def test_gemini_failure_returns_safe_response(monkeypatch):
    monkeypatch.setattr(document_summarizer, "GEMINI_API_KEY", "test-key")

    def fail(_prompt):
        raise RuntimeError("429 RESOURCE_EXHAUSTED raw details")

    monkeypatch.setattr(document_summarizer, "call_gemini_summary", fail)

    result = document_summarizer.summarize_document({"status": "success", "text": "Readable text."})

    assert result["status"] == "summary_unavailable"
    assert result["message"] == "The document summary could not be generated right now."
    assert "429" not in result["message"]


def test_summary_stored_in_sqlite(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    document = create_txt_document("Legal notice dated 1 August 2026.")
    monkeypatch.setattr(
        main.document_summarizer,
        "summarize_document",
        lambda _extraction: {"status": "success", "summary": "This document is a notice dated 1 August 2026.", "model": "test"},
    )
    client = TestClient(main.app)

    client.post(f"/api/documents/{document['id']}/summarize")
    stored = document_store.require_document(document["id"])

    assert stored["summary_text"] == "This document is a notice dated 1 August 2026."
    assert stored["summary_status"] == "success"


def test_sensitive_credentials_are_not_leaked(monkeypatch):
    monkeypatch.setattr(document_summarizer, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(
        document_summarizer,
        "call_gemini_summary",
        lambda _prompt: {"summary": "The document says password: hunter2 and OTP 123456 were shared."},
    )

    result = document_summarizer.summarize_document({"status": "success", "text": "password: hunter2 OTP 123456"})

    assert "hunter2" not in result["summary"]
    assert "[sensitive information omitted]" in result["summary"]


# --- Card-number redaction (shared with case_store.py via redaction.py, fixed 2026-09-16) ---
# This file had its own separate copy of the false-positive bug fixed in case_store.py: any
# 13-19 digit run was redacted unconditionally, no Luhn check, so an ordinary long number
# (invoice, policy, order, case number -- all common in legal documents) would be permanently
# altered. Reproduces that failure mode specifically for this file's own pipeline (input text
# sent to Gemini, and the final rendered summary), not just at the shared-module level.


def test_non_card_long_number_survives_redaction_in_prompt_sent_to_gemini(monkeypatch):
    monkeypatch.setattr(document_summarizer, "GEMINI_API_KEY", "test-key")
    reference_number = "1234567890123"  # 13 digits, not Luhn-valid -- a plausible reference number
    assert not redaction.luhn_valid(reference_number)
    captured_prompts = []

    def capture(prompt):
        captured_prompts.append(prompt)
        return {"summary": "This notice concerns a tenancy dispute."}

    monkeypatch.setattr(document_summarizer, "call_gemini_summary", capture)

    document_summarizer.summarize_document(
        {"status": "success", "text": f"Reference number: {reference_number}. This notice concerns a tenancy dispute."}
    )

    assert any(reference_number in prompt for prompt in captured_prompts)


def test_non_card_long_number_survives_in_final_summary(monkeypatch):
    monkeypatch.setattr(document_summarizer, "GEMINI_API_KEY", "test-key")
    invoice_number = "1234567890123456"  # 16 digits, not Luhn-valid -- a plausible invoice number
    assert not redaction.luhn_valid(invoice_number)
    monkeypatch.setattr(
        document_summarizer,
        "call_gemini_summary",
        lambda _prompt: {"summary": f"This invoice, number {invoice_number}, is for Rs. 5,000."},
    )

    result = document_summarizer.summarize_document(
        {"status": "success", "text": f"Invoice number: {invoice_number}. Amount: Rs. 5,000."}
    )

    assert result["status"] == "success"
    assert invoice_number in result["summary"]


def test_luhn_valid_card_number_in_document_is_still_redacted(monkeypatch):
    monkeypatch.setattr(document_summarizer, "GEMINI_API_KEY", "test-key")
    card_number = "4111111111111111"  # standard Visa test card number
    assert redaction.luhn_valid(card_number)
    monkeypatch.setattr(
        document_summarizer,
        "call_gemini_summary",
        lambda _prompt: {"summary": f"The document lists card number {card_number} for payment."},
    )

    result = document_summarizer.summarize_document({"status": "success", "text": f"Card number: {card_number}."})

    assert result["status"] == "success"
    assert card_number not in result["summary"]
    assert "[sensitive information omitted]" in result["summary"]


# --- MAX_TOTAL_CHARS / chunking capacity (fixed 2026-09-16) ---


def test_max_total_chars_matches_chunking_capacity():
    # Regression guard: this constant used to be a separate magic number slightly ABOVE what
    # chunking actually covers, so documents just under the old limit had their tail silently
    # dropped. It must always equal what chunking guarantees, not just be close to it.
    assert document_summarizer.MAX_TOTAL_CHARS == document_summarizer.MAX_CHUNKS * document_summarizer.CHUNK_CHARS


def test_summary_never_enters_legal_corpus_or_faiss(monkeypatch, tmp_path):
    configure_temp_store(monkeypatch, tmp_path)
    tracked_paths = [DOCUMENTS_DIR / "corpus_manifest.json", INDEX_PATH, METADATA_PATH]
    before = {path: path.stat().st_mtime_ns for path in tracked_paths if path.exists()}
    document = create_txt_document("This is user document text, not law.")
    monkeypatch.setattr(
        main.document_summarizer,
        "summarize_document",
        lambda _extraction: {"status": "success", "summary": "This summarizes only the user document.", "model": "test"},
    )
    client = TestClient(main.app)

    client.post(f"/api/documents/{document['id']}/summarize")

    after = {path: path.stat().st_mtime_ns for path in tracked_paths if path.exists()}
    assert after == before
