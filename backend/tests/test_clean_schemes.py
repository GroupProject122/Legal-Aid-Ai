"""scripts/clean_schemes.py: duplicates removed, field synonyms merged, bad data rejected,
nothing about any eligibility rule or URL changed."""
from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND / "scripts"))

import clean_schemes  # noqa: E402

RAW = json.loads((BACKEND / "data" / "schemes.json").read_text(encoding="utf-8"))


def test_duplicates_are_removed_leaving_34():
    schemes = clean_schemes.clean(RAW)
    ids = [scheme["id"] for scheme in schemes]
    assert len(schemes) == 34
    assert "PM-VISHWAKARMA-VERIFIED" in ids and "PMVISHWAKARMA" not in ids
    assert "MUDRA" in ids and "PMMY-MUDRA" not in ids
    assert len(set(ids)) == len(ids)
    assert len({scheme["name"] for scheme in schemes}) == len(schemes)


def test_synonyms_are_merged_everywhere():
    schemes = clean_schemes.clean(RAW)
    fields = {q for s in schemes for q in s["requiredQuestions"]} | {r["field"] for s in schemes for r in s["eligibilityRules"]}
    for old, new in clean_schemes.FIELD_SYNONYMS.items():
        assert old not in fields
    assert "annualFamilyIncome" in fields and "socialCategory" in fields


def test_rules_urls_and_verification_are_unchanged():
    original = {scheme["id"]: scheme for scheme in RAW}
    for scheme in clean_schemes.clean(RAW):
        before = original[scheme["id"]]
        assert scheme["eligibilityRules"] == before["eligibilityRules"]
        for key in ("officialUrl", "sourceUrl", "lastVerified", "benefits", "eligibilitySummary", "name"):
            assert scheme[key] == before[key]


def test_input_is_not_modified():
    raw = copy.deepcopy(RAW)
    clean_schemes.clean(raw)
    assert raw == RAW


def test_committed_clean_file_matches_the_script():
    committed = json.loads((BACKEND / "data" / "schemes_clean.json").read_text(encoding="utf-8"))
    assert committed == clean_schemes.clean(RAW)


def broken(mutate):
    raw = copy.deepcopy(RAW)
    mutate(next(s for s in raw if s["id"] == "APY"))
    return raw


@pytest.mark.parametrize(
    ("mutate", "message"),
    [
        (lambda s: s.pop("sourceUrl"), "missing keys"),
        (lambda s: s["eligibilityRules"].append({"field": "age", "operator": "notEquals", "value": 1}), "unknown operator"),
        (lambda s: s["eligibilityRules"].__setitem__(0, {"field": "age", "operator": "betweenInclusive", "value": [40, 18]}), "betweenInclusive"),
        (lambda s: s["eligibilityRules"].__setitem__(0, {"field": "age", "operator": "betweenInclusive", "value": 18}), "betweenInclusive"),
        (lambda s: s["eligibilityRules"].__setitem__(0, {"field": "age", "operator": "lessThan", "value": "forty"}), "needs a number"),
        (lambda s: s.__setitem__("officialUrl", "http://www.pfrda.org.in/"), "https"),
        (lambda s: s.__setitem__("lastVerified", "last week"), "lastVerified"),
        (lambda s: s.__setitem__("id", "PMJJBY"), "duplicate id"),
    ],
)
def test_bad_data_is_rejected_loudly(mutate, message):
    with pytest.raises(clean_schemes.SchemeDataError, match=message):
        clean_schemes.clean(broken(mutate))


def test_missing_duplicate_pair_is_rejected():
    raw = [scheme for scheme in RAW if scheme["id"] != "PMMY-MUDRA"]
    with pytest.raises(clean_schemes.SchemeDataError, match="duplicate pair"):
        clean_schemes.clean(raw)
