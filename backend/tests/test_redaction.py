from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import redaction


def test_luhn_valid_card_numbers():
    assert redaction.luhn_valid("4111111111111111")  # Visa test card
    assert redaction.luhn_valid("5500000000000004")  # Mastercard test card
    assert redaction.luhn_valid("340000000000009")  # Amex test card, 15 digits


def test_luhn_invalid_ordinary_digit_runs():
    assert not redaction.luhn_valid("1789469159760")  # 13-digit epoch timestamp
    assert not redaction.luhn_valid("1234567890123456")  # sequential, not Luhn-valid
    assert not redaction.luhn_valid("1234567890123")  # 13-digit reference number, not Luhn-valid


def test_redact_card_number_leaves_non_card_digit_runs_untouched():
    text = "Reference: 1789469159760, order ID 1234567890123456, and case 1234567890123."
    assert redaction.redact_card_number(text) == text


def test_redact_card_number_redacts_luhn_valid_numbers():
    text = "My card is 4111111111111111."
    result = redaction.redact_card_number(text)
    assert "4111111111111111" not in result
    assert "[sensitive card number omitted]" in result


def test_redact_card_number_handles_spaced_and_dashed_formats():
    for text in ("4111 1111 1111 1111", "4111-1111-1111-1111"):
        result = redaction.redact_card_number(text)
        assert "4111" not in result or "[sensitive card number omitted]" in result
        assert "1111 1111 1111 1111" not in result and "1111-1111-1111-1111" not in result


def test_redact_card_number_custom_placeholder():
    text = "Card: 4111111111111111."
    result = redaction.redact_card_number(text, placeholder="[sensitive information omitted]")
    assert "[sensitive information omitted]" in result
    assert "[sensitive card number omitted]" not in result


def test_redact_card_number_ignores_short_and_long_digit_runs():
    # Below 13 or above 19 digits is outside the pattern's own length window regardless of Luhn.
    text = "Phone: 9876543210. Some huge number: 12345678901234567890."
    assert redaction.redact_card_number(text) == text
