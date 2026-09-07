import { describe, expect, it } from "vitest";

import { matchScheme } from "../matchScheme";
import type { ConditionNode } from "../types";
import {
  andOnlyHard,
  fullProfile,
  makeScheme,
  nestedHard,
  notHard,
  profileWithout,
} from "./fixtures";

describe("simple AND-only scheme", () => {
  const scheme = makeScheme("and-only", andOnlyHard);

  it("profile fully matches -> likely_eligible", () => {
    const result = matchScheme(scheme, fullProfile);
    expect(result.bucket).toBe("likely_eligible");
    expect(result.matched_hard_conditions).toHaveLength(3);
    expect(result.matched_hard_conditions).toContain("occupation is farmer");
    expect(result.unknown_conditions).toEqual([]);
    expect(result.reasoning).toBe(
      "Matches your state, occupation, and income level.",
    );
  });

  it("one hard field missing -> possibly_eligible, gap named", () => {
    const result = matchScheme(scheme, profileWithout("occupation"));
    expect(result.bucket).toBe("possibly_eligible");
    expect(result.unknown_conditions).toEqual(["occupation"]);
    expect(result.matched_hard_conditions).toContain("state is Maharashtra");
    expect(result.reasoning).toContain("occupation");
  });

  it("one hard field explicitly fails -> not_eligible", () => {
    const result = matchScheme(scheme, { ...fullProfile, occupation: "student" });
    expect(result.bucket).toBe("not_eligible");
    expect(result.reasoning).toContain("occupation is farmer");
  });
});

describe("nested OR / AND scheme  ((SC OR ST) AND income <= 100000)", () => {
  const scheme = makeScheme("nested", nestedHard);

  it("OR branch and threshold both satisfied -> likely_eligible", () => {
    const result = matchScheme(scheme, {
      ...fullProfile,
      annual_family_income: 90_000,
    });
    expect(result.bucket).toBe("likely_eligible");
    expect(result.matched_hard_conditions).toContain("category is sc");
  });

  it("OR branch impossible -> not_eligible", () => {
    const result = matchScheme(scheme, {
      ...fullProfile,
      category: "obc",
      annual_family_income: 90_000,
    });
    expect(result.bucket).toBe("not_eligible");
  });

  it("field feeding the OR branch is missing -> possibly_eligible", () => {
    const profile = { ...profileWithout("category"), annual_family_income: 90_000 };
    const result = matchScheme(scheme, profile);
    expect(result.bucket).toBe("possibly_eligible");
    expect(result.unknown_conditions).toEqual(["category"]);
  });
});

describe("NOT condition (excluded occupation)", () => {
  const scheme = makeScheme("not-salaried", notHard);

  it("occupation is not the excluded one -> likely_eligible", () => {
    const result = matchScheme(scheme, fullProfile);
    expect(result.bucket).toBe("likely_eligible");
    expect(result.matched_hard_conditions).toContain("occupation is not salaried");
  });

  it("occupation is the excluded one -> not_eligible", () => {
    const result = matchScheme(scheme, { ...fullProfile, occupation: "salaried" });
    expect(result.bucket).toBe("not_eligible");
    expect(result.reasoning).toContain("occupation is not salaried");
  });

  it("occupation missing -> possibly_eligible", () => {
    const result = matchScheme(scheme, profileWithout("occupation"));
    expect(result.bucket).toBe("possibly_eligible");
    expect(result.unknown_conditions).toEqual(["occupation"]);
  });
});

describe("soft conditions affect ranking data only, never the bucket", () => {
  const soft: ConditionNode = {
    op: "OR",
    children: [
      { field: "category", operator: "in", value: ["sc", "st"] },
      { field: "occupation", operator: "equals", value: "farmer" },
    ],
  };
  const scheme = makeScheme(
    "soft-demo",
    { field: "annual_family_income", operator: "lte", value: 300_000 },
    soft,
  );

  it("both soft leaves satisfied -> still likely_eligible, 2 recorded", () => {
    const result = matchScheme(scheme, fullProfile);
    expect(result.bucket).toBe("likely_eligible");
    expect(result.matched_soft_conditions).toHaveLength(2);
  });

  it("no soft leaf satisfied -> same bucket, 0 recorded", () => {
    const result = matchScheme(scheme, {
      ...fullProfile,
      category: "general",
      occupation: "student",
    });
    expect(result.bucket).toBe("likely_eligible");
    expect(result.matched_soft_conditions).toEqual([]);
  });

  it("soft passing does not rescue a failed hard gate", () => {
    const result = matchScheme(scheme, {
      ...fullProfile,
      annual_family_income: 400_000,
    });
    // Soft leaves still evaluate and get recorded, but the bucket is decided
    // by the hard gate alone.
    expect(result.matched_soft_conditions).toHaveLength(2);
    expect(result.bucket).toBe("not_eligible");
  });
});

