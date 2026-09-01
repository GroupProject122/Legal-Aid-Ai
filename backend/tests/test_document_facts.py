from __future__ import annotations

import sys
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import document_facts
import main
from config import DOCUMENTS_DIR, INDEX_PATH, METADATA_PATH


client = TestClient(main.app)


def extraction(text: str = "Invoice No INV-1 dated 12 June 2026 for Rs. 15000.") -> dict:
    return {
        "status": "success",
        "filename": "invoice.txt",
        "file_type": "txt",
        "size_bytes": len(text),
        "page_count": None,
        "character_count": len(text),
        "text": text,
        "pages": [],
        "warnings": [],
    }


def gemini_payload() -> dict:
    return {
        "document_type": "invoice_or_receipt",
        "document_summary": "This appears to be an invoice for a phone purchase.",
        "parties": [{"label": "seller", "value": "ABC Mobiles", "source_page": 1, "source_excerpt": "Seller: ABC Mobiles", "confidence": "high"}],
        "dates": [{"label": "invoice_date", "value": "12 June 2026", "source_page": 1, "source_excerpt": "Date: 12 June 2026", "confidence": "high"}],
        "amounts": [{"label": "price", "value": "Rs. 15000", "source_page": 1, "source_excerpt": "Total Rs. 15000", "confidence": "high"}],
        "identifiers": [{"label": "invoice_number", "value": "INV-1", "source_page": 1, "source_excerpt": "Invoice No INV-1", "confidence": "high"}],
        "locations": [],
        "important_terms": [],
        "events": [{"label": "purchase", "value": "Phone purchase", "source_page": 1, "source_excerpt": "phone purchase", "confidence": "medium"}],
        "notices_or_demands": [],
        "other_facts": [],
        "uncertain_items": [],
        "warnings": [],
    }


def patch_gemini(monkeypatch, payload=None):
    monkeypatch.setattr(document_facts, "GEMINI_API_KEY", "test-key")
    monkeypatch.setattr(document_facts, "call_gemini_fact_extraction", lambda _extraction: payload or gemini_payload())


def test_valid_structured_fact_output(monkeypatch):
    patch_gemini(monkeypatch)

    result = document_facts.extract_facts_from_extraction(extraction())

    assert result["status"] == "success"
    assert result["confirmation_required"] is True
    assert result["fact_extraction_id"]
    assert result["facts"]["document_type"] == "invoice_or_receipt"


def test_explicit_fact_extracted_with_provenance(monkeypatch):
    patch_gemini(monkeypatch)
    result = document_facts.extract_facts_from_extraction(extraction())

    amount = result["facts"]["amounts"][0]
    assert amount["value"] == "Rs. 15000"
    assert amount["source_page"] == 1
    assert "Total" in amount["source_excerpt"]


def test_unstated_fact_not_invented_when_gemini_omits_it(monkeypatch):
    payload = gemini_payload()
    payload["locations"] = []
    patch_gemini(monkeypatch, payload)

    result = document_facts.extract_facts_from_extraction(extraction())

    assert result["facts"]["locations"] == []


def test_dates_and_amounts_preserved(monkeypatch):
    patch_gemini(monkeypatch)
    result = document_facts.extract_facts_from_extraction(extraction())

    assert result["facts"]["dates"][0]["value"] == "12 June 2026"
    assert result["facts"]["amounts"][0]["value"] == "Rs. 15000"


def test_duplicate_facts_deduplicated(monkeypatch):
    payload = gemini_payload()
    payload["amounts"].append(dict(payload["amounts"][0]))
    patch_gemini(monkeypatch, payload)

    result = document_facts.extract_facts_from_extraction(extraction())

    assert len(result["facts"]["amounts"]) == 1


def test_ambiguous_item_marked_uncertain(monkeypatch):
    payload = gemini_payload()
    payload["uncertain_items"] = [{"label": "party_role", "value": "Ramesh signed, role unclear", "source_page": 1, "source_excerpt": "Signed by Ramesh", "confidence": "low"}]
    patch_gemini(monkeypatch, payload)

    result = document_facts.extract_facts_from_extraction(extraction())

    assert result["facts"]["uncertain_items"][0]["confidence"] == "low"


def test_sensitive_identifier_removed(monkeypatch):
    payload = gemini_payload()
    payload["identifiers"].append({"label": "aadhaar", "value": "1234 5678 9012", "source_page": 1, "source_excerpt": "Aadhaar 1234 5678 9012", "confidence": "high"})
    patch_gemini(monkeypatch, payload)

    result = document_facts.extract_facts_from_extraction(extraction())
    text = str(result["facts"])

    assert "1234 5678 9012" not in text
    assert "[sensitive information omitted]" in text


def test_fact_extraction_unavailable_on_gemini_failure(monkeypatch):
    monkeypatch.setattr(document_facts, "GEMINI_API_KEY", "test-key")

    def fail(_extraction):
        raise RuntimeError("quota exhausted")

    monkeypatch.setattr(document_facts, "call_gemini_fact_extraction", fail)
    result = document_facts.extract_facts_from_extraction(extraction())

    assert result["status"] == "fact_extraction_unavailable"
    assert result["confirmation_required"] is False


def test_confirmation_required_and_user_correction_accepted(monkeypatch):
    patch_gemini(monkeypatch)
    result = document_facts.extract_facts_from_extraction(extraction())
    facts = result["facts"]
    facts["amounts"][0]["value"] = "Rs. 14000"

    confirmed = document_facts.confirm_facts(result["fact_extraction_id"], facts)

    assert confirmed.status == "confirmed"
    assert confirmed.confirmed_facts["amounts"][0]["value"] == "Rs. 14000"


def test_endpoint_fact_extraction_and_confirmation(monkeypatch):
    patch_gemini(monkeypatch)
    response = client.post("/api/documents/extract-facts", json={"extraction": extraction()})

    assert response.status_code == 200
    data = response.json()
    assert data["confirmation_required"] is True
    confirm = client.post(
        "/api/documents/confirm-facts",
        json={"fact_extraction_id": data["fact_extraction_id"], "confirmed_facts": data["facts"]},
    )
    assert confirm.status_code == 200
    assert confirm.json()["status"] == "confirmed"


def test_uploaded_facts_never_enter_faiss_or_corpus(monkeypatch):
    patch_gemini(monkeypatch)
    tracked_paths = [DOCUMENTS_DIR / "corpus_manifest.json", INDEX_PATH, METADATA_PATH]
    before = {path: path.stat().st_mtime_ns for path in tracked_paths if path.exists()}

    response = client.post("/api/documents/extract-facts", json={"extraction": extraction()})
    data = response.json()
    client.post(
        "/api/documents/confirm-facts",
        json={"fact_extraction_id": data["fact_extraction_id"], "confirmed_facts": data["facts"]},
    )

    after = {path: path.stat().st_mtime_ns for path in tracked_paths if path.exists()}
    assert after == before


def test_facts_never_appear_as_legal_citations(monkeypatch):
    patch_gemini(monkeypatch)
    response = client.post("/api/documents/extract-facts", json={"extraction": extraction()})
    data = response.json()

    assert "sources" not in data
    assert "citations" not in data
