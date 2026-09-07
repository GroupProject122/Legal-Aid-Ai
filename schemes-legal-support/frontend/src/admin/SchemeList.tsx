import { useEffect, useState } from "react";

import { listSchemes } from "../api";
import type { Scheme, VerificationStatus } from "../types";

const STATUS_ORDER: Record<VerificationStatus, number> = {
  needs_review: 0,
  stale: 1,
  verified: 2,
};

const STATUS_LABEL: Record<VerificationStatus, string> = {
  needs_review: "Needs review",
  stale: "Stale",
  verified: "Verified",
};

function jurisdiction(scheme: Scheme): string {
  return scheme.level === "State" && scheme.state
    ? `State · ${scheme.state.replace(/_/g, " ")}`
    : "Central";
}

interface SchemeListProps {
  reloadKey: number;
  onEdit: (scheme: Scheme) => void;
}

export function SchemeList({ reloadKey, onEdit }: SchemeListProps) {
  const [schemes, setSchemes] = useState<Scheme[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<"" | VerificationStatus>("");

  useEffect(() => {
    let cancelled = false;
    setSchemes(null);
    setError(null);
    listSchemes(filter || undefined)
      .then((data) => {
        if (!cancelled) setSchemes(data);
      })
      .catch((err) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load schemes.");
        }
      });
    return () => {
      cancelled = true;
    };
  }, [filter, reloadKey]);

  const sorted = schemes
    ? [...schemes].sort(
        (a, b) =>
          STATUS_ORDER[a.verification_status] -
            STATUS_ORDER[b.verification_status] ||
          a.name.localeCompare(b.name),
      )
    : [];

  const needsReview = sorted.filter(
    (s) => s.verification_status === "needs_review",
  ).length;

  return (
    <div className="scheme-list">
      <div className="list-toolbar">
        <label className="field inline">
          <span>Filter</span>
          <select
            value={filter}
            onChange={(e) =>
              setFilter(e.target.value as "" | VerificationStatus)
            }
          >
            <option value="">All statuses</option>
            <option value="needs_review">Needs review</option>
            <option value="stale">Stale</option>
            <option value="verified">Verified</option>
          </select>
        </label>
        {schemes ? (
          <span className="list-count">
            {schemes.length} scheme(s)
            {needsReview > 0 ? ` · ${needsReview} need review` : ""}
          </span>
        ) : null}
      </div>

      {error ? <p className="errors-panel">{error}</p> : null}
      {!schemes && !error ? <p className="hint">Loading…</p> : null}
      {schemes && schemes.length === 0 ? (
        <p className="hint">No schemes yet. Create one above.</p>
      ) : null}

      {sorted.length > 0 ? (
        <table className="scheme-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Jurisdiction</th>
              <th>Status</th>
              <th>Last verified</th>
              <th aria-label="actions" />
            </tr>
          </thead>
          <tbody>
            {sorted.map((scheme) => (
              <tr
                key={scheme.scheme_id}
                className={
                  scheme.verification_status === "needs_review"
                    ? "row-flag"
                    : undefined
                }
              >
                <td>
                  <strong>{scheme.name}</strong>
                  <br />
                  <span className="mono">{scheme.scheme_id}</span>
                </td>
                <td>{jurisdiction(scheme)}</td>
                <td>
                  <span
                    className={`badge-status badge-${scheme.verification_status}`}
                  >
                    {STATUS_LABEL[scheme.verification_status]}
                  </span>
                </td>
                <td>{scheme.last_verified_date ?? "—"}</td>
                <td>
                  <button
                    type="button"
                    className="btn-secondary"
                    onClick={() => onEdit(scheme)}
                  >
                    Edit
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : null}
    </div>
  );
}
