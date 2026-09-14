from __future__ import annotations

import datetime
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
        complainant_name="Priya Nair",
        complainant_address="12 MG Road, Bengaluru",
        opposite_party_name="GlowSkin Cosmetics",
        opposite_party_address="9 Ring Road, Bengaluru",
        advertisement_or_practice_description="Print ad describing the cream as clinically proven to remove wrinkles in 3 days",
        platform_or_medium="print",
        date_encountered=datetime.date(2025, 6, 1),
        how_it_caused_loss="I purchased the cream relying on this claim and it had no effect at all on my skin.",
        relief_sought=["discontinuation_of_practice"],
    )


# --- Validation: vague/empty loss description ---


def test_short_loss_description_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.MisleadingAdvertisementIntake(
            **{**base_intake_kwargs(), "how_it_caused_loss": "It didn't work."},
            claim_type="false_claim_about_goods",
        )
    assert "at least 20 characters" in str(exc_info.value)
    assert exc_info.value.errors()[0]["loc"] == ("how_it_caused_loss",)


def test_empty_loss_description_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.MisleadingAdvertisementIntake(
            **{**base_intake_kwargs(), "how_it_caused_loss": ""},
            claim_type="false_claim_about_goods",
        )
    assert exc_info.value.errors()[0]["loc"] == ("how_it_caused_loss",)


# --- Validation: date and conditional fields ---


def test_future_date_encountered_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.MisleadingAdvertisementIntake(
            **{**base_intake_kwargs(), "date_encountered": datetime.date.today() + datetime.timedelta(days=1)},
            claim_type="false_claim_about_goods",
        )
    assert exc_info.value.errors()[0]["loc"] == ("date_encountered",)


def test_compensation_relief_without_amount_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.MisleadingAdvertisementIntake(
            **{**base_intake_kwargs(), "relief_sought": ["compensation"]},
            claim_type="false_claim_about_goods",
        )
    assert "incomplete" in str(exc_info.value)
    assert exc_info.value.errors()[0]["loc"] == ("compensation_amount",)


def test_amount_paid_is_optional():
    # Not every dark-pattern claim involves a completed purchase.
    intake = drafter.MisleadingAdvertisementIntake(
        **base_intake_kwargs(), claim_type="dark_pattern_deceptive_design"
    )
    assert intake.amount_paid is None


def _rendered_paragraphs(docx_bytes: bytes) -> list[str]:
    return [p.text for p in Document(io.BytesIO(docx_bytes)).paragraphs if p.text.strip()]


def test_amount_paid_appears_in_drafted_document_when_supplied():
    intake = drafter.MisleadingAdvertisementIntake(
        **{**base_intake_kwargs(), "amount_paid": 499}, claim_type="dark_pattern_deceptive_design"
    )
    result = drafter.assemble_misleading_advertisement_draft(intake)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    assert "4. Amount paid: Rs. 499." in paragraphs


def test_amount_paid_line_absent_from_drafted_document_when_not_supplied():
    intake = drafter.MisleadingAdvertisementIntake(**base_intake_kwargs(), claim_type="dark_pattern_deceptive_design")
    result = drafter.assemble_misleading_advertisement_draft(intake)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    assert not any("Amount paid" in p for p in paragraphs)
    # And nothing else broke -- the particulars section still ends cleanly at item 3.
    assert any(p.startswith("3. Date encountered:") for p in paragraphs)


# --- Draft assembly: all five claim types render without error ---


@pytest.mark.parametrize(
    "claim_type,expect_review",
    [
        ("false_claim_about_goods", False),
        ("misleading_price_representation", False),
        ("dark_pattern_deceptive_design", True),
        ("false_guarantee_or_warranty", False),
        ("surrogate_advertisement", False),
    ],
)
def test_each_claim_type_assembles_a_draft(claim_type, expect_review):
    intake = drafter.MisleadingAdvertisementIntake(**base_intake_kwargs(), claim_type=claim_type)
    result = drafter.assemble_misleading_advertisement_draft(intake)
    assert result.docx_bytes.startswith(b"PK")  # docx is a zip archive
    assert result.citation_review_required is expect_review


def test_surrogate_advertisement_cites_guideline_not_section():
    intake = drafter.MisleadingAdvertisementIntake(**base_intake_kwargs(), claim_type="surrogate_advertisement")
    result = drafter.assemble_misleading_advertisement_draft(intake)
    assert result.citation_used["authority_level"] == "official_guidance"
    assert result.citation_used["source_file"] == "consumer/misleading_ads_guidelines_2022.pdf"


def test_dark_pattern_flags_review_with_a_real_underlying_citation():
    # Unlike tenancy's dropped unauthorized_construction ground, this one is kept: there IS a
    # checked citation behind it, just a weaker one (guideline-level, framed in the alternative).
    intake = drafter.MisleadingAdvertisementIntake(**base_intake_kwargs(), claim_type="dark_pattern_deceptive_design")
    result = drafter.assemble_misleading_advertisement_draft(intake)
    assert result.citation_review_required is True
    assert result.warnings
    assert drafter.resolve_citation_against_corpus(result.citation_used)


# --- Pre-output hard-fail checks ---


def test_unresolved_citation_hard_fails(monkeypatch):
    intake = drafter.MisleadingAdvertisementIntake(**base_intake_kwargs(), claim_type="false_claim_about_goods")
    broken = {**drafter.ADS_CLAUSE_CITATIONS[drafter.AdvertisementClaimType.false_claim_about_goods], "section_number": "999"}
    monkeypatch.setitem(drafter.ADS_CLAUSE_CITATIONS, drafter.AdvertisementClaimType.false_claim_about_goods, broken)
    with pytest.raises(drafter.CitationUnresolvedError):
        drafter.assemble_misleading_advertisement_draft(intake)


def test_all_clause_citations_resolve_against_corpus():
    for claim_type, citation in drafter.ADS_CLAUSE_CITATIONS.items():
        assert drafter.resolve_citation_against_corpus(citation), (
            f"Citation for claim type {claim_type.value!r} does not resolve against the parsed corpus"
        )


# --- Router / API-level tests ---


def base_intake_kwargs_json() -> dict:
    kwargs = base_intake_kwargs()
    kwargs["date_encountered"] = kwargs["date_encountered"].isoformat()
    kwargs["claim_type"] = "false_claim_about_goods"
    return kwargs


def test_api_validate_rejects_short_loss_description():
    response = client.post(
        "/api/complaint-drafter/consumer-misleading-ads/validate",
        json={"intake": {**base_intake_kwargs_json(), "how_it_caused_loss": "meh"}},
    )
    assert response.status_code == 400
    body = response.json()
    assert "at least 20 characters" in body["detail"]
    assert body["field"] == "how_it_caused_loss"


def test_api_validate_accepts_valid_intake():
    response = client.post(
        "/api/complaint-drafter/consumer-misleading-ads/validate",
        json={"intake": base_intake_kwargs_json()},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "valid"


def test_api_draft_returns_citation_metadata():
    response = client.post(
        "/api/complaint-drafter/consumer-misleading-ads/draft",
        json={"intake": base_intake_kwargs_json()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citation_used"]["section_cite"] == "Section 2(28)(i)"


def test_api_draft_docx_download_returns_docx_bytes():
    response = client.post(
        "/api/complaint-drafter/consumer-misleading-ads/draft/docx",
        json={"intake": base_intake_kwargs_json()},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert response.content.startswith(b"PK")
