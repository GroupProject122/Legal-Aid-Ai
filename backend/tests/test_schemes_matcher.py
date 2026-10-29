"""schemes_matcher + POST /api/schemes/match: three-valued rule evaluation, grouping, ordering,
area filtering, the spot-check profiles, and that answers are never logged or stored."""
from __future__ import annotations

import builtins
import logging
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import main
import schemes_matcher as sm

client = TestClient(main.app)
URL = "/api/schemes/match"


def rule(field, operator, value):
    return {"field": field, "operator": operator, "value": value}


def scheme(rules, sid="TEST", name="Test scheme", category="pension"):
    return {
        "id": sid, "name": name, "scope": "central", "category": category, "benefitType": "x",
        "benefits": "Some benefit.", "eligibilitySummary": "Some summary.", "eligibilityRules": rules,
        "requiredQuestions": ["age", "hasRationCard"], "eligibilityStatus": "needs_verification",
        "officialUrl": "https://example.gov.in/", "sourceUrl": "https://example.gov.in/", "lastVerified": None,
    }


def match(**answers):
    return sm.match(sm.MatchRequest(**answers))


def by_id(result, scheme_id):
    for item in result["results"] + result["notEligible"]:
        if item["id"] == scheme_id:
            return item
    raise AssertionError(f"{scheme_id} not in the result")


# --- operators -------------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("operator", "value", "answer", "expected"),
    [
        ("equals", "female", "female", "pass"),
        ("equals", "female", "Female", "pass"),
        ("equals", "female", "male", "fail"),
        ("equals", True, True, "pass"),
        ("equals", True, False, "fail"),
        ("greaterThanOrEqual", 18, 18, "pass"),
        ("greaterThanOrEqual", 18, 17, "fail"),
        ("lessThanOrEqual", 900000, 900000, "pass"),
        ("lessThanOrEqual", 900000, 900001, "fail"),
        ("lessThan", 10, 9, "pass"),
        ("lessThan", 10, 10, "fail"),
        ("betweenInclusive", [18, 40], 18, "pass"),
        ("betweenInclusive", [18, 40], 40, "pass"),
        ("betweenInclusive", [18, 40], 17, "fail"),
        ("betweenInclusive", [18, 40], 41, "fail"),
    ],
)
def test_each_operator(operator, value, answer, expected):
    assert sm.evaluate_rule(rule("age", operator, value), {"age": answer}) == expected


def test_unanswered_or_unasked_field_is_unknown():
    assert sm.evaluate_rule(rule("age", "greaterThanOrEqual", 18), {}) == "unknown"
    assert sm.evaluate_rule(rule("ownsCultivableLand", "equals", True), {"age": 30}) == "unknown"


# --- grouping --------------------------------------------------------------------------------

def test_scheme_with_no_rules_is_never_likely_eligible(monkeypatch):
    monkeypatch.setattr(sm, "load_schemes", lambda: (scheme([]),))
    result = match(age=30, gender="female", residence="rural", annualFamilyIncome=100000, socialCategory="sc", occupation="farmer")
    assert [item["group"] for item in result["results"]] == ["check_with_authority"]


def test_all_rules_pass_is_likely_eligible(monkeypatch):
    monkeypatch.setattr(sm, "load_schemes", lambda: (scheme([rule("age", "betweenInclusive", [18, 40]), rule("gender", "equals", "female")]),))
    item = match(age=25, gender="female")["results"][0]
    assert item["group"] == "likely_eligible"
    assert "you are between 18 and 40 years old" in item["reason"]


def test_unknown_fields_give_might_be_eligible_with_what_will_be_checked(monkeypatch):
    monkeypatch.setattr(sm, "load_schemes", lambda: (scheme([rule("age", "greaterThanOrEqual", 18), rule("ownsCultivableLand", "equals", True)]),))
    item = match(age=30)["results"][0]
    assert item["group"] == "might_be_eligible"
    assert item["alsoCheck"] == ["you own cultivable land"]
    assert "The authority will also check: you own cultivable land" in item["reason"]


def test_one_failing_rule_hides_the_scheme(monkeypatch):
    monkeypatch.setattr(sm, "load_schemes", lambda: (scheme([rule("age", "betweenInclusive", [18, 40]), rule("ownsCultivableLand", "equals", True)]),))
    result = match(age=45)
    assert result["results"] == []
    assert result["notEligible"][0]["group"] == "not_eligible"
    assert "you said 45 years old" in result["notEligible"][0]["reason"]


def test_order_is_group_then_name(monkeypatch):
    schemes = (
        scheme([], sid="C", name="Zeta check"),
        scheme([rule("age", "greaterThanOrEqual", 18), rule("ownsCultivableLand", "equals", True)], sid="M", name="Beta might"),
        scheme([rule("age", "greaterThanOrEqual", 18)], sid="L2", name="Bravo likely"),
        scheme([rule("age", "greaterThanOrEqual", 18)], sid="L1", name="alpha likely"),
        scheme([], sid="C2", name="Alpha check"),
    )
    monkeypatch.setattr(sm, "load_schemes", lambda: schemes)
    assert [item["id"] for item in match(age=30)["results"]] == ["L1", "L2", "M", "C2", "C"]


def test_area_filtering():
    result = match(areas=["housing", "pension"])
    categories = {item["category"] for item in result["results"] + result["notEligible"]}
    assert categories == {"housing", "pension"}
    assert len(match()["results"]) == 34  # empty areas = all, nothing answered = nothing fails


