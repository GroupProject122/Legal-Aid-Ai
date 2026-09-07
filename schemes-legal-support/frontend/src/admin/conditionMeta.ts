/**
 * Field/operator metadata for the eligibility condition builder. Mirrors the
 * backend's write-time validator (backend/src/validation/fieldMeta.ts) so the
 * builder only offers combinations the server will accept.
 */
import {
  CATEGORIES,
  EDUCATION_LEVELS,
  GENDERS,
  GOV_EMPLOYEE_GRADES,
  INDIAN_STATES,
  LAND_HOLDINGS,
  OCCUPATIONS,
  SUPPORT_TYPES,
  type Option,
} from "../options";
import type { LeafCondition, Operator, UserProfileField } from "../types";

export type FieldKind = "numeric" | "boolean" | "enum";

export const PROFILE_FIELDS: UserProfileField[] = [
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
];

export const FIELD_LABELS: Record<UserProfileField, string> = {
  state: "State",
  age: "Age",
  gender: "Gender",
  annual_family_income: "Annual family income",
  occupation: "Occupation",
  education_level: "Education level",
  category: "Category",
  support_type_needed: "Support needed",
  land_holding: "Land holding",
  paid_income_tax_last_year: "Paid income tax last year",
  monthly_pension: "Monthly pension",
  government_employee_grade: "Government employee grade",
};

const NUMERIC_FIELDS: UserProfileField[] = [
  "age",
  "annual_family_income",
  "monthly_pension",
];
const BOOLEAN_FIELDS: UserProfileField[] = ["paid_income_tax_last_year"];

export function fieldKind(field: UserProfileField): FieldKind {
  if (NUMERIC_FIELDS.includes(field)) return "numeric";
  if (BOOLEAN_FIELDS.includes(field)) return "boolean";
  return "enum";
}

export const OPERATORS_BY_KIND: Record<FieldKind, Operator[]> = {
  numeric: ["gte", "lte", "exists", "not_exists"],
  boolean: ["equals", "not_equals", "exists", "not_exists"],
  enum: ["equals", "not_equals", "in", "not_in", "exists", "not_exists"],
};

export const OPERATOR_LABELS: Record<Operator, string> = {
  equals: "equals",
  not_equals: "does not equal",
  in: "is one of",
  not_in: "is not one of",
  gte: "is at least (≥)",
  lte: "is at most (≤)",
  exists: "is provided",
  not_exists: "is not provided",
};

export const ENUM_OPTIONS: Partial<Record<UserProfileField, Option[]>> = {
  state: INDIAN_STATES,
  gender: GENDERS,
  occupation: OCCUPATIONS,
  education_level: EDUCATION_LEVELS,
  category: CATEGORIES,
  support_type_needed: SUPPORT_TYPES,
  land_holding: LAND_HOLDINGS,
  government_employee_grade: GOV_EMPLOYEE_GRADES,
};

export function operatorNeedsValue(op: Operator): boolean {
  return op !== "exists" && op !== "not_exists";
}

export function operatorNeedsArray(op: Operator): boolean {
  return op === "in" || op === "not_in";
}

export function operatorNeedsNumber(op: Operator): boolean {
  return op === "gte" || op === "lte";
}

/** A fresh leaf for "add condition" actions. */
export function defaultLeaf(): LeafCondition {
  return { field: "state", operator: "equals", value: "" };
}

/** Reset a leaf's `value` to something sensible for its field type + operator. */
export function coerceLeafValue(leaf: LeafCondition): LeafCondition {
  const { operator } = leaf;
  if (!operatorNeedsValue(operator)) return { ...leaf, value: undefined };
  if (operatorNeedsArray(operator)) {
    return { ...leaf, value: Array.isArray(leaf.value) ? leaf.value : [] };
  }
  if (operatorNeedsNumber(operator)) {
    return { ...leaf, value: typeof leaf.value === "number" ? leaf.value : 0 };
  }
  if (fieldKind(leaf.field) === "boolean") {
    return {
      ...leaf,
      value: typeof leaf.value === "boolean" ? leaf.value : false,
    };
  }
  return {
    ...leaf,
    value:
      typeof leaf.value === "string" && !Array.isArray(leaf.value)
        ? leaf.value
        : "",
  };
}
