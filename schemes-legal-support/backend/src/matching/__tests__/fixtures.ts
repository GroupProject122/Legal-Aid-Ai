import type { ConditionNode, Scheme, UserProfile } from "../types";

/** A fully-populated profile: 30yo SC farmer in Maharashtra, low income. */
export const fullProfile: UserProfile = {
  state: "Maharashtra",
  age: 30,
  gender: "male",
  annual_family_income: 150_000,
  occupation: "farmer",
  education_level: "10th_pass",
  category: "sc",
  support_type_needed: "agriculture",
};

/** Build a Scheme around an eligibility tree; the other fields are filler. */
export function makeScheme(
  scheme_id: string,
  hard: ConditionNode,
  soft: ConditionNode | null = null,
): Scheme {
  return {
    scheme_id,
    name: `Test scheme ${scheme_id}`,
    short_summary: "Fixture scheme.",
    level: "Central",
    state: null,
    category: ["test"],
    eligibility: { hard, soft },
    benefits: "Test benefit.",
    documents_required: ["Aadhaar card"],
    application_process: "Apply online.",
    official_source_url: "https://example.gov.in",
    apply_url: null,
    last_verified_date: null,
    verification_status: "needs_review",
  };
}

/** Return a copy of `fullProfile` without the named keys. */
export function profileWithout(
  ...keys: (keyof UserProfile)[]
): UserProfile {
  const copy: UserProfile = { ...fullProfile };
  for (const key of keys) delete copy[key];
  return copy;
}

// --- reusable condition-tree fixtures ---------------------------------

/** AND( state = Maharashtra, occupation = farmer, income <= 200000 ) */
export const andOnlyHard: ConditionNode = {
  op: "AND",
  children: [
    { field: "state", operator: "equals", value: "Maharashtra" },
    { field: "occupation", operator: "equals", value: "farmer" },
    { field: "annual_family_income", operator: "lte", value: 200_000 },
  ],
};

/** AND( (category in [sc, st]) OR-group, income <= 100000 ) */
export const nestedHard: ConditionNode = {
  op: "AND",
  children: [
    {
      op: "OR",
      children: [
        { field: "category", operator: "equals", value: "sc" },
        { field: "category", operator: "equals", value: "st" },
      ],
    },
    { field: "annual_family_income", operator: "lte", value: 100_000 },
  ],
};

/** AND( NOT(occupation = salaried), income <= 500000 ) */
export const notHard: ConditionNode = {
  op: "AND",
  children: [
    { op: "NOT", child: { field: "occupation", operator: "equals", value: "salaried" } },
    { field: "annual_family_income", operator: "lte", value: 500_000 },
  ],
};
