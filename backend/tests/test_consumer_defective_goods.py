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
        complainant_name="Priya Nair",
        complainant_address="12 MG Road, Bengaluru",
        opposite_party_name="ABC Mobiles Pvt Ltd",
        opposite_party_address="45 Commercial St, Bengaluru",
        goods_or_service_description="Smartphone Model X",
        transaction_date=datetime.date(2025, 6, 1),
        amount_paid=25000,
        prior_complaint_made=False,
        relief_sought=["refund"],
    )


# --- Validation: garbage input ---


def test_non_positive_amount_paid_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.ConsumerDefectiveGoodsIntake(
            **{**base_intake_kwargs(), "amount_paid": 0},
            defect_or_deficiency_type="defective_goods",
            defect_description="Screen cracked on first use.",
        )
    assert exc_info.value.errors()[0]["loc"] == ("amount_paid",)


def test_future_transaction_date_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.ConsumerDefectiveGoodsIntake(
            **{**base_intake_kwargs(), "transaction_date": datetime.date.today() + datetime.timedelta(days=1)},
            defect_or_deficiency_type="defective_goods",
            defect_description="Screen cracked on first use.",
        )
    assert exc_info.value.errors()[0]["loc"] == ("transaction_date",)


# --- Validation: conditional required fields ---


def test_prior_complaint_made_without_response_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.ConsumerDefectiveGoodsIntake(
            **{**base_intake_kwargs(), "prior_complaint_made": True},
            defect_or_deficiency_type="defective_goods",
            defect_description="Screen cracked on first use.",
        )
    assert "incomplete" in str(exc_info.value)
    assert exc_info.value.errors()[0]["loc"] == ("prior_complaint_response",)


def test_prior_complaint_not_made_with_stray_response_fails_validation():
    # Inverse of the case above: prior_complaint_made=False with a non-empty response used to
    # be accepted silently -- the base template's conditional block meant the text never reached
    # the drafted document, so the input was discarded without telling the user. Now rejected.
    with pytest.raises(ValidationError) as exc_info:
        drafter.ConsumerDefectiveGoodsIntake(
            **{**base_intake_kwargs(), "prior_complaint_response": "Seller said this is not covered."},
            defect_or_deficiency_type="defective_goods",
            defect_description="Screen cracked on first use.",
        )
    assert exc_info.value.errors()[0]["loc"] == ("prior_complaint_response",)


def test_prior_complaint_not_made_with_whitespace_response_is_treated_as_empty():
    # Whitespace-only is correctly treated as "no response", same as elsewhere in this module.
    intake = drafter.ConsumerDefectiveGoodsIntake(
        **{**base_intake_kwargs(), "prior_complaint_response": "   "},
        defect_or_deficiency_type="defective_goods",
        defect_description="Screen cracked on first use.",
    )
    assert intake.prior_complaint_response == "   "


def test_compensation_relief_without_amount_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.ConsumerDefectiveGoodsIntake(
            **{**base_intake_kwargs(), "relief_sought": ["compensation"]},
            defect_or_deficiency_type="defective_goods",
            defect_description="Screen cracked on first use.",
        )
    assert "incomplete" in str(exc_info.value)
    assert exc_info.value.errors()[0]["loc"] == ("compensation_amount",)


def test_compensation_relief_with_amount_passes_validation():
    intake = drafter.ConsumerDefectiveGoodsIntake(
        **{**base_intake_kwargs(), "relief_sought": ["refund", "compensation"], "compensation_amount": 2000},
        defect_or_deficiency_type="defective_goods",
        defect_description="Screen cracked on first use.",
    )
    assert intake.compensation_amount == 2000


# --- Forum-tier classification (Sections 34/47/58, read with the 2021 Jurisdiction Rules) ---


@pytest.mark.parametrize(
    "amount_paid,expected_tier",
    [
        (5_000_000, "district"),  # exactly Rs. 50 lakh -- "does not exceed" is inclusive
        (5_000_001, "state"),
        (20_000_000, "state"),  # exactly Rs. 2 crore -- "does not exceed" is inclusive
        (20_000_001, "national"),
    ],
)
def test_forum_tier_boundaries(amount_paid, expected_tier):
    intake = drafter.ConsumerDefectiveGoodsIntake(
        **{**base_intake_kwargs(), "amount_paid": amount_paid},
        defect_or_deficiency_type="defective_goods",
        defect_description="Screen cracked on first use.",
    )
    assert intake.forum_tier == expected_tier


