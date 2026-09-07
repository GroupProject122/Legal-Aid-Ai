/**
 * Frontend copies of the backend contract. Hand-maintained to match
 * schemes-legal-support/backend (docs/data-model.md + src/matching/types.ts);
 * no code is shared across the two packages yet.
 */

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
 * The first 8 fields are required in storage; the last 4 are optional/nullable
 * (null = unknown / not provided). The intake form submits any subset.
 */
export interface UserProfile {
  state: string; // IndianState enum value, e.g. "Tamil_Nadu"
  age: number;
  gender: Gender;
  annual_family_income: number; // INR, whole rupees
  occupation: Occupation;
  education_level: EducationLevel;
  category: SocialCategory;
  support_type_needed: SupportType;
  land_holding: LandHolding | null;
  paid_income_tax_last_year: boolean | null;
  monthly_pension: number | null; // INR, whole rupees; 0 is a real value
  government_employee_grade: GovernmentEmployeeGrade | null;
}

export type UserProfileField = keyof UserProfile;

// --- eligibility tree (for the "View details" view) ------------------------

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
  field: UserProfileField;
  operator: Operator;
  value?: unknown;
}

export type ConditionNode =
  | { op: "AND" | "OR"; children: ConditionNode[] }
  | { op: "NOT"; child: ConditionNode }
  | LeafCondition;

export interface Eligibility {
  hard: ConditionNode;
  soft: ConditionNode | null;
}

// --- scheme + match result ------------------------------------------------

export type SchemeLevel = "Central" | "State";
export type VerificationStatus = "verified" | "needs_review" | "stale";

export interface Scheme {
  scheme_id: string;
  name: string;
  short_summary: string;
  level: SchemeLevel;
  state: string | null;
  category: string[];
  eligibility: Eligibility;
  benefits: string;
  documents_required: string[];
  application_process: string;
  official_source_url: string;
  apply_url: string | null;
  last_verified_date: string | null;
  verification_status: VerificationStatus;
}

export type MatchBucket =
  | "likely_eligible"
  | "possibly_eligible"
  | "not_eligible";

export interface MatchResult {
  bucket: MatchBucket;
  matched_hard_conditions: string[];
  unknown_conditions: string[];
  matched_soft_conditions: string[];
  reasoning: string;
}

export type MatchedScheme = Scheme & MatchResult;

export interface MatchResponse {
  results: MatchedScheme[];
}

/**
 * Write shape for POST/PUT /schemes. Same as `Scheme` except
 * `verification_status` is optional (the backend defaults it to
 * `needs_review`). The backend runs `validateScheme` on this.
 */
export interface SchemeInput {
  scheme_id: string;
  name: string;
  short_summary: string;
  level: SchemeLevel;
  state: string | null;
  category: string[];
  eligibility: Eligibility;
  benefits: string;
  documents_required: string[];
  application_process: string;
  official_source_url: string;
  apply_url: string | null;
  last_verified_date: string | null;
  verification_status?: VerificationStatus;
}
