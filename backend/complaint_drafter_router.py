from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, ValidationError

import complaint_drafter as drafter

logger = logging.getLogger("legal_aid_ai.complaint_drafter_router")

# NOTE: this repo has no existing APIRouter/prefix convention -- backend/main.py declares every
# route directly on the FastAPI() app instance. This module introduces an APIRouter (as the task
# requested a "dedicated router") and is wired in via app.include_router(...) in main.py. See the
# review note in the final summary.
router = APIRouter(prefix="/api/complaint-drafter", tags=["complaint-drafter"])


class RawIntakeRequest(BaseModel):
    intake: dict[str, Any]


def _validate_intake(model: type[BaseModel], payload: dict[str, Any]) -> Any:
    try:
        return model.model_validate(payload)
    except ValidationError as exc:
        # Raised manually (rather than declaring the intake model as the route body type) so
        # the hard-validator messages -- e.g. the Rs. 3,500 rent-cap message -- reach the caller
        # verbatim. main.py's global RequestValidationError handler otherwise collapses any 422
        # into the generic "The request format is invalid.", which would swallow exactly the
        # clear jurisdictional message this feature depends on.
        #
        # Every validator on these intake models -- plain Field() constraints and the hard
        # business-rule checks in @model_validator(mode="after") methods alike -- reports a
        # single-field `loc`: complaint_drafter.py's hard validators raise via
        # _raise_field_validation_error(), which sets an explicit loc, instead of a bare
        # ValueError (which pydantic reports with an EMPTY loc for a model-level validator). So
        # `field` below is real structured data read off the error, not inferred from the
        # message text -- the response carries it as its own JSON key for the same reason.
        # main.py's http_exception_handler forwards a dict `detail` as the response body as-is.
        first_error = exc.errors()[0]
        loc_parts = [str(part) for part in first_error.get("loc", ()) if part != "__root__"]
        field = loc_parts[0] if loc_parts else None
        message = first_error.get("msg", "Invalid complaint intake data.")
        raise HTTPException(status_code=400, detail={"detail": message, "field": field}) from exc


def _validate_tenancy_eviction_intake(payload: dict[str, Any]) -> drafter.TenancyEvictionIntake:
    return _validate_intake(drafter.TenancyEvictionIntake, payload)


def _validate_consumer_goods_intake(payload: dict[str, Any]) -> drafter.ConsumerDefectiveGoodsIntake:
    return _validate_intake(drafter.ConsumerDefectiveGoodsIntake, payload)


def _validate_misleading_ad_intake(payload: dict[str, Any]) -> drafter.MisleadingAdvertisementIntake:
    return _validate_intake(drafter.MisleadingAdvertisementIntake, payload)


