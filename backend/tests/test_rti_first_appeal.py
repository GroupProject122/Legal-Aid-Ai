from __future__ import annotations

import datetime as real_datetime
import io
import sys
import types
from pathlib import Path

import pytest
from docx import Document
from fastapi.testclient import TestClient
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import complaint_drafter as drafter
import main

client = TestClient(main.app)

# "Today" for the lateness tests below. The base intake's application date is 2026-08-01, so the
# standard 30-day response period expired 2026-08-31 and the appeal window runs to 2026-09-30.
FROZEN_TODAY = real_datetime.date(2026, 9, 10)


@pytest.fixture
def frozen_today(monkeypatch):
    """Make complaint_drafter see FROZEN_TODAY as today, without touching the drafter's logic.
    The lateness check compares against datetime.date.today(), so a test that hard-codes an
    application date silently flips from "timely" to "late" once enough real days pass -- which
    is how test_timely_appeal_has_no_lateness_warning started failing on 2026-10-01."""

    class FrozenDate(real_datetime.date):
        @classmethod
        def today(cls):
            return FROZEN_TODAY

    shim = types.SimpleNamespace(**{name: getattr(real_datetime, name) for name in dir(real_datetime) if not name.startswith("__")})
    shim.date = FrozenDate
    monkeypatch.setattr(drafter, "datetime", shim)
    return FROZEN_TODAY


def base_intake_kwargs() -> dict:
    return dict(
        appellant_name="Anita Verma",
        appellant_address="14 Green Park, New Delhi",
        public_authority_name="Delhi Jal Board",
        public_authority_address="Varunalaya Phase II, Karol Bagh, New Delhi",
        information_originally_sought="Certified copies of all water quality test reports for the Karol Bagh zone.",
        original_application_date="2026-08-01",
        pio_response_type="no_response_received",
        grounds_for_appeal="No response was received within the thirty-day period prescribed under the Act.",
    )


# --- Validation ---


def test_short_grounds_for_appeal_fails_validation():
    with pytest.raises(ValidationError) as exc_info:
        drafter.RTIFirstAppealIntake(**{**base_intake_kwargs(), "grounds_for_appeal": "Not fair"})
    assert "at least 20 characters" in str(exc_info.value)
    assert exc_info.value.errors()[0]["loc"] == ("grounds_for_appeal",)


def test_missing_pio_response_date_fails_when_response_received():
    kwargs = {**base_intake_kwargs(), "pio_response_type": "request_rejected"}
    with pytest.raises(ValidationError) as exc_info:
        drafter.RTIFirstAppealIntake(**kwargs)
    assert exc_info.value.errors()[0]["loc"] == ("pio_response_date",)


def test_stray_pio_response_date_fails_when_no_response_received():
    kwargs = {**base_intake_kwargs(), "pio_response_date": "2026-08-20"}
    with pytest.raises(ValidationError) as exc_info:
        drafter.RTIFirstAppealIntake(**kwargs)
    assert exc_info.value.errors()[0]["loc"] == ("pio_response_date",)


def test_response_date_before_application_date_fails():
    kwargs = {
        **base_intake_kwargs(),
        "pio_response_type": "request_rejected",
        "original_application_date": "2026-08-20",
        "pio_response_date": "2026-08-01",
    }
    with pytest.raises(ValidationError) as exc_info:
        drafter.RTIFirstAppealIntake(**kwargs)
    assert "cannot be before original_application_date" in str(exc_info.value)


def test_future_application_date_fails():
    with pytest.raises(ValidationError):
        drafter.RTIFirstAppealIntake(**{**base_intake_kwargs(), "original_application_date": "2099-01-01"})


def test_no_response_appeal_before_30_day_period_expires_fails():
    # Found via live dry-run testing: a "no response received" appeal filed only 20 days after
    # the original request previously slipped through with no warning at all, even though the
    # deemed refusal it's claiming doesn't legally exist yet (Section 7(1)'s 30-day period
    # hasn't expired). Dates computed relative to today (not a fixed string) so this stays
    # correct regardless of when the suite runs -- see the eval cases' notes for why this isn't
    # a static eval case instead.
    import datetime

    recent_date = datetime.date.today() - datetime.timedelta(days=20)
    with pytest.raises(ValidationError) as exc_info:
        drafter.RTIFirstAppealIntake(
            **{**base_intake_kwargs(), "original_application_date": recent_date.isoformat()}
        )
    assert "has not yet expired" in str(exc_info.value)
    assert exc_info.value.errors()[0]["loc"] == ("original_application_date",)


