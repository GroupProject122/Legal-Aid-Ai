from __future__ import annotations

import builtins
import json
import logging
import sqlite3
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import legal_aid_eligibility as lae
import legal_education
import main


client = TestClient(main.app)
URL = "/api/legal-aid/eligibility"


def ask(**answers):
    body = {"state": "Delhi", "court": "other", "categories": [], **answers}
    response = client.post(URL, json=body)
    assert response.status_code == 200, response.text
    return response.json()


def rule_ids(result: dict) -> list[str]:
    return [rule["rule_id"] for rule in result["matched_rules"]]


# --- the six worked examples ---


def test_example_1_delhi_woman_no_income_eligible_via_12c():
    result = ask(categories=["woman"], age=34)
    assert result["result"] == "likely_eligible"
    assert rule_ids(result) == ["s12_c_woman"]
    assert result["matched_rules"][0]["source"]["provision"] == "Section 12(c)"


def test_example_2_delhi_income_below_limit_eligible():
    result = ask(age=41, annual_income=240000)
    assert result["result"] == "likely_eligible"
    assert rule_ids(result) == ["delhi_income_general"]


def test_example_3_delhi_income_at_limit_not_eligible_with_alternatives():
    result = ask(age=45, annual_income=300000)
    assert result["result"] == "likely_not_eligible"
    assert result["matched_rules"] == []
    names = " ".join(item["name"] for item in result["alternatives"])
    assert "clinic" in names and "Lok Adalat" in names and "15100" in names
    assert "Rs. 3,00,000" in result["reason"]


def test_example_4_delhi_senior_citizen_uses_4_lakh_limit():
    result = ask(age=67, annual_income=350000)
    assert result["result"] == "likely_eligible"
    assert rule_ids(result) == ["delhi_income_senior_citizen"]


def test_example_5_other_state_cannot_determine():
    result = ask(state="Maharashtra", age=30, annual_income=100000)
    assert result["result"] == "cannot_determine"
    assert "income limits are set by each state" in result["reason"]
    assert any(item.get("phone") == "15100" for item in result["where_to_apply"])
    assert "State Legal Services Authority" in result["where_to_apply"][0]["name"]


def test_example_6_supreme_court_cannot_determine():
    result = ask(court="supreme_court", age=40, annual_income=200000)
    assert result["result"] == "cannot_determine"
    assert "Supreme Court Legal Services Committee" in result["reason"]
    assert result["where_to_apply"][0]["name"] == "Supreme Court Legal Services Committee"


# --- boundaries: every limit is LESS THAN ---


@pytest.mark.parametrize("income, expected", [
    (299999, "likely_eligible"),
    (300000, "likely_not_eligible"),
    (300001, "likely_not_eligible"),
])
def test_general_limit_boundary(income, expected):
    assert ask(age=41, annual_income=income)["result"] == expected


@pytest.mark.parametrize("income, expected", [
    (399999, "likely_eligible"),
    (400000, "likely_not_eligible"),
])
def test_transgender_limit_boundary(income, expected):
    result = ask(categories=["transgender"], age=30, annual_income=income)
    assert result["result"] == expected
    if expected == "likely_eligible":
        assert rule_ids(result) == ["delhi_income_transgender"]
    else:
        assert "Rs. 4,00,000" in result["reason"]


@pytest.mark.parametrize("age, expected", [(59, "likely_not_eligible"), (60, "likely_eligible")])
def test_senior_citizen_age_boundary(age, expected):
    assert ask(age=age, annual_income=350000)["result"] == expected


def test_senior_citizen_at_4_lakh_not_eligible():
    assert ask(age=70, annual_income=400000)["result"] == "likely_not_eligible"


def test_limits_are_less_than_and_sourced():
    assert lae.LIMITS["delhi_general"]["amount_inr"] == 300_000
    assert lae.LIMITS["delhi_senior_citizen"]["amount_inr"] == 400_000
    assert lae.LIMITS["delhi_transgender"]["amount_inr"] == 400_000
    for limit in lae.LIMITS.values():
        assert limit["comparison"] == "less_than"
        assert limit["url"] == lae.DSLSA_ELIGIBILITY_URL
        assert limit["authority"] == "official_website"
        assert limit["source_title"] and limit["last_verified"]


