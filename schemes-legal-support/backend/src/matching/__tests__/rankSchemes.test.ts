import { describe, expect, it } from "vitest";

import { rankSchemes } from "../rankSchemes";
import type { ConditionNode, UserProfile } from "../types";
import { makeScheme } from "./fixtures";

// ST farmer, low income, in Maharashtra. Age / gender / education left blank.
const profile: UserProfile = {
  state: "Maharashtra",
  annual_family_income: 120_000,
  category: "st",
  occupation: "farmer",
};

const softTwo: ConditionNode = {
  op: "AND",
  children: [
    { field: "category", operator: "in", value: ["sc", "st"] },
    { field: "occupation", operator: "equals", value: "farmer" },
  ],
};
const softOne: ConditionNode = {
  op: "OR",
  children: [
    { field: "category", operator: "in", value: ["sc", "st"] },
    { field: "gender", operator: "equals", value: "male" }, // unknown -> not counted
  ],
};
const softZero: ConditionNode = { field: "category", operator: "equals", value: "general" };

const likelySoft2 = makeScheme(
  "ls2",
  { field: "annual_family_income", operator: "lte", value: 300_000 },
  softTwo,
);
const likelySoft1 = makeScheme(
  "ls1",
  { field: "annual_family_income", operator: "lte", value: 500_000 },
  softOne,
);
const likelySoft0 = makeScheme(
  "ls0",
  { field: "state", operator: "equals", value: "Maharashtra" },
  softZero,
);
const possibly = makeScheme("poss", {
  op: "AND",
  children: [
    { field: "annual_family_income", operator: "lte", value: 300_000 },
    { field: "age", operator: "gte", value: 18 }, // age missing -> unknown
  ],
});
const notEligible = makeScheme("no", {
  field: "occupation",
  operator: "equals",
  value: "student",
});

describe("rankSchemes", () => {
  it("excludes not_eligible, orders by bucket then soft-match count", () => {
    const ranked = rankSchemes(
      [notEligible, likelySoft0, possibly, likelySoft2, likelySoft1],
      profile,
    );
    expect(ranked.map((s) => s.scheme_id)).toEqual(["ls2", "ls1", "ls0", "poss"]);
  });

  it("drops every not_eligible scheme", () => {
    const ranked = rankSchemes([notEligible], profile);
    expect(ranked).toEqual([]);
  });

  it("carries both the Scheme fields and the MatchResult fields through", () => {
    const [top] = rankSchemes([likelySoft2], profile);
    expect(top.name).toBe("Test scheme ls2");
    expect(top.bucket).toBe("likely_eligible");
    expect(top.matched_soft_conditions).toHaveLength(2);
  });

  it("keeps input order for entries that tie on bucket and soft count", () => {
    const a = makeScheme("a", { field: "state", operator: "equals", value: "Maharashtra" });
    const b = makeScheme("b", { field: "occupation", operator: "equals", value: "farmer" });
    const ranked = rankSchemes([a, b], profile);
    expect(ranked.map((s) => s.scheme_id)).toEqual(["a", "b"]);
  });
});