def test_duplicates_are_gone():
    schemes = sm.load_schemes()
    assert len(schemes) == 34
    assert len({s["id"] for s in schemes}) == 34
    assert {"PMVISHWAKARMA", "PMMY-MUDRA"}.isdisjoint({s["id"] for s in schemes})


def test_result_fields_and_disclaimer():
    item = match()["results"][0]
    for key in ("id", "name", "category", "benefits", "eligibilitySummary", "group", "reason", "whatTheyMayAsk",
                "officialUrl", "sourceUrl", "lastVerified", "disclaimer"):
        assert key in item
    assert item["disclaimer"] == "Check eligibility on the official website before applying. This is a guide, not a decision."


# --- spot checks with the real data ----------------------------------------------------------

def test_rural_woman_25_ujjwala_is_might_not_likely():
    result = match(age=25, gender="female", residence="rural", annualFamilyIncome=150000)
    ujjwala = by_id(result, "PMUY")
    assert ujjwala["group"] == "might_be_eligible"
    assert "no one in your household already has an LPG connection" in ujjwala["alsoCheck"]
    assert by_id(result, "PMAY-U-2.0")["group"] == "not_eligible"  # urban-only


def test_urban_man_30_pmay_urban_is_might_be_eligible():
    result = match(age=30, gender="male", residence="urban", annualFamilyIncome=600000)
    assert by_id(result, "PMAY-U-2.0")["group"] == "might_be_eligible"
    assert by_id(result, "PMUY")["group"] == "not_eligible"


def test_age_45_rules_out_apy_and_pm_kmy():
    result = match(age=45)
    assert by_id(result, "APY")["group"] == "not_eligible"
    assert by_id(result, "PM-KMY")["group"] == "not_eligible"


def test_schemes_without_rules_are_check_with_authority_and_what_they_may_ask_is_readable():
    item = by_id(match(), "PMGKAY")
    assert item["group"] == "check_with_authority"
    assert "Has ration card" in item["whatTheyMayAsk"]
    assert by_id(match(), "AICTE-PRAGATI")["whatTheyMayAsk"].count("Your family's annual income") == 1


# --- API -------------------------------------------------------------------------------------

def test_endpoint_matches_and_validates():
    ok = client.post(URL, json={"age": 45, "areas": ["pension"]})
    assert ok.status_code == 200
    assert {item["id"] for item in ok.json()["notEligible"]} == {"APY", "PM-KMY"}
    assert client.post(URL, json={}).status_code == 200
    bad = client.post(URL, json={"age": -1, "gender": "x", "areas": ["unknown_area"], "extra": 1})
    assert bad.status_code == 422
    assert {error["field"] for error in bad.json()["errors"]} == {"age", "gender", "areas", "extra"}


def test_areas_endpoint():
    areas = client.get("/api/schemes/areas").json()["areas"]
    assert sum(area["count"] for area in areas) == 34
    assert {"id": "housing", "label": "Housing", "count": 2} in areas


def test_nothing_logged_or_stored(monkeypatch, caplog):
    real_open = builtins.open

    def no_write_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            raise AssertionError(f"schemes match tried to write a file: {file}")
        return real_open(file, mode, *args, **kwargs)

    def no_db(*_args, **_kwargs):
        raise AssertionError("schemes match tried to open a database")

    monkeypatch.setattr(builtins, "open", no_write_open)
    monkeypatch.setattr(sqlite3, "connect", no_db)
    sensitive = {"age": 52, "gender": "female", "residence": "rural", "annualFamilyIncome": 123457, "socialCategory": "dnt", "occupation": "street_vendor"}
    with caplog.at_level(logging.DEBUG):
        ok = client.post(URL, json=sensitive)
        bad = client.post(URL, json={**sensitive, "age": 999, "annualFamilyIncome": -123457})
        unparseable = client.post(URL, content=b"{dnt", headers={"Content-Type": "application/json"})
    assert ok.status_code == 200 and bad.status_code == 422 and unparseable.status_code == 422
    app_records = [record for record in caplog.records if record.name.split(".")[0] not in ("httpx", "asyncio")]
    assert app_records == []
    logged = "\n".join(record.getMessage() for record in caplog.records)
    for fragment in ("dnt", "street_vendor", "123457", "52", "999"):
        assert fragment not in logged
    assert "123457" not in bad.text and "999" not in bad.text


def test_module_makes_no_ai_network_or_storage_calls():
    # Code only: the module docstring itself says "no Gemini, no network, no database".
    source = Path(sm.__file__).read_text(encoding="utf-8").split('"""', 2)[-1].lower()
    for forbidden in ("genai", "gemini", "httpx", "requests", "import logging", "sqlite3", "case_store"):
        assert forbidden not in source


def test_social_category_and_occupation_stay_optional_and_change_nothing():
    # No current rule uses them, so the page no longer asks; the API still accepts them.
    base = match(age=30, gender="female", residence="rural", annualFamilyIncome=150000)
    with_extra = match(age=30, gender="female", residence="rural", annualFamilyIncome=150000, socialCategory="st", occupation="farmer")
    assert [(r["id"], r["group"]) for r in with_extra["results"]] == [(r["id"], r["group"]) for r in base["results"]]
    assert client.post(URL, json={"socialCategory": "obc", "occupation": "artisan"}).status_code == 200
