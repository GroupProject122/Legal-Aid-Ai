import { describe, expect, it } from "vitest";

import { validateScheme } from "../validateScheme";

/** A fully valid scheme record; override individual keys per test. */
function validScheme(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    scheme_id: "test-scheme",
    name: "Test Scheme",
    short_summary: "A scheme used in tests.",
    level: "Central",
    state: null,
    category: ["test"],
    eligibility: {
      hard: {
        op: "AND",
        children: [
          { field: "occupation", operator: "equals", value: "farmer" },
          { field: "annual_family_income", operator: "lte", value: 200000 },
        ],
      },
      soft: null,
    },
    benefits: "Some benefit.",
    documents_required: ["Aadhaar card"],
    application_process: "Apply online.",
    official_source_url: "https://example.gov.in",
    apply_url: null,
    last_verified_date: null,
    ...overrides,
  };
}

/** Convenience: get the errors array (fails loudly if the input was valid). */
function errorsOf(input: unknown): string[] {
  const result = validateScheme(input);
  if (result.valid) {
    throw new Error("expected invalid, but validation passed");
  }
  return result.errors;
}

describe("validateScheme — happy path", () => {
  it("accepts a fully valid Central scheme", () => {
    const result = validateScheme(validScheme());
    expect(result.valid).toBe(true);
    if (result.valid) {
      expect(result.scheme.scheme_id).toBe("test-scheme");
      expect(result.scheme.state).toBeNull();
      expect(result.scheme.verification_status).toBeUndefined();
    }
  });

  it("accepts a valid State scheme with nested OR / NOT and exists", () => {
    const result = validateScheme(
      validScheme({
        level: "State",
        state: "Maharashtra",
        eligibility: {
          hard: {
            op: "AND",
            children: [
              {
                op: "OR",
                children: [
                  { field: "category", operator: "in", value: ["sc", "st"] },
                  { field: "annual_family_income", operator: "lte", value: 800000 },
                ],
              },
              {
                op: "NOT",
                child: { field: "occupation", operator: "equals", value: "salaried" },
              },
              { field: "age", operator: "exists", value: null },
            ],
          },
          soft: { field: "gender", operator: "equals", value: "female" },
        },
      }),
    );
    expect(result.valid).toBe(true);
  });

  it("accepts verification_status verified when last_verified_date is a past date", () => {
    const result = validateScheme(
      validScheme({
        verification_status: "verified",
        last_verified_date: "2020-01-15",
      }),
    );
    expect(result.valid).toBe(true);
  });
});

describe("validateScheme — leaf field must be known", () => {
  it("rejects an unknown field and names it", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "income", operator: "gte", value: 5 },
          soft: null,
        },
      }),
    );
    expect(errors.some((e) => e.includes('"income"') && e.includes("not a known profile field"))).toBe(
      true,
    );
  });

  it("also validates the soft tree", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "age", operator: "gte", value: 18 },
          soft: { field: "bogus_field", operator: "equals", value: "x" },
        },
      }),
    );
    expect(errors.some((e) => e.startsWith("eligibility.soft.field:"))).toBe(true);
  });
});

describe("validateScheme — operator must suit the field type", () => {
  it("rejects gte/lte on an enum field", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "category", operator: "gte", value: 5 },
          soft: null,
        },
      }),
    );
    expect(
      errors.some((e) => e.includes('cannot be used on enum field "category"')),
    ).toBe(true);
  });

  it("rejects equals / in on a numeric field", () => {
    const equalsErr = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "age", operator: "equals", value: 30 },
          soft: null,
        },
      }),
    );
    expect(
      equalsErr.some((e) => e.includes('cannot be used on numeric field "age"')),
    ).toBe(true);

    const inErr = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "annual_family_income", operator: "in", value: [1, 2] },
          soft: null,
        },
      }),
    );
    expect(
      inErr.some((e) =>
        e.includes('cannot be used on numeric field "annual_family_income"'),
      ),
    ).toBe(true);
  });

  it("rejects an entirely unknown operator", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "category", operator: "startsWith", value: "s" },
          soft: null,
        },
      }),
    );
    expect(
      errors.some((e) => e.includes('"startsWith"') && e.includes("not a valid operator")),
    ).toBe(true);
  });

  it("allows exists / not_exists on any field", () => {
    const result = validateScheme(
      validScheme({
        eligibility: {
          hard: {
            op: "AND",
            children: [
              { field: "age", operator: "exists", value: null },
              { field: "gender", operator: "not_exists", value: null },
            ],
          },
          soft: null,
        },
      }),
    );
    expect(result.valid).toBe(true);
  });
});

