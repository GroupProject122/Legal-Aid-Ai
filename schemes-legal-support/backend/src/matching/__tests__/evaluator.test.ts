import { describe, expect, it } from "vitest";

import { evaluateCondition } from "../evaluator";
import type { ConditionNode, UserProfile } from "../types";

const profile: UserProfile = {
  state: "Maharashtra",
  age: 30,
  annual_family_income: 150_000,
  occupation: "farmer",
  category: "sc",
};

const pass: ConditionNode = { field: "state", operator: "equals", value: "Maharashtra" };
const fail: ConditionNode = { field: "state", operator: "equals", value: "Kerala" };
const unknown: ConditionNode = { field: "gender", operator: "equals", value: "male" };

describe("leaf operators", () => {
  it("equals / not_equals", () => {
    expect(evaluateCondition({ field: "occupation", operator: "equals", value: "farmer" }, profile)).toBe("pass");
    expect(evaluateCondition({ field: "occupation", operator: "equals", value: "student" }, profile)).toBe("fail");
    expect(evaluateCondition({ field: "occupation", operator: "not_equals", value: "student" }, profile)).toBe("pass");
    expect(evaluateCondition({ field: "occupation", operator: "not_equals", value: "farmer" }, profile)).toBe("fail");
  });

  it("in / not_in", () => {
    expect(evaluateCondition({ field: "category", operator: "in", value: ["sc", "st"] }, profile)).toBe("pass");
    expect(evaluateCondition({ field: "category", operator: "in", value: ["obc"] }, profile)).toBe("fail");
    expect(evaluateCondition({ field: "category", operator: "not_in", value: ["obc"] }, profile)).toBe("pass");
    expect(evaluateCondition({ field: "category", operator: "not_in", value: ["sc"] }, profile)).toBe("fail");
  });

  it("gte / lte on numeric fields", () => {
    expect(evaluateCondition({ field: "age", operator: "gte", value: 18 }, profile)).toBe("pass");
    expect(evaluateCondition({ field: "age", operator: "gte", value: 60 }, profile)).toBe("fail");
    expect(evaluateCondition({ field: "annual_family_income", operator: "lte", value: 200_000 }, profile)).toBe("pass");
    expect(evaluateCondition({ field: "annual_family_income", operator: "lte", value: 100_000 }, profile)).toBe("fail");
  });

  it("returns 'unknown' when a compared field is missing", () => {
    expect(evaluateCondition({ field: "gender", operator: "equals", value: "male" }, profile)).toBe("unknown");
    expect(evaluateCondition({ field: "education_level", operator: "in", value: ["graduate"] }, profile)).toBe("unknown");
    expect(evaluateCondition({ field: "age", operator: "gte", value: 18 }, {})).toBe("unknown");
  });

  it("exists / not_exists never return 'unknown'", () => {
    expect(evaluateCondition({ field: "occupation", operator: "exists", value: null }, profile)).toBe("pass");
    expect(evaluateCondition({ field: "gender", operator: "exists", value: null }, profile)).toBe("fail");
    expect(evaluateCondition({ field: "gender", operator: "not_exists", value: null }, profile)).toBe("pass");
    expect(evaluateCondition({ field: "occupation", operator: "not_exists", value: null }, profile)).toBe("fail");
  });

  it("returns 'unknown' for malformed operator values", () => {
    expect(evaluateCondition({ field: "category", operator: "in", value: "sc" }, profile)).toBe("unknown");
    expect(evaluateCondition({ field: "occupation", operator: "gte", value: 5 }, profile)).toBe("unknown");
  });
});

describe("AND groups", () => {
  it("passes only when every child passes", () => {
    expect(evaluateCondition({ op: "AND", children: [pass, pass] }, profile)).toBe("pass");
  });

  it("fails if any child fails, even alongside unknowns", () => {
    expect(evaluateCondition({ op: "AND", children: [pass, unknown, fail] }, profile)).toBe("fail");
  });

  it("is unknown if a child is unknown and none fail", () => {
    expect(evaluateCondition({ op: "AND", children: [pass, unknown] }, profile)).toBe("unknown");
  });

  it("treats an empty AND as pass", () => {
    expect(evaluateCondition({ op: "AND", children: [] }, profile)).toBe("pass");
  });
});

describe("OR groups", () => {
  it("passes if any child passes, even alongside unknowns", () => {
    expect(evaluateCondition({ op: "OR", children: [fail, unknown, pass] }, profile)).toBe("pass");
  });

  it("fails only when every child fails", () => {
    expect(evaluateCondition({ op: "OR", children: [fail, fail] }, profile)).toBe("fail");
  });

  it("is unknown if no child passes but one is unknown", () => {
    expect(evaluateCondition({ op: "OR", children: [fail, unknown] }, profile)).toBe("unknown");
  });
});

describe("NOT", () => {
  it("inverts pass and fail", () => {
    expect(evaluateCondition({ op: "NOT", child: pass }, profile)).toBe("fail");
    expect(evaluateCondition({ op: "NOT", child: fail }, profile)).toBe("pass");
  });

  it("leaves unknown unchanged", () => {
    expect(evaluateCondition({ op: "NOT", child: unknown }, profile)).toBe("unknown");
  });

  it("double negation is identity", () => {
    expect(evaluateCondition({ op: "NOT", child: { op: "NOT", child: pass } }, profile)).toBe("pass");
  });
});

