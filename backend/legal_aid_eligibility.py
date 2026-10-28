"""Free Legal Aid Eligibility Checker: tells a user whether they are likely entitled to free legal
services, why (with the legal source), and where to apply.

Deterministic rules only -- no Gemini call anywhere in this module.

Scope (everything else is "cannot_determine", never a guess):
- Section 12 of the Legal Services Authorities Act, 1987 (in our corpus) applies everywhere.
- Income limits and the extra Delhi-only categories are checked for Delhi only, per the Delhi
  State Legal Services Authority (DSLSA). The Delhi Legal Services Authority Regulations, 2002
  are NOT in our corpus and no official machine-readable copy could be found (2026-10-28), so
  those rules cite the DSLSA eligibility page with authority "official_website".
- Supreme Court cases go to the Supreme Court Legal Services Committee, which has its own
  (Central) limit under Section 12(h) -- not checked here.

Privacy: the answers include caste, disability, HIV status and income. This module has no
logger on purpose, and nothing here writes to the database or a file. main.py parses the
request body itself (see legal_aid_eligibility_endpoint) so the global RequestValidationError
handler never logs a submitted body either.
"""
from __future__ import annotations

import math
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

RESULT_LIKELY_ELIGIBLE = "likely_eligible"
RESULT_LIKELY_NOT_ELIGIBLE = "likely_not_eligible"
RESULT_CANNOT_DETERMINE = "cannot_determine"

DISCLAIMER = "This is a guide, not a final decision. The Legal Services Authority decides your application."

LAST_VERIFIED = "2026-10-28"

# --- Sources ---------------------------------------------------------------------------------

LSA_ACT_SOURCE_ID = "constitutional_public_authority__legal_services_authorities_act_1987"
NALSA_LEGAL_SERVICES_REGS_SOURCE_ID = "constitutional_public_authority__nalsa_free_and_competent_legal_services_regulations_2010"
NALSA_CLINICS_REGS_SOURCE_ID = "constitutional_public_authority__nalsa_legal_services_clinics_regulations_2011"
SENIOR_CITIZENS_ACT_SOURCE_ID = "constitutional_public_authority__maintenance_and_welfare_of_parents_and_senior_citizens_act_2007"

# DSLSA's own eligibility page. It cites "chapter VI, Rule 9, of the Delhi Legal Services
# Authority Regulation 2002" and lists the categories and income limits used below. Re-checked
# on 2026-10-28 together with the matching official page on delhi.nalsa.gov.in ("last updated
# July 01, 2025"), which gives the same Rs. 3 lakh / Rs. 4 lakh figures.
DSLSA_ELIGIBILITY_URL = "https://dslsa.org/wd/wings/legal-aid-wing-2/providing-legal-aid-benificiaries/"
DSLSA_ELIGIBILITY_TITLE = (
    "Delhi State Legal Services Authority: who is eligible for free legal aid "
    "(Delhi Legal Services Authority Regulations, 2002, Chapter VI, Rule 9)"
)
DSLSA_FAQ_URL = "https://dslsa.org/faqs/"


def corpus_source(source_id: str, provision_id: str, title: str, provision: str) -> dict[str, Any]:
    """A source in our own corpus. The frontend opens it in the source viewer; the provision is
    checked to resolve against the parsed corpus by tests/test_legal_aid_eligibility.py."""
    return {
        "title": title,
        "provision": provision,
        "authority": "statute",
        "source_id": source_id,
        "provision_id": provision_id,
        "api_url": f"/api/legal-awareness/sources/{source_id}/provisions/{provision_id}",
        "url": None,
    }


def section_12(clause: str) -> dict[str, Any]:
    return corpus_source(LSA_ACT_SOURCE_ID, "section-12", "Legal Services Authorities Act, 1987", f"Section 12({clause})")


