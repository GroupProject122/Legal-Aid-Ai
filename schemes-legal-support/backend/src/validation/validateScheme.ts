/**
 * Write-time validator for hand-entered scheme records.
 *
 * `validateScheme` never throws. It returns either the normalised `SchemeInput`
 * or the FULL list of problems found — the eligibility tree is walked to the
 * bottom and every cross-field rule is checked before returning, so a human
 * reviewer sees everything wrong at once.
 */
import { z } from "zod";

import type { Eligibility } from "../matching/types";
import {
  ALL_OPERATORS,
  ENUM_VALUES,
  INDIAN_STATES,
  KNOWN_FIELDS,
  fieldKind,
  isKnownField,
  operatorsForKind,
  type EnumField,
  type FieldKind,
  type KnownField,
} from "./fieldMeta";

export interface SchemeInput {
  scheme_id: string;
  name: string;
  short_summary: string;
  level: "Central" | "State";
  state: string | null;
  category: string[];
  eligibility: Eligibility;
  benefits: string;
  documents_required: string[];
  application_process: string;
  official_source_url: string;
  apply_url: string | null;
  last_verified_date: string | null;
  verification_status?: "verified" | "needs_review" | "stale";
}

export type ValidateSchemeResult =
  | { valid: true; scheme: SchemeInput }
  | { valid: false; errors: string[] };

const ISO_DATE = /^\d{4}-\d{2}-\d{2}$/;

const baseSchema = z
  .object({
    scheme_id: z
      .string()
      .trim()
      .min(1, "is required")
      .regex(
        /^[a-z0-9][a-z0-9-]*$/,
        "must be a lowercase slug (letters, digits and hyphens)",
      ),
    name: z.string().trim().min(1, "is required"),
    short_summary: z.string().trim().min(1, "is required"),
    level: z.enum(["Central", "State"]),
    state: z.string().trim().min(1).nullable(),
    category: z
      .array(z.string().trim().min(1))
      .min(1, "needs at least one tag"),
    benefits: z.string().trim().min(1, "is required"),
    documents_required: z.array(z.string().trim().min(1)),
    application_process: z.string().trim().min(1, "is required"),
    official_source_url: z.string().url("must be a valid URL"),
    apply_url: z.string().url("must be a valid URL").nullable(),
    last_verified_date: z
      .string()
      .regex(ISO_DATE, "must be an ISO date (YYYY-MM-DD)")
      .nullable(),
    verification_status: z
      .enum(["verified", "needs_review", "stale"])
      .optional(),
    eligibility: z.unknown(),
  })
  .strict();

function formatZodIssue(issue: z.ZodIssue): string {
  const path = issue.path.length ? issue.path.join(".") : "(root)";
  return `${path}: ${issue.message}`;
}

function dedupe(items: string[]): string[] {
  return [...new Set(items)];
}

export function validateScheme(input: unknown): ValidateSchemeResult {
  const errors: string[] = [];

  const parsed = baseSchema.safeParse(input);
  if (!parsed.success) {
    for (const issue of parsed.error.issues) errors.push(formatZodIssue(issue));
  }

  if (typeof input !== "object" || input === null || Array.isArray(input)) {
    errors.push("(root): expected a scheme object");
    return { valid: false, errors: dedupe(errors) };
  }
  const obj = input as Record<string, unknown>;

  validateEligibility(obj.eligibility, errors);
  validateLevelAndState(obj, errors);
  validateVerification(obj, errors);

  if (errors.length > 0) {
    return { valid: false, errors: dedupe(errors) };
  }
  if (!parsed.success) {
    // Unreachable in practice (base issues are collected above), but keeps the
    // types honest without a non-null assertion.
    return { valid: false, errors: ["(root): invalid scheme payload"] };
  }

  const data = parsed.data;
  const scheme: SchemeInput = {
    scheme_id: data.scheme_id,
    name: data.name,
    short_summary: data.short_summary,
    level: data.level,
    state: data.state ?? null,
    category: data.category,
    eligibility: obj.eligibility as Eligibility,
    benefits: data.benefits,
    documents_required: data.documents_required,
    application_process: data.application_process,
    official_source_url: data.official_source_url,
    apply_url: data.apply_url ?? null,
    last_verified_date: data.last_verified_date ?? null,
    verification_status: data.verification_status,
  };
  return { valid: true, scheme };
}