def _generate_draft(payload: dict[str, Any], validate_fn, assemble_fn) -> tuple[Any, drafter.DraftAssemblyResult]:
    intake = validate_fn(payload)
    try:
        result = assemble_fn(intake)
    except drafter.ComplaintDraftError as exc:
        # Hard-fail per the pipeline's pre-output check: an unresolved citation or an
        # unregistered field is a 500 (a bug in this codebase's clause/template data), not a
        # 400 (the user did nothing wrong).
        logger.error("Complaint draft assembly refused to proceed: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return intake, result


# --- Scenario 1: tenancy eviction ---


def _tenancy_grounds_filename_fragment(intake: drafter.TenancyEvictionIntake) -> str:
    """Grounds joined in statutory order (matching the document body's own ordering), not
    selection order -- e.g. two grounds picked as [subletting, arrears] still produce
    "arrears_subletting" here, consistent with how they appear in the rendered document."""
    return "_".join(ground.value for ground in drafter.ordered_grounds(intake.grounds_for_eviction))


@router.post("/tenancy-eviction/validate")
def validate_tenancy_eviction_intake(request: RawIntakeRequest) -> dict:
    intake = _validate_tenancy_eviction_intake(request.intake)
    return {
        "status": "valid",
        "grounds_for_eviction": [ground.value for ground in drafter.ordered_grounds(intake.grounds_for_eviction)],
    }


@router.post("/tenancy-eviction/draft")
def draft_tenancy_eviction(request: RawIntakeRequest) -> dict:
    intake, result = _generate_draft(request.intake, _validate_tenancy_eviction_intake, drafter.assemble_tenancy_eviction_draft)
    logger.info(
        "Tenancy eviction draft generated grounds=%s citation_review_required=%s",
        [ground.value for ground in drafter.ordered_grounds(intake.grounds_for_eviction)],
        result.citation_review_required,
    )
    return {"status": "success", "scenario": "tenancy_eviction", **result.metadata()}


@router.post("/tenancy-eviction/draft/docx")
def download_tenancy_eviction_docx(request: RawIntakeRequest) -> Response:
    intake, result = _generate_draft(request.intake, _validate_tenancy_eviction_intake, drafter.assemble_tenancy_eviction_draft)
    filename = f"eviction_petition_{_tenancy_grounds_filename_fragment(intake)}.docx"
    return Response(
        content=result.docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/tenancy-eviction/draft/pdf")
def download_tenancy_eviction_pdf(request: RawIntakeRequest) -> Response:
    intake, result = _generate_draft(request.intake, _validate_tenancy_eviction_intake, drafter.assemble_tenancy_eviction_draft)
    try:
        pdf_bytes = drafter.convert_docx_bytes_to_pdf(result.docx_bytes)
    except drafter.PdfConversionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    filename = f"eviction_petition_{_tenancy_grounds_filename_fragment(intake)}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- Scenario 2: consumer defective goods / deficient service ---


@router.post("/consumer-defective-goods/validate")
def validate_consumer_goods_intake(request: RawIntakeRequest) -> dict:
    intake = _validate_consumer_goods_intake(request.intake)
    return {
        "status": "valid",
        "defect_or_deficiency_type": intake.defect_or_deficiency_type.value,
        "forum_tier": intake.forum_tier,
    }


@router.post("/consumer-defective-goods/draft")
def draft_consumer_goods(request: RawIntakeRequest) -> dict:
    intake, result = _generate_draft(request.intake, _validate_consumer_goods_intake, drafter.assemble_consumer_defective_goods_draft)
    logger.info(
        "Consumer defective-goods draft generated type=%s forum_tier=%s citation_review_required=%s",
        intake.defect_or_deficiency_type.value,
        intake.forum_tier,
        result.citation_review_required,
    )
    return {"status": "success", "scenario": "consumer_defective_goods", "forum_tier": intake.forum_tier, **result.metadata()}


@router.post("/consumer-defective-goods/draft/docx")
def download_consumer_goods_docx(request: RawIntakeRequest) -> Response:
    intake, result = _generate_draft(request.intake, _validate_consumer_goods_intake, drafter.assemble_consumer_defective_goods_draft)
    filename = f"consumer_complaint_{intake.defect_or_deficiency_type.value}.docx"
    return Response(
        content=result.docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/consumer-defective-goods/draft/pdf")
def download_consumer_goods_pdf(request: RawIntakeRequest) -> Response:
    intake, result = _generate_draft(request.intake, _validate_consumer_goods_intake, drafter.assemble_consumer_defective_goods_draft)
    try:
        pdf_bytes = drafter.convert_docx_bytes_to_pdf(result.docx_bytes)
    except drafter.PdfConversionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    filename = f"consumer_complaint_{intake.defect_or_deficiency_type.value}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# --- Scenario 3: misleading advertisement / dark patterns ---


@router.post("/consumer-misleading-ads/validate")
def validate_misleading_ad_intake(request: RawIntakeRequest) -> dict:
    intake = _validate_misleading_ad_intake(request.intake)
    return {"status": "valid", "claim_type": intake.claim_type.value}


@router.post("/consumer-misleading-ads/draft")
def draft_misleading_ad(request: RawIntakeRequest) -> dict:
    intake, result = _generate_draft(request.intake, _validate_misleading_ad_intake, drafter.assemble_misleading_advertisement_draft)
    logger.info(
        "Misleading advertisement draft generated claim_type=%s citation_review_required=%s",
        intake.claim_type.value,
        result.citation_review_required,
    )
    return {"status": "success", "scenario": "consumer_misleading_ads", **result.metadata()}


@router.post("/consumer-misleading-ads/draft/docx")
def download_misleading_ad_docx(request: RawIntakeRequest) -> Response:
    intake, result = _generate_draft(request.intake, _validate_misleading_ad_intake, drafter.assemble_misleading_advertisement_draft)
    filename = f"consumer_complaint_{intake.claim_type.value}.docx"
    return Response(
        content=result.docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/consumer-misleading-ads/draft/pdf")
def download_misleading_ad_pdf(request: RawIntakeRequest) -> Response:
    intake, result = _generate_draft(request.intake, _validate_misleading_ad_intake, drafter.assemble_misleading_advertisement_draft)
    try:
        pdf_bytes = drafter.convert_docx_bytes_to_pdf(result.docx_bytes)
    except drafter.PdfConversionError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    filename = f"consumer_complaint_{intake.claim_type.value}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