# --- child is worked out from age; nothing else is inferred ---


def test_age_17_is_child():
    result = ask(age=17)
    assert result["result"] == "likely_eligible"
    assert rule_ids(result) == ["s12_c_child"]


def test_age_18_is_not_child_and_gender_is_never_inferred():
    result = ask(age=18)
    assert result["result"] == "cannot_determine"
    assert result["needs"] == ["annual_income"]


# --- every category on its own ---

CATEGORY_RULE = {
    "sc_st": "s12_a_sc_st",
    "trafficking_or_begar": "s12_b_trafficking_or_begar",
    "woman": "s12_c_woman",
    "disability": "s12_d_disability",
    "disaster_victim": "s12_e_disaster_victim",
    "industrial_workman": "s12_f_industrial_workman",
    "in_custody": "s12_g_in_custody",
    "acid_attack_victim": "delhi_acid_attack_victim",
    "hiv_aids": "delhi_hiv_aids",
    "defence_family": "delhi_defence_family",
}


def test_every_category_is_covered_here():
    assert set(CATEGORY_RULE) | {"transgender"} == {category.value for category in lae.Category}


@pytest.mark.parametrize("category, rule_id", sorted(CATEGORY_RULE.items()))
def test_each_category_alone_is_eligible(category, rule_id):
    result = ask(categories=[category], age=35)
    assert result["result"] == "likely_eligible"
    assert rule_ids(result) == [rule_id]
    assert result["alternatives"] == []


def test_transgender_alone_needs_income():
    # Transgender persons get a higher income limit in Delhi, not eligibility on its own.
    result = ask(categories=["transgender"], age=35)
    assert result["result"] == "cannot_determine"
    assert result["needs"] == ["annual_income"]


@pytest.mark.parametrize("category", sorted(CATEGORY_RULE))
def test_category_plus_high_income_still_eligible(category):
    result = ask(categories=[category], age=35, annual_income=5_000_000)
    assert result["result"] == "likely_eligible"
    assert CATEGORY_RULE[category] in rule_ids(result)


def test_several_categories_all_listed_in_order():
    result = ask(categories=["hiv_aids", "woman", "sc_st"], age=35)
    assert rule_ids(result) == ["s12_a_sc_st", "s12_c_woman", "delhi_hiv_aids"]


def test_no_category_and_no_income_asks_for_income_instead_of_guessing():
    result = ask(age=41)
    assert result["result"] == "cannot_determine"
    assert result["needs"] == ["annual_income"]
    assert result["matched_rules"] == []
    assert "income" in result["reason"]


def test_zero_income_is_eligible_not_missing():
    assert ask(age=41, annual_income=0)["result"] == "likely_eligible"


# --- out-of-scope paths still show Section 12, which applies everywhere ---


def test_other_state_shows_section_12_match_but_stays_cannot_determine():
    result = ask(state="Maharashtra", categories=["woman"], age=30)
    assert result["result"] == "cannot_determine"
    assert rule_ids(result) == ["s12_c_woman"]
    assert "Section 12(c)" in result["reason"]


def test_other_state_ignores_delhi_only_categories():
    result = ask(state="Kerala", categories=["hiv_aids"], age=30)
    assert result["result"] == "cannot_determine"
    assert result["matched_rules"] == []


def test_supreme_court_beats_delhi_and_shows_section_12_match():
    result = ask(court="supreme_court", categories=["sc_st"], age=30)
    assert result["result"] == "cannot_determine"
    assert rule_ids(result) == ["s12_a_sc_st"]


@pytest.mark.parametrize("state", ["Delhi", "delhi", " New Delhi ", "NCT of Delhi", "N.C.T. of Delhi"])
def test_delhi_name_variants(state):
    assert ask(state=state, categories=["woman"], age=30)["result"] == "likely_eligible"


