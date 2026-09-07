import request from "supertest";
import { afterAll, beforeAll, describe, expect, it } from "vitest";

import { app } from "../../index";
import { prisma } from "../../lib/prisma";
import { seed } from "../../../prisma/seed";

beforeAll(async () => {
  await seed(prisma);
});

afterAll(async () => {
  await prisma.scheme.deleteMany({ where: { schemeId: { startsWith: "itest-" } } });
  await prisma.$disconnect();
});

/** A valid create/update payload; override keys per test. */
function schemePayload(
  overrides: Record<string, unknown> = {},
): Record<string, unknown> {
  return {
    scheme_id: "itest-scheme",
    name: "Integration Test Scheme",
    short_summary: "Created by the schemes route integration tests.",
    level: "Central",
    state: null,
    category: ["test"],
    eligibility: {
      hard: {
        op: "AND",
        children: [
          { field: "occupation", operator: "equals", value: "student" },
          { field: "age", operator: "lte", value: 25 },
        ],
      },
      soft: null,
    },
    benefits: "A test benefit.",
    documents_required: ["Aadhaar card"],
    application_process: "Apply on the test portal.",
    official_source_url: "https://example.gov.in/itest",
    apply_url: null,
    last_verified_date: null,
    ...overrides,
  };
}

describe("GET /schemes/:schemeId", () => {
  it("returns full detail for a known scheme", async () => {
    const res = await request(app).get("/schemes/pm-kisan");

    expect(res.status).toBe(200);
    expect(res.body.scheme_id).toBe("pm-kisan");
    expect(res.body.eligibility.hard.op).toBe("AND");
    expect(Array.isArray(res.body.documents_required)).toBe(true);
    expect(res.body.verification_status).toBe("needs_review");
  });

  it("404s for an unknown scheme id", async () => {
    const res = await request(app).get("/schemes/does-not-exist");

    expect(res.status).toBe(404);
    expect(res.body.error).toContain("does-not-exist");
  });
});

describe("GET /schemes (list)", () => {
  it("lists all schemes", async () => {
    const res = await request(app).get("/schemes");

    expect(res.status).toBe(200);
    expect(Array.isArray(res.body.schemes)).toBe(true);
    expect(res.body.schemes.length).toBeGreaterThanOrEqual(5);
  });

  it("filters by verification_status", async () => {
    const res = await request(app).get("/schemes?verification_status=needs_review");

    expect(res.status).toBe(200);
    expect(res.body.schemes.length).toBeGreaterThanOrEqual(1);
    for (const scheme of res.body.schemes) {
      expect(scheme.verification_status).toBe("needs_review");
    }
  });

  it("400s on an unknown verification_status filter", async () => {
    const res = await request(app).get("/schemes?verification_status=banana");
    expect(res.status).toBe(400);
  });
});

describe("POST /schemes", () => {
  it("creates a scheme and defaults verification_status to needs_review", async () => {
    const res = await request(app)
      .post("/schemes")
      .send(schemePayload({ scheme_id: "itest-create" }));

    expect(res.status).toBe(201);
    expect(res.body.scheme_id).toBe("itest-create");
    expect(res.body.verification_status).toBe("needs_review");
  });

  it("rejects an invalid submission with the full list of errors", async () => {
    const res = await request(app)
      .post("/schemes")
      .send(
        schemePayload({
          scheme_id: "itest-bad",
          level: "State",
          state: null, // (1) required for State level
          official_source_url: "not-a-url", // (2)
          eligibility: {
            hard: {
              op: "AND",
              children: [
                { field: "income", operator: "gte", value: 5 }, // (3) unknown field
                { field: "category", operator: "gte", value: 1 }, // (4) gte on enum
              ],
            },
            soft: null,
          },
          verification_status: "verified", // (5) verified without a date
          last_verified_date: null,
        }),
      );

    expect(res.status).toBe(400);
    expect(res.body.error).toBe("Scheme validation failed");
    expect(Array.isArray(res.body.errors)).toBe(true);
    expect(res.body.errors.length).toBeGreaterThanOrEqual(4);
    expect(res.body.errors).toContain(
      'state: must be provided when level is "State"',
    );
    expect(
      res.body.errors.some((e: string) => e.includes("not a known profile field")),
    ).toBe(true);
    expect(
      res.body.errors.some((e: string) =>
        e.includes('cannot be used on enum field "category"'),
      ),
    ).toBe(true);
  });

  it("409s on a duplicate scheme_id", async () => {
    await request(app).post("/schemes").send(schemePayload({ scheme_id: "itest-dup" }));
    const res = await request(app)
      .post("/schemes")
      .send(schemePayload({ scheme_id: "itest-dup" }));

    expect(res.status).toBe(409);
    expect(res.body.error).toContain("itest-dup");
  });
});

describe("PUT /schemes/:schemeId", () => {
  it("updates an existing scheme", async () => {
    await request(app).post("/schemes").send(schemePayload({ scheme_id: "itest-put" }));

    const res = await request(app)
      .put("/schemes/itest-put")
      .send(
        schemePayload({
          scheme_id: "itest-put",
          name: "Renamed Integration Scheme",
          verification_status: "verified",
          last_verified_date: "2021-06-01",
        }),
      );

    expect(res.status).toBe(200);
    expect(res.body.name).toBe("Renamed Integration Scheme");
    expect(res.body.verification_status).toBe("verified");
    expect(res.body.last_verified_date).toBe("2021-06-01");
  });

  it("404s when the target scheme does not exist", async () => {
    const res = await request(app)
      .put("/schemes/itest-missing")
      .send(schemePayload({ scheme_id: "itest-missing" }));

    expect(res.status).toBe(404);
  });

  it("rejects an invalid update with 400 and errors", async () => {
    await request(app).post("/schemes").send(schemePayload({ scheme_id: "itest-put2" }));

    const res = await request(app)
      .put("/schemes/itest-put2")
      .send(
        schemePayload({
          scheme_id: "itest-put2",
          eligibility: {
            hard: { field: "age", operator: "in", value: "nope" },
            soft: null,
          },
        }),
      );

    expect(res.status).toBe(400);
    expect(res.body.errors.length).toBeGreaterThanOrEqual(1);
  });
});
