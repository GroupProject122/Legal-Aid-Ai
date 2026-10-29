import React from 'react';
import { ArrowLeft, ChevronRight, ExternalLink, Info, ShieldCheck } from 'lucide-react';

import { HeaderControls, PageDivider, DocumentsBackgroundArt } from '../shared/PageChrome.jsx';
import { fetchAreas, matchSchemes, SchemesError } from './api.js';

const NOTICE =
  'Information is based on official scheme guidelines and simplified for guidance. Always confirm on the official website before applying. Your answers are not saved.';

const GENDERS = [
  { value: 'female', label: 'Woman' },
  { value: 'male', label: 'Man' },
  { value: 'other', label: 'Other' }
];
const RESIDENCES = [
  { value: 'rural', label: 'Village / rural area' },
  { value: 'urban', label: 'Town or city' }
];
const SOCIAL_CATEGORIES = [
  { value: 'general', label: 'General' },
  { value: 'obc', label: 'OBC' },
  { value: 'sc', label: 'SC' },
  { value: 'st', label: 'ST' },
  { value: 'ebc', label: 'EBC' },
  { value: 'dnt', label: 'DNT (denotified tribe)' },
  { value: 'other', label: 'Other' }
];
const OCCUPATIONS = [
  { value: 'farmer', label: 'Farmer' },
  { value: 'student', label: 'Student' },
  { value: 'salaried', label: 'Salaried job' },
  { value: 'self_employed', label: 'Self-employed / own business' },
  { value: 'unemployed', label: 'Not working' },
  { value: 'artisan', label: 'Artisan or craftsperson' },
  { value: 'street_vendor', label: 'Street vendor' },
  { value: 'other', label: 'Other' }
];

const SECTIONS = [
  { group: 'likely_eligible', title: 'Likely eligible', intro: 'Your answers meet all of the conditions listed for these schemes.' },
  { group: 'might_be_eligible', title: 'You might be eligible', intro: 'Nothing you said rules these out. The authority will check the other conditions shown on each card.' },
  { group: 'check_with_authority', title: 'Check with the authority', intro: "These schemes' eligibility can't be checked from a few questions. Here is what they cover and what they may ask you." }
];

const EMPTY_ANSWERS = { age: '', gender: '', residence: '', annualFamilyIncome: '', socialCategory: '', occupation: '' };

function formatDate(isoDate) {
  const date = new Date(`${isoDate}T00:00:00`);
  if (Number.isNaN(date.getTime())) return isoDate;
  return date.toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
}

/** Moves focus to a step's heading when the step changes, so keyboard and screen-reader users land on it. */
function useFocusOnChange(step) {
  const ref = React.useRef(null);
  const first = React.useRef(true);
  React.useEffect(() => {
    if (first.current) {
      first.current = false;
      return;
    }
    ref.current?.focus();
  }, [step]);
  return ref;
}

function ChoiceField({ legend, name, options, value, onChange, hint }) {
  return (
    <fieldset className="scheme-field schemes-choice">
      <legend>{legend} <span className="schemes-optional">(optional)</span></legend>
      {hint ? <p className="scheme-note">{hint}</p> : null}
      <div className="schemes-choice-row">
        {options.map((option) => (
          <label className="scheme-radio schemes-pill" key={option.value}>
            <input type="radio" name={name} value={option.value} checked={value === option.value} onChange={() => onChange(option.value)} />
            {option.label}
          </label>
        ))}
        <label className="scheme-radio schemes-pill schemes-pill-skip">
          <input type="radio" name={name} value="" checked={!value} onChange={() => onChange('')} />
          Skip
        </label>
      </div>
    </fieldset>
  );
}