# --- result shape ---


def test_result_shape_and_disclaimer():
    result = ask(categories=["woman"], age=34)
    assert result["disclaimer"] == (
        "This is a guide, not a final decision. The Legal Services Authority decides your application."
    )
    assert result["last_verified"] == lae.LAST_VERIFIED
    assert result["where_to_apply"] and result["documents_to_bring"]
    assert {item.get("phone") for item in result["where_to_apply"]} >= {"1516", "15100"}


def test_income_match_mentions_affidavit_and_assumption():
    result = ask(age=41, annual_income=100000)
    assert any("affidavit" in item["text"] for item in result["documents_to_bring"])
    assert result["notes"] == [lae.USER_NOTES["income_basis"]]
    assert ask(age=67, annual_income=100000)["notes"][-1] == lae.USER_NOTES["senior_citizen_age"]


def test_alternatives_only_when_not_eligible():
    assert ask(categories=["woman"], age=34)["alternatives"] == []
    assert ask(age=45, annual_income=900000)["alternatives"]


# --- sources ---


def all_corpus_sources() -> list[dict]:
    sources = [rule.source for rule in lae.RULES.values()]
    sources += [lae.SENIOR_CITIZEN_DEFINITION_SOURCE, lae.INCOME_AFFIDAVIT_SOURCE, lae.APPLICATION_SOURCE]
    sources += [item["source"] for item in lae.ALTERNATIVES if "source" in item]
    return [source for source in sources if source["authority"] == "statute"]


def test_every_corpus_source_resolves_against_the_corpus():
    for source in all_corpus_sources():
        provision = legal_education.get_provision(source["source_id"], source["provision_id"])
        assert provision["label"] == source["provision"].split("(")[0]
        assert source["api_url"] == f"/api/legal-awareness/sources/{source['source_id']}/provisions/{source['provision_id']}"


def test_section_12_clause_letters_match_corpus_text():
    provision = legal_education.get_provision(lae.LSA_ACT_SOURCE_ID, "section-12")
    assert provision["source"]["short_title"] or provision["source"]["document_title"]
    text = next(
        json.loads(line)["text"]
        for line in (Path(main.__file__).parent / "parsed" / "legal_chunks.jsonl").open(encoding="utf-8")
        if json.loads(line).get("chunk_id") == provision["chunk_id"]
    )
    expected = {
        "a": "Scheduled Caste or Scheduled Tribe",
        "b": "trafficking in human beings or begar",
        "c": "a woman or a child",
        "d": "person with disability",
        "e": "mass disaster",
        "f": "an industrial workman",
        "g": "in custody",
    }
    for rule in lae.RULES.values():
        if rule.jurisdiction != "all_india":
            continue
        letter = rule.source["provision"][len("Section 12("):-1]
        assert rule.rule_id.startswith(f"s12_{letter}_")
        assert expected[letter] in text


def test_delhi_rules_cite_dslsa_as_official_website():
    for rule in lae.RULES.values():
        if rule.jurisdiction == "Delhi":
            assert rule.source["authority"] == "official_website"
            assert rule.source["url"] == lae.DSLSA_ELIGIBILITY_URL
            assert rule.source["source_id"] is None


# --- validation ---


@pytest.mark.parametrize("override, field", [
    ({"age": -1}, "age"),
    ({"age": 121}, "age"),
    ({"age": 34.5}, "age"),
    ({"age": "34"}, "age"),
    ({"age": True}, "age"),
    ({"age": None}, "age"),
    ({"annual_income": -1}, "annual_income"),
    ({"annual_income": "lots"}, "annual_income"),
    ({"annual_income": False}, "annual_income"),
    ({"court": "high_court"}, "court"),
    ({"categories": ["woman", "child"]}, "categories"),
    ({"categories": "woman"}, "categories"),
    ({"state": ""}, "state"),
    ({"state": "x" * 61}, "state"),
    ({"aadhaar": "1234"}, "aadhaar"),
])
def test_invalid_input_returns_field_level_422(override, field):
    body = {"state": "Delhi", "court": "other", "categories": [], "age": 30, **override}
    response = client.post(URL, json=body)
    assert response.status_code == 422
    errors = response.json()["errors"]
    assert [error["field"] for error in errors] == [field]
    assert errors[0]["message"]