def dslsa_source(provision: str) -> dict[str, Any]:
    return {
        "title": DSLSA_ELIGIBILITY_TITLE,
        "provision": provision,
        "authority": "official_website",
        "source_id": None,
        "provision_id": None,
        "api_url": None,
        "url": DSLSA_ELIGIBILITY_URL,
        "last_verified": LAST_VERIFIED,
    }


# --- Income limits ---------------------------------------------------------------------------

# One place to update when limits change. Section 12(h) of the Act sets only a floor ("annual
# income less than rupees nine thousand or such other higher amount as may be prescribed by the
# State Government") -- Delhi has prescribed higher amounts, and those are what apply. Every
# limit is LESS THAN, not "up to": an income of exactly Rs. 3,00,000 is NOT under the general
# limit. History, from DSLSA's own pages: the 2019 DSLSA application form still printed
# Rs. 1 lakh (general) and Rs. 2 lakh (senior citizen / transgender); some older DSLSA pages
# still show Rs. 2 lakh. We use the current figures shown on the DSLSA eligibility page.
LIMITS: dict[str, dict[str, Any]] = {
    "delhi_general": {
        "label": "Anyone (Delhi)",
        "limit_name": "the general limit",
        "amount_inr": 300_000,
        "comparison": "less_than",
        "source_title": DSLSA_ELIGIBILITY_TITLE,
        "source_wording": "Person having annual income less than Rs. 3 Lac",
        "url": DSLSA_ELIGIBILITY_URL,
        "authority": "official_website",
        "last_verified": LAST_VERIFIED,
    },
    "delhi_senior_citizen": {
        "label": "Senior citizen (Delhi)",
        "limit_name": "the limit for senior citizens",
        "amount_inr": 400_000,
        "comparison": "less_than",
        "source_title": DSLSA_ELIGIBILITY_TITLE,
        "source_wording": "Senior Citizen having annual income less than Rs. 4 Lac",
        "url": DSLSA_ELIGIBILITY_URL,
        "authority": "official_website",
        "last_verified": LAST_VERIFIED,
    },
    "delhi_transgender": {
        "label": "Transgender person (Delhi)",
        "limit_name": "the limit for transgender persons",
        "amount_inr": 400_000,
        "comparison": "less_than",
        "source_title": DSLSA_ELIGIBILITY_TITLE,
        "source_wording": "Transgender having annual income less than Rs. 4 Lac",
        "url": DSLSA_ELIGIBILITY_URL,
        "authority": "official_website",
        "last_verified": LAST_VERIFIED,
    },
}

# Neither the DSLSA page nor the delhi.nalsa.gov.in page defines these two points. Recorded here
# rather than hidden; see CHANGELOG.md.
ASSUMPTIONS: dict[str, str] = {
    "income_basis": (
        "The limit is compared with the applicant's OWN annual income. The current DSLSA page only "
        "says 'annual income'. Section 12(h) of the Act says a person 'in receipt of annual "
        "income', Section 13(2) accepts 'an affidavit made by a person as to his income', and "
        "DSLSA's own application form asks for the 'income of the applicant'. No source we found "
        "mentions family or household income. The Authority may still ask about family support."
    ),
    "senior_citizen_age": (
        "DSLSA does not state an age for 'senior citizen'. We use 60 and above, the statutory "
        "definition in Section 2(h) of the Maintenance and Welfare of Parents and Senior Citizens "
        "Act, 2007 (in our corpus), which is also the age NALSA uses."
    ),
}

# What the user sees for each assumption above, in plain words.
USER_NOTES: dict[str, str] = {
    "income_basis": "We compared the limit with your own yearly income. The Authority may also ask "
                    "about your family's support.",
    "senior_citizen_age": "We counted you as a senior citizen because you are 60 or older. DSLSA does "
                          "not say which age it uses.",
}

SENIOR_CITIZEN_MIN_AGE = 60  # Section 2(h), Senior Citizens Act, 2007 -- see ASSUMPTIONS
CHILD_MAX_AGE_EXCLUSIVE = 18  # "child" in Section 12(c) = under 18
MIN_AGE = 0
MAX_AGE = 120
MAX_STATE_CHARS = 60