def test_forum_tier_is_based_on_amount_paid_not_compensation():
    # The Act's own text is "value of the goods or services paid as consideration" -- it does not
    # mention compensation claimed. A large compensation ask must not push the tier up.
    intake = drafter.ConsumerDefectiveGoodsIntake(
        **{**base_intake_kwargs(), "amount_paid": 1000, "relief_sought": ["compensation"], "compensation_amount": 50_000_000},
        defect_or_deficiency_type="defective_goods",
        defect_description="Screen cracked on first use.",
    )
    assert intake.forum_tier == "district"


# --- Draft assembly: all five grounds render without error ---


@pytest.mark.parametrize(
    "ground",
    ["defective_goods", "deficient_service", "short_delivery", "spurious_goods", "unfair_trade_practice_in_sale"],
)
def test_each_ground_assembles_a_draft(ground):
    intake = drafter.ConsumerDefectiveGoodsIntake(
        **base_intake_kwargs(), defect_or_deficiency_type=ground, defect_description="Particulars of the issue."
    )
    result = drafter.assemble_consumer_defective_goods_draft(intake)
    assert result.docx_bytes.startswith(b"PK")  # docx is a zip archive
    assert result.citation_used["section_number"] == "2"
    assert result.citation_review_required is False
    assert len(result.additional_citations) == 1


# --- Pre-output hard-fail checks ---


def test_unresolved_ground_citation_hard_fails(monkeypatch):
    intake = drafter.ConsumerDefectiveGoodsIntake(
        **base_intake_kwargs(), defect_or_deficiency_type="defective_goods", defect_description="Screen cracked."
    )
    broken = {**drafter.GOODS_CLAUSE_CITATIONS[drafter.DefectOrDeficiencyType.defective_goods], "section_number": "999"}
    monkeypatch.setitem(drafter.GOODS_CLAUSE_CITATIONS, drafter.DefectOrDeficiencyType.defective_goods, broken)
    with pytest.raises(drafter.CitationUnresolvedError):
        drafter.assemble_consumer_defective_goods_draft(intake)


def test_unresolved_forum_citation_hard_fails(monkeypatch):
    intake = drafter.ConsumerDefectiveGoodsIntake(
        **base_intake_kwargs(), defect_or_deficiency_type="defective_goods", defect_description="Screen cracked."
    )
    broken = {**drafter.CONSUMER_FORUM_TIER_CITATIONS["district"], "rule_number": "999"}
    monkeypatch.setitem(drafter.CONSUMER_FORUM_TIER_CITATIONS, "district", broken)
    with pytest.raises(drafter.CitationUnresolvedError):
        drafter.assemble_consumer_defective_goods_draft(intake)


def test_all_clause_citations_resolve_against_corpus():
    for ground, citation in drafter.GOODS_CLAUSE_CITATIONS.items():
        assert drafter.resolve_citation_against_corpus(citation), (
            f"Citation for ground {ground.value!r} does not resolve against the parsed corpus"
        )


def test_all_forum_tier_citations_resolve_against_corpus():
    for tier, citation in drafter.CONSUMER_FORUM_TIER_CITATIONS.items():
        assert drafter.resolve_citation_against_corpus(citation), (
            f"Citation for forum tier {tier!r} does not resolve against the parsed corpus"
        )


# --- Router / API-level tests ---


def base_intake_kwargs_json() -> dict:
    kwargs = base_intake_kwargs()
    kwargs["transaction_date"] = kwargs["transaction_date"].isoformat()
    kwargs["defect_or_deficiency_type"] = "defective_goods"
    kwargs["defect_description"] = "Screen cracked on first use."
    return kwargs


def test_api_validate_rejects_non_positive_amount():
    response = client.post(
        "/api/complaint-drafter/consumer-defective-goods/validate",
        json={"intake": {**base_intake_kwargs_json(), "amount_paid": -5}},
    )
    assert response.status_code == 400
    assert response.json()["field"] == "amount_paid"


def test_api_validate_accepts_valid_intake_and_returns_forum_tier():
    response = client.post(
        "/api/complaint-drafter/consumer-defective-goods/validate",
        json={"intake": base_intake_kwargs_json()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "valid"
    assert body["forum_tier"] == "district"


def test_api_draft_returns_citation_metadata():
    response = client.post(
        "/api/complaint-drafter/consumer-defective-goods/draft",
        json={"intake": base_intake_kwargs_json()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citation_used"]["section_cite"] == "Section 2(10)"
    assert len(body["additional_citations"]) == 1


def test_api_draft_docx_download_returns_docx_bytes():
    response = client.post(
        "/api/complaint-drafter/consumer-defective-goods/draft/docx",
        json={"intake": base_intake_kwargs_json()},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert response.content.startswith(b"PK")
