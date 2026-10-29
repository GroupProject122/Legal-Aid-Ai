"""Clean backend/data/schemes.json into backend/data/schemes_clean.json for the Schemes page.

    python scripts/clean_schemes.py            (from backend/)

Re-runnable; the original file is never modified. It:
- drops two duplicate entries (the same scheme listed twice under different ids);
- renames question/rule field names that mean the same thing, so one answer works for every
  scheme that asks it (FIELD_SYNONYMS);
- validates every scheme and stops with a list of every problem if anything is wrong.

It does not add, remove or change any eligibility rule, value or URL.
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1]
SOURCE = BACKEND / "data" / "schemes.json"
TARGET = BACKEND / "data" / "schemes_clean.json"

# id dropped -> id kept (the kept entry is the more complete / better-sourced one).
DUPLICATES = {
    "PMVISHWAKARMA": "PM-VISHWAKARMA-VERIFIED",
    "PMMY-MUDRA": "MUDRA",
}

# Same question asked under two names. The left-hand name is replaced by the right-hand one in
# eligibilityRules and requiredQuestions.
FIELD_SYNONYMS = {
    "familyIncome": "annualFamilyIncome",
    "applicantCategory": "socialCategory",
    "educationQualification": "educationLevel",
    "disabilityCertificateStatus": "hasDisabilityCertificateOrUDID",
}

REQUIRED_KEYS = (
    "id", "name", "scope", "category", "benefitType", "benefits", "eligibilitySummary",
    "eligibilityRules", "requiredQuestions", "eligibilityStatus", "officialUrl", "sourceUrl",
    "lastVerified",
)
OPERATORS = {"equals", "greaterThanOrEqual", "lessThanOrEqual", "lessThan", "betweenInclusive"}
NUMERIC_OPERATORS = {"greaterThanOrEqual", "lessThanOrEqual", "lessThan"}
DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class SchemeDataError(ValueError):
    """Raised with every problem found, one per line."""


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def validate(schemes: list[dict]) -> list[str]:
    """All problems in `schemes`, as readable lines. Empty list = valid."""
    problems: list[str] = []
    if not isinstance(schemes, list) or not schemes:
        return ["the file must contain a non-empty list of schemes"]
    seen_ids: set[str] = set()
    seen_names: set[str] = set()
    for index, scheme in enumerate(schemes):
        where = f"scheme #{index + 1} ({scheme.get('id', '?') if isinstance(scheme, dict) else '?'})"
        if not isinstance(scheme, dict):
            problems.append(f"{where}: not an object")
            continue
        missing = [key for key in REQUIRED_KEYS if key not in scheme]
        if missing:
            problems.append(f"{where}: missing keys {missing}")
            continue
        for key in ("id", "name", "category", "benefits", "eligibilitySummary"):
            if not isinstance(scheme[key], str) or not scheme[key].strip():
                problems.append(f"{where}: '{key}' must be a non-empty string")
        if scheme["id"] in seen_ids:
            problems.append(f"{where}: duplicate id")
        if scheme["name"] in seen_names:
            problems.append(f"{where}: duplicate name '{scheme['name']}'")
        seen_ids.add(scheme["id"])
        seen_names.add(scheme["name"])
        for key in ("officialUrl", "sourceUrl"):
            if not isinstance(scheme[key], str) or not scheme[key].startswith("https://"):
                problems.append(f"{where}: '{key}' must be an https URL, got {scheme[key]!r}")
        verified = scheme["lastVerified"]
        if verified is not None and not (isinstance(verified, str) and DATE_RE.match(verified)):
            problems.append(f"{where}: 'lastVerified' must be null or YYYY-MM-DD, got {verified!r}")
        questions = scheme["requiredQuestions"]
        if not isinstance(questions, list) or not all(isinstance(q, str) and q for q in questions):
            problems.append(f"{where}: 'requiredQuestions' must be a list of field names")
        rules = scheme["eligibilityRules"]
        if not isinstance(rules, list):
            problems.append(f"{where}: 'eligibilityRules' must be a list")
            continue
        for rule_index, rule in enumerate(rules):
            at = f"{where} rule {rule_index + 1}"
            if not isinstance(rule, dict) or set(rule) != {"field", "operator", "value"}:
                problems.append(f"{at}: must have exactly field, operator and value")
                continue
            operator, value = rule["operator"], rule["value"]
            if not isinstance(rule["field"], str) or not rule["field"]:
                problems.append(f"{at}: 'field' must be a non-empty string")
            if operator not in OPERATORS:
                problems.append(f"{at}: unknown operator {operator!r}")
            elif operator == "betweenInclusive":
                if not (isinstance(value, list) and len(value) == 2 and all(is_number(v) for v in value) and value[0] <= value[1]):
                    problems.append(f"{at}: betweenInclusive needs [min, max] numbers, got {value!r}")
            elif operator in NUMERIC_OPERATORS and not is_number(value):
                problems.append(f"{at}: {operator} needs a number, got {value!r}")
            elif operator == "equals" and not isinstance(value, (str, bool, int, float)):
                problems.append(f"{at}: equals needs a single value, got {value!r}")
    return problems


def rename(field: str) -> str:
    return FIELD_SYNONYMS.get(field, field)


def clean(raw: list[dict]) -> list[dict]:
    """Validated, de-duplicated schemes with field synonyms merged. Raises SchemeDataError."""
    problems = validate_raw_duplicates(raw)
    if problems:
        raise SchemeDataError("\n".join(problems))
    kept = [dict(scheme) for scheme in raw if scheme.get("id") not in DUPLICATES]
    for scheme in kept:
        scheme["eligibilityRules"] = [{**rule, "field": rename(rule["field"])} for rule in scheme["eligibilityRules"]]
        questions: list[str] = []
        for question in scheme["requiredQuestions"]:
            name = rename(question)
            if name not in questions:
                questions.append(name)
        scheme["requiredQuestions"] = questions
    problems = validate(kept)
    if problems:
        raise SchemeDataError("\n".join(problems))
    return kept


def validate_raw_duplicates(raw: list[dict]) -> list[str]:
    """The duplicate pairs must both be present before dropping one -- otherwise the source file
    changed and this script's assumptions need a fresh look."""
    if not isinstance(raw, list):
        return ["the file must contain a list of schemes"]
    ids = {scheme.get("id") for scheme in raw if isinstance(scheme, dict)}
    return [
        f"expected duplicate pair {dropped!r} / {kept!r} is not both present"
        for dropped, kept in DUPLICATES.items()
        if dropped not in ids or kept not in ids
    ]


def url_warnings(schemes: list[dict]) -> list[str]:
    """Not errors (the URLs are kept exactly as given), but worth a human look."""
    return [
        f"{scheme['id']}: {key} contains whitespace: {scheme[key]!r}"
        for scheme in schemes
        for key in ("officialUrl", "sourceUrl")
        if re.search(r"\s", scheme[key])
    ]


def main() -> int:
    raw = json.loads(SOURCE.read_text(encoding="utf-8"))
    try:
        schemes = clean(raw)
    except SchemeDataError as exc:
        print(f"schemes.json is not valid -- nothing written:\n{exc}", file=sys.stderr)
        return 1
    for warning in url_warnings(schemes):
        print(f"warning: {warning}", file=sys.stderr)
    TARGET.write_text(json.dumps(schemes, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    without_rules = sum(1 for scheme in schemes if not scheme["eligibilityRules"])
    print(f"Wrote {TARGET.relative_to(BACKEND)}: {len(schemes)} schemes ({len(raw) - len(schemes)} duplicates removed), "
          f"{without_rules} with no machine-checkable rules.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