def test_no_response_appeal_exactly_on_expiry_day_succeeds():
    import datetime

    expiry_date = datetime.date.today() - datetime.timedelta(days=drafter.RTI_STANDARD_RESPONSE_DAYS)
    intake = drafter.RTIFirstAppealIntake(
        **{**base_intake_kwargs(), "original_application_date": expiry_date.isoformat()}
    )
    assert intake.original_application_date == expiry_date


def test_no_response_appeal_well_after_30_days_succeeds():
    import datetime

    old_date = datetime.date.today() - datetime.timedelta(days=45)
    intake = drafter.RTIFirstAppealIntake(
        **{**base_intake_kwargs(), "original_application_date": old_date.isoformat()}
    )
    assert intake.original_application_date == old_date


# --- Draft assembly ---


def _rendered_paragraphs(docx_bytes: bytes) -> list[str]:
    return [p.text for p in Document(io.BytesIO(docx_bytes)).paragraphs if p.text.strip()]


def test_draft_assembles_without_error():
    intake = drafter.RTIFirstAppealIntake(**base_intake_kwargs())
    result = drafter.assemble_rti_first_appeal_draft(intake)
    assert result.docx_bytes.startswith(b"PK")
    assert result.citation_used["section_cite"] == "Section 19(1)"
    assert result.additional_citations == []


def test_no_response_received_produces_deemed_refusal_language():
    intake = drafter.RTIFirstAppealIntake(**base_intake_kwargs())
    result = drafter.assemble_rti_first_appeal_draft(intake)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    assert any("deemed refusal" in p for p in paragraphs)


def test_request_rejected_includes_pio_response_date():
    intake = drafter.RTIFirstAppealIntake(
        **{**base_intake_kwargs(), "pio_response_type": "request_rejected", "pio_response_date": "2026-08-20"}
    )
    result = drafter.assemble_rti_first_appeal_draft(intake)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    joined = " ".join(paragraphs)
    assert "rejected the request" in joined
    assert "20 August 2026" in joined


def test_late_appeal_gets_lateness_warning(frozen_today):
    # Deemed refusal 2026-07-31; 41 days before FROZEN_TODAY -> outside the 30-day window.
    intake = drafter.RTIFirstAppealIntake(**{**base_intake_kwargs(), "original_application_date": "2026-07-01"})
    result = drafter.assemble_rti_first_appeal_draft(intake)
    assert any("more than 30 days" in w for w in result.warnings)
    paragraphs = _rendered_paragraphs(result.docx_bytes)
    assert any("condone the delay" in p for p in paragraphs)


def test_timely_appeal_has_no_lateness_warning(frozen_today):
    # Deemed refusal 2026-08-31; 10 days before FROZEN_TODAY -> inside the 30-day window.
    intake = drafter.RTIFirstAppealIntake(**base_intake_kwargs())
    result = drafter.assemble_rti_first_appeal_draft(intake)
    assert not any("more than 30 days" in w for w in result.warnings)


def test_all_citations_resolve_against_corpus():
    assert drafter.resolve_citation_against_corpus(drafter.RTI_FIRST_APPEAL_CITATION)


def test_unresolved_citation_hard_fails(monkeypatch):
    intake = drafter.RTIFirstAppealIntake(**base_intake_kwargs())
    broken = {**drafter.RTI_FIRST_APPEAL_CITATION, "section_number": "999"}
    monkeypatch.setattr(drafter, "RTI_FIRST_APPEAL_CITATION", broken)
    with pytest.raises(drafter.CitationUnresolvedError):
        drafter.assemble_rti_first_appeal_draft(intake)


# --- Router / API-level tests ---


def test_api_validate_rejects_short_grounds():
    response = client.post(
        "/api/complaint-drafter/rti-first-appeal/validate",
        json={"intake": {**base_intake_kwargs(), "grounds_for_appeal": "Not fair"}},
    )
    assert response.status_code == 400
    body = response.json()
    assert "at least 20 characters" in body["detail"]
    assert body["field"] == "grounds_for_appeal"


def test_api_draft_returns_citation_metadata():
    response = client.post(
        "/api/complaint-drafter/rti-first-appeal/draft",
        json={"intake": base_intake_kwargs()},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["citation_used"]["section_cite"] == "Section 19(1)"


def test_api_draft_docx_download_returns_docx_bytes():
    response = client.post(
        "/api/complaint-drafter/rti-first-appeal/draft/docx",
        json={"intake": base_intake_kwargs()},
    )
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/vnd.openxmlformats")
    assert response.content.startswith(b"PK")
