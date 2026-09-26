from __future__ import annotations

import io
import sys
from pathlib import Path

import pytest
from docx import Document
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import complaint_drafter as drafter
import main

client = TestClient(main.app)


def base_intake_kwargs() -> dict:
    return dict(
        complainant_name="Suresh Kumar",
        complainant_address="12 Vasant Kunj, New Delhi",
        bank_name="State Bank of India",
        bank_branch_address="Vasant Kunj Branch, New Delhi",
        account_category="standard_account",
        transaction_date="2026-09-10",
        transaction_amount=45000,
        bank_communication_date="2026-09-10",
        date_first_reported_to_bank="2026-09-10",
        unauthorized_transaction_description="An unknown UPI transfer of Rs 45,000 to an unfamiliar UPI ID I never authorized.",
    )


# --- Validation ---


def test_non_positive_transaction_amount_gets_custom_message():
    with pytest.raises(ValidationError) as exc_info:
        drafter.BankFraudComplaintIntake(**{**base_intake_kwargs(), "transaction_amount": 0})
    assert "must be a positive amount" in str(exc_info.value)
    assert "greater than 0" not in str(exc_info.value)


def test_communication_before_transaction_fails():
    with pytest.raises(ValidationError) as exc_info:
        drafter.BankFraudComplaintIntake(
            **{**base_intake_kwargs(), "transaction_date": "2026-09-10", "bank_communication_date": "2026-09-05"}
        )
    assert "cannot be before transaction_date" in str(exc_info.value)


def test_future_transaction_date_fails():
    with pytest.raises(ValidationError):
        drafter.BankFraudComplaintIntake(**{**base_intake_kwargs(), "transaction_date": "2099-01-01"})


def test_short_description_fails():
    with pytest.raises(ValidationError):
        drafter.BankFraudComplaintIntake(
            **{**base_intake_kwargs(), "unauthorized_transaction_description": "Money gone"}
        )


# --- Liability tier computation (computed_field) ---


@pytest.mark.parametrize(
    "elapsed_days,expected_tier",
    [(0, "zero"), (3, "zero"), (4, "limited"), (7, "limited"), (8, "bank_policy"), (30, "bank_policy")],
)
def test_liability_tier_boundaries(elapsed_days, expected_tier):
    import datetime

    base_date = datetime.date(2026, 8, 1)
    intake = drafter.BankFraudComplaintIntake(
        **{
            **base_intake_kwargs(),
            "transaction_date": base_date.isoformat(),
            "bank_communication_date": base_date.isoformat(),
            "date_first_reported_to_bank": (base_date + datetime.timedelta(days=elapsed_days)).isoformat(),
        }
    )
    assert intake.elapsed_days_to_report == elapsed_days
    assert intake.liability_tier == expected_tier


def test_reporting_before_communication_clamps_to_zero_elapsed_days():
    # Edge case: reported before the bank's own communication (e.g. customer noticed first).
    # Should clamp to 0, not go negative.
    intake = drafter.BankFraudComplaintIntake(
        **{**base_intake_kwargs(), "bank_communication_date": "2026-09-10", "date_first_reported_to_bank": "2026-09-10"}
    )
    assert intake.elapsed_days_to_report == 0


@pytest.mark.parametrize(
    "account_category,expected_cap",
    [("bsbd_account", 5_000), ("standard_account", 10_000), ("high_value_account", 25_000)],
)
def test_liability_cap_matches_account_category(account_category, expected_cap):
    assert drafter.ACCOUNT_CATEGORY_LIABILITY_CAP_INR[drafter.AccountCategory(account_category)] == expected_cap


# --- Draft assembly ---


def _rendered_paragraphs(docx_bytes: bytes) -> list[str]:
    return [p.text for p in Document(io.BytesIO(docx_bytes)).paragraphs if p.text.strip()]


def test_draft_assembles_with_three_citations():
    intake = drafter.BankFraudComplaintIntake(**base_intake_kwargs())
    result = drafter.assemble_bank_fraud_complaint_draft(intake)
    assert result.docx_bytes.startswith(b"PK")
    assert result.citation_used["section_cite"] == "Guideline 8 (Table 2)"
    additional = [c["section_cite"] for c in result.additional_citations]
    assert additional == ["Guideline 7 (Table 1)", "Section 66D"]


def test_zero_liability_language_appears_in_document():
    intake = drafter.BankFraudComplaintIntake(**base_intake_kwargs())
    result = drafter.assemble_bank_fraud_complaint_draft(intake)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    joined = " ".join(paragraphs)
    assert "liability for this transaction is zero" in joined


def test_limited_liability_language_and_cap_appear_in_document():
    intake = drafter.BankFraudComplaintIntake(
        **{
            **base_intake_kwargs(),
            "transaction_date": "2026-09-01",
            "bank_communication_date": "2026-09-01",
            "date_first_reported_to_bank": "2026-09-05",
        }
    )
    result = drafter.assemble_bank_fraud_complaint_draft(intake)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    joined = " ".join(paragraphs)
    assert "limited to the lower of the transaction value" in joined
    assert "Rs. 10,000" in joined


def test_it_act_cybercrime_language_appears_in_document():
    intake = drafter.BankFraudComplaintIntake(**base_intake_kwargs())
    result = drafter.assemble_bank_fraud_complaint_draft(intake)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    assert any("National Cybercrime Reporting Portal" in p for p in paragraphs)
    assert any("Section 66D" in p for p in paragraphs)


def test_all_citations_resolve_against_corpus():
    assert drafter.resolve_citation_against_corpus(drafter.BANK_FRAUD_LIABILITY_TIER_CITATION)
    assert drafter.resolve_citation_against_corpus(drafter.BANK_FRAUD_LIABILITY_CAP_CITATION)
    assert drafter.resolve_citation_against_corpus(drafter.BANK_FRAUD_IT_ACT_CITATION)


def test_unresolved_citation_hard_fails(monkeypatch):
    intake = drafter.BankFraudComplaintIntake(**base_intake_kwargs())
    broken = {**drafter.BANK_FRAUD_IT_ACT_CITATION, "section_number": "999"}
    monkeypatch.setattr(drafter, "BANK_FRAUD_IT_ACT_CITATION", broken)
    with pytest.raises(drafter.CitationUnresolvedError):
        drafter.assemble_bank_fraud_complaint_draft(intake)


# --- Router / API-level tests ---


def test_api_validate_rejects_non_positive_amount():
    response = client.post(
        "/api/complaint-drafter/bank-fraud-complaint/validate",
        json={"intake": {**base_intake_kwargs(), "transaction_amount": 0}},
    )
    assert response.status_code == 400
    body = response.json()
    assert "must be a positive amount" in body["detail"]
    assert body["field"] == "transaction_amount"


def test_api_validate_returns_liability_tier():
    response = client.post(
        "/api/complaint-drafter/bank-fraud-complaint/validate",
        json={"intake": base_intake_kwargs()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["liability_tier"] == "zero"
    assert body["elapsed_days_to_report"] == 0


def test_api_draft_returns_citation_metadata():
    response = client.post(
        "/api/complaint-drafter/bank-fraud-complaint/draft",
        json={"intake": base_intake_kwargs()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citation_used"]["section_cite"] == "Guideline 8 (Table 2)"
    assert body["liability_tier"] == "zero"


def test_api_draft_docx_download_returns_docx_bytes():
    response = client.post(
        "/api/complaint-drafter/bank-fraud-complaint/draft/docx",
        json={"intake": base_intake_kwargs()},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert response.content.startswith(b"PK")