DELHI_NAMES = {"delhi", "new delhi", "nct of delhi", "national capital territory of delhi", "nct delhi"}


def is_below_limit(income: float, limit: dict[str, Any]) -> bool:
    if limit["comparison"] != "less_than":
        raise ValueError(f"Unsupported comparison: {limit['comparison']}")
    return income < limit["amount_inr"]


def format_inr(amount: float) -> str:
    """Indian digit grouping: 300000 -> 'Rs. 3,00,000'."""
    whole = int(round(amount))
    digits = str(whole)
    if len(digits) > 3:
        head, tail = digits[:-3], digits[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        digits = ",".join(groups + [tail])
    return f"Rs. {digits}"


# --- Request model ---------------------------------------------------------------------------


class Court(str, Enum):
    supreme_court = "supreme_court"
    other = "other"


class Category(str, Enum):
    sc_st = "sc_st"
    trafficking_or_begar = "trafficking_or_begar"
    woman = "woman"
    disability = "disability"
    disaster_victim = "disaster_victim"
    industrial_workman = "industrial_workman"
    in_custody = "in_custody"
    transgender = "transgender"
    acid_attack_victim = "acid_attack_victim"
    hiv_aids = "hiv_aids"
    defence_family = "defence_family"


# "Child" is deliberately not a category: it is worked out from the age the user gives. Nothing
# else (gender included) is ever inferred -- the user ticks what applies.
class EligibilityRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str
    court: Court
    categories: list[Category] = Field(default_factory=list)
    age: int
    annual_income: float | None = None

    @field_validator("state", mode="before")
    @classmethod
    def check_state(cls, value: Any) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Tell us which state the case is in.")
        if len(value.strip()) > MAX_STATE_CHARS:
            raise ValueError(f"State name is too long (at most {MAX_STATE_CHARS} characters).")
        return value.strip()

    @field_validator("age", mode="before")
    @classmethod
    def check_age(cls, value: Any) -> int:
        # bool is an int in Python; a fractional age is a typo, not something to round.
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError("Enter your age as a whole number.")
        if not MIN_AGE <= value <= MAX_AGE:
            raise ValueError(f"Age must be between {MIN_AGE} and {MAX_AGE}.")
        return value

    @field_validator("annual_income", mode="before")
    @classmethod
    def check_annual_income(cls, value: Any) -> float | None:
        if value is None:
            return None
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("Enter your yearly income as a number of rupees.")
        if value < 0:
            raise ValueError("Yearly income cannot be negative. Enter 0 if you have no income.")
        return float(value)

    @field_validator("categories", mode="after")
    @classmethod
    def dedupe_categories(cls, value: list[Category]) -> list[Category]:
        return list(dict.fromkeys(value))


FIELD_MESSAGES = {
    "missing": "This answer is required.",
    "extra_forbidden": "This question is not part of the check.",
}
ENUM_MESSAGES = {
    "court": "Choose 'supreme_court' or 'other'.",
    "categories": "One of the ticked options is not recognised.",
}


def validation_errors(exc: ValidationError) -> list[dict[str, str]]:
    """Field-level errors for the API. Deliberately built from loc + type only, never from the
    submitted input (pydantic's own error dicts carry the input -- caste, HIV status, income)."""
    errors = []
    for error in exc.errors(include_input=False, include_url=False):
        loc = [str(part) for part in error.get("loc", ())]
        field_name = loc[0] if loc else "body"
        error_type = error.get("type", "")
        if error_type == "value_error":
            message = str(error.get("ctx", {}).get("error") or error.get("msg", ""))
        elif error_type in FIELD_MESSAGES:
            message = FIELD_MESSAGES[error_type]
        elif error_type == "enum" or field_name in ENUM_MESSAGES:
            message = ENUM_MESSAGES.get(field_name, "This answer is not one of the allowed options.")
        else:
            message = "This answer is not in the expected format."
        errors.append({"field": field_name, "message": message})
    return errors


# --- Rules -----------------------------------------------------------------------------------


@dataclass(frozen=True)
class Rule:
    rule_id: str
    jurisdiction: str  # "all_india" (Section 12) or "Delhi"
    check: Callable[[EligibilityRequest], bool]
    reason: str
    source: dict[str, Any]
    limit_key: str | None = None


def ticked(category: Category) -> Callable[[EligibilityRequest], bool]:
    return lambda answers: category in answers.categories


def is_child(answers: EligibilityRequest) -> bool:
    return answers.age < CHILD_MAX_AGE_EXCLUSIVE


def is_senior_citizen(answers: EligibilityRequest) -> bool:
    return answers.age >= SENIOR_CITIZEN_MIN_AGE


# Category rules: any one match is enough, whatever the income. Order is the order of Section
# 12's clauses, then the Delhi-only categories.
CATEGORY_RULES: tuple[Rule, ...] = (
    Rule("s12_a_sc_st", "all_india", ticked(Category.sc_st),
         "You belong to a Scheduled Caste or Scheduled Tribe.", section_12("a")),
    Rule("s12_b_trafficking_or_begar", "all_india", ticked(Category.trafficking_or_begar),
         "You are a victim of trafficking in human beings or begar (forced unpaid labour).", section_12("b")),
    Rule("s12_c_woman", "all_india", ticked(Category.woman),
         "You are a woman. Women are entitled whatever their income.", section_12("c")),
    Rule("s12_c_child", "all_india", is_child,
         f"You are under {CHILD_MAX_AGE_EXCLUSIVE}, so you count as a child.", section_12("c")),
    Rule("s12_d_disability", "all_india", ticked(Category.disability),
         "You are a person with a disability.", section_12("d")),
    Rule("s12_e_disaster_victim", "all_india", ticked(Category.disaster_victim),
         "You are a victim of a mass disaster, ethnic violence, caste atrocity, flood, drought, "
         "earthquake or industrial disaster.", section_12("e")),
    Rule("s12_f_industrial_workman", "all_india", ticked(Category.industrial_workman),
         "You are an industrial workman.", section_12("f")),
    Rule("s12_g_in_custody", "all_india", ticked(Category.in_custody),
         "You are in custody (including a protective home, juvenile home, or psychiatric hospital "
         "or nursing home).", section_12("g")),
    Rule("delhi_acid_attack_victim", "Delhi", ticked(Category.acid_attack_victim),
         "In Delhi, acid attack victims are eligible whatever their income.",
         dslsa_source("Acid Attack Victim")),
    Rule("delhi_hiv_aids", "Delhi", ticked(Category.hiv_aids),
         "In Delhi, people infected with or affected by HIV/AIDS are eligible whatever their income.",
         dslsa_source("Person infected and affected with HIV Aids")),
    Rule("delhi_defence_family", "Delhi", ticked(Category.defence_family),
         "In Delhi, defence personnel, veterans and their families are eligible whatever their "
         "income (NALSA Veer Parivar Sahayata Yojana, 2025).",
         dslsa_source("Defence Personnel, Veterans and their Families (NALSA Veer Parivar Sahayata Yojana, 2025)")),
)


def below(limit_key: str) -> Callable[[EligibilityRequest], bool]:
    return lambda answers: answers.annual_income is not None and is_below_limit(answers.annual_income, LIMITS[limit_key])


# Income rules: only looked at when no category rule matched. The higher limits come first so
# the reason names the limit that actually helps the person.
INCOME_RULES: tuple[Rule, ...] = (
    Rule("delhi_income_senior_citizen", "Delhi",
         lambda a: is_senior_citizen(a) and below("delhi_senior_citizen")(a),
         f"You are {SENIOR_CITIZEN_MIN_AGE} or older and your yearly income is less than "
         f"{format_inr(LIMITS['delhi_senior_citizen']['amount_inr'])}, the Delhi limit for senior citizens.",
         dslsa_source(LIMITS["delhi_senior_citizen"]["source_wording"]), "delhi_senior_citizen"),
    Rule("delhi_income_transgender", "Delhi",
         lambda a: Category.transgender in a.categories and below("delhi_transgender")(a),
         f"You are a transgender person and your yearly income is less than "
         f"{format_inr(LIMITS['delhi_transgender']['amount_inr'])}, the Delhi limit for transgender persons.",
         dslsa_source(LIMITS["delhi_transgender"]["source_wording"]), "delhi_transgender"),
    Rule("delhi_income_general", "Delhi", below("delhi_general"),
         f"Your yearly income is less than {format_inr(LIMITS['delhi_general']['amount_inr'])}, the Delhi limit.",
         dslsa_source(LIMITS["delhi_general"]["source_wording"]), "delhi_general"),
)

RULES: dict[str, Rule] = {rule.rule_id: rule for rule in CATEGORY_RULES + INCOME_RULES}

SENIOR_CITIZEN_DEFINITION_SOURCE = corpus_source(
    SENIOR_CITIZENS_ACT_SOURCE_ID, "section-2",
    "Maintenance and Welfare of Parents and Senior Citizens Act, 2007", "Section 2(h)",
)
INCOME_AFFIDAVIT_SOURCE = corpus_source(LSA_ACT_SOURCE_ID, "section-13", "Legal Services Authorities Act, 1987", "Section 13(2)")
APPLICATION_SOURCE = corpus_source(
    NALSA_LEGAL_SERVICES_REGS_SOURCE_ID, "regulation-3",
    "NALSA (Free and Competent Legal Services) Regulations, 2010", "Regulation 3",
)
LOK_ADALAT_SOURCE = corpus_source(LSA_ACT_SOURCE_ID, "section-19", "Legal Services Authorities Act, 1987", "Section 19")
CLINICS_SOURCE = corpus_source(
    NALSA_CLINICS_REGS_SOURCE_ID, "regulation-3",
    "NALSA (Legal Services Clinics) Regulations, 2011", "Regulation 3",
)


def applicable_limit_keys(answers: EligibilityRequest) -> list[str]:
    keys = ["delhi_general"]
    if is_senior_citizen(answers):
        keys.append("delhi_senior_citizen")
    if Category.transgender in answers.categories:
        keys.append("delhi_transgender")
    return keys


def is_delhi(state: str) -> bool:
    return " ".join(state.lower().replace(".", "").split()) in DELHI_NAMES


# --- Fixed guidance --------------------------------------------------------------------------

NALSA_HELPLINE = {"name": "NALSA legal services helpline", "phone": "15100",
                  "detail": "Free national helpline for legal aid and advice."}

APPLY_HOW = {
    "name": "How to apply",
    "detail": "You can fill in an application form, write a simple letter, or just ask in person. "
              "If you cannot write, the staff must help you fill it in.",
    "source": APPLICATION_SOURCE,
}

WHERE_TO_APPLY_DELHI: list[dict[str, Any]] = [
    {"name": "Front office of your District Legal Services Authority (DLSA)",
     "detail": "Every district court complex in Delhi has one. Go to the one nearest you, or the one "
               "where your case is."},
    {"name": "Delhi State Legal Services Authority (DSLSA), Central Office",
     "detail": "Patiala House Courts Complex, New Delhi - 110001.", "url": "https://dslsa.org"},
    {"name": "Delhi High Court Legal Services Committee",
     "detail": "If your case is in the Delhi High Court, apply here instead."},
    {"name": "DSLSA helpline", "phone": "1516", "detail": "Free, 24x7."},
    NALSA_HELPLINE,
    APPLY_HOW,
]

WHERE_TO_APPLY_OTHER_STATE: list[dict[str, Any]] = [
    {"name": "Your State Legal Services Authority, or the District Legal Services Authority at your district court",
     "detail": "They will tell you the income limit that applies in your state.", "url": "https://nalsa.gov.in"},
    NALSA_HELPLINE,
    APPLY_HOW,
]

WHERE_TO_APPLY_SUPREME_COURT: list[dict[str, Any]] = [
    {"name": "Supreme Court Legal Services Committee",
     "detail": "Handles free legal aid for cases in the Supreme Court of India, New Delhi."},
    NALSA_HELPLINE,
    APPLY_HOW,
]

DOCUMENTS_ALWAYS = [
    {"text": "Any papers about your case: notices, summons, court papers, a copy of the FIR, "
             "agreements, letters or receipts."},
    {"text": "An identity proof you already have. If you don't have one, ask at the front office."},
]
DOCUMENTS_CATEGORY = {
    "text": "If you have one, any paper that shows the category you ticked (for example a certificate). "
            "You can also sign a self-declaration on DSLSA's application form.",
}
DOCUMENTS_INCOME = {
    "text": "A signed statement (affidavit) of your yearly income. The law says this is usually "
            "enough proof of income.",
    "source": INCOME_AFFIDAVIT_SOURCE,
}

ALTERNATIVES: list[dict[str, Any]] = [
    {"name": "Free legal aid clinic",
     "detail": "Legal services clinics give free legal advice. Ask your District Legal Services "
               "Authority where the nearest one is.",
     "source": CLINICS_SOURCE},
    {"name": "Lok Adalat",
     "detail": "Settle a dispute by agreement, before or during a court case. Not available for "
               "serious criminal offences that cannot be compromised.",
     "source": LOK_ADALAT_SOURCE},
    {"name": "Call 15100", "phone": "15100",
     "detail": "NALSA's free helpline can advise you and tell you about other free help."},
    {"name": "Free legal advice in Delhi",
     "detail": "DSLSA says free legal advice is available to anyone, even if you can't get a free "
               "lawyer. If you apply and are refused, you can appeal to the Chairman of the Authority.",
     "url": DSLSA_FAQ_URL},
]


# --- Result ----------------------------------------------------------------------------------


@dataclass
class EligibilityResult:
    result: str
    headline: str
    reason: str
    matched_rules: list[dict[str, Any]]
    where_to_apply: list[dict[str, Any]]
    documents_to_bring: list[dict[str, Any]]
    alternatives: list[dict[str, Any]]
    needs: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    disclaimer: str = DISCLAIMER
    last_verified: str = LAST_VERIFIED

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def matched(rule: Rule) -> dict[str, Any]:
    return {"rule_id": rule.rule_id, "jurisdiction": rule.jurisdiction, "reason": rule.reason, "source": rule.source}


def section_12_matches(answers: EligibilityRequest) -> list[Rule]:
    return [rule for rule in CATEGORY_RULES if rule.jurisdiction == "all_india" and rule.check(answers)]


def check_eligibility(answers: EligibilityRequest | dict[str, Any]) -> EligibilityResult:
    """Category matches win before income is considered; income is only needed when no category
    matches. Raises pydantic.ValidationError for a dict that fails EligibilityRequest."""
    if not isinstance(answers, EligibilityRequest):
        answers = EligibilityRequest.model_validate(answers)

    if answers.court == Court.supreme_court:
        rules = section_12_matches(answers)
        reason = (
            "Cases in the Supreme Court are handled by the Supreme Court Legal Services Committee, "
            "which uses its own income limit set by the Central Government. This tool does not check that limit."
        )
        if rules:
            clauses = ", ".join(rule.source["provision"] for rule in rules)
            reason += (f" You appear to fall under {clauses} of the Legal Services Authorities Act, which "
                       "also applies in the Supreme Court, so you are very likely entitled -- the Committee must confirm it.")
        return EligibilityResult(
            result=RESULT_CANNOT_DETERMINE,
            headline="Ask the Supreme Court Legal Services Committee",
            reason=reason,
            matched_rules=[matched(rule) for rule in rules],
            where_to_apply=WHERE_TO_APPLY_SUPREME_COURT,
            documents_to_bring=list(DOCUMENTS_ALWAYS),
            alternatives=[],
        )

    if not is_delhi(answers.state):
        rules = section_12_matches(answers)
        reason = (
            "The groups listed in Section 12 of the Legal Services Authorities Act (for example women, "
            "children, SC/ST, people with disabilities and people in custody) apply in every state. "
            "But income limits are set by each state, and this tool only knows Delhi's."
        )
        if rules:
            clauses = ", ".join(rule.source["provision"] for rule in rules)
            reason += (f" You appear to fall under {clauses}, so you are very likely entitled in your "
                       "state too -- your State Legal Services Authority must confirm it.")
        return EligibilityResult(
            result=RESULT_CANNOT_DETERMINE,
            headline="Check with your State Legal Services Authority",
            reason=reason,
            matched_rules=[matched(rule) for rule in rules],
            where_to_apply=WHERE_TO_APPLY_OTHER_STATE,
            documents_to_bring=list(DOCUMENTS_ALWAYS),
            alternatives=[],
        )

    category_matches = [rule for rule in CATEGORY_RULES if rule.check(answers)]
    if category_matches:
        return EligibilityResult(
            result=RESULT_LIKELY_ELIGIBLE,
            headline="You are likely entitled to free legal aid",
            reason=category_matches[0].reason + " Your income does not matter for this.",
            matched_rules=[matched(rule) for rule in category_matches],
            where_to_apply=WHERE_TO_APPLY_DELHI,
            documents_to_bring=DOCUMENTS_ALWAYS + [DOCUMENTS_CATEGORY],
            alternatives=[],
        )

    if answers.annual_income is None:
        # Never guess: none of the categories applies, so the answer depends on income alone.
        return EligibilityResult(
            result=RESULT_CANNOT_DETERMINE,
            headline="We need your yearly income",
            reason="None of the groups you ticked gives free legal aid on its own, so in Delhi it "
                   "depends on your yearly income. Please tell us your income to finish the check.",
            matched_rules=[],
            where_to_apply=WHERE_TO_APPLY_DELHI,
            documents_to_bring=list(DOCUMENTS_ALWAYS),
            alternatives=[],
            needs=["annual_income"],
        )

    notes = [USER_NOTES["income_basis"]]
    if is_senior_citizen(answers):
        notes.append(USER_NOTES["senior_citizen_age"])

    income_match = next((rule for rule in INCOME_RULES if rule.check(answers)), None)
    if income_match:
        return EligibilityResult(
            result=RESULT_LIKELY_ELIGIBLE,
            headline="You are likely entitled to free legal aid",
            reason=income_match.reason,
            matched_rules=[matched(income_match)],
            where_to_apply=WHERE_TO_APPLY_DELHI,
            documents_to_bring=DOCUMENTS_ALWAYS + [DOCUMENTS_INCOME],
            alternatives=[],
            notes=notes,
        )

    best_key = max(applicable_limit_keys(answers), key=lambda key: LIMITS[key]["amount_inr"])
    limit = LIMITS[best_key]
    return EligibilityResult(
        result=RESULT_LIKELY_NOT_ELIGIBLE,
        headline="You are probably not entitled to a free lawyer",
        reason=(
            f"In Delhi, the yearly income must be less than {format_inr(limit['amount_inr'])} "
            f"({limit['limit_name']}). You told us {format_inr(answers.annual_income)}, which is not "
            "below that limit, and none of the groups that get free legal aid regardless of income applies."
        ),
        matched_rules=[],
        where_to_apply=WHERE_TO_APPLY_DELHI,
        documents_to_bring=list(DOCUMENTS_ALWAYS),
        alternatives=ALTERNATIVES,
        notes=notes,
    )
