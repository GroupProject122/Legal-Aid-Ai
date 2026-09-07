import { matchScheme } from "./matchScheme";
import type { MatchBucket, MatchResult, Scheme, UserProfile } from "./types";

const BUCKET_RANK: Record<MatchBucket, number> = {
  likely_eligible: 0,
  possibly_eligible: 1,
  not_eligible: 2,
};

/**
 * Match every scheme against the profile, drop the not-eligible ones, and sort:
 *
 *   1. likely_eligible before possibly_eligible
 *   2. within a bucket, more matched soft conditions first
 *
 * Ties keep their input order (`Array.prototype.sort` is stable).
 */
export function rankSchemes(
  schemes: Scheme[],
  profile: UserProfile,
): (Scheme & MatchResult)[] {
  return schemes
    .map((scheme) => ({ ...scheme, ...matchScheme(scheme, profile) }))
    .filter((entry) => entry.bucket !== "not_eligible")
    .sort((a, b) => {
      const byBucket = BUCKET_RANK[a.bucket] - BUCKET_RANK[b.bucket];
      if (byBucket !== 0) return byBucket;
      return b.matched_soft_conditions.length - a.matched_soft_conditions.length;
    });
}
