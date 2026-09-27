"""Which of a user's documents "may also be relevant" to a case.

Deterministic keyword rules -- no LLM call, so the Ask page's side panel stays instant and the
result never depends on a live service. Each document is sorted into zero or more KINDS by
looking at its confirmed document type (if its facts were confirmed), its filename and the start
of its extracted text. A kind is relevant to every case (identity / address proof: asked for
when filing almost anything) or to specific legal areas (a rent agreement to a tenancy case).

Only a suggestion, shown to the user with a short reason; nothing here feeds the legal answer.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, Iterable

ALL_DOMAINS = frozenset({"consumer", "tenancy", "cyber", "constitutional_public_authority"})
MAX_SUGGESTIONS = 5
MAX_UNIVERSAL_SUGGESTIONS = 2


@dataclass(frozen=True)
class DocumentKind:
    key: str
    label: str
    reason: str
    domains: frozenset[str]
    patterns: tuple[str, ...]
    document_types: frozenset[str] = frozenset()
    # Documents useful in every case (identity/address proof) rank below ones that match the
    # case's own legal area.
    universal: bool = False


KINDS: tuple[DocumentKind, ...] = (
    DocumentKind(
        key="identity_proof",
        label="Identity proof",
        reason="Identity proof is usually asked for when you file a complaint or application.",
        domains=ALL_DOMAINS,
        universal=True,
        patterns=(
            r"\baadhaa?r\b", r"\badhaa?r\b", r"\buidai\b", r"\bpan card\b", r"\bpermanent account number\b",
            r"\bpassport\b", r"\bvoter id\b", r"\belection commission\b", r"\bepic\b",
            r"\bdriving licen[cs]e\b", r"\bidentity card\b", r"\bid card\b", r"\bid proof\b",
        ),
    ),
    DocumentKind(
        key="address_proof",
        label="Proof of address",
        reason="Proof of address is often asked for when filing, and shows which office or forum covers your area.",
        domains=ALL_DOMAINS,
        universal=True,
        patterns=(
            r"\belectricity bill\b", r"\bwater bill\b", r"\bgas bill\b", r"\butility bill\b", r"\bration card\b",
            r"\baddress proof\b", r"\bproof of (?:address|residence)\b", r"\bresidence (?:proof|certificate)\b",
            r"\bdomicile\b",
        ),
    ),
    DocumentKind(
        key="rent_agreement",
        label="Rent agreement",
        reason="A rent or lease agreement sets out the terms your landlord and you agreed to.",
        domains=frozenset({"tenancy"}),
        document_types=frozenset({"rent_agreement"}),
        patterns=(
            r"\brent(?:al)? agreement\b", r"\blease (?:agreement|deed)\b", r"\bleave and licen[cs]e\b",
            r"\btenancy agreement\b", r"\blicensor\b", r"\blessor\b",
        ),
    ),
    DocumentKind(
        key="rent_payment",
        label="Rent or deposit record",
        reason="Rent receipts and deposit records show what you paid your landlord.",
        domains=frozenset({"tenancy"}),
        patterns=(r"\brent receipt\b", r"\bsecurity deposit\b", r"\bmonthly rent\b", r"\brent paid\b"),
    ),
    DocumentKind(
        key="invoice_or_receipt",
        label="Invoice or receipt",
        reason="An invoice or receipt proves what you bought, when, and for how much.",
        domains=frozenset({"consumer"}),
        document_types=frozenset({"invoice_or_receipt"}),
        # "(?<!postal )": an Indian Postal Order number (RTI fee) is not a purchase order.
        patterns=(r"\binvoice\b", r"\breceipt\b", r"\btax invoice\b", r"(?<!postal )\border (?:id|no|number)\b", r"\bbill no\b"),
    ),
    DocumentKind(
        key="warranty",
        label="Warranty or service record",
        reason="A warranty card or service record helps show the seller's or maker's obligations.",
        domains=frozenset({"consumer"}),
        patterns=(r"\bwarranty\b", r"\bguarantee card\b", r"\bservice (?:centre|center|record|report)\b", r"\bjob sheet\b"),
    ),
    DocumentKind(
        key="transaction_record",
        label="Payment or bank record",
        reason="Bank or payment records show where money went, which matters for refunds and fraud reports.",
        domains=frozenset({"consumer", "cyber"}),
        document_types=frozenset({"transaction_record"}),
        patterns=(
            r"\bbank statement\b", r"\baccount statement\b", r"\btransaction (?:id|receipt|details)\b",
            # Not a bare "UPI": rent receipts and invoices often just say "paid by UPI".
            r"\butr\b", r"\bupi (?:transaction|ref|reference|id)\b", r"\bdebited\b", r"\bneft\b", r"\bimps\b",
        ),
    ),
    DocumentKind(
        key="police_or_cyber_report",
        label="Police or cybercrime report",
        reason="An FIR or cybercrime complaint acknowledgement shows the incident was reported.",
        domains=frozenset({"cyber"}),
        patterns=(
            r"\bfir\b", r"\bfirst information report\b", r"cybercrime\.gov\.in", r"\bcyber ?crime\b",
            r"\backnowledg(?:e)?ment (?:no|number)\b", r"\bpolice (?:complaint|station)\b",
        ),
    ),
    DocumentKind(
        key="legal_notice",
        label="Legal notice",
        reason="A notice you sent or received is part of the record of the dispute.",
        domains=frozenset({"tenancy", "consumer", "constitutional_public_authority"}),
        document_types=frozenset({"legal_notice"}),
        patterns=(r"\blegal notice\b", r"\beviction notice\b", r"\bnotice dated\b", r"\bshow cause\b"),
    ),
    DocumentKind(
        key="earlier_complaint",
        label="Earlier complaint",
        reason="An earlier complaint and any reply show what has already been tried.",
        domains=frozenset({"consumer", "cyber", "constitutional_public_authority"}),
        document_types=frozenset({"complaint"}),
        patterns=(r"\bcomplaint (?:no|number|draft)\b", r"\bgrievance\b", r"\bdocket\b"),
    ),
    DocumentKind(
        key="government_record",
        label="RTI or government record",
        reason="RTI applications and government orders or replies are the core record in a public-authority matter.",
        domains=frozenset({"constitutional_public_authority"}),
        patterns=(
            r"\brti\b", r"\bright to information\b", r"\bpublic information officer\b", r"\bgovernment order\b",
            r"\bgazette\b", r"\bfirst appeal\b",
        ),
    ),
)


def document_kinds(document: dict[str, Any]) -> list[DocumentKind]:
    """The kinds a document looks like, from its confirmed type, filename and text sample."""
    text = " ".join(
        str(part or "") for part in (document.get("filename"), document.get("text_sample"))
    ).lower()
    text = re.sub(r"[_\-]+", " ", text)
    confirmed_type = document.get("document_type")
    kinds = []
    for kind in KINDS:
        if confirmed_type and confirmed_type in kind.document_types:
            kinds.append(kind)
        elif any(re.search(pattern, text) for pattern in kind.patterns):
            kinds.append(kind)
    return kinds


def suggest_documents(
    documents: Iterable[dict[str, Any]],
    case_id: int,
    case_domains: Iterable[str],
    limit: int = MAX_SUGGESTIONS,
) -> list[dict[str, Any]]:
    """Documents (not already in this case) that may help with a case in `case_domains`: ones
    matching the case's legal area first, then identity/address proof, newest first within each.
    Up to MAX_UNIVERSAL_SUGGESTIONS places are kept for identity/address proof so area matches
    cannot crowd them out. Each result is the document's metadata plus `relevance_label` and
    `relevance_reason`."""
    domains = {domain for domain in case_domains if domain}
    area_matches: list[dict[str, Any]] = []
    universal_matches: list[dict[str, Any]] = []
    for document in documents:  # `documents` arrives newest first
        if case_id in document.get("case_ids", ()):
            continue
        kinds = document_kinds(document)
        # A document that plainly belongs to another legal area (a notice to a landlord, a
        # cybercrime report) is not offered to this case just because it is also a generic
        # "legal notice" or "payment record".
        home_domains = {
            domain for kind in kinds if not kind.universal and len(kind.domains) == 1 for domain in kind.domains
        }
        if home_domains and not home_domains & domains:
            continue
        matching = [kind for kind in kinds if kind.domains & domains]
        if not matching:
            continue
        # A kind specific to the case's legal area beats a universal one.
        best = min(matching, key=lambda kind: kind.universal)
        suggestion = {
            key: document[key]
            for key in ("id", "filename", "file_type", "created_at", "updated_at")
            if key in document
        }
        suggestion["relevance_label"] = best.label
        suggestion["relevance_reason"] = best.reason
        (universal_matches if best.universal else area_matches).append(suggestion)
    universal_count = min(len(universal_matches), MAX_UNIVERSAL_SUGGESTIONS, limit)
    area = area_matches[: limit - universal_count]
    return area + universal_matches[: limit - len(area)]


def document_category(document: dict[str, Any]) -> str | None:
    """The one legal area a document plainly belongs to, for colour-coding the Documents page
    the same way My Cases is: the first specific (non-universal) kind it matches that points at
    a single area -- an invoice is consumer, a rent agreement tenancy, an RTI reply
    constitutional_public_authority. None when nothing points at one area: identity/address
    proof, or a bank statement (consumer or cyber)."""
    for kind in document_kinds(document):
        if not kind.universal and len(kind.domains) == 1:
            return next(iter(kind.domains))
    return None