describe("empty hard gate", () => {
  it("evaluates as open to everyone", () => {
    const scheme = makeScheme("open", { op: "AND", children: [] });
    const result = matchScheme(scheme, {});
    expect(result.bucket).toBe("likely_eligible");
    expect(result.reasoning).toBe("This scheme has no eligibility restrictions.");
  });
});

describe("unknown_conditions: a leaf is dropped only when its OWN parent group resolved", () => {
  // Mirrors prisma/seed.ts `pmKisanV2`. The last OR resolves to pass via the
  // `monthly_pension not_exists` sibling, so the `monthly_pension lte 9999`
  // leaf (unknown when pension is absent) is answered by the group.
  const pmKisanV2Hard: ConditionNode = {
    op: "AND",
    children: [
      { field: "land_holding", operator: "equals", value: "individual" },
      {
        op: "NOT",
        child: {
          field: "paid_income_tax_last_year",
          operator: "equals",
          value: true,
        },
      },
      {
        op: "OR",
        children: [
          { field: "government_employee_grade", operator: "equals", value: "not_applicable" },
          { field: "government_employee_grade", operator: "equals", value: "group_d_mts" },
        ],
      },
      {
        op: "OR",
        children: [
          { field: "monthly_pension", operator: "not_exists", value: null },
          { field: "monthly_pension", operator: "lte", value: 9999 },
          { field: "government_employee_grade", operator: "equals", value: "group_d_mts" },
        ],
      },
    ],
  };

  it("1. PM-KISAN-v2 profile 1: 'monthly pension' leaves unknown_conditions, but the not_exists match stays", () => {
    const result = matchScheme(makeScheme("pm-kisan-v2", pmKisanV2Hard), {
      land_holding: "individual",
      paid_income_tax_last_year: false,
      government_employee_grade: "not_applicable",
      // monthly_pension omitted
    });

    expect(result.bucket).toBe("likely_eligible");
    expect(result.unknown_conditions).toEqual([]);
    expect(result.unknown_conditions).not.toContain("monthly pension");
    expect(result.matched_hard_conditions).toContain("monthly pension is not provided");
  });

  it("2. AND(age >= 18, age <= 60) with age missing: parent AND is itself unknown, so 'age' is still reported", () => {
    const hard: ConditionNode = {
      op: "AND",
      children: [
        { field: "age", operator: "gte", value: 18 },
        { field: "age", operator: "lte", value: 60 },
      ],
    };
    const result = matchScheme(makeScheme("age-window", hard), {});

    expect(result.bucket).toBe("possibly_eligible");
    expect(result.unknown_conditions).toEqual(["age"]);
  });

  it("3. same field in two sibling groups: suppressed in the resolved group, kept in the unresolved one (per-group, not global)", () => {
    const hard: ConditionNode = {
      op: "AND",
      children: [
        {
          // group A — resolves to pass via `not_exists`
          op: "OR",
          children: [
            { field: "land_holding", operator: "not_exists", value: null },
            { field: "land_holding", operator: "equals", value: "individual" },
          ],
        },
        {
          // group B — stays unknown (both leaves unknown)
          op: "OR",
          children: [
            { field: "land_holding", operator: "equals", value: "individual" },
            { field: "land_holding", operator: "equals", value: "institutional" },
          ],
        },
      ],
    };
    const result = matchScheme(makeScheme("two-groups", hard), {}); // land_holding missing

    expect(result.bucket).toBe("possibly_eligible");
    // group A resolved -> its unknown `equals` leaf is dropped;
    // group B did not resolve -> its `land_holding` leaves survive.
    expect(result.unknown_conditions).toEqual(["land holding"]);
    expect(result.matched_hard_conditions).toContain("land holding is not provided");
  });
});
