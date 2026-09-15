from __future__ import annotations

import datetime
import io
import logging
import shutil
import subprocess
import tempfile
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any

import jinja2
from docxtpl import DocxTemplate
import pydantic_core
from pydantic import BaseModel, Field, computed_field, model_validator
from pydantic_core import InitErrorDetails, PydanticCustomError

import rag
from config import BASE_DIR

logger = logging.getLogger("legal_aid_ai.complaint_drafter")

CLAUSES_DIR = BASE_DIR / "clauses"
TEMPLATES_DIR = BASE_DIR / "templates"
TENANCY_EVICTION_TEMPLATE_PATH = TEMPLATES_DIR / "tenancy_eviction_base.docx"
CONSUMER_GOODS_TEMPLATE_PATH = TEMPLATES_DIR / "consumer_defective_goods_base.docx"
CONSUMER_ADS_TEMPLATE_PATH = TEMPLATES_DIR / "consumer_misleading_ads_base.docx"

RENT_CAP_INR = 3500
RENT_CAP_MESSAGE = (
    "This tenancy's monthly rent exceeds Rs. 3,500. Under Section 3 of the Delhi Rent "
    "Control Act, 1958, premises let at this rent are excluded from the Act's coverage. This "
    "complaint type does not apply."
)


class ComplaintDraftError(Exception):
    """Raised when a draft cannot be produced safely and must hard-fail rather than proceed."""


class CitationUnresolvedError(ComplaintDraftError):
    """Raised when a clause's legal citation does not resolve against the parsed corpus."""


class FieldProvenanceError(ComplaintDraftError):
    """Raised when a field would appear in the output document without a tracked, deterministic origin."""


class PdfConversionError(ComplaintDraftError):
    """Raised when LibreOffice headless conversion to PDF is unavailable or fails."""


def _raise_field_validation_error(instance: BaseModel, field: str, message: str) -> None:
    """Raise a pydantic ValidationError whose single error is scoped to `field` via `loc`,
    the same way a plain Field()-level constraint (e.g. Field(gt=0)) is. A bare
    `raise ValueError(...)` from inside a `model_validator(mode="after")` always reports with
    an EMPTY loc -- pydantic has no way to know which field a model-level check was "about" --
    so every hard validator in this module calls this instead. That gives the API response (and
    from there, the frontend) a real `field` value to key off of, instead of having to
    string-match the message text for a field name."""
    raise pydantic_core.ValidationError.from_exception_data(
        title=type(instance).__name__,
        line_errors=[
            InitErrorDetails(
                type=PydanticCustomError("complaint_drafter_hard_validator", message),
                loc=(field,),
                input=getattr(instance, field, None),
            )
        ],
    )


# NOTE: an "unauthorized_construction" ground (Section 14(1)(k)) was deliberately dropped from
# this enum. Clause (k) covers use of the premises contrary to conditions imposed by
# government/DDA/MCD while leasing the land -- a practitioner convention for unauthorized-
# construction petitions, not a verbatim textual match in the Act. That's too weak a citation
# basis to ship. Reinstate it (enum value + CLAUSE_FILE_BY_GROUND + CLAUSE_CITATIONS +
# GROUND_CLAUSE_LETTER + GROUND_LABEL + GROUND_STATUTORY_ORDER entries, and a restored clause
# file) only after a human has done a manual legal review and confirmed the correct citation.
class EvictionGround(str, Enum):
    arrears = "arrears"
    subletting = "subletting"
    damage = "damage"
    bona_fide_requirement = "bona_fide_requirement"


class ReliefSought(str, Enum):
    recovery_of_possession = "recovery_of_possession"
    arrears_payment = "arrears_payment"
    damages = "damages"


# --- Scenario 1: Tenancy eviction / possession dispute under the Delhi Rent Control Act, 1958 ---


class TenancyEvictionIntake(BaseModel):
    tenant_name: str = Field(min_length=1)
    tenant_address: str = Field(min_length=1)
    landlord_name: str = Field(min_length=1)
    landlord_address: str = Field(min_length=1)
    property_address: str = Field(min_length=1)
    # KNOWN AMBIGUITY, documented rather than resolved: the Act defines "standard rent" and
    # "basic rent" in Section 2, but has no standalone definition of plain "rent" -- checked, it
    # is absent. Section 5(2)(a) treats "rent" and other payments as distinct concepts (it bars
    # a landlord from charging premium/pugree "in addition to the rent"), which is a textual
    # signal but not a rule: it tells us the Act's own usage of "rent" is narrower than "total
    # consideration paid," not whether a specific maintenance/service charge should be folded
    # into this field for the Rs. 3,500 cap in Section 3(c). Whether a composite rent figure vs.
    # a genuinely separately-billed maintenance charge counts is a contract-dependent factual
    # question (how the tenancy agreement itself characterizes the payment), not something the
    # statute resolves in the abstract -- and not something this schema attempts to answer. Enter
    # whatever the tenancy agreement characterizes as rent; if a separate maintenance/service
    # charge exists, get advice on whether it should be included before relying on this field.
    monthly_rent: float = Field(gt=0)
    tenancy_start_date: datetime.date
    # Multi-ground petitions (e.g. arrears + subletting pleaded together, or arrears + bona fide
    # requirement in the alternative) are legally common in practice -- as of 2026-09-15 this is
    # a list, not a single value. Breaking change to the intake shape (no external consumers
    # existed yet, so no dual-support/versioning was needed). Rendered output always appears in
    # fixed statutory order (see GROUND_STATUTORY_ORDER), never in the order the user picked.
    grounds_for_eviction: list[EvictionGround] = Field(min_length=1)
    relief_sought: list[ReliefSought] = Field(min_length=1)

    # Conditionally required based on grounds_for_eviction.
    arrears_amount: float | None = Field(default=None, gt=0)
    arrears_period_months: int | None = Field(default=None, gt=0)
    subletting_details: str | None = None
    damage_description: str | None = None
    bona_fide_reason: str | None = None

    @model_validator(mode="after")
    def check_rent_cap(self) -> "TenancyEvictionIntake":
        if self.monthly_rent > RENT_CAP_INR:
            _raise_field_validation_error(self, "monthly_rent", RENT_CAP_MESSAGE)
        return self

    @model_validator(mode="after")
    def check_tenancy_start_date_not_future(self) -> "TenancyEvictionIntake":
        if self.tenancy_start_date > datetime.date.today():
            _raise_field_validation_error(self, "tenancy_start_date", "Tenancy start date cannot be in the future.")
        return self

    @model_validator(mode="after")
    def check_grounds_for_eviction_has_no_duplicates(self) -> "TenancyEvictionIntake":
        grounds = self.grounds_for_eviction
        if len(set(grounds)) != len(grounds):
            _raise_field_validation_error(
                self,
                "grounds_for_eviction",
                "grounds_for_eviction contains a duplicate value. Select each ground at most once.",
            )
        return self

    @model_validator(mode="after")
    def check_conditional_fields_for_grounds(self) -> "TenancyEvictionIntake":
        grounds = self.grounds_for_eviction
        if EvictionGround.arrears in grounds:
            if self.arrears_amount is None or self.arrears_period_months is None:
                _raise_field_validation_error(
                    self,
                    "arrears_amount",
                    "grounds_for_eviction includes 'arrears' but arrears_amount and "
                    "arrears_period_months were not both supplied. This complaint is incomplete.",
                )
        if EvictionGround.subletting in grounds:
            if not self.subletting_details or not self.subletting_details.strip():
                _raise_field_validation_error(
                    self,
                    "subletting_details",
                    "grounds_for_eviction includes 'subletting' but subletting_details was not "
                    "supplied. This complaint is incomplete.",
                )
        if EvictionGround.damage in grounds:
            if not self.damage_description or not self.damage_description.strip():
                _raise_field_validation_error(
                    self,
                    "damage_description",
                    "grounds_for_eviction includes 'damage' but damage_description was not "
                    "supplied. This complaint is incomplete.",
                )
        if EvictionGround.bona_fide_requirement in grounds:
            if not self.bona_fide_reason or not self.bona_fide_reason.strip():
                _raise_field_validation_error(
                    self,
                    "bona_fide_reason",
                    "grounds_for_eviction includes 'bona_fide_requirement' but bona_fide_reason "
                    "was not supplied. This complaint is incomplete.",
                )
        return self


