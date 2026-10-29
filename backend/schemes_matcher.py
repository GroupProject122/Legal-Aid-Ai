"""Matches a few optional answers against the central government schemes in
data/schemes_clean.json (built by scripts/clean_schemes.py) for POST /api/schemes/match.

Deterministic rules only -- no Gemini, no network, no database -- and the answers are neither
logged nor stored. Each scheme's eligibilityRules are a flat list that must all hold, evaluated
three-valued: a rule on a field the user answered passes or fails; a rule on any other field (or
an unanswered one) is unknown.
- any rule fails                 -> not_eligible (returned separately)
- all rules pass                 -> likely_eligible
- none fail, some unknown        -> might_be_eligible ("The authority will also check: ...")
- the scheme has no rules at all -> check_with_authority (never likely_eligible)
"""
from __future__ import annotations

import json
import re
from functools import lru_cache
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from config import BASE_DIR

DATA_PATH = BASE_DIR / "data" / "schemes_clean.json"
DISCLAIMER = "Check eligibility on the official website before applying. This is a guide, not a decision."
GROUP_ORDER = ("likely_eligible", "might_be_eligible", "check_with_authority")

# The scheme categories in plain words, for the "pick areas" step.
AREA_LABELS = {
    "agriculture": "Farming and agriculture",
    "business": "Business and self-employment",
    "child_welfare": "Child welfare",
    "disability_support": "Disability support",
    "education": "Education and scholarships",
    "employment": "Employment",
    "energy": "Energy and electricity",
    "food_security": "Food and rations",
    "healthcare": "Health",
    "housing": "Housing",
    "insurance": "Insurance",
    "pension": "Pension",
    "skills_employment": "Skills and training",
    "social_welfare": "Social welfare",
    "women_family": "Women and family",
    "worker_welfare": "Workers' welfare",
}


@lru_cache(maxsize=1)
def load_schemes() -> tuple[dict[str, Any], ...]:
    """Loaded once (at app startup) and cached; the file is the cleaner's validated output."""
    return tuple(json.loads(DATA_PATH.read_text(encoding="utf-8")))


def scheme_areas() -> list[str]:
    return sorted({scheme["category"] for scheme in load_schemes()})


class MatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    age: int | None = Field(default=None, ge=0, le=120)
    gender: Literal["male", "female", "other"] | None = None
    residence: Literal["urban", "rural"] | None = None
    annualFamilyIncome: float | None = Field(default=None, ge=0, le=1_000_000_000)
    socialCategory: Literal["general", "obc", "sc", "st", "ebc", "dnt", "other"] | None = None
    occupation: Literal["farmer", "student", "salaried", "self_employed", "unemployed", "artisan", "street_vendor", "other"] | None = None
    areas: list[str] = Field(default_factory=list)

    @field_validator("areas")
    @classmethod
    def check_areas(cls, value: list[str]) -> list[str]:
        known = set(scheme_areas())
        unknown = [area for area in value if area not in known]
        if unknown:
            raise ValueError("Choose areas from the list shown.")
        return value


def validation_errors(exc: ValidationError) -> list[dict[str, str]]:
    """Field-level errors built from loc + type only, never from the submitted input."""
    errors = []
    for error in exc.errors(include_input=False, include_url=False):
        loc = [str(part) for part in error.get("loc", ())]
        field_name = loc[0] if loc else "body"
        error_type = error.get("type", "")
        if error_type == "value_error":
            message = str(error.get("ctx", {}).get("error") or "This answer is not valid.")
        elif error_type == "extra_forbidden":
            message = "This question is not part of the form."
        elif error_type == "literal_error":
            message = "This answer is not one of the allowed options."
        else:
            message = "This answer is not in the expected format."
        errors.append({"field": field_name, "message": message})
    return errors


# --- plain-English wording -------------------------------------------------------------------

# Boolean rule fields: (wording when the rule wants true, wording when it wants false).
BOOLEAN_CONDITIONS = {
    "ownsCultivableLand": ("you own cultivable land", "you do not own cultivable land"),
    "institutionalLandholder": ("you are an institutional landholder", "you are not an institutional landholder"),
    "excludedUnderPMKisanRules": ("you fall in a group excluded under the PM-KISAN rules", "you do not fall in any group excluded under the PM-KISAN rules"),
    "eligiblePoorHousehold": ("your household is an eligible poor household under the scheme", "your household is not an eligible poor household"),
    "householdHasLPGConnection": ("your household already has an LPG connection", "no one in your household already has an LPG connection"),
    "familyOwnsPuccaHouseInIndia": ("your family owns a pucca house in India", "your family does not own a pucca house anywhere in India"),
    "familyReceivedGovernmentHousingBenefitInLast20Years": ("your family received a government housing benefit in the last 20 years", "your family has not received a government housing benefit in the last 20 years"),
    "hasParticipatingBankOrPostOfficeAccount": ("you have an account with a participating bank or post office", "you do not have an account with a participating bank or post office"),
    "consentsToEnrolmentAndAutoDebit": ("you agree to enrol and to the premium being auto-debited", "you do not agree to auto-debit"),
    "hasSavingsBankOrPostOfficeAccount": ("you have a savings bank or post-office account", "you do not have a savings bank or post-office account"),
    "girlChildIsResidentIndian": ("the girl child is a resident Indian", "the girl child is not a resident Indian"),
    "worksInEligibleTraditionalTrade": ("you work in one of the scheme's eligible traditional trades", "you do not work in an eligible traditional trade"),
    "governmentEmployeeOrFamilyMember": ("you or a family member is a government employee", "neither you nor a family member is a government employee"),
}

