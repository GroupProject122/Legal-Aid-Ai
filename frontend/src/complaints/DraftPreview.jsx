import React from 'react';
import { AlertTriangle, Download, FileText, ShieldCheck } from 'lucide-react';

import { ApiError, downloadDocx, downloadPdf, saveBlob } from './api.js';
import { FIELD_SCHEMAS } from './IntakeForm.jsx';
import { SCENARIOS } from './ScenarioPicker.jsx';

function scenarioMeta(scenario) {
  return SCENARIOS.find((item) => item.id === scenario);
}

function formatDate(value) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function formatFieldValue(field, value) {
  if (value === undefined || value === null || value === '') return null;
  if (field.type === 'yesno') return value ? 'Yes' : 'No';
  if (field.type === 'date') return formatDate(value);
  if (field.type === 'number') return `₹${Number(value).toLocaleString('en-IN')}`;
  if (field.type === 'select') {
    return field.options.find((option) => option.value === value)?.label || value;
  }
  if (field.type === 'multiselect') {
    const values = Array.isArray(value) ? value : [];
    return values.map((item) => field.options.find((option) => option.value === item)?.label || item).join(', ') || null;
  }
  return String(value);
}

/** Read-only summary of what was submitted -- reuses the same field schema
 * IntakeForm.jsx is driven by, rather than re-deriving field labels here. */
function IntakeSummary({ scenario, intake }) {
  const fields = FIELD_SCHEMAS[scenario];
  return (
    <dl className="complaint-summary-grid">
      {fields.map((field) => {
        const display = formatFieldValue(field, intake[field.name]);
        if (display === null) return null;
        return (
          <div className="complaint-summary-item" key={field.name}>
            <dt>{field.label}</dt>
            <dd>{display}</dd>
          </div>
        );
      })}
    </dl>
  );
}

function CitationRow({ citation }) {
  return (
    <li className="complaint-citation-row">
      <span className="complaint-citation-cite">{citation.section_cite}</span>
      <span className="complaint-citation-act">{citation.act_short_title}</span>
      {citation.authority_level ? (
        <span className={`complaint-citation-authority complaint-citation-authority-${citation.authority_level}`}>
          {citation.authority_level === 'primary' ? 'Statute' : 'Official guidance'}
        </span>
      ) : null}
    </li>
  );
}

function DownloadButton({ label, icon: Icon, onDownload }) {
  const [status, setStatus] = React.useState('idle');
  const [error, setError] = React.useState(null);

  const handleClick = async () => {
    setStatus('loading');
    setError(null);
    try {
      const { blob, filename } = await onDownload();
      saveBlob(blob, filename);
      setStatus('idle');
    } catch (err) {
      setStatus('error');
      setError(err instanceof ApiError ? err.message : 'Something went wrong while generating the file.');
    }
  };

  return (
    <div className="complaint-download-button">
      <button type="button" className="ask-button" onClick={handleClick} disabled={status === 'loading'}>
        <Icon size={17} strokeWidth={1.8} />
        <span>{status === 'loading' ? 'Preparing…' : label}</span>
      </button>
      {error ? <p className="scheme-error complaint-download-error" role="alert">{error}</p> : null}
    </div>
  );
}

export function DraftPreview({ scenario, intake, draft, onBack }) {
  const meta = scenarioMeta(scenario);
  const citations = [draft.citation_used, ...(draft.additional_citations || [])].filter(Boolean);

  return (
    <section className="complaint-preview rights-panel">
      <button type="button" className="rights-back-button" onClick={onBack}>
        ← Edit this complaint
      </button>

      <header className="complaint-preview-header">
        <h3>{meta?.title || 'Draft ready'}</h3>
        <p className="complaint-preview-act">{meta?.act}</p>
      </header>

      {draft.citation_review_required ? (
        <div className="complaint-review-banner" role="alert">
          <AlertTriangle size={22} strokeWidth={1.8} />
          <div>
            <strong>This ground needs manual legal review before filing.</strong>
            {(draft.warnings || []).map((warning) => (
              <p key={warning}>{warning}</p>
            ))}
          </div>
        </div>
      ) : null}

      {draft.forum_tier ? (
        <p className="complaint-forum-tier">
          Forum: <strong>{draft.forum_tier === 'district' ? 'District' : draft.forum_tier === 'state' ? 'State' : 'National'} Consumer Disputes Redressal Commission</strong>
        </p>
      ) : null}

      <div className="complaint-preview-section">
        <h4>What you entered</h4>
        <IntakeSummary scenario={scenario} intake={intake} />
      </div>

      <div className="complaint-preview-section">
        <h4>Legal citation used</h4>
        <ul className="complaint-citation-list">
          {citations.map((citation, index) => (
            <CitationRow citation={citation} key={`${citation.section_cite}-${index}`} />
          ))}
        </ul>
      </div>

      <div className="complaint-preview-section complaint-download-section">
        <h4>Download</h4>
        <p className="scheme-note">
          The full formatted document is generated fresh from what you entered above — nothing
          is saved on the server.
        </p>
        <div className="complaint-download-row">
          <DownloadButton label="Download DOCX" icon={FileText} onDownload={() => downloadDocx(scenario, intake)} />
          <DownloadButton label="Download PDF" icon={Download} onDownload={() => downloadPdf(scenario, intake)} />
        </div>
      </div>

      <div className="response-disclaimer complaint-disclaimer">
        <ShieldCheck size={16} strokeWidth={1.7} />
        <span>This is legal information, not professional legal advice. Review the draft carefully before filing it.</span>
      </div>
    </section>
  );
}
