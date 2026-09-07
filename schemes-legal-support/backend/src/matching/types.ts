/**
 * Shared types for the eligibility matching module.
 *
 * These mirror the grammar documented in ../../../docs/data-model.md. This
 * module is pure logic: it does not import the Prisma client or Express.
 *
 * NOTE ON `UserProfile`: for matching, every field is OPTIONAL. The intake
 * form may be only partially filled, and a missing field is exactly what
 * produces the "unknown" evaluation state. The *persisted* UserProfile
 * (prisma/schema.prisma) requires all fields.
 */

export type IndianState = string;

export type Gender = "male" | "female" | "other";

export type Occupation =
  | "farmer"
  | "student"
  | "unemployed"
  | "salaried"
  | "self_employed"
  | "other";

export type EducationLevel =
  | "below_10th"
  | "10th_pass"
  | "12th_pass"
  | "graduate"
  | "postgraduate"
  | "other";

export type SocialCategory =
  | "general"
  | "obc"
  | "sc"
  | "st"
  | "ebc"
  | "dnt"
  | "other";

export type SupportType =
  | "financial_aid"
  | "education"
  | "healthcare"
  | "housing"
  | "employment"
  | "agriculture"
  | "business"
  | "other";

export type LandHolding = "none" | "individual" | "institutional";

export type GovernmentEmployeeGrade =
  | "not_applicable"
  | "group_a_b_c"
  | "group_d_mts";

/**
 * The intake fields a leaf condition's `field` may name. The first 8 are
 * required on a stored profile; the last 4 are optional/nullable.
 */
export const USER_PROFILE_FIELDS = [
  "state",
  "age",
  "gender",
  "annual_family_income",
  "occupation",
  "education_level",
  "category",
  "support_type_needed",
  "land_holding",
  "paid_income_tax_last_year",
  "monthly_pension",
  "government_employee_grade",
] as const;

export type UserProfileFieldKey = (typeof USER_PROFILE_FIELDS)[number];

export interface UserProfile {
  state?: IndianState;
  age?: number;
  gender?: Gender;
  annual_family_income?: number;
  occupation?: Occupation;
  education_level?: EducationLevel;
  category?: SocialCategory;
  support_type_needed?: SupportType;
  // Optional / nullable. null | undefined = unknown / not provided.
  land_holding?: LandHolding | null;
  paid_income_tax_last_year?: boolean | null;
  monthly_pension?: number | null;
  government_employee_grade?: GovernmentEmployeeGrade | null;
}

export type Operator =
  | "equals"
  | "not_equals"
  | "in"
  | "not_in"
  | "gte"
  | "lte"
  | "exists"
  | "not_exists";

export interface LeafCondition {
  field: UserProfileFieldKey;
  operator: Operator;
  /** Shape depends on `operator`; ignored for `exists` / `not_exists`. */
  value?: unknown;
}

export interface GroupNode {
  op: "AND" | "OR";
  children: ConditionNode[];
}

export interface NotNode {
  op: "NOT";
  child: ConditionNode;
}

export type ConditionNode = GroupNode | NotNode | LeafCondition;

export interface Eligibility {
  /** Gate: an unmatched `hard` tree excludes the user. */
  hard: ConditionNode;
  /** Tiebreaker: `soft` only affects ranking, never eligibility. May be null. */
  soft: ConditionNode | null;
}

export interface Scheme {
  scheme_id: string;
  name: string;
  short_summary: string;
  level: "Central" | "State";
  state: IndianState | null;
  category: string[];
  eligibility: Eligibility;
  benefits: string;
  documents_required: string[];
  application_process: string;
  official_source_url: string;
  apply_url: string | null;
  last_verified_date: string | null;
  verification_status: "verified" | "needs_review" | "stale";
}

export type EvalResult = "pass" | "fail" | "unknown";

export type MatchBucket =
  | "likely_eligible"
  | "possibly_eligible"
  | "not_eligible";

export interface MatchResult {
  bucket: MatchBucket;
  /** Human-readable descriptions of hard leaf conditions the profile satisfies. */
  matched_hard_conditions: string[];
  /** Field labels the profile is missing that block a definite answer. */
  unknown_conditions: string[];
  /** Human-readable descriptions of soft leaf conditions the profile satisfies. */
  matched_soft_conditions: string[];
  /** Short, auto-generated plain-English explanation. */
  reasoning: string;
}