# Clause selector: flat dict lookup only. Do not generalize into a rules engine.
CLAUSE_FILE_BY_GROUND: dict[EvictionGround, str] = {
    EvictionGround.arrears: "tenancy_arrears_ground.txt",
    EvictionGround.subletting: "tenancy_subletting_ground.txt",
    EvictionGround.damage: "tenancy_damage_ground.txt",
    EvictionGround.bona_fide_requirement: "tenancy_bona_fide_ground.txt",
}

# Pre-verified citations for each clause. Each entry must resolve against the corpus chunks
# rag.py loads (the same chunk data claim_verifier.py resolves claims against) via source_file
# + section_number before a draft using that clause is allowed to proceed.
CLAUSE_CITATIONS: dict[EvictionGround, dict[str, Any]] = {
    EvictionGround.arrears: {
        "act_short_title": "Delhi Rent Control Act, 1958",
        "section_cite": "Section 14(1)(a)",
        "source_file": "tenancy/delhi_rent_control_act_1958.pdf",
        "section_number": "14",
        "confidence": "high",
    },
    EvictionGround.subletting: {
        "act_short_title": "Delhi Rent Control Act, 1958",
        "section_cite": "Section 14(1)(b)",
        "source_file": "tenancy/delhi_rent_control_act_1958.pdf",
        "section_number": "14",
        "confidence": "high",
    },
    EvictionGround.damage: {
        "act_short_title": "Delhi Rent Control Act, 1958",
        "section_cite": "Section 14(1)(j)",
        "source_file": "tenancy/delhi_rent_control_act_1958.pdf",
        "section_number": "14",
        "confidence": "high",
    },
    EvictionGround.bona_fide_requirement: {
        "act_short_title": "Delhi Rent Control Act, 1958",
        "section_cite": "Section 14(1)(e)",
        "source_file": "tenancy/delhi_rent_control_act_1958.pdf",
        "section_number": "14",
        "confidence": "high",
    },
}

GROUND_CLAUSE_LETTER: dict[EvictionGround, str] = {
    EvictionGround.arrears: "(a)",
    EvictionGround.subletting: "(b)",
    EvictionGround.damage: "(j)",
    EvictionGround.bona_fide_requirement: "(e)",
}

GROUND_LABEL: dict[EvictionGround, str] = {
    EvictionGround.arrears: "Non-payment of arrears of rent",
    EvictionGround.subletting: "Unauthorized subletting",
    EvictionGround.damage: "Substantial damage to the premises",
    EvictionGround.bona_fide_requirement: "Bona fide personal requirement of the landlord",
}

# Fixed rendering order for multi-ground petitions, matching Section 14(1)'s own lettering
# ((a) arrears, (b) subletting, (e) bona fide requirement, (j) damage) -- NOT the order the user
# selected grounds in on the form. A petition listing grounds out of the statute's own sequence
# reads as sloppy drafting; this fixes that regardless of selection order.
GROUND_STATUTORY_ORDER: list[EvictionGround] = [
    EvictionGround.arrears,
    EvictionGround.subletting,
    EvictionGround.bona_fide_requirement,
    EvictionGround.damage,
]


def ordered_grounds(grounds: list[EvictionGround]) -> list[EvictionGround]:
    """`grounds` (in whatever order the user selected them) reordered to GROUND_STATUTORY_ORDER."""
    return [ground for ground in GROUND_STATUTORY_ORDER if ground in grounds]


def _join_clause_letters(letters: list[str]) -> str:
    """"(a)" | "(a) AND (b)" | "(a), (b) AND (e)" -- for the petition title. Matches the
    all-caps title's own style (the word "AND" is capitalized; each clause letter itself stays
    lowercase, matching the statute's own lettering)."""
    if len(letters) == 1:
        return letters[0]
    if len(letters) == 2:
        return f"{letters[0]} AND {letters[1]}"
    return f"{', '.join(letters[:-1])} AND {letters[-1]}"


# Standard Indian pleading convention for multi-ground petitions: grounds are pleaded "in the
# alternative and/or cumulatively" so a court finding against the petitioner on one ground can
# still grant relief on another -- this is procedural boilerplate (not a legal citation), and
# this exact "in the alternative and/or cumulatively" phrasing (or a close variant of it) is the
# conventional way Indian pleadings (eviction petitions under rent control statutes included)
# frame more than one ground/cause of action pleaded together. Only used when 2+ grounds are
# selected; the single-ground path is untouched (see _build_render_context/the base template).
MULTI_GROUND_FRAMING_LINE = (
    "The Petitioner/Landlord relies upon the following ground(s) of eviction under Section "
    "14(1) of the Delhi Rent Control Act, 1958, in the alternative and/or cumulatively, as may "
    "be applicable:"
)

RELIEF_LABEL: dict[ReliefSought, str] = {
    ReliefSought.recovery_of_possession: "Recovery of vacant and peaceful possession of the tenanted premises.",
    ReliefSought.arrears_payment: "Payment of the arrears of rent due and payable by the Respondent/Tenant.",
    ReliefSought.damages: "Damages/compensation for loss caused by the Respondent/Tenant's conduct.",
}

# Registry of every field name that may appear in the docxtpl rendering context, together with
# how it was derived. The pre-output check refuses to render any context key that is not
# registered here -- this is what "every field was user-supplied or a deterministic rule" means
# in code, not just in a comment. Each scenario has its own registry (see _verify_field_provenance)
# since the same context-variable name can mean different things -- e.g. "forum_name" is a fixed
# constant for tenancy but a derived forum-tier lookup for the consumer scenarios.
TENANCY_FIELD_PROVENANCE: dict[str, str] = {
    "forum_name": "deterministic_rule:fixed forum text for Delhi Rent Control Act petitions",
    "petition_title": "deterministic_rule:derived from grounds_for_eviction via GROUND_CLAUSE_LETTER",
    "tenant_name": "user_supplied",
    "tenant_address": "user_supplied",
    "landlord_name": "user_supplied",
    "landlord_address": "user_supplied",
    "property_address": "user_supplied",
    "monthly_rent_display": "deterministic_rule:formatted from user_supplied monthly_rent",
    "tenancy_start_date_display": "deterministic_rule:formatted from user_supplied tenancy_start_date",
    # Single-ground path only (rendered when len(grounds_for_eviction) == 1) -- kept byte-for-byte
    # identical to the pre-multi-ground behavior; see _build_render_context.
    "grounds_label": "deterministic_rule:derived from grounds_for_eviction via GROUND_LABEL",
    "grounds_clause": "deterministic_rule:selected clause file rendered from user_supplied conditional fields",
    "citation_line": "deterministic_rule:derived from grounds_for_eviction via CLAUSE_CITATIONS",
    # Multi-ground path only (rendered when len(grounds_for_eviction) > 1) -- each entry has its
    # own label/clause_text/citation_line, reordered to GROUND_STATUTORY_ORDER regardless of the
    # order the user selected them in.
    "grounds": "deterministic_rule:derived from grounds_for_eviction, reordered via GROUND_STATUTORY_ORDER",
    "multi_ground_framing_line": "deterministic_rule:fixed MULTI_GROUND_FRAMING_LINE boilerplate, only rendered when len(grounds) > 1",
    "relief_sought_lines": "deterministic_rule:derived from relief_sought via RELIEF_LABEL",
    "generated_date_display": "deterministic_rule:today's date, formatted",
}


