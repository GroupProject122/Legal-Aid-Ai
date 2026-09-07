import { PrismaClient } from "@prisma/client";

/**
 * Single shared PrismaClient instance. Import this everywhere instead of
 * calling `new PrismaClient()` per module, so dev hot-reloads don't exhaust
 * the Postgres connection pool.
 */
export const prisma = new PrismaClient();
