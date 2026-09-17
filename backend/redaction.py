"""Shared PII/sensitive-value redaction helpers.

Card-number redaction lived as two separate, independently-maintained copies -- one in
case_store.py (saved case/message persistence), one in document_summarizer.py (document summary
generation) -- until 2026-09-16. When the false-positive bug in the card-number pattern (any
13-19 digit run got redacted unconditionally, no Luhn check, so ordinary long digit runs --
timestamps, invoice/order/reference/case numbers, all common in legal documents -- were
permanently and silently altered) was fixed in case_store.py, document_summarizer.py's own copy
was missed entirely: nothing tied the two together, so the same bug shipped twice and only one
copy got fixed. This module exists so that can't happen again -- there is now exactly one place
that decides whether a digit run is a plausible card number.

Deliberately narrow scope: only the card-number check lives here. Each caller keeps its own
other, context-specific patterns (OTP/PIN/password wording differs between the two call sites;
case_store.py has a separate 12-digit Aadhaar-shaped pattern document_summarizer.py doesn't have
and shouldn't gain by default). Don't add more patterns here without a specific reason both
callers should share them -- most redaction patterns are legitimately caller-specific.
"""
from __future__ import annotations

import re

CARD_NUMBER_PATTERN = re.compile(r"\b(?:\d[ -]?){13,19}\b")

DEFAULT_CARD_NUMBER_PLACEHOLDER = "[sensitive card number omitted]"


def luhn_valid(digits: str) -> bool:
    """Standard Luhn (mod 10) checksum. `digits` must be a string of only 0-9 characters."""
    total = 0
    for index, char in enumerate(reversed(digits)):
        digit = int(char)
        if index % 2 == 1:
            digit *= 2
            if digit > 9:
                digit -= 9
        total += digit
    return total % 10 == 0


def redact_card_number(text: str, placeholder: str = DEFAULT_CARD_NUMBER_PLACEHOLDER) -> str:
    """Replace only Luhn-valid 13-19 digit runs (plausible real card numbers) in `text` with
    `placeholder`. A 13-19 digit run that fails the Luhn check -- an ordinary timestamp, invoice
    number, order/reference number, case number, etc. -- is left untouched. Not a perfect filter
    (a Luhn-valid non-card number could still false-positive), but it's the standard,
    well-understood way to distinguish plausible card numbers from arbitrary digit strings.
    `placeholder` is configurable per caller: case_store.py and document_summarizer.py each had
    their own existing placeholder wording before this module existed, and this refactor
    preserves both rather than forcing one on both callers."""

    def _replace(match: re.Match) -> str:
        digits_only = re.sub(r"[ -]", "", match.group(0))
        if not (13 <= len(digits_only) <= 19) or not luhn_valid(digits_only):
            return match.group(0)
        return placeholder

    return CARD_NUMBER_PATTERN.sub(_replace, text)