describe("validateScheme — value shape must match the operator", () => {
  it("rejects in without an array", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "category", operator: "in", value: "sc" },
          soft: null,
        },
      }),
    );
    expect(errors.some((e) => e.includes('operator "in" needs an array'))).toBe(true);
  });

  it("rejects an empty in array", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "category", operator: "in", value: [] },
          soft: null,
        },
      }),
    );
    expect(errors.some((e) => e.includes("non-empty array"))).toBe(true);
  });

  it("rejects gte without a number", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "age", operator: "gte", value: "30" },
          soft: null,
        },
      }),
    );
    expect(errors.some((e) => e.includes('operator "gte" needs a finite number'))).toBe(
      true,
    );
  });

  it("rejects equals with a non-scalar value", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "gender", operator: "equals", value: ["male"] },
          soft: null,
        },
      }),
    );
    expect(
      errors.some((e) => e.includes('operator "equals" needs a single scalar value')),
    ).toBe(true);
  });

  it("rejects an enum value outside the field's allowed set", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "category", operator: "equals", value: "vip" },
          soft: null,
        },
      }),
    );
    expect(errors.some((e) => e.includes('"vip" is not valid for "category"'))).toBe(true);
  });

  it("rejects a missing value for an operator that needs one", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "category", operator: "equals" },
          soft: null,
        },
      }),
    );
    expect(errors.some((e) => e.includes('is required for operator "equals"'))).toBe(true);
  });
});

describe("validateScheme — group structure", () => {
  it("rejects an empty AND group", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: { hard: { op: "AND", children: [] }, soft: null },
      }),
    );
    expect(errors.some((e) => e.includes("needs at least one condition"))).toBe(true);
  });

  it("rejects an unknown group operator", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: { op: "NAND", children: [{ field: "age", operator: "gte", value: 1 }] },
          soft: null,
        },
      }),
    );
    expect(errors.some((e) => e.includes("not a valid group operator"))).toBe(true);
  });

  it("recurses and reports the path of a bad nested leaf", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: {
            op: "OR",
            children: [
              { field: "age", operator: "gte", value: 18 },
              {
                op: "NOT",
                child: { field: "occupation", operator: "gte", value: 3 },
              },
            ],
          },
          soft: null,
        },
      }),
    );
    expect(
      errors.some((e) =>
        e.startsWith("eligibility.hard.children[1].child.operator:"),
      ),
    ).toBe(true);
  });
});

describe("validateScheme — level / state coherence", () => {
  it("rejects State level with a null state", () => {
    const errors = errorsOf(validScheme({ level: "State", state: null }));
    expect(errors).toContain('state: must be provided when level is "State"');
  });

  it("rejects Central level with a non-null state", () => {
    const errors = errorsOf(validScheme({ level: "Central", state: "Bihar" }));
    expect(errors).toContain('state: must be null when level is "Central"');
  });

  it("rejects an unrecognised state name", () => {
    const errors = errorsOf(validScheme({ level: "State", state: "Freedonia" }));
    expect(
      errors.some((e) => e.includes("not a recognised Indian state")),
    ).toBe(true);
  });
});

describe("validateScheme — verified requires a valid past date", () => {
  it("rejects verified with no last_verified_date", () => {
    const errors = errorsOf(
      validScheme({ verification_status: "verified", last_verified_date: null }),
    );
    expect(
      errors.some((e) =>
        e.includes('is required when verification_status is "verified"'),
      ),
    ).toBe(true);
  });

  it("rejects a future last_verified_date", () => {
    const errors = errorsOf(
      validScheme({
        verification_status: "verified",
        last_verified_date: "2999-01-01",
      }),
    );
    expect(errors.some((e) => e.includes("is in the future"))).toBe(true);
  });

  it("rejects a non-real calendar date", () => {
    const errors = errorsOf(validScheme({ last_verified_date: "2021-02-30" }));
    expect(errors.some((e) => e.includes("not a real calendar date"))).toBe(true);
  });
});

describe("validateScheme — non-object and unknown keys", () => {
  it("rejects null / string input", () => {
    expect(validateScheme(null).valid).toBe(false);
    expect(validateScheme("nope").valid).toBe(false);
  });

  it("rejects unknown top-level keys", () => {
    const errors = errorsOf(validScheme({ extra_field: true }));
    expect(errors.some((e) => e.toLowerCase().includes("unrecognized key"))).toBe(true);
  });
});