@dataclass
class DraftAssemblyResult:
    docx_bytes: bytes
    citation_used: dict[str, Any]
    citation_review_required: bool
    warnings: list[str] = field(default_factory=list)
    # Additional citations backing the same draft (e.g. a forum-jurisdiction citation alongside
    # the ground's own citation). Empty for scenarios that only ever cite one provision.
    additional_citations: list[dict[str, Any]] = field(default_factory=list)

    def metadata(self) -> dict[str, Any]:
        return {
            "citation_used": self.citation_used,
            "additional_citations": self.additional_citations,
            "citation_review_required": self.citation_review_required,
            "warnings": self.warnings,
        }


_STRICT_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined)
_corpus_provision_index_cache: dict[str, set[str]] | None = None


def _loaded_corpus_chunks() -> list[rag.RetrievedChunk]:
    """The same chunk data claim_verifier.py resolves claims against, as RetrievedChunk
    instances -- reuses rag.py's own loading path (LegalRAG.load() / .chunks) instead of a
    separate JSONL parse, so the drafter and the /api/ask verification path can't silently
    drift apart on what the corpus actually contains. Does not call retrieve()/answer() and
    does not affect /api/ask's retrieval or ranking behavior.
    """
    if not rag.rag.loaded:
        rag.rag.load()
    return [
        rag.RetrievedChunk(
            text=item.get("text", ""),
            source=item.get("source", ""),
            document_title=item.get("document_title") or item.get("source", ""),
            page=int(item.get("page") or 0),
            score=0.0,
            domain=item.get("domain"),
            retrieval_priority=item.get("retrieval_priority"),
            authority_level=item.get("authority_level"),
            status=item.get("status"),
            document_type=item.get("document_type"),
            chapter=item.get("chapter"),
            section_number=item.get("section_number"),
            section_title=item.get("section_title"),
            rule_number=item.get("rule_number"),
            rule_title=item.get("rule_title"),
            chunk_id=item.get("chunk_id"),
            article_number=item.get("article_number"),
            article_title=item.get("article_title"),
            regulation_number=item.get("regulation_number"),
            regulation_title=item.get("regulation_title"),
            guideline_number=item.get("guideline_number"),
            guideline_title=item.get("guideline_title"),
            page_start=item.get("page_start"),
            page_end=item.get("page_end"),
        )
        for item in rag.rag.chunks
    ]


# Statutes chunk under section_number, but the corpus's own parser (ingest.py) chunks rules
# and guidelines under rule_number / guideline_number instead (see e.g. jurisdiction_rules_2021
# .pdf and the misleading-ads/dark-patterns guidelines). A citation into a non-statute source
# names which field it lives in via "provision_field" (default "section_number" for backward
# compatibility with citations that predate this, i.e. every tenancy citation).
PROVISION_NUMBER_FIELDS = ("section_number", "rule_number", "guideline_number", "article_number", "regulation_number")


def _corpus_provision_index() -> dict[tuple[str, str], set[str]]:
    """(RetrievedChunk.source, provision field name) -> set of values present in the loaded
    corpus for that field. Loaded lazily and cached for the process lifetime."""
    global _corpus_provision_index_cache
    if _corpus_provision_index_cache is None:
        index: dict[tuple[str, str], set[str]] = {}
        for chunk in _loaded_corpus_chunks():
            if not chunk.source:
                continue
            for field_name in PROVISION_NUMBER_FIELDS:
                value = getattr(chunk, field_name, None)
                if value:
                    index.setdefault((chunk.source, field_name), set()).add(str(value))
        _corpus_provision_index_cache = index
    return _corpus_provision_index_cache


def resolve_citation_against_corpus(citation: dict[str, Any]) -> bool:
    provision_field = citation.get("provision_field", "section_number")
    provision_value = citation.get(provision_field)
    values = _corpus_provision_index().get((citation["source_file"], provision_field))
    return bool(values and provision_value is not None and str(provision_value) in values)


def _require_citation_resolved(citation: dict[str, Any], label: str) -> None:
    if resolve_citation_against_corpus(citation):
        return
    provision_field = citation.get("provision_field", "section_number")
    raise CitationUnresolvedError(
        f"Citation for {label} ({citation['section_cite']} of {citation['act_short_title']}) does not "
        f"resolve against the parsed corpus (source_file={citation['source_file']!r}, "
        f"{provision_field}={citation.get(provision_field)!r}). Refusing to generate a draft with an "
        "unverifiable citation."
    )


def _citation_review_warning(citation: dict[str, Any], label: str) -> str | None:
    if citation.get("confidence") != "needs_manual_review":
        return None
    return (
        f"Citation for {label} ({citation['section_cite']}) is flagged needs_manual_review: it "
        "resolves against the corpus but the mapping to that provision is not a verbatim textual "
        "match. A human must confirm applicability before this document is filed."
    )


def _clause_render_fields(intake: TenancyEvictionIntake) -> dict[str, Any]:
    """Explicit whitelist of fields clause files may reference, pre-formatted for display.
    Only user-supplied intake fields (formatted by a deterministic rule where noted) -- clauses
    never receive the full intake dump."""
    return {
        "property_address": intake.property_address,
        "arrears_amount": _format_inr(intake.arrears_amount) if intake.arrears_amount is not None else None,
        "arrears_period_months": intake.arrears_period_months,
        "subletting_details": intake.subletting_details,
        "damage_description": intake.damage_description,
        "bona_fide_reason": intake.bona_fide_reason,
    }


def _render_clause_file(clause_filename: str, fields: dict[str, Any]) -> str:
    """Shared primitive: render one clause .txt file with Jinja2 against an explicit field
    whitelist (never the full intake dump). Used by all three scenarios."""
    clause_path = CLAUSES_DIR / clause_filename
    if not clause_path.exists():
        raise ComplaintDraftError(f"Clause file missing: {clause_filename}")
    clause_source = clause_path.read_text(encoding="utf-8").strip()
    template = _STRICT_JINJA_ENV.from_string(clause_source)
    try:
        # StrictUndefined ensures a clause referencing a field outside its whitelist hard-fails
        # immediately, instead of silently rendering an empty string.
        return template.render(**fields)
    except jinja2.exceptions.UndefinedError as exc:
        raise FieldProvenanceError(
            f"Clause '{clause_filename}' references a field not present in its field whitelist: {exc}"
        ) from exc


def _render_clause_text(ground: EvictionGround, intake: TenancyEvictionIntake) -> str:
    return _render_clause_file(CLAUSE_FILE_BY_GROUND[ground], _clause_render_fields(intake))


def _format_inr(amount: float) -> str:
    return f"Rs. {amount:,.2f}".rstrip("0").rstrip(".") if amount == int(amount) else f"Rs. {amount:,.2f}"


