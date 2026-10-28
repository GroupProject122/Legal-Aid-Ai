import React from 'react';
import { Download, FileText, ShieldCheck, X } from 'lucide-react';

import { saveBlob } from '../complaints/api.js';
import { CaseFileError, downloadCaseFile } from './api.js';

const NOT_LEGAL_ADVICE_NOTICE =
  'This is legal information to help you explain your situation. It is not legal advice and has not been reviewed by a lawyer.';
const NO_ANSWERS_HINT = 'Available once Legal Aid AI has answered a question in this case.';

/**
 * "Download case file" trigger + confirmation dialog. `compact` renders the
 * icon-only square button used in My Cases' card actions; otherwise the pill
 * used in the Ask page toolbar. With no answers yet the button stays
 * focusable (aria-disabled, not `disabled`) so keyboard and pointer users can
 * both reach the explanation of why it's unavailable.
 */
export function CaseFileButton({ caseId, caseTitle, hasAnswers, compact = false }) {
  const [open, setOpen] = React.useState(false);
  const triggerRef = React.useRef(null);
  const hintId = React.useId();

  const handleClick = () => {
    if (hasAnswers) setOpen(true);
  };
  const close = () => {
    setOpen(false);
    triggerRef.current?.focus();
  };

  const label = `Download case file${caseTitle ? ` for ${caseTitle}` : ''}`;
  return (
    <span className="case-file-trigger">
      <button
        ref={triggerRef}
        type="button"
        className={compact ? 'case-file-icon-button' : 'outline-action case-file-pill'}
        aria-label={compact ? label : undefined}
        aria-disabled={!hasAnswers || undefined}
        aria-describedby={hasAnswers ? undefined : hintId}
        title={hasAnswers ? label : NO_ANSWERS_HINT}
        onClick={handleClick}
      >
        <Download size={compact ? 17 : 15} strokeWidth={1.8} aria-hidden="true" />
        {compact ? null : <span>Download case file</span>}
      </button>
      {!hasAnswers ? <span id={hintId} role="tooltip" className="case-file-tooltip">{NO_ANSWERS_HINT}</span> : null}
      {open ? <CaseFileDialog caseId={caseId} caseTitle={caseTitle} onClose={close} /> : null}
    </span>
  );
}

function CaseFileDialog({ caseId, caseTitle, onClose }) {
  const [status, setStatus] = React.useState('idle');
  const [error, setError] = React.useState('');
  const [pdfUnavailable, setPdfUnavailable] = React.useState(false);
  const dialogRef = React.useRef(null);
  const pdfButtonRef = React.useRef(null);
  const docxButtonRef = React.useRef(null);
  const titleId = React.useId();
  const noticeId = React.useId();
  const busy = status !== 'idle';

  React.useEffect(() => {
    pdfButtonRef.current?.focus();
  }, []);

  // After a PDF 503 the focused PDF button becomes disabled, which would drop focus to <body>;
  // move it to the Word button once the re-render (re-enabling that button) has committed.
  React.useEffect(() => {
    if (pdfUnavailable) docxButtonRef.current?.focus();
  }, [pdfUnavailable]);

  // Escape closes; Tab stays inside the dialog.
  const handleKeyDown = (event) => {
    if (event.key === 'Escape' && !busy) {
      event.stopPropagation();
      onClose();
      return;
    }
    if (event.key !== 'Tab') return;
    const focusable = [...dialogRef.current.querySelectorAll('button:not([disabled])')];
    if (!focusable.length) return;
    const first = focusable[0];
    const last = focusable[focusable.length - 1];
    if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    } else if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    }
  };

  const download = async (format) => {
    setStatus(format);
    setError('');
    try {
      const { blob, filename } = await downloadCaseFile(caseId, format);
      saveBlob(blob, filename);
      onClose();
    } catch (err) {
      setStatus('idle');
      if (err instanceof CaseFileError && format === 'pdf' && err.pdfUnavailable) {
        setPdfUnavailable(true);
        setError('PDF isn’t available on this server right now. You can download the Word (.docx) version instead — it has the same content.');
      } else {
        setError(err instanceof CaseFileError ? err.message : 'Something went wrong while creating the case file.');
      }
    }
  };

  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={busy ? undefined : onClose}>
      <section
        ref={dialogRef}
        className="attachment-modal document-action-modal case-file-dialog"
        role="dialog"
        aria-modal="true"
        aria-labelledby={titleId}
        aria-describedby={noticeId}
        onMouseDown={(event) => event.stopPropagation()}
        onKeyDown={handleKeyDown}
      >
        <button type="button" className="modal-close" aria-label="Close case file dialog" onClick={onClose} disabled={busy}>
          <X size={20} />
        </button>
        <div className="modal-emblem">
          <FileText size={30} strokeWidth={1.55} />
        </div>
        <h3 id={titleId}>Download case file</h3>
        {caseTitle ? <p className="case-file-case-title">{caseTitle}</p> : null}
        <div className="case-file-notice" id={noticeId}>
          <ShieldCheck size={18} strokeWidth={1.7} aria-hidden="true" />
          <p>{NOT_LEGAL_ADVICE_NOTICE}</p>
        </div>
        <p className="case-file-contents">
          A summary of your situation, the facts you gave, a timeline, the legal sources Legal Aid AI checked, where to go,
          an evidence checklist and free legal help contacts — to take to a lawyer or your District Legal Services Authority.
          Sensitive numbers like OTPs and passwords are removed.
        </p>
        {error ? <p className="document-error" role="alert">{error}</p> : null}
        <div className="document-dialog-actions case-file-actions">
          <button
            ref={pdfButtonRef}
            type="button"
            className="case-open-button"
            onClick={() => download('pdf')}
            disabled={busy || pdfUnavailable}
          >
            <Download size={16} strokeWidth={1.8} aria-hidden="true" />
            {status === 'pdf' ? 'Preparing…' : 'Download PDF'}
          </button>
          <button
            ref={docxButtonRef}
            type="button"
            className={pdfUnavailable ? 'case-open-button' : 'document-outline-button'}
            onClick={() => download('docx')}
            disabled={busy}
          >
            {status === 'docx' ? 'Preparing…' : 'Word (.docx)'}
          </button>
        </div>
      </section>
    </div>
  );
}
