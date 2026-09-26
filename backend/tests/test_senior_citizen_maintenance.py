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
        applicant_name="Ram Prasad Sharma",
        applicant_address="45 Model Town, Delhi",
        applicant_age=68,
        respondent_relationship="child",
        respondent_name="Suresh Sharma",
        respondent_address="12 Rohini Sector 9, Delhi",
        neglect_description="My son has refused to provide any financial support or food for the last six months.",
        requested_monthly_maintenance_amount=8000,
    )


# --- Validation ---


def test_applicant_under_60_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.SeniorCitizenMaintenanceIntake(**{**base_intake_kwargs(), "applicant_age": 55})
    assert "at least 60" in str(exc_info.value)
    assert exc_info.value.errors()[0]["loc"] == ("applicant_age",)


def test_amount_over_statutory_cap_fails_with_custom_message():
    with pytest.raises(ValidationError) as exc_info:
        drafter.SeniorCitizenMaintenanceIntake(
            **{**base_intake_kwargs(), "requested_monthly_maintenance_amount": 15000}
        )
    assert "exceeds Rs. 10,000" in str(exc_info.value)
    assert "greater than 0" not in str(exc_info.value)


def test_non_positive_amount_gets_custom_message_not_pydantics_generic_one():
    with pytest.raises(ValidationError) as exc_info:
        drafter.SeniorCitizenMaintenanceIntake(
            **{**base_intake_kwargs(), "requested_monthly_maintenance_amount": 0}
        )
    assert "must be a positive amount" in str(exc_info.value)
    assert "greater than 0" not in str(exc_info.value)


def test_missing_relative_property_connection_fails():
    kwargs = {
        **base_intake_kwargs(),
        "respondent_relationship": "relative_of_childless_senior_citizen",
    }
    with pytest.raises(ValidationError) as exc_info:
        drafter.SeniorCitizenMaintenanceIntake(**kwargs)
    assert exc_info.value.errors()[0]["loc"] == ("relative_property_connection",)


def test_stray_relative_property_connection_fails_for_child_respondent():
    kwargs = {**base_intake_kwargs(), "relative_property_connection": "would inherit my property"}
    with pytest.raises(ValidationError) as exc_info:
        drafter.SeniorCitizenMaintenanceIntake(**kwargs)
    assert exc_info.value.errors()[0]["loc"] == ("relative_property_connection",)


def test_short_neglect_description_fails():
    with pytest.raises(ValidationError):
        drafter.SeniorCitizenMaintenanceIntake(**{**base_intake_kwargs(), "neglect_description": "He ignores me"})


# --- Draft assembly ---


def _rendered_paragraphs(docx_bytes: bytes) -> list[str]:
    return [p.text for p in Document(io.BytesIO(docx_bytes)).paragraphs if p.text.strip()]


def test_draft_assembles_without_error_for_child_respondent():
    intake = drafter.SeniorCitizenMaintenanceIntake(**base_intake_kwargs())
    result = drafter.assemble_senior_citizen_maintenance_draft(intake)
    assert result.docx_bytes.startswith(b"PK")
    assert result.citation_used["section_cite"] == "Section 4(1)(i)"
    assert result.additional_citations[0]["section_cite"] == "Section 9(2)"


def test_draft_assembles_for_relative_of_childless_senior_citizen():
    intake = drafter.SeniorCitizenMaintenanceIntake(
        **{
            **base_intake_kwargs(),
            "respondent_relationship": "relative_of_childless_senior_citizen",
            "relative_property_connection": "occupies my ancestral house and would inherit it as my nearest heir",
        }
    )
    result = drafter.assemble_senior_citizen_maintenance_draft(intake)
    assert result.citation_used["section_cite"] == "Section 4(1)(ii)"
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    assert any("would inherit it as my nearest heir" in p for p in paragraphs)


def test_statutory_cap_citation_appears_in_drafted_document():
    intake = drafter.SeniorCitizenMaintenanceIntake(**base_intake_kwargs())
    result = drafter.assemble_senior_citizen_maintenance_draft(intake)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    assert any("Section 9(2)" in p for p in paragraphs)


def test_all_citations_resolve_against_corpus():
    for relationship in drafter.RespondentRelationship:
        assert drafter.resolve_citation_against_corpus(drafter.RESPONDENT_RELATIONSHIP_CITATIONS[relationship])
    assert drafter.resolve_citation_against_corpus(drafter.MAINTENANCE_AMOUNT_CAP_CITATION)


def test_unresolved_citation_hard_fails(monkeypatch):
    intake = drafter.SeniorCitizenMaintenanceIntake(**base_intake_kwargs())
    broken = {
        drafter.RespondentRelationship.child: {**drafter.RESPONDENT_RELATIONSHIP_CITATIONS[drafter.RespondentRelationship.child], "section_number": "999"},
        drafter.RespondentRelationship.relative_of_childless_senior_citizen: drafter.RESPONDENT_RELATIONSHIP_CITATIONS[
            drafter.RespondentRelationship.relative_of_childless_senior_citizen
        ],
    }
    monkeypatch.setattr(drafter, "RESPONDENT_RELATIONSHIP_CITATIONS", broken)
    with pytest.raises(drafter.CitationUnresolvedError):
        drafter.assemble_senior_citizen_maintenance_draft(intake)


# --- Router / API-level tests ---


def test_api_validate_rejects_over_cap_amount():
    response = client.post(
        "/api/complaint-drafter/senior-citizen-maintenance/validate",
        json={"intake": {**base_intake_kwargs(), "requested_monthly_maintenance_amount": 15000}},
    )
    assert response.status_code == 400
    body = response.json()
    assert "exceeds Rs. 10,000" in body["detail"]
    assert body["field"] == "requested_monthly_maintenance_amount"


def test_api_draft_returns_citation_metadata():
    response = client.post(
        "/api/complaint-drafter/senior-citizen-maintenance/draft",
        json={"intake": base_intake_kwargs()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citation_used"]["section_cite"] == "Section 4(1)(i)"
    assert body["additional_citations"][0]["section_cite"] == "Section 9(2)"


def test_api_draft_docx_download_returns_docx_bytes():
    response = client.post(
        "/api/complaint-drafter/senior-citizen-maintenance/draft/docx",
        json={"intake": base_intake_kwargs()},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert response.content.startswith(b"PK")
