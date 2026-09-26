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
        tenant_name="Priya Nair",
        tenant_address="23 Lajpat Nagar, New Delhi",
        landlord_name="Mohan Gupta",
        landlord_address="45 Greater Kailash, New Delhi",
        property_address="23 Lajpat Nagar, New Delhi",
        essential_supply_type="water",
        date_supply_cut_off="2026-09-01",
        how_supply_was_cut_off="The landlord instructed the caretaker to disconnect the main water line after a rent dispute.",
    )


# --- Validation ---


def test_short_description_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.TenantEssentialSupplyIntake(**{**base_intake_kwargs(), "how_supply_was_cut_off": "Water stopped"})
    assert "at least 20 characters" in str(exc_info.value)
    assert exc_info.value.errors()[0]["loc"] == ("how_supply_was_cut_off",)


def test_future_cutoff_date_fails_validation():
    with pytest.raises(ValidationError):
        drafter.TenantEssentialSupplyIntake(**{**base_intake_kwargs(), "date_supply_cut_off": "2099-01-01"})


def test_missing_required_field_fails_validation():
    kwargs = base_intake_kwargs()
    del kwargs["property_address"]
    with pytest.raises(ValidationError) as exc_info:
        drafter.TenantEssentialSupplyIntake(**kwargs)
    assert exc_info.value.errors()[0]["loc"] == ("property_address",)


# --- Draft assembly ---


def _rendered_paragraphs(docx_bytes: bytes) -> list[str]:
    return [p.text for p in Document(io.BytesIO(docx_bytes)).paragraphs if p.text.strip()]


def test_draft_assembles_without_error():
    intake = drafter.TenantEssentialSupplyIntake(**base_intake_kwargs())
    result = drafter.assemble_tenant_essential_supply_draft(intake)
    assert result.docx_bytes.startswith(b"PK")
    assert result.citation_used["section_cite"] == "Section 45"


@pytest.mark.parametrize(
    "supply_type",
    ["water", "electricity", "lights_in_passages_and_staircases", "conservancy_and_sanitary_services"],
)
def test_each_essential_supply_type_assembles_a_draft(supply_type):
    intake = drafter.TenantEssentialSupplyIntake(**{**base_intake_kwargs(), "essential_supply_type": supply_type})
    result = drafter.assemble_tenant_essential_supply_draft(intake)
    assert result.docx_bytes.startswith(b"PK")
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    assert any(drafter.ESSENTIAL_SUPPLY_TYPE_LABEL[drafter.EssentialSupplyType(supply_type)] in p for p in paragraphs)


def test_landlord_stated_reason_appears_when_supplied():
    intake = drafter.TenantEssentialSupplyIntake(
        **{**base_intake_kwargs(), "landlord_stated_reason": "He claimed I owed unpaid maintenance charges."}
    )
    result = drafter.assemble_tenant_essential_supply_draft(intake)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    assert any("unpaid maintenance charges" in p for p in paragraphs)


def test_no_stated_reason_line_when_omitted():
    intake = drafter.TenantEssentialSupplyIntake(**base_intake_kwargs())
    result = drafter.assemble_tenant_essential_supply_draft(intake)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    assert not any("does not amount to just and sufficient cause" in p for p in paragraphs)


def test_all_citations_resolve_against_corpus():
    assert drafter.resolve_citation_against_corpus(drafter.ESSENTIAL_SUPPLY_CITATION)


def test_unresolved_citation_hard_fails(monkeypatch):
    intake = drafter.TenantEssentialSupplyIntake(**base_intake_kwargs())
    broken = {**drafter.ESSENTIAL_SUPPLY_CITATION, "section_number": "999"}
    monkeypatch.setattr(drafter, "ESSENTIAL_SUPPLY_CITATION", broken)
    with pytest.raises(drafter.CitationUnresolvedError):
        drafter.assemble_tenant_essential_supply_draft(intake)


# --- Router / API-level tests ---


def test_api_validate_rejects_short_description():
    response = client.post(
        "/api/complaint-drafter/tenant-essential-supply/validate",
        json={"intake": {**base_intake_kwargs(), "how_supply_was_cut_off": "Water stopped"}},
    )
    assert response.status_code == 400
    body = response.json()
    assert "at least 20 characters" in body["detail"]
    assert body["field"] == "how_supply_was_cut_off"


def test_api_draft_returns_citation_metadata():
    response = client.post(
        "/api/complaint-drafter/tenant-essential-supply/draft",
        json={"intake": base_intake_kwargs()},
    )
    assert response.status_code == 200
    assert response.json()["citation_used"]["section_cite"] == "Section 45"


def test_api_draft_docx_download_returns_docx_bytes():
    response = client.post(
        "/api/complaint-drafter/tenant-essential-supply/draft/docx",
        json={"intake": base_intake_kwargs()},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert response.content.startswith(b"PK")
