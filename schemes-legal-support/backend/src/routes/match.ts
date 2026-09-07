import { Router } from "express";
import { z } from "zod";

import { prisma } from "../lib/prisma";
import { prismaSchemeToScheme } from "../lib/schemeMapper";
import { rankSchemes } from "../matching";

export const matchRouter = Router();

/**
 * Request body for POST /match: any subset of the intake fields. `.strict()`
 * rejects unknown keys; numeric fields are coerced so `"30"` is accepted as
 * `30`. Values that can't be coerced or aren't in the allowed set → 400.
 */
const profileSchema = z
  .object({
    state: z.string().min(1),
    age: z.coerce.number().finite().int().min(0).max(150),
    gender: z.enum(["male", "female", "other"]),
    annual_family_income: z.coerce.number().finite().int().min(0),
    occupation: z.enum([
      "farmer",
      "student",
      "unemployed",
      "salaried",
      "self_employed",
      "other",
    ]),
    education_level: z.enum([
      "below_10th",
      "10th_pass",
      "12th_pass",
      "graduate",
      "postgraduate",
      "other",
    ]),
    category: z.enum(["general", "obc", "sc", "st", "ebc", "dnt", "other"]),
    support_type_needed: z.enum([
      "financial_aid",
      "education",
      "healthcare",
      "housing",
      "employment",
      "agriculture",
      "business",
      "other",
    ]),
    // Optional / nullable intake fields.
    land_holding: z.enum(["none", "individual", "institutional"]),
    paid_income_tax_last_year: z.preprocess((v) => {
      if (v === true || v === "true") return true;
      if (v === false || v === "false") return false;
      return v;
    }, z.boolean()),
    monthly_pension: z.coerce.number().finite().int().min(0),
    government_employee_grade: z.enum([
      "not_applicable",
      "group_a_b_c",
      "group_d_mts",
    ]),
  })
  .partial()
  .strict();

matchRouter.post("/", async (req, res) => {
  const parsed = profileSchema.safeParse(req.body ?? {});
  if (!parsed.success) {
    return res.status(400).json({
      error: "Invalid request body",
      details: parsed.error.flatten(),
    });
  }

  try {
    const rows = await prisma.scheme.findMany();
    const schemes = rows.map(prismaSchemeToScheme);
    const results = rankSchemes(schemes, parsed.data);
    return res.json({ results });
  } catch (err) {
    console.error("[POST /match] failed:", err);
    return res.status(500).json({ error: "Internal server error" });
  }
});