describe("validateScheme — reports ALL errors at once", () => {
  it("collects base, tree and cross-field errors together", () => {
    const errors = errorsOf({
      scheme_id: "Bad ID With Spaces",
      name: "",
      short_summary: "ok",
      level: "State",
      state: null, // (1) state required for State level
      category: [],
      eligibility: {
        hard: {
          op: "AND",
          children: [
            { field: "income", operator: "gte", value: 5 }, // (2) unknown field
            { field: "category", operator: "gte", value: 1 }, // (3) gte on enum
            { field: "age", operator: "gte", value: "old" }, // (4) value not a number
          ],
        },
        soft: null,
      },
      benefits: "ok",
      documents_required: [],
      application_process: "ok",
      official_source_url: "not-a-url", // (5) bad url
      apply_url: null,
      last_verified_date: null,
      verification_status: "verified", // (6) verified without a date
    });

    expect(errors.length).toBeGreaterThanOrEqual(5);
    expect(errors.some((e) => e.startsWith("scheme_id:"))).toBe(true);
    expect(errors.some((e) => e.startsWith("official_source_url:"))).toBe(true);
    expect(errors).toContain('state: must be provided when level is "State"');
    expect(errors.some((e) => e.includes("not a known profile field"))).toBe(true);
    expect(errors.some((e) => e.includes('cannot be used on enum field "category"'))).toBe(
      true,
    );
    expect(
      errors.some((e) =>
        e.includes('is required when verification_status is "verified"'),
      ),
    ).toBe(true);
  });
});

describe("validateScheme — new optional fields", () => {
  it("accepts land_holding / government_employee_grade / paid_income_tax_last_year / monthly_pension leaves", () => {
    const result = validateScheme(
      validScheme({
        eligibility: {
          hard: {
            op: "AND",
            children: [
              { field: "land_holding", operator: "equals", value: "individual" },
              {
                field: "government_employee_grade",
                operator: "in",
                value: ["not_applicable", "group_d_mts"],
              },
              {
                field: "paid_income_tax_last_year",
                operator: "equals",
                value: false,
              },
              { field: "monthly_pension", operator: "lte", value: 10000 },
            ],
          },
          soft: null,
        },
      }),
    );
    expect(result.valid).toBe(true);
  });

  it("rejects a bad enum value for land_holding", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "land_holding", operator: "equals", value: "farmland" },
          soft: null,
        },
      }),
    );
    expect(errors.some((e) => e.includes('"farmland" is not valid for "land_holding"'))).toBe(true);
  });

  it("rejects gte/lte on land_holding or government_employee_grade (enum)", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "government_employee_grade", operator: "gte", value: 1 },
          soft: null,
        },
      }),
    );
    expect(
      errors.some((e) => e.includes('cannot be used on enum field "government_employee_grade"')),
    ).toBe(true);
  });

  it("rejects in / gte / lte on paid_income_tax_last_year (boolean field)", () => {
    const inErr = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "paid_income_tax_last_year", operator: "in", value: [true] },
          soft: null,
        },
      }),
    );
    expect(
      inErr.some((e) => e.includes('cannot be used on boolean field "paid_income_tax_last_year"')),
    ).toBe(true);
  });

  it("rejects a non-boolean value for paid_income_tax_last_year equals", () => {
    const errors = errorsOf(
      validScheme({
        eligibility: {
          hard: {
            field: "paid_income_tax_last_year",
            operator: "equals",
            value: "no",
          },
          soft: null,
        },
      }),
    );
    expect(errors.some((e) => e.includes("needs true or false"))).toBe(true);
  });

  it("rejects equals / in on monthly_pension (numeric field) and a non-number lte value", () => {
    const equalsErr = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "monthly_pension", operator: "equals", value: 0 },
          soft: null,
        },
      }),
    );
    expect(
      equalsErr.some((e) => e.includes('cannot be used on numeric field "monthly_pension"')),
    ).toBe(true);

    const lteErr = errorsOf(
      validScheme({
        eligibility: {
          hard: { field: "monthly_pension", operator: "lte", value: "10000" },
          soft: null,
        },
      }),
    );
    expect(lteErr.some((e) => e.includes('operator "lte" needs a finite number'))).toBe(true);
  });

  it("accepts exists / not_exists on every new field", () => {
    const result = validateScheme(
      validScheme({
        eligibility: {
          hard: {
            op: "AND",
            children: [
              { field: "land_holding", operator: "exists", value: null },
              { field: "paid_income_tax_last_year", operator: "not_exists", value: null },
              { field: "monthly_pension", operator: "exists", value: null },
              { field: "government_employee_grade", operator: "not_exists", value: null },
            ],
          },
          soft: null,
        },
      }),
    );
    expect(result.valid).toBe(true);
  });
});
