import React from 'react';
import { AlertTriangle, ArrowUpRight, ExternalLink, Info, Phone, Scale, ShieldAlert, ShieldQuestion } from 'lucide-react';

import { HeaderControls, PageDivider, DocumentsBackgroundArt } from '../shared/PageChrome.jsx';
import { MAX_MESSAGE_CHARS, ScamCheckError, checkMessage } from './api.js';

// Never green: the checker has no "safe" result, only "no common warning signs".
const VERDICTS = {
  high_risk: { label: 'High risk', icon: ShieldAlert, tone: 'danger' },
  warning_signs: { label: 'Warning signs found', icon: AlertTriangle, tone: 'caution' },
  no_common_signs: { label: 'Check complete', icon: ShieldQuestion, tone: 'neutral' }
};

const SCAM_TYPE_LABELS = {
  bank_kyc_fraud: 'Fake bank / KYC update',
  otp_or_credential_theft: 'OTP or password theft',
  digital_arrest_or_authority_threat: "Fake police / 'digital arrest'",
  courier_or_parcel_scam: 'Fake courier or parcel',
  electricity_bill_scam: 'Fake electricity bill',
  prize_or_refund_scam: 'Fake prize, lottery or refund',
  job_or_task_scam: 'Fake job or task offer',
  remote_access_scam: 'Remote-access app scam',
  upi_collect_scam: "UPI 'collect request' scam",
  loan_app_or_extortion: 'Loan app or extortion',
  malicious_app_link: 'Harmful app (.apk) link',
  phishing_link: 'Suspicious link'
};

function Snippet({ snippet, highlight }) {
  if (!snippet) return null;
  const valid = Array.isArray(highlight) && highlight.length === 2 && highlight[0] >= 0 && highlight[1] <= snippet.length && highlight[0] < highlight[1];
  if (!valid) return <q className="scam-snippet">{snippet}</q>;
  const [start, end] = highlight;
  return (
    <q className="scam-snippet">
      {snippet.slice(0, start)}
      <mark>{snippet.slice(start, end)}</mark>
      {snippet.slice(end)}
    </q>
  );
}

function StepText({ step }) {
  // The phone number ("1930") becomes a tel: link and a link label that already appears in the
  // text (e.g. "cybercrime.gov.in") is linked in place; otherwise the link follows the text.
  const tokens = [];
  if (step.tel && step.text.includes(step.tel)) tokens.push({ match: step.tel, href: `tel:${step.tel}`, className: 'scam-tel' });
  const linkInline = step.link && step.text.includes(step.link.label);
  if (linkInline) tokens.push({ match: step.link.label, href: step.link.href, className: 'scam-inline-link', external: true });

  let parts = [step.text];
  tokens.forEach((token) => {
    parts = parts.flatMap((part) => {
      if (typeof part !== 'string' || !part.includes(token.match)) return [part];
      const index = part.indexOf(token.match);
      return [part.slice(0, index), token, part.slice(index + token.match.length)];
    });
  });

  return (
    <span>
      {parts.map((part, index) => (typeof part === 'string' ? part : (
        <a
          key={index}
          className={part.className}
          href={part.href}
          {...(part.external ? { target: '_blank', rel: 'noreferrer' } : {})}
        >
          {part.match}
        </a>
      )))}
      {step.link && !linkInline ? (
        <>
          {' '}
          <a href={step.link.href} target="_blank" rel="noreferrer" className="scam-inline-link">
            {step.link.label}
            <ExternalLink size={13} aria-hidden="true" />
          </a>
        </>
      ) : null}
    </span>
  );
}

function sourceHref(law) {
  // A whole-document source (an official web page or press release) has no provision: link to
  // the document itself in the source viewer.
  if (!law.provision_id) return `#/rights/source/${encodeURIComponent(law.source_id)}`;
  return `#/rights/source/${encodeURIComponent(law.source_id)}/provision/${encodeURIComponent(law.provision_id)}`;
}

function lostMoneyQuestion(scamType) {
  // Deliberately does NOT include the pasted message: it may hold OTPs or account numbers.
  const kind = SCAM_TYPE_LABELS[scamType];
  return kind
    ? `I lost money after a suspicious message that looked like a ${kind.toLowerCase()} scam. What should I do now?`
    : 'I lost money after a suspicious SMS/WhatsApp message. What should I do now?';
}

