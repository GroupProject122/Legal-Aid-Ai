import { Prisma } from "@prisma/client";
import { Router } from "express";

import { prisma } from "../lib/prisma";
import {
  prismaSchemeToScheme,
  schemeInputToPrismaData,
} from "../lib/schemeMapper";
import { validateScheme } from "../validation/validateScheme";

export const schemesRouter = Router();

const VERIFICATION_STATUSES = ["verified", "needs_review", "stale"] as const;
type VerificationStatus = (typeof VERIFICATION_STATUSES)[number];

function isVerificationStatus(value: unknown): value is VerificationStatus {
  return (
    typeof value === "string" &&
    (VERIFICATION_STATUSES as readonly string[]).includes(value)
  );
}

/**
 * GET /schemes
 *
 * List every scheme (for the admin screen). Optional `?verification_status=`
 * filter. Ordered most-recently-updated first.
 */
schemesRouter.get("/", async (req, res) => {
  const filter = req.query.verification_status;
  if (filter !== undefined && !isVerificationStatus(filter)) {
    return res.status(400).json({
      error: `Unknown verification_status filter '${String(filter)}' (allowed: ${VERIFICATION_STATUSES.join(", ")})`,
    });
  }

  try {
    const rows = await prisma.scheme.findMany({
      where: isVerificationStatus(filter)
        ? { verificationStatus: filter }
        : undefined,
      orderBy: { updatedAt: "desc" },
    });
    return res.json({ schemes: rows.map(prismaSchemeToScheme) });
  } catch (err) {
    console.error("[GET /schemes] failed:", err);
    return res.status(500).json({ error: "Internal server error" });
  }
});

/**
 * GET /schemes/:schemeId — full detail for one scheme, 404 if unknown.
 */
schemesRouter.get("/:schemeId", async (req, res) => {
  try {
    const row = await prisma.scheme.findUnique({
      where: { schemeId: req.params.schemeId },
    });

    if (!row) {
      return res
        .status(404)
        .json({ error: `No scheme with schemeId '${req.params.schemeId}'` });
    }

    return res.json(prismaSchemeToScheme(row));
  } catch (err) {
    console.error("[GET /schemes/:schemeId] failed:", err);
    return res.status(500).json({ error: "Internal server error" });
  }
});

/**
 * POST /schemes
 *
 * Create a scheme from a hand-entered record. Validates with `validateScheme`
 * and returns 400 with the FULL error list on failure. `verification_status`
 * defaults to "needs_review". 201 on success, 409 if the scheme_id is taken.
 */
schemesRouter.post("/", async (req, res) => {
  const result = validateScheme(req.body);
  if (!result.valid) {
    return res
      .status(400)
      .json({ error: "Scheme validation failed", errors: result.errors });
  }

  try {
    const created = await prisma.scheme.create({
      data: schemeInputToPrismaData(result.scheme),
    });
    return res.status(201).json(prismaSchemeToScheme(created));
  } catch (err) {
    if (
      err instanceof Prisma.PrismaClientKnownRequestError &&
      err.code === "P2002"
    ) {
      return res.status(409).json({
        error: `A scheme with scheme_id '${result.scheme.scheme_id}' already exists`,
      });
    }
    console.error("[POST /schemes] failed:", err);
    return res.status(500).json({ error: "Internal server error" });
  }
});

/**
 * PUT /schemes/:schemeId
 *
 * Replace an existing scheme. Same validation as POST. 404 if the target
 * doesn't exist; 409 if renaming onto a scheme_id that's already taken.
 */
schemesRouter.put("/:schemeId", async (req, res) => {
  const result = validateScheme(req.body);
  if (!result.valid) {
    return res
      .status(400)
      .json({ error: "Scheme validation failed", errors: result.errors });
  }

  try {
    const existing = await prisma.scheme.findUnique({
      where: { schemeId: req.params.schemeId },
    });
    if (!existing) {
      return res
        .status(404)
        .json({ error: `No scheme with schemeId '${req.params.schemeId}'` });
    }

    const updated = await prisma.scheme.update({
      where: { schemeId: req.params.schemeId },
      data: schemeInputToPrismaData(result.scheme),
    });
    return res.json(prismaSchemeToScheme(updated));
  } catch (err) {
    if (
      err instanceof Prisma.PrismaClientKnownRequestError &&
      err.code === "P2002"
    ) {
      return res.status(409).json({
        error: `A scheme with scheme_id '${result.scheme.scheme_id}' already exists`,
      });
    }
    console.error("[PUT /schemes/:schemeId] failed:", err);
    return res.status(500).json({ error: "Internal server error" });
  }
});
