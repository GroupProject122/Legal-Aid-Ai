from __future__ import annotations

import datetime
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import complaint_drafter as drafter
import main

client = TestClient(main.app)


def base_intake_kwargs() -> dict:
    return dict(
        tenant_name="Ramesh Kumar",
        tenant_address="B-12, Lajpat Nagar, New Delhi",
        landlord_name="Sunita Sharma",
        landlord_address="C-45, Defence Colony, New Delhi",
        property_address="B-12, Lajpat Nagar, New Delhi",
        monthly_rent=2500,
        tenancy_start_date=datetime.date(2019, 4, 1),
        relief_sought=["recovery_of_possession"],
    )


# --- Validation: rent cap ---


def test_rent_above_cap_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.TenancyEvictionIntake(
            **{**base_intake_kwargs(), "monthly_rent": 3600},
            grounds_for_eviction="arrears",
            arrears_amount=1000,
            arrears_period_months=1,
        )
    assert drafter.RENT_CAP_MESSAGE in str(exc_info.value)
    # The hard validator must carry a field-scoped loc (via _raise_field_validation_error),
    # not the empty loc a bare `raise ValueError(...)` from a model_validator would produce --
    # this is what lets the API response (and the frontend) key off a real `field`, not
    # string-match the message text.
    error = exc_info.value.errors()[0]
    assert error["loc"] == ("monthly_rent",)
    assert error["msg"] == drafter.RENT_CAP_MESSAGE


def test_rent_at_cap_boundary_is_allowed():
    intake = drafter.TenancyEvictionIntake(
        **{**base_intake_kwargs(), "monthly_rent": 3500},
        grounds_for_eviction="arrears",
        arrears_amount=1000,
        arrears_period_months=1,
    )
    assert intake.monthly_rent == 3500


# --- Validation: conditional required fields ---


def test_arrears_ground_without_amount_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.TenancyEvictionIntake(**base_intake_kwargs(), grounds_for_eviction="arrears")
    assert "arrears_amount" in str(exc_info.value)
    assert exc_info.value.errors()[0]["loc"] == ("arrears_amount",)


def test_subletting_ground_without_details_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.TenancyEvictionIntake(**base_intake_kwargs(), grounds_for_eviction="subletting")
    assert exc_info.value.errors()[0]["loc"] == ("subletting_details",)


# --- Validation: tenancy start date ---


def test_future_tenancy_start_date_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.TenancyEvictionIntake(
            **{**base_intake_kwargs(), "tenancy_start_date": datetime.date.today() + datetime.timedelta(days=1)},
            grounds_for_eviction="arrears",
            arrears_amount=1000,
            arrears_period_months=1,
        )
    assert exc_info.value.errors()[0]["loc"] == ("tenancy_start_date",)


# --- Draft assembly: all five grounds render without error ---


@pytest.mark.parametrize(
    "ground,extra",
    [
        ("arrears", {"arrears_amount": 45000, "arrears_period_months": 6}),
        ("subletting", {"subletting_details": "Sublet to a third party without consent."}),
        ("damage", {"damage_description": "Removed a load-bearing wall without permission."}),
        ("bona_fide_requirement", {"bona_fide_reason": "Landlord's son needs the flat to live in."}),
    ],
)
def test_each_ground_assembles_a_draft(ground, extra):
    intake = drafter.TenancyEvictionIntake(**base_intake_kwargs(), grounds_for_eviction=ground, **extra)
    result = drafter.assemble_tenancy_eviction_draft(intake)
    assert result.docx_bytes.startswith(b"PK")  # docx is a zip archive
    assert result.citation_used["section_number"] == "14"
    assert result.citation_review_required is False


def test_unauthorized_construction_ground_was_deliberately_dropped():
    # Section 14(1)(k) is a practitioner convention, not a verbatim textual match -- too weak a
    # citation basis to ship. Guards against silently reinstating it without manual legal review.
    assert "unauthorized_construction" not in {ground.value for ground in drafter.EvictionGround}
    assert not (drafter.CLAUSES_DIR / "tenancy_unauthorized_construction_ground.txt").exists()


