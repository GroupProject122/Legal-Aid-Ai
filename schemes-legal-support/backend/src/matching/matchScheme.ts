import { evaluateCondition, invert } from "./evaluator";
import type {
  ConditionNode,
  EvalResult,
  LeafCondition,
  MatchBucket,
  MatchResult,
  NotNode,
  Scheme,
  UserProfile,
  UserProfileFieldKey,
} from "./types";

/**
 * Match one scheme against a profile.
 *
 * The `hard` tree decides the bucket:
 *   "fail"    -> not_eligible
 *   "pass"    -> likely_eligible
 *   "unknown" -> possibly_eligible  (and `unknown_conditions` names the gaps)
 *
 * The `soft` tree never changes the bucket — the leaves it satisfies are
 * reported in `matched_soft_conditions` for ranking / display only.
 */
export function matchScheme(scheme: Scheme, profile: UserProfile): MatchResult {
  const { hard, soft } = scheme.eligibility;

  const hardResult = evaluateCondition(hard, profile);
  const bucket: MatchBucket =
    hardResult === "fail"
      ? "not_eligible"
      : hardResult === "pass"
        ? "likely_eligible"
        : "possibly_eligible";

  const hardLeaves = collectLeafOutcomes(hard, profile);
  const softLeaves = soft ? collectLeafOutcomes(soft, profile) : [];

  const matched_hard_conditions = dedupe(
    hardLeaves.filter((o) => o.result === "pass").map(describeOutcome),
  );
  const unknown_conditions = dedupe(
    hardLeaves
      // Skip "unknown" leaves whose immediate parent AND/OR already resolved
      // via a sibling — the group's result answers the question, so there is
      // nothing to ask the user for. See `collectLeafOutcomes`.
      .filter((o) => o.result === "unknown" && !o.answeredByParentGroup)
      .map((o) => labelFor(o.leaf.field)),
  );
  const failedDescriptions = dedupe(
    hardLeaves.filter((o) => o.result === "fail").map(describeOutcome),
  );
  const matched_soft_conditions = dedupe(
    softLeaves.filter((o) => o.result === "pass").map(describeOutcome),
  );

  const matchedFieldLabels = dedupe(
    hardLeaves.filter((o) => o.result === "pass").map((o) => labelFor(o.leaf.field)),
  );

  const reasoning = buildReasoning({
    bucket,
    matchedFieldLabels,
    unknownFieldLabels: unknown_conditions,
    failedDescriptions,
  });

  return {
    bucket,
    matched_hard_conditions,
    unknown_conditions,
    matched_soft_conditions,
    reasoning,
  };
}

// --- tree walk ----------------------------------------------------------

interface LeafOutcome {
  leaf: LeafCondition;
  /** Effective result for this leaf, with enclosing NOTs already applied. */
  result: EvalResult;
  /** True when an odd number of NOT wrappers enclose this leaf. */
  negated: boolean;
  /**
   * True when this leaf is "unknown" but the AND/OR group it sits *directly*
   * inside already resolved (to pass or fail) via a sibling. The group's own
   * result answers the question, so this leaf should be left out of
   * `unknown_conditions`. Set per immediate parent group, never globally: an
   * unknown leaf on an unrelated branch that shares a field name is untouched.
   */
  answeredByParentGroup: boolean;
}

/**
 * Evaluate every leaf in a tree individually, in document order. NOT wrappers
 * are folded into each leaf's `result` and `negated` flag rather than kept as
 * structure, so callers get a flat list of "did this specific check hold".
 *
 * For each AND/OR group, if the group as a whole resolved (pass/fail), any of
 * its *direct* leaf children that are themselves "unknown" are flagged
 * `answeredByParentGroup` — a sibling settled the group, so the profile gap in
 * that leaf no longer needs surfacing. Nested groups and NOT-wrapped leaves
 * have their own immediate parent and are not flagged by an outer group.
 */