# Numeric rule fields: (subject, unit). Income is formatted in rupees.
NUMERIC_SUBJECTS = {
    "age": ("you are", "years old"),
    "girlChildAge": ("the girl child is", "years old"),
    "annualFamilyIncome": ("your annual family income is", "rupees"),
    "disabilityPercentage": ("your disability is", "%"),
    "cultivableLandHectares": ("your cultivable land is", "hectares"),
}

EQUALS_CONDITIONS = {
    ("gender", "female"): "the applicant is a woman",
    ("gender", "male"): "the applicant is a man",
    ("residence", "urban"): "you live in an urban area",
    ("residence", "rural"): "you live in a rural area",
}

ACRONYMS = {"lpg": "LPG", "udid": "UDID", "nfsa": "NFSA", "apy": "APY", "pm": "PM", "kisan": "KISAN", "e": "e",
            "shram": "Shram", "eshram": "e-Shram", "sukanya": "Sukanya", "tarun": "Tarun", "india": "India", "indian": "Indian"}

# requiredQuestions that read badly when split mechanically.
QUESTION_LABELS = {
    "age": "Your age",
    "gender": "Your gender",
    "state": "Your state",
    "district": "Your district",
    "residence": "Whether you live in a rural or urban area",
    "annualFamilyIncome": "Your family's annual income",
    "monthlyFamilyIncome": "Your family's monthly income",
    "monthlyIncome": "Your monthly income",
    "socialCategory": "Your social category (e.g. SC, ST, OBC)",
    "class12Marks": "Your Class 12 marks",
    "hasDisabilityCertificateOrUDID": "Whether you have a disability certificate or UDID card",
    "listedAsNFSAEligibleBeneficiary": "Whether you are listed as an eligible beneficiary under the National Food Security Act",
    "excludedUnderPMKisanRules": "Whether you fall in a group excluded under the PM-KISAN rules",
    "familyReceivedGovernmentHousingBenefitInLast20Years": "Whether your family received a government housing benefit in the last 20 years",
    "familyOwnsPuccaHouseInIndia": "Whether your family owns a pucca house in India",
    "householdHasLPGConnection": "Whether your household already has an LPG connection",
    "existingAPYSubscription": "Whether you already subscribe to the Atal Pension Yojana",
    "existingEShramRegistration": "Whether you are already registered on e-Shram",
    "previousTarunLoanRepaymentStatus": "Whether you repaid any earlier MUDRA Tarun loan",
    "incomeTaxpayerStatus": "Whether you pay income tax",
    "indianCitizen": "Whether you are an Indian citizen",
    "occupation": "Your occupation",
}


def humanize(field: str) -> str:
    """'hasRationCard' -> 'Has ration card'. Used for fields without a hand-written label."""
    if field in QUESTION_LABELS:
        return QUESTION_LABELS[field]
    words = re.sub(r"(?<=[a-z0-9])(?=[A-Z])|(?<=[A-Z])(?=[A-Z][a-z])", " ", field).split()
    words = [ACRONYMS.get(word.lower(), word.lower()) for word in words]
    text = " ".join(words)
    return text[:1].upper() + text[1:]


def format_rupees(amount: float) -> str:
    """Indian digit grouping: 900000 -> 'Rs. 9,00,000'."""
    whole = str(int(round(amount)))
    if len(whole) > 3:
        head, tail = whole[:-3], whole[-3:]
        head = re.sub(r"(\d)(?=(\d{2})+$)", r"\1,", head)
        whole = f"{head},{tail}"
    return f"Rs. {whole}"


def format_value(field: str, value: Any) -> str:
    if field == "annualFamilyIncome":
        return format_rupees(value)
    number = int(value) if isinstance(value, float) and value.is_integer() else value
    unit = NUMERIC_SUBJECTS.get(field, ("", ""))[1]
    return f"{number}%" if unit == "%" else f"{number} {unit}".strip()