function ResultCard({ result, headingRef }) {
  const verdict = VERDICTS[result.verdict] || VERDICTS.no_common_signs;
  const VerdictIcon = verdict.icon;
  const typeLabel = SCAM_TYPE_LABELS[result.scam_type];

  return (
    <section className={`rights-panel scam-result scam-result-${verdict.tone}`} aria-labelledby="scam-result-heading">
      <div className="scam-verdict">
        <VerdictIcon size={30} strokeWidth={1.7} aria-hidden="true" />
        <div>
          <h3 id="scam-result-heading" tabIndex={-1} ref={headingRef}>{verdict.label}</h3>
          <p>{result.headline}</p>
          {typeLabel ? <p className="scam-type">Looks like: <strong>{typeLabel}</strong></p> : null}
          {result.ai_explanation ? <p className="scam-ai-explanation">{result.ai_explanation}</p> : null}
        </div>
      </div>

      {result.note ? (
        <p className="scam-note" role="status"><Info size={16} aria-hidden="true" /> {result.note}</p>
      ) : null}

      {result.signs_found?.length ? (
        <div className="scam-section">
          <h4>Warning signs in this message</h4>
          <ul className="scam-sign-list">
            {result.signs_found.map((sign) => (
              <li key={sign.rule_id} className={`scam-sign scam-sign-${sign.strength}`}>
                <p>
                  {sign.explanation}
                  {sign.source === 'ai' ? <span className="scam-sign-source"> (found by AI)</span> : null}
                </p>
                <Snippet snippet={sign.snippet} highlight={sign.highlight} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="scam-section">
        <h4>What to do</h4>
        <ol className="rights-step-list scam-steps">
          {result.what_to_do.map((step) => (
            <li key={step.text}>
              <StepText step={step} />
              {step.sources?.length ? (
                <span className="scam-step-sources">
                  {' '}Source:{' '}
                  {step.sources.map((source, index) => (
                    <React.Fragment key={`${source.source_id}-${source.provision_id || 'document'}`}>
                      {index ? ', ' : ''}
                      <a href={sourceHref(source)}>{source.label}</a>
                    </React.Fragment>
                  ))}
                </span>
              ) : null}
            </li>
          ))}
        </ol>
      </div>

      {result.laws_that_may_apply?.length ? (
        <div className="scam-section">
          <h4>Laws that may apply</h4>
          <ul className="scam-law-list">
            {result.laws_that_may_apply.map((law) => (
              <li key={`${law.source_id}-${law.provision_id}`}>
                <a href={sourceHref(law)} className="scam-law-link">
                  <Scale size={15} aria-hidden="true" />
                  {law.label}, {law.act}
                  <ArrowUpRight size={14} aria-hidden="true" />
                </a>
                <p>{law.why}</p>
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="scam-actions">
        <button
          type="button"
          className="helpline-action"
          onClick={() => { window.location.hash = `#/ask?q=${encodeURIComponent(lostMoneyQuestion(result.scam_type))}`; }}
        >
          I lost money -- what now?
        </button>
        <a className="helpline-action helpline-action-visit" href="#/helplines">
          <Phone size={15} aria-hidden="true" />
          Helplines
        </a>
      </div>

      <p className="helpline-disclaimer scam-disclaimer">{result.disclaimer}</p>
    </section>
  );
}

export default function ScamCheck() {
  const [message, setMessage] = React.useState('');
  const [result, setResult] = React.useState(null);
  const [error, setError] = React.useState('');
  const [isChecking, setIsChecking] = React.useState(false);
  const headingRef = React.useRef(null);

  React.useEffect(() => {
    if (result) headingRef.current?.focus();
  }, [result]);

  const trimmedLength = message.trim().length;
  const tooLong = message.length > MAX_MESSAGE_CHARS;

  const handleSubmit = async (event) => {
    event.preventDefault();
    if (!trimmedLength || tooLong || isChecking) return;
    setIsChecking(true);
    setError('');
    setResult(null);
    try {
      setResult(await checkMessage(message));
    } catch (err) {
      setError(err instanceof ScamCheckError ? err.message : 'The message could not be checked right now.');
    } finally {
      setIsChecking(false);
    }
  };

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="rights-content-frame">
        <header className="documents-page-header">
          <div className="header-ornament-line"><span /><i>◇</i></div>
          <h2>Check a Message</h2>
          <div className="header-ornament-line"><i>◇</i><span /></div>
          <p>Paste a suspicious SMS, WhatsApp or email message to see common warning signs and what to do next.</p>
          <PageDivider />
        </header>

        <form className="rights-panel scam-form" onSubmit={handleSubmit}>
          <label htmlFor="scam-message" className="scam-label">Paste the message here</label>
          <textarea
            id="scam-message"
            className="scam-textarea"
            value={message}
            onChange={(event) => setMessage(event.target.value)}
            rows={8}
            maxLength={MAX_MESSAGE_CHARS + 200}
            placeholder="e.g. Dear customer, your account will be blocked today. Update KYC at …"
            aria-describedby="scam-privacy scam-count"
            autoComplete="off"
            spellCheck={false}
          />
          <div className="scam-form-footer">
            <p id="scam-privacy" className="scam-privacy">We don't save your message, and we never open links in it.</p>
            <span id="scam-count" className={`scam-count ${tooLong ? 'scam-count-over' : ''}`}>
              {message.length.toLocaleString('en-IN')} / {MAX_MESSAGE_CHARS.toLocaleString('en-IN')}
            </span>
          </div>
          <button type="submit" className="ask-button scam-submit" disabled={!trimmedLength || tooLong || isChecking}>
            {isChecking ? 'Checking…' : 'Check'}
          </button>
          {error ? <p className="scam-error" role="alert">{error}</p> : null}
        </form>

        <div aria-live="polite">
          {result ? <ResultCard result={result} headingRef={headingRef} /> : null}
        </div>
      </div>
    </>
  );
}