// --- eligibility tree ----------------------------------------------------

function validateEligibility(elig: unknown, errors: string[]): void {
  if (elig === null || typeof elig !== "object" || Array.isArray(elig)) {
    errors.push("eligibility: must be an object of the form { hard, soft }");
    return;
  }
  const e = elig as Record<string, unknown>;

  if (!("hard" in e)) {
    errors.push("eligibility.hard: is required");
  } else {
    validateNode(e.hard, "eligibility.hard", errors);
  }

  if (!("soft" in e)) {
    errors.push(
      "eligibility.soft: is required (use null when there are no soft conditions)",
    );
  } else if (e.soft !== null) {
    validateNode(e.soft, "eligibility.soft", errors);
  }
}

function validateNode(node: unknown, path: string, errors: string[]): void {
  if (node === null || typeof node !== "object" || Array.isArray(node)) {
    errors.push(
      `${path}: must be an AND/OR group, a NOT wrapper, or a { field, operator, value } leaf`,
    );
    return;
  }
  const n = node as Record<string, unknown>;
  const hasOp = "op" in n;
  const hasField = "field" in n;

  if (hasOp && (n.op === "AND" || n.op === "OR")) {
    if (hasField) {
      errors.push(`${path}: an ${n.op} group must not also carry a "field"`);
    }
    const children = n.children;
    if (!Array.isArray(children)) {
      errors.push(`${path}.children: must be an array`);
    } else if (children.length === 0) {
      errors.push(
        `${path}.children: an ${n.op} group needs at least one condition`,
      );
    } else {
      children.forEach((child, index) =>
        validateNode(child, `${path}.children[${index}]`, errors),
      );
    }
    return;
  }

  if (hasOp && n.op === "NOT") {
    if (!("child" in n)) {
      errors.push(
        `${path}.child: a NOT wrapper needs exactly one child condition`,
      );
    } else {
      validateNode(n.child, `${path}.child`, errors);
    }
    return;
  }

  if (hasOp) {
    errors.push(
      `${path}.op: "${String(n.op)}" is not a valid group operator (expected "AND", "OR" or "NOT")`,
    );
    return;
  }

  if (hasField) {
    validateLeaf(n, path, errors);
    return;
  }

  errors.push(
    `${path}: unrecognised condition — needs "op" (AND/OR/NOT) or "field" (a leaf)`,
  );
}

function validateLeaf(
  n: Record<string, unknown>,
  path: string,
  errors: string[],
): void {
  const field = n.field;
  const operator = n.operator;

  const fieldOk = isKnownField(field);
  if (!fieldOk) {
    errors.push(
      `${path}.field: "${String(field)}" is not a known profile field (allowed: ${KNOWN_FIELDS.join(", ")})`,
    );
  }

  const operatorOk =
    typeof operator === "string" &&
    (ALL_OPERATORS as readonly string[]).includes(operator);
  if (!operatorOk) {
    errors.push(
      `${path}.operator: "${String(operator)}" is not a valid operator (allowed: ${ALL_OPERATORS.join(", ")})`,
    );
  }

  if (!fieldOk || !operatorOk) return;

  const kind = fieldKind(field);
  const allowedOps = operatorsForKind(kind);
  if (!(allowedOps as readonly string[]).includes(operator)) {
    errors.push(
      `${path}.operator: "${operator}" cannot be used on ${kind} field "${field}" ` +
        `(operators allowed on ${kind} fields: ${allowedOps.join(", ")})`,
    );
  }

  validateLeafValue(n, path, field, operator, kind, errors);
}

