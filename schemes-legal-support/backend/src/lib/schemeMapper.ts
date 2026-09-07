import { Prisma, type Scheme as PrismaScheme } from "@prisma/client";

import type { Eligibility, Scheme } from "../matching";
import type { SchemeInput } from "../validation/validateScheme";

/**
 * Convert a persisted Prisma `Scheme` row into the snake_case `Scheme` shape
 * the matching engine and the public API use (see docs/data-model.md). The
 * `eligibility` jsonb column is trusted to hold a valid `{ hard, soft }` tree;
 * write-time validation is a separate concern.
 */
export function prismaSchemeToScheme(row: PrismaScheme): Scheme {
  return {
    scheme_id: row.schemeId,
    name: row.name,
    short_summary: row.shortSummary,
    level: row.level,
    state: row.state,
    category: row.category,
    eligibility: row.eligibility as unknown as Eligibility,
    benefits: row.benefits,
    documents_required: row.documentsRequired,
    application_process: row.applicationProcess,
    official_source_url: row.officialSourceUrl,
    apply_url: row.applyUrl,
    last_verified_date: row.lastVerifiedDate
      ? row.lastVerifiedDate.toISOString().slice(0, 10)
      : null,
    verification_status: row.verificationStatus,
  };
}

/**
 * Convert a validated `SchemeInput` (snake_case, from the write API) into the
 * camelCase column data Prisma's create/update accept. `verification_status`
 * falls back to "needs_review" when the caller didn't set it.
 */
export function schemeInputToPrismaData(
  input: SchemeInput,
): Prisma.SchemeUncheckedCreateInput {
  return {
    schemeId: input.scheme_id,
    name: input.name,
    shortSummary: input.short_summary,
    level: input.level,
    // `validateScheme` has already checked this is a real IndianState or null.
    state: input.state as Prisma.SchemeUncheckedCreateInput["state"],
    category: input.category,
    eligibility: input.eligibility as unknown as Prisma.InputJsonValue,
    benefits: input.benefits,
    documentsRequired: input.documents_required,
    applicationProcess: input.application_process,
    officialSourceUrl: input.official_source_url,
    applyUrl: input.apply_url,
    lastVerifiedDate: input.last_verified_date
      ? new Date(`${input.last_verified_date}T00:00:00.000Z`)
      : null,
    verificationStatus: input.verification_status ?? "needs_review",
  };
}
