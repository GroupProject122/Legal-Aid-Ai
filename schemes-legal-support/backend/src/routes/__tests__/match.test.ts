import request from "supertest";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { app } from "../../index";
import { prisma } from "../../lib/prisma";
import { seed } from "../../../prisma/seed";

/**
 * Integration tests for POST /match. These hit a real Postgres via Prisma —
 * `DATABASE_URL` must point at a migrated database (see README). The suite
 * seeds the 5 sample schemes first so it is self-contained.
 */
beforeAll(async () => {
  await seed(prisma);
});

afterAll(async () => {
  await prisma.$disconnect();
});

describe("POST /match", () => {
  it("returns PM-KISAN as likely_eligible for a matching farmer profile", async () => {
    const res = await request(app)
      .post("/match")
      .send({ occupation: "farmer", annual_family_income: 150_000, state: "Bihar" });

    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.results)).toBe(true);

    const pmKisan = res.body.results.find(
      (r: { scheme_id: string }) => r.scheme_id === "pm-kisan",
    );
    expect(pmKisan).toBeDefined();
    expect(pmKisan.bucket).toBe("likely_eligible");
    expect(pmKisan.matched_hard_conditions.length).toBeGreaterThan(0);
  });

  it("puts schemes with missing fields in possibly_eligible with unknown_conditions", async () => {
    // Farmer, but income not provided -> PM-KISAN income check is unknown.
    const res = await request(app).post("/match").send({ occupation: "farmer" });

    expect(res.status).toBe(200);
    const pmKisan = res.body.results.find(
      (r: { scheme_id: string }) => r.scheme_id === "pm-kisan",
    );
    expect(pmKisan).toBeDefined();
    expect(pmKisan.bucket).toBe("possibly_eligible");
    expect(pmKisan.unknown_conditions).toContain("income level");

    // Every returned scheme is eligible-or-maybe; none are not_eligible.
    for (const r of res.body.results) {
      expect(["likely_eligible", "possibly_eligible"]).toContain(r.bucket);
    }
  });

  it("rejects an invalid body (non-numeric age) with 400", async () => {
    const res = await request(app).post("/match").send({ age: "not-a-number" });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe("Invalid request body");
    expect(res.body.details.fieldErrors.age).toBeDefined();
  });

  it("rejects unknown fields with 400", async () => {
    const res = await request(app)
      .post("/match")
      .send({ occupation: "farmer", favourite_colour: "blue" });

    expect(res.status).toBe(400);
    expect(res.body.error).toBe("Invalid request body");
  });

  it("handles an empty profile without crashing", async () => {
    const res = await request(app).post("/match").send({});

    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.results)).toBe(true);
    // With nothing known, no scheme can be confirmed or ruled out.
    for (const r of res.body.results) {
      expect(r.bucket).toBe("possibly_eligible");
    }
    // None of the seeded schemes is unconditional, so all 6 come back as
    // maybes. (>= rather than ==: the DB may also hold bulk-loaded schemes.)
    expect(res.body.results.length).toBeGreaterThanOrEqual(6);
  });

  it("coerces numeric strings (age: \"40\") instead of rejecting them", async () => {
    const res = await request(app)
      .post("/match")
      .send({ age: "40", occupation: "unemployed" });

    expect(res.status).toBe(200);
    const pmkvy = res.body.results.find(
      (r: { scheme_id: string }) => r.scheme_id === "pmkvy-4",
    );
    expect(pmkvy).toBeDefined();
    expect(pmkvy.bucket).toBe("likely_eligible");
  });

  it("PM-KISAN-v2: likely / not_eligible / possibly across the 3 new-field profiles", async () => {
    // 1. all three checks satisfied -> likely_eligible
    const r1 = await request(app).post("/match").send({
      land_holding: "individual",
      paid_income_tax_last_year: false,
      government_employee_grade: "not_applicable",
    });
    const s1 = r1.body.results.find(
      (r: { scheme_id: string }) => r.scheme_id === "pm-kisan-v2",
    );
    expect(s1?.bucket).toBe("likely_eligible");

    // 2. paid income tax -> hard NOT() fails -> not_eligible -> filtered out
    const r2 = await request(app).post("/match").send({
      land_holding: "individual",
      paid_income_tax_last_year: true,
      government_employee_grade: "not_applicable",
    });
    expect(
      r2.body.results.some(
        (r: { scheme_id: string }) => r.scheme_id === "pm-kisan-v2",
      ),
    ).toBe(false);

    // 3. land_holding omitted -> possibly_eligible, gap surfaced
    const r3 = await request(app).post("/match").send({
      paid_income_tax_last_year: false,
      government_employee_grade: "not_applicable",
    });
    const s3 = r3.body.results.find(
      (r: { scheme_id: string }) => r.scheme_id === "pm-kisan-v2",
    );
    expect(s3?.bucket).toBe("possibly_eligible");
    expect(s3?.unknown_conditions).toContain("land holding");
  });

  it("accepts the new optional fields (with coercion) and rejects bad values", async () => {
    const ok = await request(app).post("/match").send({
      land_holding: "individual",
      paid_income_tax_last_year: "false", // string coerced to boolean
      monthly_pension: "0", // string coerced to number
      government_employee_grade: "not_applicable",
    });
    expect(ok.status).toBe(200);
    expect(Array.isArray(ok.body.results)).toBe(true);

    const badEnum = await request(app)
      .post("/match")
      .send({ land_holding: "farmland" });
    expect(badEnum.status).toBe(400);

    const badBool = await request(app)
      .post("/match")
      .send({ paid_income_tax_last_year: "maybe" });
    expect(badBool.status).toBe(400);
  });
});
