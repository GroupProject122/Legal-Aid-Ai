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
        applicant_name="Anita Verma",
        applicant_address="14 Green Park, New Delhi",
        public_authority_name="Delhi Jal Board",
        public_authority_address="Varunalaya Phase II, Karol Bagh, New Delhi",
        information_sought="Certified copies of all water quality test reports for the Karol Bagh zone from January 2026 to June 2026.",
        preferred_mode="certified_copies",
        is_bpl_applicant=False,
    )


# --- Validation: vague/empty information request ---


def test_short_information_sought_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.RTIApplicationIntake(**{**base_intake_kwargs(), "information_sought": "Water report"})
    assert "at least 20 characters" in str(exc_info.value)
    assert exc_info.value.errors()[0]["loc"] == ("information_sought",)


def test_empty_information_sought_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.RTIApplicationIntake(**{**base_intake_kwargs(), "information_sought": ""})
    assert exc_info.value.errors()[0]["loc"] == ("information_sought",)


def test_missing_required_field_fails_validation():
    kwargs = base_intake_kwargs()
    del kwargs["public_authority_name"]
    with pytest.raises(ValidationError) as exc_info:
        drafter.RTIApplicationIntake(**kwargs)
    assert exc_info.value.errors()[0]["loc"] == ("public_authority_name",)


# --- No "reason" field exists on this form, by design ---


def test_intake_model_has_no_reason_field():
    # Section 6(2) of the Act entitles an applicant to withhold the reason for a request
    # entirely -- this form must not ask for one, and the clause text says so explicitly.
    fields = drafter.RTIApplicationIntake.model_fields
    assert not any("reason" in name for name in fields)


# --- Draft assembly ---


def _rendered_paragraphs(docx_bytes: bytes) -> list[str]:
    return [p.text for p in Document(io.BytesIO(docx_bytes)).paragraphs if p.text.strip()]


def test_draft_assembles_without_error():
    intake = drafter.RTIApplicationIntake(**base_intake_kwargs())
    result = drafter.assemble_rti_application_draft(intake)
    assert result.docx_bytes.startswith(b"PK")  # docx is a zip archive
    assert result.citation_review_required is False
    assert result.citation_used["section_cite"] == "Section 6(1)"
    assert result.additional_citations == []


def test_information_sought_and_preferred_mode_appear_in_drafted_document():
    intake = drafter.RTIApplicationIntake(**base_intake_kwargs())
    result = drafter.assemble_rti_application_draft(intake)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    joined = " ".join(paragraphs)
    assert "water quality test reports" in joined
    assert "Certified copies of the relevant documents/records" in joined
    assert "Delhi Jal Board" in joined


def test_no_reason_is_required_line_appears_in_drafted_document():
    # The clause text must say this explicitly (Section 6(2)), not just happen to omit a
    # reason field -- a user reading the draft should see their right to withhold it stated.
    intake = drafter.RTIApplicationIntake(**base_intake_kwargs())
    result = drafter.assemble_rti_application_draft(intake)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    assert any("not required to give" in p for p in paragraphs)


def test_bpl_applicant_gets_fee_exemption_clause_and_additional_citation():
    intake = drafter.RTIApplicationIntake(**{**base_intake_kwargs(), "is_bpl_applicant": True})
    result = drafter.assemble_rti_application_draft(intake)
    assert result.additional_citations == [drafter.RTI_BPL_FEE_EXEMPTION_CITATION]
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    assert any("below the poverty line" in p for p in paragraphs)
    assert any("Section 7(5), proviso" in p for p in paragraphs)


def test_non_bpl_applicant_has_no_fee_exemption_clause():
    intake = drafter.RTIApplicationIntake(**base_intake_kwargs())
    result = drafter.assemble_rti_application_draft(intake)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    assert not any("below the poverty line" in p for p in paragraphs)


@pytest.mark.parametrize("preferred_mode", ["certified_copies", "inspection_of_records", "electronic_format"])
def test_each_preferred_mode_assembles_a_draft(preferred_mode):
    intake = drafter.RTIApplicationIntake(**{**base_intake_kwargs(), "preferred_mode": preferred_mode})
    result = drafter.assemble_rti_application_draft(intake)
    assert result.docx_bytes.startswith(b"PK")


# --- Pre-output hard-fail checks ---


def test_unresolved_citation_hard_fails(monkeypatch):
    intake = drafter.RTIApplicationIntake(**base_intake_kwargs())
    broken = {**drafter.RTI_REQUEST_CITATION, "section_number": "999"}
    monkeypatch.setattr(drafter, "RTI_REQUEST_CITATION", broken)
    with pytest.raises(drafter.CitationUnresolvedError):
        drafter.assemble_rti_application_draft(intake)


def test_unresolved_bpl_citation_hard_fails_only_when_bpl_selected(monkeypatch):
    broken = {**drafter.RTI_BPL_FEE_EXEMPTION_CITATION, "section_number": "999"}
    monkeypatch.setattr(drafter, "RTI_BPL_FEE_EXEMPTION_CITATION", broken)

    # Non-BPL applicant: the broken BPL citation is never checked, so this still succeeds.
    intake = drafter.RTIApplicationIntake(**base_intake_kwargs())
    result = drafter.assemble_rti_application_draft(intake)
    assert result.docx_bytes.startswith(b"PK")

    # BPL applicant: now it must hard-fail.
    intake_bpl = drafter.RTIApplicationIntake(**{**base_intake_kwargs(), "is_bpl_applicant": True})
    with pytest.raises(drafter.CitationUnresolvedError):
        drafter.assemble_rti_application_draft(intake_bpl)


def test_all_citations_resolve_against_corpus():
    assert drafter.resolve_citation_against_corpus(drafter.RTI_REQUEST_CITATION)
    assert drafter.resolve_citation_against_corpus(drafter.RTI_BPL_FEE_EXEMPTION_CITATION)


# --- Router / API-level tests ---


def base_intake_kwargs_json() -> dict:
    return base_intake_kwargs()


def test_api_validate_rejects_short_information_sought():
    response = client.post(
        "/api/complaint-drafter/rti-application/validate",
        json={"intake": {**base_intake_kwargs_json(), "information_sought": "Water report"}},
    )
    assert response.status_code == 400
    body = response.json()
    assert "at least 20 characters" in body["detail"]
    assert body["field"] == "information_sought"


def test_api_validate_accepts_valid_intake():
    response = client.post(
        "/api/complaint-drafter/rti-application/validate",
        json={"intake": base_intake_kwargs_json()},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "valid"


def test_api_draft_returns_citation_metadata():
    response = client.post(
        "/api/complaint-drafter/rti-application/draft",
        json={"intake": base_intake_kwargs_json()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citation_used"]["section_cite"] == "Section 6(1)"
    assert body["additional_citations"] == []


def test_api_draft_returns_bpl_additional_citation():
    response = client.post(
        "/api/complaint-drafter/rti-application/draft",
        json={"intake": {**base_intake_kwargs_json(), "is_bpl_applicant": True}},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["additional_citations"][0]["section_cite"] == "Section 7(5), proviso"


def test_api_draft_docx_download_returns_docx_bytes():
    response = client.post(
        "/api/complaint-drafter/rti-application/draft/docx",
        json={"intake": base_intake_kwargs_json()},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert response.content.startswith(b"PK")
