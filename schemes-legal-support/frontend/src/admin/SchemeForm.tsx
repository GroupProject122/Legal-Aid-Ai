import { useMemo, useState, type FormEvent } from "react";

import { ApiError, createScheme, updateScheme } from "../api";
import { INDIAN_STATES } from "../options";
import type {
  ConditionNode,
  Scheme,
  SchemeInput,
  SchemeLevel,
  VerificationStatus,
} from "../types";
import { ConditionBuilder } from "./ConditionBuilder";
import { defaultLeaf } from "./conditionMeta";

const VERIFICATION_STATUSES: VerificationStatus[] = [
  "needs_review",
  "stale",
  "verified",
];

function emptyHard(): ConditionNode {
  return { op: "AND", children: [defaultLeaf()] };
}

interface SchemeFormProps {
  mode: "create" | "edit";
  initial?: Scheme;
  onSaved: (scheme: Scheme) => void;
  onCancel: () => void;
}

export function SchemeForm({ mode, initial, onSaved, onCancel }: SchemeFormProps) {
  const [schemeId, setSchemeId] = useState(initial?.scheme_id ?? "");
  const [name, setName] = useState(initial?.name ?? "");
  const [shortSummary, setShortSummary] = useState(initial?.short_summary ?? "");
  const [level, setLevel] = useState<SchemeLevel>(initial?.level ?? "Central");
  const [stateVal, setStateVal] = useState(initial?.state ?? "");
  const [category, setCategory] = useState((initial?.category ?? []).join(", "));
  const [benefits, setBenefits] = useState(initial?.benefits ?? "");
  const [documents, setDocuments] = useState(
    (initial?.documents_required ?? []).join("\n"),
  );
  const [applicationProcess, setApplicationProcess] = useState(
    initial?.application_process ?? "",
  );
  const [officialSourceUrl, setOfficialSourceUrl] = useState(
    initial?.official_source_url ?? "",
  );
  const [applyUrl, setApplyUrl] = useState(initial?.apply_url ?? "");
  const [lastVerifiedDate, setLastVerifiedDate] = useState(
    initial?.last_verified_date ?? "",
  );
  const [verificationStatus, setVerificationStatus] =
    useState<VerificationStatus>(initial?.verification_status ?? "needs_review");

  const [hard, setHard] = useState<ConditionNode>(
    initial?.eligibility.hard ?? emptyHard(),
  );
  const [hasSoft, setHasSoft] = useState<boolean>(
    Boolean(initial?.eligibility.soft),
  );
  const [soft, setSoft] = useState<ConditionNode>(
    initial?.eligibility.soft ?? defaultLeaf(),
  );

  const [saving, setSaving] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);
  const [savedNote, setSavedNote] = useState<string | null>(null);

  const input: SchemeInput = useMemo(
    () => ({
      scheme_id: schemeId.trim(),
      name: name.trim(),
      short_summary: shortSummary.trim(),
      level,
      state: level === "State" ? stateVal.trim() || null : null,
      category: category
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean),
      eligibility: { hard, soft: hasSoft ? soft : null },
      benefits: benefits.trim(),
      documents_required: documents
        .split("\n")
        .map((s) => s.trim())
        .filter(Boolean),
      application_process: applicationProcess.trim(),
      official_source_url: officialSourceUrl.trim(),
      apply_url: applyUrl.trim() || null,
      last_verified_date: lastVerifiedDate || null,
      verification_status: verificationStatus,
    }),
    [
      schemeId,
      name,
      shortSummary,
      level,
      stateVal,
      category,
      hard,
      hasSoft,
      soft,
      benefits,
      documents,
      applicationProcess,
      officialSourceUrl,
      applyUrl,
      lastVerifiedDate,
      verificationStatus,
    ],
  );

  const verifiedWithoutDate =
    verificationStatus === "verified" && !lastVerifiedDate;

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (saving) return;
    setSaving(true);
    setErrors([]);
    setSavedNote(null);
    try {
      const saved =
        mode === "create"
          ? await createScheme(input)
          : await updateScheme(initial?.scheme_id ?? input.scheme_id, input);
      setSavedNote(`Saved "${saved.name}".`);
      onSaved(saved);
    } catch (err) {
      if (err instanceof ApiError && Array.isArray(err.details)) {
        setErrors(err.details as string[]);
      } else if (err instanceof ApiError) {
        setErrors([`${err.message}${err.status ? ` (HTTP ${err.status})` : ""}`]);
      } else {
        setErrors([err instanceof Error ? err.message : "Save failed."]);
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    // noValidate: the backend's validateScheme is the single source of truth,
    // so we don't want native per-field popups fragmenting the error list.
    <form className="scheme-form" onSubmit={handleSubmit} noValidate>
      <div className="form-topbar">
        <h2>{mode === "create" ? "New scheme" : `Edit: ${initial?.name}`}</h2>
        <button type="button" className="btn-link" onClick={onCancel}>
          ← Back to list
        </button>
      </div>

      {errors.length > 0 ? (
        <div className="errors-panel" role="alert">
          <h3>Fix these {errors.length} problem(s) before saving</h3>
          <ul>
            {errors.map((e, i) => (
              <li key={i}>{e}</li>
            ))}
          </ul>
        </div>
      ) : null}
      {savedNote ? <p className="saved-note">{savedNote}</p> : null}

      <fieldset>
        <legend>Basics</legend>
        <div className="form-grid">
          <label className="field">
            <span>Scheme ID (slug)</span>
            <input
              value={schemeId}
              onChange={(e) => setSchemeId(e.target.value)}
              placeholder="pm-kisan"
              readOnly={mode === "edit"}
            />
            {mode === "edit" ? (
              <small className="hint">ID can't be changed here.</small>
            ) : null}
          </label>

          <label className="field">
            <span>Name</span>
            <input value={name} onChange={(e) => setName(e.target.value)} />
          </label>

          <label className="field">
            <span>Level</span>
            <select
              value={level}
              onChange={(e) => setLevel(e.target.value as SchemeLevel)}
            >
              <option value="Central">Central</option>
              <option value="State">State</option>
            </select>
          </label>

          {level === "State" ? (
            <label className="field">
              <span>State</span>
              <select
                value={stateVal}
                onChange={(e) => setStateVal(e.target.value)}
              >
                <option value="">— choose —</option>
                {INDIAN_STATES.map((o) => (
                  <option key={o.value} value={o.value}>
                    {o.label}
                  </option>
                ))}
              </select>
            </label>
          ) : null}

          <label className="field wide">
            <span>Short summary</span>
            <input
              value={shortSummary}
              onChange={(e) => setShortSummary(e.target.value)}
            />
          </label>

          <label className="field wide">
            <span>Category tags (comma-separated)</span>
            <input
              value={category}
              onChange={(e) => setCategory(e.target.value)}
              placeholder="agriculture, income-support"
            />
          </label>
        </div>
      </fieldset>

      <fieldset>
        <legend>Eligibility — hard conditions (the gate)</legend>
        <ConditionBuilder node={hard} onChange={setHard} />
      </fieldset>

      <fieldset>
        <legend>Eligibility — soft conditions (ranking only)</legend>
        <label className="check">
          <input
            type="checkbox"
            checked={hasSoft}
            onChange={(e) => setHasSoft(e.target.checked)}
          />
          This scheme has soft conditions
        </label>
        {hasSoft ? (
          <ConditionBuilder node={soft} onChange={setSoft} />
        ) : (
          <p className="hint">No soft conditions — sent as <code>null</code>.</p>
        )}
      </fieldset>

      <fieldset>
        <legend>Content</legend>
        <div className="form-grid">
          <label className="field wide">
            <span>Benefits</span>
            <textarea
              rows={3}
              value={benefits}
              onChange={(e) => setBenefits(e.target.value)}
            />
          </label>
          <label className="field wide">
            <span>Documents required (one per line)</span>
            <textarea
              rows={4}
              value={documents}
              onChange={(e) => setDocuments(e.target.value)}
            />
          </label>
          <label className="field wide">
            <span>Application process</span>
            <textarea
              rows={3}
              value={applicationProcess}
              onChange={(e) => setApplicationProcess(e.target.value)}
            />
          </label>
          <label className="field wide">
            <span>Official source URL</span>
            <input
              type="url"
              value={officialSourceUrl}
              onChange={(e) => setOfficialSourceUrl(e.target.value)}
              placeholder="https://…"
            />
          </label>
          <label className="field wide">
            <span>Apply URL (optional)</span>
            <input
              type="url"
              value={applyUrl}
              onChange={(e) => setApplyUrl(e.target.value)}
              placeholder="https://… (leave blank for none)"
            />
          </label>
        </div>
      </fieldset>

      <fieldset>
        <legend>Verification</legend>
        <div className="form-grid">
          <label className="field">
            <span>Last verified date</span>
            <input
              type="date"
              value={lastVerifiedDate}
              onChange={(e) => setLastVerifiedDate(e.target.value)}
            />
          </label>
          <label className="field">
            <span>Verification status</span>
            <select
              value={verificationStatus}
              onChange={(e) =>
                setVerificationStatus(e.target.value as VerificationStatus)
              }
            >
              {VERIFICATION_STATUSES.map((s) => (
                <option key={s} value={s}>
                  {s.replace("_", " ")}
                </option>
              ))}
            </select>
          </label>
          <div className="field">
            <span>&nbsp;</span>
            <button
              type="button"
              className="btn-secondary"
              disabled={!lastVerifiedDate || verificationStatus === "verified"}
              onClick={() => setVerificationStatus("verified")}
            >
              Mark as verified
            </button>
            {!lastVerifiedDate ? (
              <small className="hint">Set the last verified date first.</small>
            ) : null}
          </div>
        </div>
        {verifiedWithoutDate ? (
          <p className="inline-warn">
            “verified” needs a last verified date — the backend will reject this.
          </p>
        ) : null}
      </fieldset>

      <details className="json-preview">
        <summary>Preview the JSON that will be sent</summary>
        <pre>{JSON.stringify(input, null, 2)}</pre>
      </details>

      <div className="form-actions">
        <button type="submit" className="btn-primary" disabled={saving}>
          {saving ? "Saving…" : mode === "create" ? "Create scheme" : "Save changes"}
        </button>
        <button type="button" className="btn-link" onClick={onCancel}>
          Cancel
        </button>
      </div>
    </form>
  );
}