function collectLeafOutcomes(
  node: ConditionNode,
  profile: UserProfile,
  negated = false,
): LeafOutcome[] {
  if (isLeafNode(node)) {
    const raw = evaluateCondition(node, profile);
    return [
      {
        leaf: node,
        result: negated ? invert(raw) : raw,
        negated,
        answeredByParentGroup: false,
      },
    ];
  }
  if (isNotNode(node)) {
    return collectLeafOutcomes(node.child, profile, !negated);
  }

  // AND / OR group. "Did it resolve?" is invariant under negation — `invert`
  // maps pass<->fail and leaves unknown alone — so evaluate the raw subtree.
  const groupResolved = evaluateCondition(node, profile) !== "unknown";

  return node.children.flatMap((child) => {
    const outcomes = collectLeafOutcomes(child, profile, negated);
    if (groupResolved && isLeafNode(child)) {
      return outcomes.map((outcome) =>
        outcome.result === "unknown"
          ? { ...outcome, answeredByParentGroup: true }
          : outcome,
      );
    }
    return outcomes;
  });
}

// --- descriptions -----------------------------------------------------

/** Friendly noun for each profile field, used to build plain-English text. */
const FIELD_LABELS: Record<UserProfileFieldKey, string> = {
  state: "state",
  age: "age",
  gender: "gender",
  annual_family_income: "income level",
  occupation: "occupation",
  education_level: "education level",
  category: "category",
  support_type_needed: "type of support needed",
  land_holding: "land holding",
  paid_income_tax_last_year: "income-tax status",
  monthly_pension: "monthly pension",
  government_employee_grade: "government employee grade",
};

function labelFor(field: UserProfileFieldKey): string {
  return FIELD_LABELS[field] ?? String(field);
}

function fmt(value: unknown): string {
  return Array.isArray(value) ? value.join(", ") : String(value);
}

/** Turn one leaf outcome into a human-readable clause, honouring negation. */
function describeOutcome(outcome: LeafOutcome): string {
  const { leaf, negated } = outcome;
  const label = labelFor(leaf.field);
  const v = fmt(leaf.value);

  switch (leaf.operator) {
    case "equals":
      return negated ? `${label} is not ${v}` : `${label} is ${v}`;
    case "not_equals":
      return negated ? `${label} is ${v}` : `${label} is not ${v}`;
    case "in":
      return negated
        ? `${label} is not one of ${v}`
        : `${label} is one of ${v}`;
    case "not_in":
      return negated
        ? `${label} is one of ${v}`
        : `${label} is not one of ${v}`;
    case "gte":
      return negated ? `${label} is below ${v}` : `${label} is at least ${v}`;
    case "lte":
      return negated ? `${label} is above ${v}` : `${label} is at most ${v}`;
    case "exists":
      return negated ? `${label} is not provided` : `${label} is provided`;
    case "not_exists":
      return negated ? `${label} is provided` : `${label} is not provided`;
    default:
      return `${label} ${leaf.operator} ${v}`;
  }
}

// --- reasoning one-liner --------------------------------------------------

function buildReasoning(args: {
  bucket: MatchBucket;
  matchedFieldLabels: string[];
  unknownFieldLabels: string[];
  failedDescriptions: string[];
}): string {
  const { bucket, matchedFieldLabels, unknownFieldLabels, failedDescriptions } =
    args;

  if (bucket === "likely_eligible") {
    return matchedFieldLabels.length
      ? `Matches your ${oxford(matchedFieldLabels)}.`
      : "This scheme has no eligibility restrictions.";
  }

  if (bucket === "possibly_eligible") {
    const need = unknownFieldLabels.length
      ? `We still need your ${oxford(unknownFieldLabels)} to confirm.`
      : "Some eligibility details could not be checked.";
    return matchedFieldLabels.length
      ? `Matches your ${oxford(matchedFieldLabels)}. ${need}`
      : need;
  }

  // not_eligible
  return failedDescriptions.length
    ? `Doesn't meet this scheme's requirement that ${oxford(
        failedDescriptions.slice(0, 2),
      )}.`
    : "Your profile doesn't meet this scheme's requirements.";
}

/** "a" | "a and b" | "a, b, and c" */
function oxford(items: string[]): string {
  if (items.length === 0) return "";
  if (items.length === 1) return items[0];
  if (items.length === 2) return `${items[0]} and ${items[1]}`;
  return `${items.slice(0, -1).join(", ")}, and ${items[items.length - 1]}`;
}

// --- helpers ---------------------------------------------------------

function isLeafNode(node: ConditionNode): node is LeafCondition {
  return typeof (node as LeafCondition).field === "string";
}

function isNotNode(node: ConditionNode): node is NotNode {
  return (node as NotNode).op === "NOT";
}

function dedupe(items: string[]): string[] {
  return [...new Set(items)];
}