def condition_text(rule: dict[str, Any]) -> str:
    """The rule as a plain sentence fragment, e.g. 'you are between 18 and 40 years old'."""
    field, operator, value = rule["field"], rule["operator"], rule["value"]
    if field in BOOLEAN_CONDITIONS and operator == "equals" and isinstance(value, bool):
        return BOOLEAN_CONDITIONS[field][0 if value else 1]
    if operator == "equals" and (field, value) in EQUALS_CONDITIONS:
        return EQUALS_CONDITIONS[(field, value)]
    if field in NUMERIC_SUBJECTS:
        subject = NUMERIC_SUBJECTS[field][0]
        if operator == "betweenInclusive":
            low, high = value
            # "between 18 and 40 years old" -- the unit once, after the upper bound (rupees on both).
            low_text = format_value(field, low) if field == "annualFamilyIncome" else str(int(low) if float(low).is_integer() else low)
            return f"{subject} between {low_text} and {format_value(field, high)}"
        phrase = {"greaterThanOrEqual": "at least", "lessThanOrEqual": "at most", "lessThan": "under", "equals": "exactly"}[operator]
        return f"{subject} {phrase} {format_value(field, value)}"
    phrase = {"equals": "is", "greaterThanOrEqual": "is at least", "lessThanOrEqual": "is at most", "lessThan": "is under",
              "betweenInclusive": "is between"}[operator]
    shown = f"{value[0]} and {value[1]}" if operator == "betweenInclusive" else value
    return f"{humanize(field).lower()} {phrase} {shown}"


def answer_text(field: str, answer: Any) -> str:
    if field in NUMERIC_SUBJECTS:
        return format_value(field, answer)
    return str(answer)


# --- evaluation ------------------------------------------------------------------------------

def evaluate_rule(rule: dict[str, Any], answers: dict[str, Any]) -> str:
    """'pass', 'fail' or 'unknown' (the field was not answered, or is not one of the questions)."""
    field, operator, value = rule["field"], rule["operator"], rule["value"]
    if field not in answers:
        return "unknown"
    answer = answers[field]
    if operator == "equals":
        if isinstance(value, str) and isinstance(answer, str):
            return "pass" if answer.strip().lower() == value.strip().lower() else "fail"
        return "pass" if answer == value else "fail"
    if isinstance(answer, bool) or not isinstance(answer, (int, float)):
        return "unknown"
    if operator == "greaterThanOrEqual":
        ok = answer >= value
    elif operator == "lessThanOrEqual":
        ok = answer <= value
    elif operator == "lessThan":
        ok = answer < value
    elif operator == "betweenInclusive":
        ok = value[0] <= answer <= value[1]
    else:  # the cleaner only lets the five operators above through
        return "unknown"
    return "pass" if ok else "fail"


def match_scheme(scheme: dict[str, Any], answers: dict[str, Any]) -> dict[str, Any]:
    rules = scheme["eligibilityRules"]
    outcomes = [(rule, evaluate_rule(rule, answers)) for rule in rules]
    failed = [rule for rule, outcome in outcomes if outcome == "fail"]
    passed = [rule for rule, outcome in outcomes if outcome == "pass"]
    unknown = [rule for rule, outcome in outcomes if outcome == "unknown"]
    also_check: list[str] = []
    if not rules:
        group = "check_with_authority"
        reason = f"This scheme's eligibility can't be checked from a few questions. In short: {scheme['eligibilitySummary']}"
    elif failed:
        group = "not_eligible"
        reason = "Based on your answers, this scheme requires that " + "; and that ".join(
            f"{condition_text(rule)} (you said {answer_text(rule['field'], answers[rule['field']])})" for rule in failed
        ) + "."
    elif unknown:
        group = "might_be_eligible"
        also_check = [condition_text(rule) for rule in unknown]
        met = f" Your answers meet: {'; '.join(condition_text(rule) for rule in passed)}." if passed else ""
        reason = f"Nothing in your answers rules this out.{met} The authority will also check: {'; '.join(also_check)}."
    else:
        group = "likely_eligible"
        reason = f"Your answers meet all of this scheme's listed conditions: {'; '.join(condition_text(rule) for rule in passed)}."
    return {
        "id": scheme["id"],
        "name": scheme["name"],
        "category": scheme["category"],
        "area": AREA_LABELS.get(scheme["category"], humanize(scheme["category"])),
        "benefits": scheme["benefits"],
        "eligibilitySummary": scheme["eligibilitySummary"],
        "group": group,
        "reason": reason,
        "alsoCheck": also_check,
        "whatTheyMayAsk": [humanize(question) for question in scheme["requiredQuestions"]],
        "officialUrl": scheme["officialUrl"],
        "sourceUrl": scheme["sourceUrl"],
        "lastVerified": scheme["lastVerified"],
        "disclaimer": DISCLAIMER,
    }


def match(request: MatchRequest) -> dict[str, Any]:
    answers = {
        field: value
        for field, value in request.model_dump(exclude={"areas"}).items()
        if value is not None
    }
    areas = set(request.areas)
    results = [match_scheme(scheme, answers) for scheme in load_schemes() if not areas or scheme["category"] in areas]
    shown = sorted(
        (result for result in results if result["group"] != "not_eligible"),
        key=lambda result: (GROUP_ORDER.index(result["group"]), result["name"].lower()),
    )
    not_eligible = sorted((result for result in results if result["group"] == "not_eligible"), key=lambda r: r["name"].lower())
    return {"results": shown, "notEligible": not_eligible, "disclaimer": DISCLAIMER}


def areas_payload() -> dict[str, Any]:
    counts: dict[str, int] = {}
    for scheme in load_schemes():
        counts[scheme["category"]] = counts.get(scheme["category"], 0) + 1
    return {"areas": [{"id": area, "label": AREA_LABELS.get(area, humanize(area)), "count": counts[area]} for area in scheme_areas()]}