function QuestionsStep({ answers, setAnswers, onNext }) {
  const set = (field) => (value) => setAnswers((current) => ({ ...current, [field]: value }));
  const ageId = React.useId();
  const incomeId = React.useId();
  const categoryId = React.useId();
  const occupationId = React.useId();
  return (
    <form
      className="scheme-form"
      onSubmit={(event) => {
        event.preventDefault();
        onNext();
      }}
    >
      <p className="schemes-step-intro">Answer what you're comfortable with. Every question can be skipped.</p>
      <div className="scheme-field-grid">
        <div className="scheme-field">
          <label htmlFor={ageId}>Your age <span className="schemes-optional">(optional)</span></label>
          <input id={ageId} inputMode="numeric" autoComplete="off" placeholder="e.g. 32" value={answers.age} onChange={(event) => set('age')(event.target.value)} />
        </div>
        <div className="scheme-field">
          <label htmlFor={incomeId}>Family's yearly income in rupees <span className="schemes-optional">(optional)</span></label>
          <input id={incomeId} inputMode="numeric" autoComplete="off" placeholder="e.g. 1,50,000" value={answers.annualFamilyIncome} onChange={(event) => set('annualFamilyIncome')(event.target.value)} />
        </div>
      </div>
      <ChoiceField legend="Gender" name="schemes-gender" options={GENDERS} value={answers.gender} onChange={set('gender')} />
      <ChoiceField legend="Where do you live?" name="schemes-residence" options={RESIDENCES} value={answers.residence} onChange={set('residence')} />
      <div className="scheme-field-grid">
        <div className="scheme-field">
          <label htmlFor={categoryId}>Social category <span className="schemes-optional">(optional)</span></label>
          <select id={categoryId} value={answers.socialCategory} onChange={(event) => set('socialCategory')(event.target.value)}>
            <option value="">Skip</option>
            {SOCIAL_CATEGORIES.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </div>
        <div className="scheme-field">
          <label htmlFor={occupationId}>What do you do? <span className="schemes-optional">(optional)</span></label>
          <select id={occupationId} value={answers.occupation} onChange={(event) => set('occupation')(event.target.value)}>
            <option value="">Skip</option>
            {OCCUPATIONS.map((option) => <option key={option.value} value={option.value}>{option.label}</option>)}
          </select>
        </div>
      </div>
      <div className="scheme-actions">
        <button type="submit" className="ask-button">
          Next: choose areas <ChevronRight size={16} strokeWidth={2} aria-hidden="true" />
        </button>
        <button type="button" className="outline-action" onClick={() => { setAnswers(EMPTY_ANSWERS); onNext(); }}>
          Skip all questions
        </button>
      </div>
    </form>
  );
}

function AreasStep({ areas, areasError, chosen, setChosen, onBack, onShow, loading, error }) {
  const all = chosen.length === 0;
  const toggle = (id) => setChosen((current) => (current.includes(id) ? current.filter((area) => area !== id) : [...current, id]));
  return (
    <form
      className="scheme-form"
      onSubmit={(event) => {
        event.preventDefault();
        onShow();
      }}
    >
      <fieldset className="scheme-field">
        <legend>Which areas are you interested in?</legend>
        <p className="scheme-note">Leave "All areas" ticked to see every scheme.</p>
        {areasError ? <p className="scheme-error" role="alert">{areasError}</p> : null}
        <div className="schemes-area-grid">
          <label className="schemes-area">
            <input type="checkbox" checked={all} onChange={() => setChosen([])} />
            <span>All areas</span>
          </label>
          {areas.map((area) => (
            <label className="schemes-area" key={area.id}>
              <input type="checkbox" checked={chosen.includes(area.id)} onChange={() => toggle(area.id)} />
              <span>{area.label} <small>({area.count})</small></span>
            </label>
          ))}
        </div>
      </fieldset>
      {error ? <p className="scheme-error" role="alert">{error}</p> : null}
      <div className="scheme-actions">
        <button type="submit" className="ask-button" disabled={loading}>
          {loading ? 'Finding schemes…' : 'Show schemes'}
        </button>
        <button type="button" className="outline-action" onClick={onBack}>
          <ArrowLeft size={15} strokeWidth={2} aria-hidden="true" /> Back to questions
        </button>
      </div>
    </form>
  );
}

function SchemeCard({ scheme, showReason = true }) {
  return (
    <article className={`schemes-card schemes-card-${scheme.group}`}>
      <p className="schemes-card-area">{scheme.area}</p>
      <h4>{scheme.name}</h4>
      <p className="schemes-card-benefits">{scheme.benefits}</p>
      {showReason ? <p className="schemes-card-reason">{scheme.reason}</p> : null}
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
    </article>
  );
}

function ResultsStep({ data, onChange }) {
  const visible = SECTIONS.map((section) => ({ ...section, schemes: data.results.filter((scheme) => scheme.group === section.group) }));
  return (
    <div className="schemes-results">
      <button type="button" className="outline-action schemes-change" onClick={onChange}>
        <ArrowLeft size={15} strokeWidth={2} aria-hidden="true" /> Change answers or areas
      </button>
      {visible.map((section) => (
        <section className="schemes-section" key={section.group} aria-labelledby={`schemes-${section.group}`}>
          <h3 id={`schemes-${section.group}`}>
            {section.title} <span className="schemes-count">{section.schemes.length}</span>
          </h3>
          <p className="schemes-section-intro">{section.intro}</p>
          {section.schemes.length ? (
            <div className="schemes-card-grid">
              {section.schemes.map((scheme) => <SchemeCard scheme={scheme} key={scheme.id} />)}
            </div>
          ) : (
            <p className="schemes-empty">
              {section.group === 'likely_eligible'
                ? 'No scheme can be confirmed from these questions alone — every scheme also has conditions the authority checks. See the next section.'
                : 'None in the areas you chose.'}
            </p>
          )}
        </section>
      ))}
      {data.notEligible.length ? (
        <details className="schemes-not-eligible">
          <summary>Not eligible based on your answers ({data.notEligible.length})</summary>
          <div className="schemes-card-grid">
            {data.notEligible.map((scheme) => <SchemeCard scheme={scheme} key={scheme.id} />)}
          </div>
        </details>
      ) : null}
      <p className="schemes-disclaimer">
        <ShieldCheck size={16} strokeWidth={1.8} aria-hidden="true" /> {data.disclaimer}
      </p>
    </div>
  );
}

export default function SchemesPage() {
  const [step, setStep] = React.useState('questions');
  const [answers, setAnswers] = React.useState(EMPTY_ANSWERS);
  const [areas, setAreas] = React.useState([]);
  const [areasError, setAreasError] = React.useState('');
  const [chosen, setChosen] = React.useState([]);
  const [results, setResults] = React.useState(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState('');
  const headingRef = useFocusOnChange(step);

  React.useEffect(() => {
    let cancelled = false;
    fetchAreas()
      .then((payload) => { if (!cancelled) setAreas(payload.areas || []); })
      .catch((err) => { if (!cancelled) setAreasError(err instanceof SchemesError ? err.message : 'Could not load the list of areas.'); });
    return () => { cancelled = true; };
  }, []);

  const showResults = async () => {
    setLoading(true);
    setError('');
    try {
      setResults(await matchSchemes(answers, chosen));
      setStep('results');
    } catch (err) {
      setError(err instanceof SchemesError ? err.message : 'Something went wrong while finding schemes. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const stepTitle = { questions: 'Step 1 of 2: About you', areas: 'Step 2 of 2: Choose areas', results: 'Schemes for you' }[step];

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="schemes-content-frame">
        <header className="documents-page-header">
          <div className="header-ornament-line" aria-hidden="true"><span /><i>◇</i></div>
          <h2>Schemes</h2>
          <div className="header-ornament-line" aria-hidden="true"><i>◇</i><span /></div>
          <p>Find central government schemes you may be able to apply for.</p>
          <PageDivider />
        </header>

        <p className="schemes-notice" role="note">
          <Info size={18} strokeWidth={1.8} aria-hidden="true" />
          <span>{NOTICE}</span>
        </p>

        <section className="rights-panel schemes-panel">
          <h3 ref={headingRef} tabIndex={-1} className="schemes-step-title">{stepTitle}</h3>
          {step === 'questions' ? (
            <QuestionsStep answers={answers} setAnswers={setAnswers} onNext={() => setStep('areas')} />
          ) : null}
          {step === 'areas' ? (
            <AreasStep
              areas={areas}
              areasError={areasError}
              chosen={chosen}
              setChosen={setChosen}
              onBack={() => setStep('questions')}
              onShow={showResults}
              loading={loading}
              error={error}
            />
          ) : null}
          {step === 'results' && results ? <ResultsStep data={results} onChange={() => setStep('questions')} /> : null}
        </section>
      </div>
    </>
  );
}