describe("nested trees", () => {
  it("(SC OR ST) AND income <= 200000", () => {
    const tree: ConditionNode = {
      op: "AND",
      children: [
        {
          op: "OR",
          children: [
            { field: "category", operator: "equals", value: "sc" },
            { field: "category", operator: "equals", value: "st" },
          ],
        },
        { field: "annual_family_income", operator: "lte", value: 200_000 },
      ],
    };
    expect(evaluateCondition(tree, profile)).toBe("pass");
    expect(evaluateCondition(tree, { ...profile, category: "obc" })).toBe("fail");
    expect(evaluateCondition(tree, { ...profile, category: undefined })).toBe("unknown");
  });
});

describe("optional / nullable fields (land_holding, paid_income_tax_last_year, monthly_pension, government_employee_grade)", () => {
  it("land_holding — enum equals, with unknown for missing AND explicit null", () => {
    const c: ConditionNode = { field: "land_holding", operator: "equals", value: "individual" };
    expect(evaluateCondition(c, { land_holding: "individual" })).toBe("pass");
    expect(evaluateCondition(c, { land_holding: "institutional" })).toBe("fail");
    expect(evaluateCondition(c, {})).toBe("unknown");
    expect(evaluateCondition(c, { land_holding: null })).toBe("unknown");
  });

  it("government_employee_grade — in / not_in", () => {
    const inSet: ConditionNode = {
      field: "government_employee_grade",
      operator: "in",
      value: ["not_applicable", "group_d_mts"],
    };
    expect(evaluateCondition(inSet, { government_employee_grade: "not_applicable" })).toBe("pass");
    expect(evaluateCondition(inSet, { government_employee_grade: "group_a_b_c" })).toBe("fail");
    expect(evaluateCondition(inSet, {})).toBe("unknown");
    expect(evaluateCondition(inSet, { government_employee_grade: null })).toBe("unknown");
  });

  it("paid_income_tax_last_year — boolean equals; false is a real value, null is unknown", () => {
    const mustBeFalse: ConditionNode = {
      field: "paid_income_tax_last_year",
      operator: "equals",
      value: false,
    };
    expect(evaluateCondition(mustBeFalse, { paid_income_tax_last_year: false })).toBe("pass");
    expect(evaluateCondition(mustBeFalse, { paid_income_tax_last_year: true })).toBe("fail");
    expect(evaluateCondition(mustBeFalse, {})).toBe("unknown");
    expect(evaluateCondition(mustBeFalse, { paid_income_tax_last_year: null })).toBe("unknown");

    const mustBeTrue: ConditionNode = {
      field: "paid_income_tax_last_year",
      operator: "not_equals",
      value: true,
    };
    expect(evaluateCondition(mustBeTrue, { paid_income_tax_last_year: false })).toBe("pass");
    expect(evaluateCondition(mustBeTrue, { paid_income_tax_last_year: true })).toBe("fail");
  });

  it("monthly_pension — gte/lte; 0 is a real value (not unknown), null is unknown", () => {
    const cap: ConditionNode = { field: "monthly_pension", operator: "lte", value: 10_000 };
    expect(evaluateCondition(cap, { monthly_pension: 5_000 })).toBe("pass");
    expect(evaluateCondition(cap, { monthly_pension: 15_000 })).toBe("fail");
    expect(evaluateCondition(cap, { monthly_pension: 0 })).toBe("pass");
    expect(evaluateCondition(cap, {})).toBe("unknown");
    expect(evaluateCondition(cap, { monthly_pension: null })).toBe("unknown");
  });

  it("exists / not_exists on a nullable field never returns unknown", () => {
    const ex: ConditionNode = { field: "monthly_pension", operator: "exists", value: null };
    expect(evaluateCondition(ex, { monthly_pension: 0 })).toBe("pass");
    expect(evaluateCondition(ex, { monthly_pension: null })).toBe("fail");
    expect(evaluateCondition(ex, {})).toBe("fail");

    const nx: ConditionNode = { field: "land_holding", operator: "not_exists", value: null };
    expect(evaluateCondition(nx, {})).toBe("pass");
    expect(evaluateCondition(nx, { land_holding: null })).toBe("pass");
    expect(evaluateCondition(nx, { land_holding: "none" })).toBe("fail");
  });

  it("AND group goes 'unknown' (not 'fail') when a new field is missing", () => {
    const tree: ConditionNode = {
      op: "AND",
      children: [
        { field: "land_holding", operator: "equals", value: "individual" },
        { field: "paid_income_tax_last_year", operator: "equals", value: false },
      ],
    };
    expect(
      evaluateCondition(tree, { paid_income_tax_last_year: false }),
    ).toBe("unknown"); // land_holding missing
    expect(
      evaluateCondition(tree, {
        land_holding: "individual",
        paid_income_tax_last_year: false,
      }),
    ).toBe("pass");
    expect(
      evaluateCondition(tree, {
        land_holding: "individual",
        paid_income_tax_last_year: true,
      }),
    ).toBe("fail");
  });
});
