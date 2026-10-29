import React from 'react';
import { ChevronDown, ExternalLink } from 'lucide-react';

import { buildCheckAnswers, checkScheme, SchemesError } from './api.js';
import { benefitSummary, GROUP_LABELS } from './cardText.js';

function formatDate(isoDate) {
  const date = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

/** The "You might be eligible" card's quick questions: answering re-checks this one scheme. */
function QuickQuestions({ scheme, profileAnswers, onChecked }) {
  const [cardAnswers, setCardAnswers] = React.useState({});
  const [busy, setBusy] = React.useState(false);
  const [error, setError] = React.useState('');
  const baseId = React.useId();
  const set = (field, value) => setCardAnswers((current) => ({ ...current, [field]: value }));
  const answered = scheme.questions.some((question) => (cardAnswers[question.field] ?? '') !== '');

  const submit = async (event) => {
    event.preventDefault();
    setBusy(true);
    setError('');
    try {
      onChecked(await checkScheme(scheme.id, buildCheckAnswers(profileAnswers, cardAnswers, scheme.questions)));
    } catch (err) {
      setError(err instanceof SchemesError ? err.message : 'Could not check this scheme. Please try again.');
      setBusy(false);
    }
  };

  return (
    <form className="schemes-quick" onSubmit={submit}>
      <p className="schemes-quick-title">Quick questions</p>
      {scheme.questions.map((question, index) => {
        const id = `${baseId}-${index}`;
        if (question.type === 'number') {
          return (
            <div className="schemes-quick-row" key={question.field}>
              <label htmlFor={id}>{question.question}</label>
              <input id={id} inputMode="decimal" autoComplete="off" value={cardAnswers[question.field] ?? ''}
                onChange={(event) => set(question.field, event.target.value)}
                placeholder={question.unit === 'rupees' ? 'e.g. 1,50,000' : question.unit} />
            </div>
          );
        }
        const options = question.type === 'yes_no' ? [{ value: 'yes', label: 'Yes' }, { value: 'no', label: 'No' }] : question.options;
        return (
          <fieldset className="schemes-quick-row" key={question.field}>
            <legend>{question.question}</legend>
            <div className="schemes-choice-row">
              {options.map((option) => (
                <label className="scheme-radio schemes-pill" key={option.value}>
                  <input type="radio" name={id} value={option.value} checked={cardAnswers[question.field] === option.value}
                    onChange={() => set(question.field, option.value)} />
                  {option.label}
                </label>
              ))}
            </div>
          </fieldset>
        );
      })}
      {error ? <p className="scheme-error" role="alert">{error}</p> : null}
      <button type="submit" className="outline-action schemes-quick-submit" disabled={!answered || busy}>
        {busy ? 'Checking…' : 'Check this scheme'}
      </button>
    </form>
  );
}

/**
 * One result card, collapsed by default to: category, name (still a heading), result badge, a
 * one-line benefit summary and a chevron button. The button (or a click anywhere on the header)
 * shows the details. Open/closed is owned by the page, so "Expand all"/"Collapse all" work and a
 * new search starts collapsed. The details stay rendered while hidden, so quick-question answers
 * survive collapsing.
 */
export default function SchemeCard({ scheme, open = false, onToggle, profileAnswers, onChecked }) {
  const baseId = React.useId();
  const detailsId = `${baseId}-details`;
  return (
    <article className={`schemes-card schemes-card-${scheme.group}${open ? ' is-open' : ''}`}>
      <div className="schemes-card-header" onClick={onToggle}>
        <div className="schemes-card-head-text">
          <p className="schemes-card-area">{scheme.area}</p>
          <h4>{scheme.name}</h4>
          <span className={`schemes-badge schemes-badge-${scheme.group}`}>{GROUP_LABELS[scheme.group]}</span>
          {open ? null : <p className="schemes-card-summary">{benefitSummary(scheme.benefits)}</p>}
        </div>
        <button
          type="button"
          className="schemes-card-toggle"
          aria-expanded={open}
          aria-controls={detailsId}
          aria-label={`${open ? 'Hide' : 'Show'} details for ${scheme.name}`}
        >
          <ChevronDown size={20} strokeWidth={2} aria-hidden="true" />
        </button>
      </div>
      <div id={detailsId} className="schemes-card-details" hidden={!open}>
        <p className="schemes-card-benefits">{scheme.benefits}</p>
        <p className="schemes-card-reason">{scheme.reason}</p>
        {scheme.group === 'might_be_eligible' && scheme.questions?.length && onChecked ? (
          <QuickQuestions scheme={scheme} profileAnswers={profileAnswers} onChecked={onChecked} />
        ) : null}
        {scheme.authorityChecks?.length ? (
          <div className="schemes-authority">
            <p className="schemes-card-ask-title">The authority will also check</p>
            <ul>
              {scheme.authorityChecks.map((check) => (
                <li key={check.condition}><strong>{check.condition[0].toUpperCase() + check.condition.slice(1)}.</strong> {check.explanation}</li>
              ))}
            </ul>
          </div>
        ) : null}
        {scheme.group === 'check_with_authority' ? (
          <div className="schemes-card-ask">
            <p><strong>In short:</strong> {scheme.eligibilitySummary}</p>
            {scheme.whatTheyMayAsk.length ? (
              <>
                <p className="schemes-card-ask-title">What they may ask you</p>
                <ul>{scheme.whatTheyMayAsk.map((item) => <li key={item}>{item}</li>)}</ul>
              </>
            ) : null}
          </div>
        ) : scheme.whatTheyMayAsk.length ? (
          <details className="schemes-card-more">
            <summary>What they may ask you</summary>
            <ul>{scheme.whatTheyMayAsk.map((item) => <li key={item}>{item}</li>)}</ul>
          </details>
        ) : null}
        <div className="schemes-card-footer">
          <a className="schemes-official" href={scheme.officialUrl} target="_blank" rel="noopener noreferrer">
            Official website <ExternalLink size={14} strokeWidth={2} aria-hidden="true" />
            <span className="sr-only"> (opens in a new tab)</span>
          </a>
          <span className={`schemes-verified ${scheme.lastVerified ? '' : 'is-unverified'}`.trim()}>
            {scheme.lastVerified ? `Last verified: ${formatDate(scheme.lastVerified)}` : 'Not yet verified'}
          </span>
        </div>
      </div>
    </article>
  );
}