# --- Pre-output hard-fail checks ---


def test_unresolved_citation_hard_fails(monkeypatch):
    intake = drafter.TenancyEvictionIntake(
        **base_intake_kwargs(), grounds_for_eviction="arrears", arrears_amount=1000, arrears_period_months=1
    )
    broken_citation = {**drafter.CLAUSE_CITATIONS[drafter.EvictionGround.arrears], "section_number": "999"}
    monkeypatch.setitem(drafter.CLAUSE_CITATIONS, drafter.EvictionGround.arrears, broken_citation)
    with pytest.raises(drafter.CitationUnresolvedError):
        drafter.assemble_tenancy_eviction_draft(intake)


def test_clause_referencing_unwhitelisted_field_hard_fails(monkeypatch, tmp_path):
    bad_clause = tmp_path / "bad_clause.txt"
    bad_clause.write_text("This references {{ some_field_not_on_the_whitelist }}.")
    monkeypatch.setattr(drafter, "CLAUSES_DIR", tmp_path)
    intake = drafter.TenancyEvictionIntake(
        **base_intake_kwargs(), grounds_for_eviction="arrears", arrears_amount=1000, arrears_period_months=1
    )
    monkeypatch.setitem(drafter.CLAUSE_FILE_BY_GROUND, drafter.EvictionGround.arrears, "bad_clause.txt")
    with pytest.raises(drafter.FieldProvenanceError):
        drafter.assemble_tenancy_eviction_draft(intake)


def test_all_clause_citations_resolve_against_corpus():
    for ground, citation in drafter.CLAUSE_CITATIONS.items():
        assert drafter.resolve_citation_against_corpus(citation), (
            f"Citation for ground {ground.value!r} does not resolve against the parsed corpus"
        )


# --- PDF conversion: missing LibreOffice is a clear, typed error ---


def test_pdf_conversion_without_libreoffice_raises_clear_error(monkeypatch):
    monkeypatch.setattr(drafter.shutil, "which", lambda _name: None)
    with pytest.raises(drafter.PdfConversionError):
        drafter.convert_docx_bytes_to_pdf(b"not a real docx")


# --- Router / API-level tests ---


def test_api_validate_rejects_rent_above_cap():
    response = client.post(
        "/api/complaint-drafter/tenancy-eviction/validate",
        json={"intake": {**base_intake_kwargs_json(), "monthly_rent": 10000}},
    )
    assert response.status_code == 400
    body = response.json()
    assert "Rs. 3,500" in body["detail"]
    # Structured field, not inferred from the message text -- this is what the frontend now
    # reads directly instead of string-matching the detail for a field name.
    assert body["field"] == "monthly_rent"


def test_api_validate_accepts_valid_intake():
    response = client.post(
        "/api/complaint-drafter/tenancy-eviction/validate",
        json={"intake": base_intake_kwargs_json()},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "valid"


def test_api_draft_returns_citation_metadata():
    response = client.post(
        "/api/complaint-drafter/tenancy-eviction/draft",
        json={"intake": base_intake_kwargs_json()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citation_used"]["section_cite"] == "Section 14(1)(a)"


def test_api_draft_docx_download_returns_docx_bytes():
    response = client.post(
        "/api/complaint-drafter/tenancy-eviction/draft/docx",
        json={"intake": base_intake_kwargs_json()},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert response.content.startswith(b"PK")


def base_intake_kwargs_json() -> dict:
    kwargs = base_intake_kwargs()
    kwargs["tenancy_start_date"] = kwargs["tenancy_start_date"].isoformat()
    kwargs["grounds_for_eviction"] = "arrears"
    kwargs["arrears_amount"] = 45000
    kwargs["arrears_period_months"] = 6
    return kwargs