@pytest.mark.parametrize("missing", ["state", "court", "age"])
def test_missing_required_field(missing):
    body = {"state": "Delhi", "court": "other", "categories": [], "age": 30}
    body.pop(missing)
    response = client.post(URL, json=body)
    assert response.status_code == 422
    assert response.json()["errors"] == [{"field": missing, "message": "This answer is required."}]


@pytest.mark.parametrize("raw", [b"not json", b"[1, 2]", b"", b"null"])
def test_non_object_body_is_422(raw):
    response = client.post(URL, content=raw, headers={"Content-Type": "application/json"})
    assert response.status_code == 422


def test_error_response_never_echoes_input():
    response = client.post(URL, json={"state": "Delhi", "court": "other", "categories": ["hiv_aids", "SECRET-CASTE"], "age": 30})
    assert response.status_code == 422
    assert "SECRET-CASTE" not in response.text
    assert "hiv_aids" not in response.text


def test_check_eligibility_accepts_dict_and_raises_on_bad_dict():
    assert lae.check_eligibility({"state": "Delhi", "court": "other", "age": 10}).result == "likely_eligible"
    with pytest.raises(lae.ValidationError):
        lae.check_eligibility({"state": "Delhi", "court": "other", "age": 200})


def test_format_inr_uses_indian_grouping():
    assert lae.format_inr(300000) == "Rs. 3,00,000"
    assert lae.format_inr(5_000_000) == "Rs. 50,00,000"
    assert lae.format_inr(999) == "Rs. 999"


# --- privacy and determinism ---


def test_nothing_logged_or_stored(monkeypatch, caplog):
    real_open = builtins.open

    def no_write_open(file, mode="r", *args, **kwargs):
        if any(flag in mode for flag in ("w", "a", "x", "+")):
            raise AssertionError(f"eligibility check tried to write a file: {file}")
        return real_open(file, mode, *args, **kwargs)

    def no_db(*_args, **_kwargs):
        raise AssertionError("eligibility check tried to open a database")

    monkeypatch.setattr(builtins, "open", no_write_open)
    monkeypatch.setattr(sqlite3, "connect", no_db)
    sensitive = {"state": "Delhi", "court": "other", "categories": ["sc_st", "hiv_aids", "disability"], "age": 52, "annual_income": 123457}
    with caplog.at_level(logging.DEBUG):
        ok = client.post(URL, json=sensitive)
        bad = client.post(URL, json={**sensitive, "age": 999, "annual_income": -123457})
        unparseable = client.post(URL, content=b"{hiv_aids", headers={"Content-Type": "application/json"})
    assert ok.status_code == 200
    assert bad.status_code == 422
    assert unparseable.status_code == 422
    # httpx (the test client) logs the URL and status; asyncio logs its event-loop selector.
    app_records = [record for record in caplog.records if record.name.split(".")[0] not in ("httpx", "asyncio")]
    assert app_records == []
    logged = "\n".join(record.getMessage() for record in caplog.records)
    for fragment in ("sc_st", "hiv_aids", "disability", "123457", "52", "999"):
        assert fragment not in logged


def test_module_makes_no_ai_or_network_calls():
    source = Path(lae.__file__).read_text(encoding="utf-8")
    for forbidden in ("genai", "gemini", "httpx", "requests", "logging", "sqlite3", "case_store"):
        assert forbidden not in source.lower().split('"""', 2)[-1]


def test_eval_case_file_passes_in_full():
    import evaluate_legal_aid_eligibility as evaluator

    report = evaluator.evaluate()
    failures = [item["id"] for item in report["results"] if not item["evaluation"]["passed"]]
    assert failures == []
    assert report["metrics"]["case_count"] >= 30
