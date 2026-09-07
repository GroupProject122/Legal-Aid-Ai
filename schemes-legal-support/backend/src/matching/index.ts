/**
 * Eligibility matching engine (pure logic — no DB, no HTTP).
 *
 *   evaluateCondition — three-valued evaluation of one condition tree
 *   matchScheme       — bucket + explanation for one scheme vs one profile
 *   rankSchemes       — filter + order a list of schemes for one profile
 */
export * from "./types";
export { evaluateCondition, invert } from "./evaluator";
export { matchScheme } from "./matchScheme";
export { rankSchemes } from "./rankSchemes";
