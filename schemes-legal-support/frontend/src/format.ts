import { humanizeToken } from "./options";
import type { ConditionNode, LeafCondition, UserProfileField } from "./types";

const FIELD_LABELS: Record<UserProfileField, string> = {
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

/** "state", "education level" -> "state and education level" / "a, b and c". */
export function joinList(items: string[]): string {
  if (items.length === 0) return "";
  if (items.length === 1) return items[0];
  return `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return value.map(formatValue).join(", ");
  if (typeof value === "number") return value.toLocaleString("en-IN");
  return humanizeToken(String(value));
}

export function isLeaf(node: ConditionNode): node is LeafCondition {
  return "field" in node;
}

/** One-line, plain-English rendering of a leaf condition. */
export function describeLeaf(node: LeafCondition): string {
  const label = FIELD_LABELS[node.field] ?? node.field;
  const value = formatValue(node.value);

  switch (node.operator) {
    case "equals":
      return `${label} is ${value}`;
    case "not_equals":
      return `${label} is not ${value}`;
    case "in":
      return `${label} is one of: ${value}`;
    case "not_in":
      return `${label} is not one of: ${value}`;
    case "gte":
      return `${label} is at least ${value}`;
    case "lte":
      return `${label} is at most ${value}`;
    case "exists":
      return `${label} is provided`;
    case "not_exists":
      return `${label} is not provided`;
    default:
      return `${label} ${node.operator} ${value}`;
  }
}
