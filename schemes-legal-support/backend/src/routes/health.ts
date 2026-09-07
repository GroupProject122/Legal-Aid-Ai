import { Router } from "express";
import { prisma } from "../lib/prisma";

export const healthRouter = Router();

/**
 * GET /health
 *
 * Liveness check plus a best-effort Postgres connectivity probe. Returns 200
 * as long as the process is up; `db` is "up" only if `SELECT 1` succeeds.
 */
healthRouter.get("/", async (_req, res) => {
  let db: "up" | "down" = "down";
  try {
    await prisma.$queryRaw`SELECT 1`;
    db = "up";
  } catch {
    db = "down";
  }

  res.json({
    status: "ok",
    service: "schemes-legal-support-backend",
    db,
    timestamp: new Date().toISOString(),
  });
});
