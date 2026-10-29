import React from 'react';
import { ExternalLink, Phone } from 'lucide-react';

import { HeaderControls, PageDivider, DocumentsBackgroundArt } from '../shared/PageChrome.jsx';
import helplines, { HELPLINE_DOMAINS, TENANCY_NOTE, LAST_VERIFIED } from './helplinesData.js';

function formatDate(isoDate) {
  const date = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

function HelplineCard({ entry }) {
  return (
    <article className="helpline-card">
      <h4>{entry.name}</h4>
      <p className="helpline-handles">{entry.handles}</p>
      <p className="helpline-when">
        <strong>When to use:</strong> {entry.whenToUse}
      </p>
      <div className="helpline-actions">
        {entry.number ? (
          <a className="helpline-action helpline-action-call" href={`tel:${entry.number}`}>
            <Phone size={16} strokeWidth={2} />
            Call {entry.number}
          </a>
        ) : null}
        {entry.website ? (
          <a
            className="helpline-action helpline-action-visit"
            href={entry.website}
            target="_blank"
            rel="noreferrer"
          >
            <ExternalLink size={15} strokeWidth={2} />
            Visit website
          </a>
        ) : null}
      </div>
      <p className="helpline-verified">
        Source verified {formatDate(entry.lastVerified)} —{' '}
        <a href={entry.sourceUrl} target="_blank" rel="noreferrer">
          official source
        </a>
      </p>
    </article>
  );
}

function TenancySection() {
  return (
    <section className="rights-panel helpline-tenancy-panel">
      <h3>{TENANCY_NOTE.heading}</h3>
      <p>{TENANCY_NOTE.body}</p>
      <div className="helpline-tenancy-links">
        {TENANCY_NOTE.links.map((link) => (
          <div className="helpline-tenancy-link" key={link.id}>
            <span className="helpline-tenancy-link-name">{link.name}</span>
            <div className="helpline-actions">
              {link.number ? (
                <a className="helpline-action helpline-action-call" href={`tel:${link.number}`}>
                  <Phone size={16} strokeWidth={2} />
                  Call {link.number}
                </a>
              ) : null}
              <a
                className="helpline-action helpline-action-visit"
                href={link.website}
                target="_blank"
                rel="noreferrer"
              >
                <ExternalLink size={15} strokeWidth={2} />
                Visit website
              </a>
            </div>
          </div>
        ))}
      </div>
      <p className="helpline-verified">Source verified {formatDate(TENANCY_NOTE.lastVerified)}.</p>
    </section>
  );
}

export default function Helplines() {
  const [activeFilter, setActiveFilter] = React.useState('all');

  const visibleDomains =
    activeFilter === 'all' ? HELPLINE_DOMAINS : HELPLINE_DOMAINS.filter((domain) => domain.id === activeFilter);

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="rights-content-frame">
        <header className="documents-page-header">
          <div className="header-ornament-line"><span /><i>◇</i></div>
          <h2>Helplines</h2>
          <div className="header-ornament-line"><i>◇</i><span /></div>
          <p>Official Indian helplines and complaint portals for the problems this app covers.</p>
          <PageDivider />
        </header>

        <div className="helpline-filter-row" role="group" aria-label="Filter helplines by domain">
          <button
            type="button"
            className={`helpline-filter-chip ${activeFilter === 'all' ? 'helpline-filter-chip-active' : ''}`}
            onClick={() => setActiveFilter('all')}
          >
            All
          </button>
          {HELPLINE_DOMAINS.map((domain) => (
            <button
              type="button"
              key={domain.id}
              className={`helpline-filter-chip ${activeFilter === domain.id ? 'helpline-filter-chip-active' : ''}`}
              onClick={() => setActiveFilter(domain.id)}
            >
              {domain.label}
            </button>
          ))}
        </div>

        {visibleDomains.map((domain) => {
          const entries = helplines.filter((entry) => entry.domain === domain.id);
          if (entries.length === 0) return null;
          return (
            <section className="rights-panel" key={domain.id}>
              <h3>{domain.label}</h3>
              <div className="helpline-grid">
                {entries.map((entry) => (
                  <HelplineCard entry={entry} key={entry.id} />
                ))}
              </div>
            </section>
          );
        })}

        {/* Always shown regardless of filter -- there's no "Tenancy" chip (nothing to filter
            to), but the honest explanation of that gap shouldn't be hidden behind "All". */}
        <TenancySection />

        <p className="helpline-disclaimer">
          Legal Aid AI is not connected to these services; numbers were verified on {formatDate(LAST_VERIFIED)}.
          Check the official site if a number does not work.
        </p>
      </div>
    </>
  );
}
