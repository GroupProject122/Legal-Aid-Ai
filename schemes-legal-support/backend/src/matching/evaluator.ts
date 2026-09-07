import type {
  ConditionNode,
  EvalResult,
  GroupNode,
  LeafCondition,
  NotNode,
  UserProfile,
} from "./types";

/**
 * Three-valued (Kleene) evaluation of a condition tree against a — possibly
 * partial — user profile.
 *
 *   "pass"    the profile satisfies the condition
 *   "fail"    the profile contradicts the condition
 *   "unknown" a required profile field is missing, so it can't be decided
 *
 * See ../../../docs/data-model.md for the grammar this walks.
 */
export function evaluateCondition(
  node: ConditionNode,
  profile: UserProfile,
): EvalResult {
  if (isGroupNode(node)) {
    return node.op === "AND"
      ? evaluateAnd(node.children, profile)
      : evaluateOr(node.children, profile);
  }
  if (isNotNode(node)) {
    return invert(evaluateCondition(node.child, profile));
  }
  return evaluateLeaf(node, profile);
}

// --- group evaluation -------------------------------------------------------

/**
 * AND: fail if any child fails; otherwise unknown if any child is unknown;
 * otherwise pass. An empty `children` array is defined to pass (a scheme with
 * no hard conditions is open to everyone).
 */
function evaluateAnd(
  children: ConditionNode[],
  profile: UserProfile,
): EvalResult {
  let sawUnknown = false;
  for (const child of children) {
    const result = evaluateCondition(child, profile);
    if (result === "fail") return "fail";
    if (result === "unknown") sawUnknown = true;
  }
  return sawUnknown ? "unknown" : "pass";
}

/**
 * OR: pass if any child passes; otherwise unknown if any child is unknown;
 * otherwise fail (every child failed). An empty `children` array fails.
 */
function evaluateOr(
  children: ConditionNode[],
  profile: UserProfile,
): EvalResult {
  let sawUnknown = false;
  for (const child of children) {
    const result = evaluateCondition(child, profile);
    if (result === "pass") return "pass";
    if (result === "unknown") sawUnknown = true;
  }
  return sawUnknown ? "unknown" : "fail";
}

/** NOT: swaps pass/fail; unknown stays unknown. */
export function invert(result: EvalResult): EvalResult {
  if (result === "pass") return "fail";
  if (result === "fail") return "pass";
  return "unknown";
}

// --- leaf evaluation ------------------------------------------------------

/**
 * Apply a single operator to `profile[field]` vs `leaf.value`.
 *
 * If the field is missing/null and the operator is not `exists` / `not_exists`,
 * the result is "unknown". A value whose shape doesn't fit the operator
 * (e.g. `in` with a non-array `value`, `gte` on a non-number) is also
 * "unknown" — bad data must not silently pass or exclude a user.
 */
function evaluateLeaf(leaf: LeafCondition, profile: UserProfile): EvalResult {
  const actual = profile[leaf.field];
  const present = actual !== undefined && actual !== null;

  // Presence operators are the only ones defined on a missing field.
  if (leaf.operator === "exists") return present ? "pass" : "fail";
  if (leaf.operator === "not_exists") return present ? "fail" : "pass";

  if (!present) return "unknown";

  switch (leaf.operator) {
    case "equals":
      return bool(actual === leaf.value);
    case "not_equals":
      return bool(actual !== leaf.value);
    case "in":
      if (!Array.isArray(leaf.value)) return "unknown";
      return bool(leaf.value.includes(actual));
    case "not_in":
      if (!Array.isArray(leaf.value)) return "unknown";
      return bool(!leaf.value.includes(actual));
    case "gte":
      if (typeof actual !== "number" || typeof leaf.value !== "number") {
        return "unknown";
      }
      return bool(actual >= leaf.value);
    case "lte":
      if (typeof actual !== "number" || typeof leaf.value !== "number") {
        return "unknown";
      }
      return bool(actual <= leaf.value);
    default:
      // Unrecognised operator — undecidable rather than pass/fail.
      return "unknown";
  }
}

// --- node discrimination --------------------------------------------------

function isGroupNode(node: ConditionNode): node is GroupNode {
  const op = (node as GroupNode).op;
  return op === "AND" || op === "OR";
}

function isNotNode(node: ConditionNode): node is NotNode {
  return (node as NotNode).op === "NOT";
}

function bool(ok: boolean): EvalResult {
  return ok ? "pass" : "fail";
}