def _build_render_context(
    intake: TenancyEvictionIntake,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Returns (context, primary_citation, additional_citations). Reordered to
    GROUND_STATUTORY_ORDER regardless of the order the user selected grounds in. The single-
    ground path (len(grounds) == 1) computes grounds_label/grounds_clause/citation_line exactly
    as before this feature -- same keys, same values, same base-template branch -- so a
    single-ground draft is byte-for-byte unchanged. The multi-ground path (2+) computes a
    `grounds` list instead (one entry per ground, each with its own label/clause_text/
    citation_line) plus a fixed framing line, rendered by a different base-template branch."""
    grounds = ordered_grounds(intake.grounds_for_eviction)
    citations = [CLAUSE_CITATIONS[ground] for ground in grounds]
    primary_citation = citations[0]
    additional_citations = citations[1:]

    context = {
        "forum_name": "IN THE COURT OF THE RENT CONTROLLER, DELHI",
        "petition_title": (
            f"PETITION FOR EVICTION UNDER SECTION 14(1)"
            f"{_join_clause_letters([GROUND_CLAUSE_LETTER[ground] for ground in grounds])} OF THE "
            "DELHI RENT CONTROL ACT, 1958"
        ),
        "tenant_name": intake.tenant_name,
        "tenant_address": intake.tenant_address,
        "landlord_name": intake.landlord_name,
        "landlord_address": intake.landlord_address,
        "property_address": intake.property_address,
        "monthly_rent_display": _format_inr(intake.monthly_rent),
        "tenancy_start_date_display": intake.tenancy_start_date.strftime("%d %B %Y"),
        "relief_sought_lines": [RELIEF_LABEL[item] for item in intake.relief_sought],
        "generated_date_display": datetime.date.today().strftime("%d %B %Y"),
    }

    if len(grounds) == 1:
        ground = grounds[0]
        citation = citations[0]
        context["grounds_label"] = GROUND_LABEL[ground]
        context["grounds_clause"] = _render_clause_text(ground, intake)
        context["citation_line"] = f"(See {citation['section_cite']} of the {citation['act_short_title']}.)"
    else:
        context["multi_ground_framing_line"] = MULTI_GROUND_FRAMING_LINE
        context["grounds"] = [
            {
                "label": GROUND_LABEL[ground],
                "clause_text": _render_clause_text(ground, intake),
                "citation_line": f"(See {citation['section_cite']} of the {citation['act_short_title']}.)",
            }
            for ground, citation in zip(grounds, citations)
        ]

    return context, primary_citation, additional_citations


def _verify_field_provenance(context: dict[str, Any], provenance: dict[str, str]) -> None:
    unregistered = [key for key in context if key not in provenance]
    if unregistered:
        raise FieldProvenanceError(
            "Refusing to render draft: the following fields have no tracked provenance "
            f"(neither user-supplied nor a registered deterministic rule): {unregistered}"
        )


def assemble_tenancy_eviction_draft(intake: TenancyEvictionIntake) -> DraftAssemblyResult:
    """Slot-fill the fixed base template with the intake data and the selected clause(s).

    No LLM call is made anywhere in this path. Hard-fails (raises) rather than emitting a
    partial document if any selected ground's citation doesn't resolve, or an unregistered field
    would be rendered.
    """
    grounds = ordered_grounds(intake.grounds_for_eviction)
    # Pre-output check: every selected ground's citation must resolve against the corpus, not
    # just the first one -- a multi-ground draft is only as trustworthy as its weakest citation.
    for ground in grounds:
        _require_citation_resolved(CLAUSE_CITATIONS[ground], f"ground '{ground.value}'")

    context, citation, additional_citations = _build_render_context(intake)
    _verify_field_provenance(context, TENANCY_FIELD_PROVENANCE)

    if not TENANCY_EVICTION_TEMPLATE_PATH.exists():
        raise ComplaintDraftError(
            f"Base template not found: {TENANCY_EVICTION_TEMPLATE_PATH}. Run "
            "build_templates.build_tenancy_eviction_base_template() to generate it."
        )

    doc = DocxTemplate(str(TENANCY_EVICTION_TEMPLATE_PATH))
    doc.render(context, jinja_env=_STRICT_JINJA_ENV)
    buffer = io.BytesIO()
    doc.save(buffer)

    warnings: list[str] = []
    citation_review_required = False
    for ground, ground_citation in zip(grounds, [citation, *additional_citations]):
        review_warning = _citation_review_warning(ground_citation, f"ground '{ground.value}'")
        if review_warning:
            warnings.append(review_warning)
            citation_review_required = True

    logger.info(
        "Tenancy eviction draft assembled grounds=%s citations=%s citation_review_required=%s",
        [ground.value for ground in grounds],
        [item["section_cite"] for item in [citation, *additional_citations]],
        citation_review_required,
    )

    return DraftAssemblyResult(
        docx_bytes=buffer.getvalue(),
        citation_used=citation,
        citation_review_required=citation_review_required,
        warnings=warnings,
        additional_citations=additional_citations,
    )


# --- Scenario 2: Defective goods / deficient service, refund or replacement (Consumer Protection Act, 2019) ---


class DefectOrDeficiencyType(str, Enum):
    defective_goods = "defective_goods"
    deficient_service = "deficient_service"
    short_delivery = "short_delivery"
    spurious_goods = "spurious_goods"
    unfair_trade_practice_in_sale = "unfair_trade_practice_in_sale"


class GoodsReliefSought(str, Enum):
    refund = "refund"
    replacement = "replacement"
    compensation = "compensation"
    removal_of_defect = "removal_of_defect"


# Pecuniary jurisdiction: Sections 34(1), 47(1)(a)(i) and 58(1)(a)(i) of the Act each fix a
# rupee threshold for District/State/National Commission jurisdiction based on "the value of
# the goods or services paid as consideration" -- and each carries a proviso letting the
# Central Government "prescribe such other value". That proviso power has in fact been
# exercised: the Consumer Protection (Jurisdiction ...) Rules, 2021 (in our corpus, Rules 3-5)
# set the values actually in force today at Rs. 50 lakh and Rs. 2 crore, not the Act's bare
# original figures of Rs. 1 crore / Rs. 10 crore. We use the operative, currently-in-force
# values. NOTE: the statutory phrase is "value of the goods or services paid as consideration"
# only -- it does not mention compensation claimed. This function therefore classifies on
# amount_paid alone, not amount_paid + compensation_amount combined.
DISTRICT_COMMISSION_MAX_INR = 5_000_000  # Rs. 50 lakh (Jurisdiction Rules, 2021, Rule 3)
STATE_COMMISSION_MAX_INR = 20_000_000  # Rs. 2 crore (Jurisdiction Rules, 2021, Rule 4)


def determine_consumer_forum_tier(amount_paid: float) -> str:
    if amount_paid <= DISTRICT_COMMISSION_MAX_INR:
        return "district"
    if amount_paid <= STATE_COMMISSION_MAX_INR:
        return "state"
    return "national"


CONSUMER_FORUM_DISPLAY_NAME: dict[str, str] = {
    "district": "DISTRICT CONSUMER DISPUTES REDRESSAL COMMISSION",
    "state": "STATE CONSUMER DISPUTES REDRESSAL COMMISSION",
    "national": "NATIONAL CONSUMER DISPUTES REDRESSAL COMMISSION",
}

CONSUMER_FORUM_TIER_CITATIONS: dict[str, dict[str, Any]] = {
    "district": {
        "act_short_title": "Consumer Protection Act, 2019",
        "section_cite": (
            "Section 34(1) proviso, read with Rule 3 of the Consumer Protection (Jurisdiction of "
            "the District Commission, the State Commission and the National Commission) Rules, 2021"
        ),
        "source_file": "consumer/jurisdiction_rules_2021.pdf",
        "provision_field": "rule_number",
        "rule_number": "3",
        "confidence": "high",
        "authority_level": "primary",
    },
    "state": {
        "act_short_title": "Consumer Protection Act, 2019",
        "section_cite": (
            "Section 47(1)(a)(i) proviso, read with Rule 4 of the Consumer Protection (Jurisdiction of "
            "the District Commission, the State Commission and the National Commission) Rules, 2021"
        ),
        "source_file": "consumer/jurisdiction_rules_2021.pdf",
        "provision_field": "rule_number",
        "rule_number": "4",
        "confidence": "high",
        "authority_level": "primary",
    },
    "national": {
        "act_short_title": "Consumer Protection Act, 2019",
        "section_cite": (
            "Section 58(1)(a)(i) proviso, read with Rule 5 of the Consumer Protection (Jurisdiction of "
            "the District Commission, the State Commission and the National Commission) Rules, 2021"
        ),
        "source_file": "consumer/jurisdiction_rules_2021.pdf",
        "provision_field": "rule_number",
        "rule_number": "5",
        "confidence": "high",
        "authority_level": "primary",
    },
}


class ConsumerDefectiveGoodsIntake(BaseModel):
    complainant_name: str = Field(min_length=1)
    complainant_address: str = Field(min_length=1)
    opposite_party_name: str = Field(min_length=1)
    opposite_party_address: str = Field(min_length=1)
    goods_or_service_description: str = Field(min_length=1)
    transaction_date: datetime.date
    amount_paid: float = Field(gt=0)
    defect_or_deficiency_type: DefectOrDeficiencyType
    defect_description: str = Field(min_length=1)
    prior_complaint_made: bool
    relief_sought: list[GoodsReliefSought] = Field(min_length=1)

    # Conditionally required.
    prior_complaint_response: str | None = None
    compensation_amount: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def check_transaction_date_not_future(self) -> "ConsumerDefectiveGoodsIntake":
        if self.transaction_date > datetime.date.today():
            _raise_field_validation_error(self, "transaction_date", "Transaction date cannot be in the future.")
        return self

    @model_validator(mode="after")
    def check_prior_complaint_response_present(self) -> "ConsumerDefectiveGoodsIntake":
        if self.prior_complaint_made and (not self.prior_complaint_response or not self.prior_complaint_response.strip()):
            _raise_field_validation_error(
                self,
                "prior_complaint_response",
                "prior_complaint_made is true but prior_complaint_response was not supplied. "
                "This complaint is incomplete.",
            )
        return self

    @model_validator(mode="after")
    def check_prior_complaint_response_not_stray(self) -> "ConsumerDefectiveGoodsIntake":
        # The inverse of check_prior_complaint_response_present: prior_complaint_made=False
        # with a non-empty prior_complaint_response was previously accepted silently -- the base
        # template's conditional block means that text never actually reaches the drafted
        # document, so the user's input was being discarded without any signal that it was
        # discarded. Reject instead, so the inconsistency surfaces at intake time.
        if not self.prior_complaint_made and self.prior_complaint_response and self.prior_complaint_response.strip():
            _raise_field_validation_error(
                self,
                "prior_complaint_response",
                "prior_complaint_made is false but prior_complaint_response was supplied. Set "
                "prior_complaint_made to true if you already raised this complaint with the "
                "Opposite Party, or remove the response text if you did not.",
            )
        return self

    @model_validator(mode="after")
    def check_compensation_amount_present(self) -> "ConsumerDefectiveGoodsIntake":
        if GoodsReliefSought.compensation in self.relief_sought and self.compensation_amount is None:
            _raise_field_validation_error(
                self,
                "compensation_amount",
                "relief_sought includes 'compensation' but compensation_amount was not supplied "
                "(or was not a positive amount). This complaint is incomplete.",
            )
        return self

    @computed_field  # type: ignore[prop-decorator]
    @property
    def forum_tier(self) -> str:
        """Which commission tier has pecuniary jurisdiction over this complaint, per Sections
        34/47/58 of the Act as read with the 2021 Jurisdiction Rules. Always computed -- never
        silently omitted -- so it is visible on the validated intake itself, not just buried in
        internal drafting logic."""
        return determine_consumer_forum_tier(self.amount_paid)


# Clause selector: flat dict lookup only. Do not generalize into a rules engine.
GOODS_CLAUSE_FILE_BY_TYPE: dict[DefectOrDeficiencyType, str] = {
    DefectOrDeficiencyType.defective_goods: "consumer_defective_goods_ground.txt",
    DefectOrDeficiencyType.deficient_service: "consumer_deficient_service_ground.txt",
    DefectOrDeficiencyType.short_delivery: "consumer_short_delivery_ground.txt",
    DefectOrDeficiencyType.spurious_goods: "consumer_spurious_goods_ground.txt",
    DefectOrDeficiencyType.unfair_trade_practice_in_sale: "consumer_unfair_trade_practice_ground.txt",
}

# Pre-verified citations. All five grounds are defined terms within Section 2 of the Act (its
# single definitions section), checked individually rather than reused wholesale:
#   defective_goods                -> Section 2(10) "defect" (quality/potency/purity/standard prong)
#   deficient_service               -> Section 2(11) "deficiency"
#   short_delivery                   -> Section 2(10) "defect" -- the SAME clause as defective_goods,
#                                        but its own distinct prong: clause (10) expressly lists
#                                        "quantity" among the attributes whose shortcoming is a
#                                        defect, which is exactly what a short-delivery claim is.
#                                        This is a checked, correct citation, not lazy reuse.
#   spurious_goods                   -> Section 2(43) "spurious goods"
#   unfair_trade_practice_in_sale    -> Section 2(47) "unfair trade practice"
GOODS_CLAUSE_CITATIONS: dict[DefectOrDeficiencyType, dict[str, Any]] = {
    DefectOrDeficiencyType.defective_goods: {
        "act_short_title": "Consumer Protection Act, 2019",
        "section_cite": "Section 2(10)",
        "source_file": "consumer/consumer_protection_act_2019.pdf",
        "section_number": "2",
        "confidence": "high",
        "authority_level": "primary",
    },
    DefectOrDeficiencyType.deficient_service: {
        "act_short_title": "Consumer Protection Act, 2019",
        "section_cite": "Section 2(11)",
        "source_file": "consumer/consumer_protection_act_2019.pdf",
        "section_number": "2",
        "confidence": "high",
        "authority_level": "primary",
    },
    DefectOrDeficiencyType.short_delivery: {
        "act_short_title": "Consumer Protection Act, 2019",
        "section_cite": "Section 2(10) (the 'quantity' prong)",
        "source_file": "consumer/consumer_protection_act_2019.pdf",
        "section_number": "2",
        "confidence": "high",
        "authority_level": "primary",
    },
    DefectOrDeficiencyType.spurious_goods: {
        "act_short_title": "Consumer Protection Act, 2019",
        "section_cite": "Section 2(43)",
        "source_file": "consumer/consumer_protection_act_2019.pdf",
        "section_number": "2",
        "confidence": "high",
        "authority_level": "primary",
    },
    DefectOrDeficiencyType.unfair_trade_practice_in_sale: {
        "act_short_title": "Consumer Protection Act, 2019",
        "section_cite": "Section 2(47)",
        "source_file": "consumer/consumer_protection_act_2019.pdf",
        "section_number": "2",
        "confidence": "high",
        "authority_level": "primary",
    },
}

GOODS_TYPE_LABEL: dict[DefectOrDeficiencyType, str] = {
    DefectOrDeficiencyType.defective_goods: "Defective goods",
    DefectOrDeficiencyType.deficient_service: "Deficient service",
    DefectOrDeficiencyType.short_delivery: "Short delivery of goods",
    DefectOrDeficiencyType.spurious_goods: "Spurious goods",
    DefectOrDeficiencyType.unfair_trade_practice_in_sale: "Unfair trade practice in sale",
}

# Phrasing anchored to Section 39(1) of the Act (District Commission's power to order relief).
GOODS_RELIEF_LABEL: dict[GoodsReliefSought, str] = {
    GoodsReliefSought.refund: "Return to the Complainant the price or charges paid, along with interest thereon.",
    GoodsReliefSought.replacement: "Replace the goods with new goods of similar description, free from any defect.",
    GoodsReliefSought.compensation: "Pay compensation to the Complainant for the loss or injury suffered.",
    GoodsReliefSought.removal_of_defect: "Remove the defect in the goods or the deficiency in the service.",
}

GOODS_FIELD_PROVENANCE: dict[str, str] = {
    "forum_name": "deterministic_rule:derived from amount_paid via determine_consumer_forum_tier + CONSUMER_FORUM_DISPLAY_NAME",
    "complaint_title": "deterministic_rule:fixed title text for Consumer Protection Act complaints",
    "complainant_name": "user_supplied",
    "complainant_address": "user_supplied",
    "opposite_party_name": "user_supplied",
    "opposite_party_address": "user_supplied",
    "goods_or_service_description": "user_supplied",
    "transaction_date_display": "deterministic_rule:formatted from user_supplied transaction_date",
    "amount_paid_display": "deterministic_rule:formatted from user_supplied amount_paid",
    "defect_type_label": "deterministic_rule:derived from defect_or_deficiency_type via GOODS_TYPE_LABEL",
    "grounds_clause": "deterministic_rule:selected clause file rendered from user_supplied conditional fields",
    "citation_line": "deterministic_rule:derived from defect_or_deficiency_type via GOODS_CLAUSE_CITATIONS",
    "forum_citation_line": "deterministic_rule:derived from forum_tier via CONSUMER_FORUM_TIER_CITATIONS",
    "prior_complaint_made": "user_supplied",
    "prior_complaint_response": "user_supplied",
    "relief_sought_lines": "deterministic_rule:derived from relief_sought via GOODS_RELIEF_LABEL",
    "generated_date_display": "deterministic_rule:today's date, formatted",
}


def _goods_clause_render_fields(intake: ConsumerDefectiveGoodsIntake) -> dict[str, Any]:
    return {
        "goods_or_service_description": intake.goods_or_service_description,
        "transaction_date_display": intake.transaction_date.strftime("%d %B %Y"),
        "amount_paid_display": _format_inr(intake.amount_paid),
        "defect_description": intake.defect_description,
    }


def _build_goods_render_context(intake: ConsumerDefectiveGoodsIntake) -> dict[str, Any]:
    defect_type = intake.defect_or_deficiency_type
    citation = GOODS_CLAUSE_CITATIONS[defect_type]
    forum_citation = CONSUMER_FORUM_TIER_CITATIONS[intake.forum_tier]
    grounds_clause = _render_clause_file(GOODS_CLAUSE_FILE_BY_TYPE[defect_type], _goods_clause_render_fields(intake))

    return {
        "forum_name": f"BEFORE THE {CONSUMER_FORUM_DISPLAY_NAME[intake.forum_tier]}",
        "complaint_title": "COMPLAINT UNDER THE CONSUMER PROTECTION ACT, 2019",
        "complainant_name": intake.complainant_name,
        "complainant_address": intake.complainant_address,
        "opposite_party_name": intake.opposite_party_name,
        "opposite_party_address": intake.opposite_party_address,
        "goods_or_service_description": intake.goods_or_service_description,
        "transaction_date_display": intake.transaction_date.strftime("%d %B %Y"),
        "amount_paid_display": _format_inr(intake.amount_paid),
        "defect_type_label": GOODS_TYPE_LABEL[defect_type],
        "grounds_clause": grounds_clause,
        "citation_line": f"(See {citation['section_cite']} of the {citation['act_short_title']}.)",
        "forum_citation_line": f"(See {forum_citation['section_cite']}.)",
        "prior_complaint_made": intake.prior_complaint_made,
        "prior_complaint_response": intake.prior_complaint_response or "",
        "relief_sought_lines": [GOODS_RELIEF_LABEL[item] for item in intake.relief_sought],
        "generated_date_display": datetime.date.today().strftime("%d %B %Y"),
    }


def assemble_consumer_defective_goods_draft(intake: ConsumerDefectiveGoodsIntake) -> DraftAssemblyResult:
    """Slot-fill the fixed base template for the defective-goods/deficient-service scenario.

    No LLM call is made anywhere in this path. Hard-fails (raises) rather than emitting a
    partial document if either citation doesn't resolve or an unregistered field would render.
    """
    defect_type = intake.defect_or_deficiency_type
    citation = GOODS_CLAUSE_CITATIONS[defect_type]
    forum_citation = CONSUMER_FORUM_TIER_CITATIONS[intake.forum_tier]
    _require_citation_resolved(citation, f"ground '{defect_type.value}'")
    _require_citation_resolved(forum_citation, f"forum tier '{intake.forum_tier}'")

    context = _build_goods_render_context(intake)
    _verify_field_provenance(context, GOODS_FIELD_PROVENANCE)

    if not CONSUMER_GOODS_TEMPLATE_PATH.exists():
        raise ComplaintDraftError(
            f"Base template not found: {CONSUMER_GOODS_TEMPLATE_PATH}. Run "
            "build_templates.build_consumer_defective_goods_base_template() to generate it."
        )

    doc = DocxTemplate(str(CONSUMER_GOODS_TEMPLATE_PATH))
    doc.render(context, jinja_env=_STRICT_JINJA_ENV)
    buffer = io.BytesIO()
    doc.save(buffer)

    warnings: list[str] = []
    ground_warning = _citation_review_warning(citation, f"ground '{defect_type.value}'")
    forum_warning = _citation_review_warning(forum_citation, f"forum tier '{intake.forum_tier}'")
    for warning in (ground_warning, forum_warning):
        if warning:
            warnings.append(warning)
    citation_review_required = bool(ground_warning or forum_warning)

    logger.info(
        "Consumer defective-goods draft assembled type=%s forum_tier=%s citation=%s citation_review_required=%s",
        defect_type.value,
        intake.forum_tier,
        citation["section_cite"],
        citation_review_required,
    )

    return DraftAssemblyResult(
        docx_bytes=buffer.getvalue(),
        citation_used=citation,
        citation_review_required=citation_review_required,
        warnings=warnings,
        additional_citations=[forum_citation],
    )


# --- Scenario 3: Unfair trade practice / misleading advertisement (Consumer Protection Act, 2019,
# informed by the CCPA's misleading-ads and dark-patterns guidelines) ---


class PlatformOrMedium(str, Enum):
    print = "print"
    television = "television"
    digital_display = "digital_display"
    social_media = "social_media"
    e_commerce_website = "e_commerce_website"
    other = "other"


class AdvertisementClaimType(str, Enum):
    false_claim_about_goods = "false_claim_about_goods"
    misleading_price_representation = "misleading_price_representation"
    dark_pattern_deceptive_design = "dark_pattern_deceptive_design"
    false_guarantee_or_warranty = "false_guarantee_or_warranty"
    surrogate_advertisement = "surrogate_advertisement"


class AdsReliefSought(str, Enum):
    discontinuation_of_practice = "discontinuation_of_practice"
    compensation = "compensation"
    corrective_advertisement = "corrective_advertisement"


MIN_LOSS_DESCRIPTION_CHARS = 20


class MisleadingAdvertisementIntake(BaseModel):
    complainant_name: str = Field(min_length=1)
    complainant_address: str = Field(min_length=1)
    opposite_party_name: str = Field(min_length=1)
    opposite_party_address: str = Field(min_length=1)
    advertisement_or_practice_description: str = Field(min_length=1)
    platform_or_medium: PlatformOrMedium
    date_encountered: datetime.date
    claim_type: AdvertisementClaimType
    how_it_caused_loss: str
    relief_sought: list[AdsReliefSought] = Field(min_length=1)

    # Not every dark-pattern claim involves a completed purchase.
    amount_paid: float | None = Field(default=None, gt=0)
    compensation_amount: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def check_loss_description_specific(self) -> "MisleadingAdvertisementIntake":
        # This scenario is more prone to vague claims than a transaction-anchored one, since
        # there is no invoice/receipt to fall back on -- so the minimum bar is enforced here.
        if not self.how_it_caused_loss or len(self.how_it_caused_loss.strip()) < MIN_LOSS_DESCRIPTION_CHARS:
            _raise_field_validation_error(
                self,
                "how_it_caused_loss",
                "how_it_caused_loss must describe the specific loss or harm caused "
                f"(at least {MIN_LOSS_DESCRIPTION_CHARS} characters). A vague or empty description "
                "is not enough to draft this complaint.",
            )
        return self

    @model_validator(mode="after")
    def check_date_encountered_not_future(self) -> "MisleadingAdvertisementIntake":
        if self.date_encountered > datetime.date.today():
            _raise_field_validation_error(self, "date_encountered", "Date encountered cannot be in the future.")
        return self

    @model_validator(mode="after")
    def check_compensation_amount_present(self) -> "MisleadingAdvertisementIntake":
        if AdsReliefSought.compensation in self.relief_sought and self.compensation_amount is None:
            _raise_field_validation_error(
                self,
                "compensation_amount",
                "relief_sought includes 'compensation' but compensation_amount was not supplied "
                "(or was not a positive amount). This complaint is incomplete.",
            )
        return self


# Clause selector: flat dict lookup only. Do not generalize into a rules engine.
ADS_CLAUSE_FILE_BY_TYPE: dict[AdvertisementClaimType, str] = {
    AdvertisementClaimType.false_claim_about_goods: "ads_false_claim_ground.txt",
    AdvertisementClaimType.misleading_price_representation: "ads_misleading_price_ground.txt",
    AdvertisementClaimType.dark_pattern_deceptive_design: "ads_dark_pattern_ground.txt",
    AdvertisementClaimType.false_guarantee_or_warranty: "ads_false_guarantee_ground.txt",
    AdvertisementClaimType.surrogate_advertisement: "ads_surrogate_advertisement_ground.txt",
}

# Pre-verified citations, checked individually. Three of the five grounds are direct definitional
# hits inside the Act itself; two are guideline-level (see per-entry notes) -- CCPA guidelines are
# document_type=guidelines / authority_level=official_guidance in our corpus manifest, distinct
# from the Act's document_type=statute / authority_level=primary, and that distinction is carried
# through here via "authority_level" and reflected in the clause text, not asserted with the same
# confidence as a statutory citation.
ADS_CLAUSE_CITATIONS: dict[AdvertisementClaimType, dict[str, Any]] = {
    AdvertisementClaimType.false_claim_about_goods: {
        "act_short_title": "Consumer Protection Act, 2019",
        "section_cite": "Section 2(28)(i)",
        "source_file": "consumer/consumer_protection_act_2019.pdf",
        "section_number": "2",
        "confidence": "high",
        "authority_level": "primary",
    },
    AdvertisementClaimType.misleading_price_representation: {
        "act_short_title": "Consumer Protection Act, 2019",
        "section_cite": "Section 2(47)(i)(i)",
        "source_file": "consumer/consumer_protection_act_2019.pdf",
        "section_number": "2",
        "confidence": "high",
        "authority_level": "primary",
    },
    AdvertisementClaimType.false_guarantee_or_warranty: {
        "act_short_title": "Consumer Protection Act, 2019",
        "section_cite": "Section 2(28)(ii)",
        "source_file": "consumer/consumer_protection_act_2019.pdf",
        "section_number": "2",
        "confidence": "high",
        "authority_level": "primary",
    },
    # "surrogate advertisement" is not defined anywhere in the Act's own text (checked: absent
    # from consumer_protection_act_2019.pdf entirely). Its only definition and prohibition are
    # guideline-level (CCPA, official_guidance), but the match is clean and direct -- Guideline
    # 6(1) is a one-sentence operative prohibition tracking Guideline 2(h)'s definition verbatim.
    AdvertisementClaimType.surrogate_advertisement: {
        "act_short_title": "Guidelines for Prevention of Misleading Advertisements and Endorsements for Misleading Advertisements, 2022",
        "section_cite": "Guideline 6(1), read with the definition in Guideline 2(h)",
        "source_file": "consumer/misleading_ads_guidelines_2022.pdf",
        "provision_field": "guideline_number",
        "guideline_number": "6",
        "confidence": "high",
        "authority_level": "official_guidance",
    },
    # "dark pattern" is likewise absent from the Act's own text. Guideline 2(e)'s definition is
    # clean, but it defines a dark pattern as "amounting to misleading advertisement OR unfair
    # trade practice OR violation of consumer rights" -- an explicit either/or, not a single fixed
    # Act provision. That is a genuinely weaker citation basis than the other four grounds here
    # (each a single direct hit), so -- same as tenancy's dropped unauthorized_construction ground
    # -- this is flagged needs_manual_review rather than asserted with unwarranted confidence.
    # Unlike unauthorized_construction, there IS a real, checked, non-fabricated citation behind
    # it (Guideline 4's prohibition + Guideline 2(e)'s definition), so it is kept rather than
    # dropped; a human should confirm which statutory characterization fits the facts before filing.
    AdvertisementClaimType.dark_pattern_deceptive_design: {
        "act_short_title": "Guidelines for Prevention and Regulation of Dark Patterns, 2023",
        "section_cite": "Guideline 4, read with the definition in Guideline 2(e)",
        "source_file": "consumer/dark_patterns_guidelines_2023.pdf",
        "provision_field": "guideline_number",
        "guideline_number": "4",
        "confidence": "needs_manual_review",
        "authority_level": "official_guidance",
    },
}

ADS_CLAIM_TYPE_LABEL: dict[AdvertisementClaimType, str] = {
    AdvertisementClaimType.false_claim_about_goods: "False claim about goods or service",
    AdvertisementClaimType.misleading_price_representation: "Misleading price representation",
    AdvertisementClaimType.dark_pattern_deceptive_design: "Dark pattern / deceptive design",
    AdvertisementClaimType.false_guarantee_or_warranty: "False guarantee or warranty",
    AdvertisementClaimType.surrogate_advertisement: "Surrogate advertisement",
}

PLATFORM_LABEL: dict[PlatformOrMedium, str] = {
    PlatformOrMedium.print: "print media",
    PlatformOrMedium.television: "television",
    PlatformOrMedium.digital_display: "a digital display advertisement",
    PlatformOrMedium.social_media: "social media",
    PlatformOrMedium.e_commerce_website: "an e-commerce website",
    PlatformOrMedium.other: "another medium",
}

# Phrasing anchored to Section 39(1) of the Act (District Commission's power to order relief) --
# clause (g)/(n) for discontinuation, (d) for compensation, and (l) for corrective advertisement.
ADS_RELIEF_LABEL: dict[AdsReliefSought, str] = {
    AdsReliefSought.discontinuation_of_practice: "Discontinue the unfair trade practice or misleading advertisement and not repeat it.",
    AdsReliefSought.compensation: "Pay compensation to the Complainant for the loss or injury suffered.",
    AdsReliefSought.corrective_advertisement: "Issue a corrective advertisement to neutralise the effect of the misleading advertisement, at the cost of the Opposite Party.",
}

ADS_FIELD_PROVENANCE: dict[str, str] = {
    "forum_name": "deterministic_rule:fixed forum text for Consumer Protection Act complaints",
    "complaint_title": "deterministic_rule:fixed title text for Consumer Protection Act complaints",
    "complainant_name": "user_supplied",
    "complainant_address": "user_supplied",
    "opposite_party_name": "user_supplied",
    "opposite_party_address": "user_supplied",
    "advertisement_or_practice_description": "user_supplied",
    "platform_label": "deterministic_rule:derived from platform_or_medium via PLATFORM_LABEL",
    "date_encountered_display": "deterministic_rule:formatted from user_supplied date_encountered",
    "amount_paid_display": "deterministic_rule:formatted from user_supplied amount_paid (None when amount_paid was not supplied -- an optional field in this scenario, not every claim involves a completed purchase)",
    "claim_type_label": "deterministic_rule:derived from claim_type via ADS_CLAIM_TYPE_LABEL",
    "grounds_clause": "deterministic_rule:selected clause file rendered from user_supplied conditional fields",
    "citation_line": "deterministic_rule:derived from claim_type via ADS_CLAUSE_CITATIONS",
    "relief_sought_lines": "deterministic_rule:derived from relief_sought via ADS_RELIEF_LABEL",
    "generated_date_display": "deterministic_rule:today's date, formatted",
}


def _ads_clause_render_fields(intake: MisleadingAdvertisementIntake) -> dict[str, Any]:
    return {
        "advertisement_or_practice_description": intake.advertisement_or_practice_description,
        "platform_label": PLATFORM_LABEL[intake.platform_or_medium],
        "how_it_caused_loss": intake.how_it_caused_loss,
    }


def _build_ads_render_context(intake: MisleadingAdvertisementIntake) -> dict[str, Any]:
    claim_type = intake.claim_type
    citation = ADS_CLAUSE_CITATIONS[claim_type]
    grounds_clause = _render_clause_file(ADS_CLAUSE_FILE_BY_TYPE[claim_type], _ads_clause_render_fields(intake))

    return {
        "forum_name": "BEFORE THE DISTRICT CONSUMER DISPUTES REDRESSAL COMMISSION",
        "complaint_title": "COMPLAINT UNDER THE CONSUMER PROTECTION ACT, 2019",
        "complainant_name": intake.complainant_name,
        "complainant_address": intake.complainant_address,
        "opposite_party_name": intake.opposite_party_name,
        "opposite_party_address": intake.opposite_party_address,
        "advertisement_or_practice_description": intake.advertisement_or_practice_description,
        "platform_label": PLATFORM_LABEL[intake.platform_or_medium],
        "date_encountered_display": intake.date_encountered.strftime("%d %B %Y"),
        "amount_paid_display": _format_inr(intake.amount_paid) if intake.amount_paid is not None else None,
        "claim_type_label": ADS_CLAIM_TYPE_LABEL[claim_type],
        "grounds_clause": grounds_clause,
        "citation_line": f"(See {citation['section_cite']} of the {citation['act_short_title']}.)",
        "relief_sought_lines": [ADS_RELIEF_LABEL[item] for item in intake.relief_sought],
        "generated_date_display": datetime.date.today().strftime("%d %B %Y"),
    }


def assemble_misleading_advertisement_draft(intake: MisleadingAdvertisementIntake) -> DraftAssemblyResult:
    """Slot-fill the fixed base template for the misleading-advertisement/dark-pattern scenario.

    No LLM call is made anywhere in this path. Hard-fails (raises) rather than emitting a
    partial document if the citation doesn't resolve or an unregistered field would render.
    """
    claim_type = intake.claim_type
    citation = ADS_CLAUSE_CITATIONS[claim_type]
    _require_citation_resolved(citation, f"claim type '{claim_type.value}'")

    context = _build_ads_render_context(intake)
    _verify_field_provenance(context, ADS_FIELD_PROVENANCE)

    if not CONSUMER_ADS_TEMPLATE_PATH.exists():
        raise ComplaintDraftError(
            f"Base template not found: {CONSUMER_ADS_TEMPLATE_PATH}. Run "
            "build_templates.build_misleading_advertisement_base_template() to generate it."
        )

    doc = DocxTemplate(str(CONSUMER_ADS_TEMPLATE_PATH))
    doc.render(context, jinja_env=_STRICT_JINJA_ENV)
    buffer = io.BytesIO()
    doc.save(buffer)

    warnings: list[str] = []
    review_warning = _citation_review_warning(citation, f"claim type '{claim_type.value}'")
    citation_review_required = review_warning is not None
    if review_warning:
        warnings.append(review_warning)

    logger.info(
        "Misleading advertisement draft assembled claim_type=%s citation=%s citation_review_required=%s",
        claim_type.value,
        citation["section_cite"],
        citation_review_required,
    )

    return DraftAssemblyResult(
        docx_bytes=buffer.getvalue(),
        citation_used=citation,
        citation_review_required=citation_review_required,
        warnings=warnings,
    )


def convert_docx_bytes_to_pdf(docx_bytes: bytes) -> bytes:
    """Convert DOCX bytes to PDF via LibreOffice headless. Same template source as the DOCX
    output -- this does not re-render from a separate PDF template/renderer."""
    soffice_path = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice_path:
        raise PdfConversionError(
            "LibreOffice ('soffice') was not found on PATH. Install LibreOffice to enable PDF "
            "export; DOCX export does not require it."
        )

    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        docx_path = tmp_path / "draft.docx"
        docx_path.write_bytes(docx_bytes)
        try:
            result = subprocess.run(
                [
                    soffice_path,
                    "--headless",
                    "--norestore",
                    "--convert-to",
                    "pdf",
                    "--outdir",
                    str(tmp_path),
                    str(docx_path),
                ],
                capture_output=True,
                timeout=60,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise PdfConversionError("LibreOffice headless PDF conversion timed out.") from exc

        pdf_path = tmp_path / "draft.pdf"
        if result.returncode != 0 or not pdf_path.exists():
            stderr = result.stderr.decode("utf-8", errors="replace") if result.stderr else ""
            raise PdfConversionError(f"LibreOffice PDF conversion failed: {stderr.strip() or 'unknown error'}")
        return pdf_path.read_bytes()