function validateLeafValue(
  n: Record<string, unknown>,
  path: string,
  field: KnownField,
  operator: string,
  kind: FieldKind,
  errors: string[],
): void {
  if (operator === "exists" || operator === "not_exists") return;

  const value = n.value;
  if (!("value" in n) || value === undefined) {
    errors.push(`${path}.value: is required for operator "${operator}"`);
    return;
  }

  if (operator === "gte" || operator === "lte") {
    if (typeof value !== "number" || !Number.isFinite(value)) {
      errors.push(`${path}.value: operator "${operator}" needs a finite number`);
    }
    return;
  }

  if (operator === "in" || operator === "not_in") {
    if (!Array.isArray(value)) {
      errors.push(`${path}.value: operator "${operator}" needs an array`);
      return;
    }
    if (value.length === 0) {
      errors.push(
        `${path}.value: operator "${operator}" needs a non-empty array`,
      );
      return;
    }
    if (kind === "enum") {
      const allowed = ENUM_VALUES[field as EnumField];
      const bad = value.filter(
        (item) => typeof item !== "string" || !allowed.includes(item),
      );
      if (bad.length > 0) {
        errors.push(
          `${path}.value: ${JSON.stringify(bad)} not valid for "${field}" (allowed: ${allowed.join(", ")})`,
        );
      }
    }
    return;
  }

  // equals / not_equals
  if (value === null || Array.isArray(value) || typeof value === "object") {
    errors.push(
      `${path}.value: operator "${operator}" needs a single scalar value`,
    );
    return;
  }
  if (kind === "boolean" && typeof value !== "boolean") {
    errors.push(
      `${path}.value: operator "${operator}" on boolean field "${field}" needs true or false`,
    );
    return;
  }
  if (kind === "enum") {
    const allowed = ENUM_VALUES[field as EnumField];
    if (typeof value !== "string" || !allowed.includes(value)) {
      errors.push(
        `${path}.value: "${String(value)}" is not valid for "${field}" (allowed: ${allowed.join(", ")})`,
      );
    }
  }
}

// --- cross-field rules -------------------------------------------------

function validateLevelAndState(
  obj: Record<string, unknown>,
  errors: string[],
): void {
  const level = obj.level;
  const state = obj.state ?? null;

  if (level === "State" && state === null) {
    errors.push('state: must be provided when level is "State"');
  }
  if (level === "Central" && state !== null) {
    errors.push('state: must be null when level is "Central"');
  }
  if (
    typeof state === "string" &&
    !(INDIAN_STATES as readonly string[]).includes(state)
  ) {
    errors.push(
      `state: "${state}" is not a recognised Indian state or union territory`,
    );
  }
}

function parseCalendarDate(iso: string): Date | null {
  const [year, month, day] = iso.split("-").map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  if (
    date.getUTCFullYear() !== year ||
    date.getUTCMonth() !== month - 1 ||
    date.getUTCDate() !== day
  ) {
    return null;
  }
  return date;
}

function endOfTodayUtc(): number {
  const now = new Date();
  return Date.UTC(
    now.getUTCFullYear(),
    now.getUTCMonth(),
    now.getUTCDate(),
    23,
    59,
    59,
    999,
  );
}

function validateVerification(
  obj: Record<string, unknown>,
  errors: string[],
): void {
  const status = obj.verification_status;
  const lastVerified = obj.last_verified_date ?? null;

  if (typeof lastVerified === "string" && ISO_DATE.test(lastVerified)) {
    const parsed = parseCalendarDate(lastVerified);
    if (!parsed) {
      errors.push(
        `last_verified_date: "${lastVerified}" is not a real calendar date`,
      );
    } else if (parsed.getTime() > endOfTodayUtc()) {
      errors.push(`last_verified_date: "${lastVerified}" is in the future`);
    }
  }

  if (status === "verified" && lastVerified === null) {
    errors.push(
      'last_verified_date: is required when verification_status is "verified"',
    );
  }
}
