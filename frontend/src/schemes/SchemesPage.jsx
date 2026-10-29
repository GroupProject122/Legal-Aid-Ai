import React from 'react';
import { ArrowLeft, ChevronRight, ShieldCheck } from 'lucide-react';

import { HeaderControls, PageDivider, DocumentsBackgroundArt } from '../shared/PageChrome.jsx';
import { fetchAreas, matchSchemes, SchemesError } from './api.js';
import { EMPTY_ANSWERS } from './questions.js';
import SchemeCard from './SchemeCard.jsx';

const GENDERS = [
  { value: 'female', label: 'Woman' },
  { value: 'male', label: 'Man' },
  { value: 'other', label: 'Other' }
];
const RESIDENCES = [
  { value: 'rural', label: 'Village / rural area' },
  { value: 'urban', label: 'Town or city' }
];
const SECTIONS = [
  { group: 'likely_eligible', title: 'Likely eligible', intro: 'Your answers meet all of the conditions listed for these schemes.' },
  { group: 'might_be_eligible', title: 'You might be eligible', intro: 'Nothing you said rules these out. The authority will check the other conditions shown on each card.' },
  { group: 'check_with_authority', title: 'Check with the authority', intro: "These schemes' eligibility can't be checked from a few questions. Here is what they cover and what they may ask you." }
];

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

const SECTION_TITLES = {
  likely_eligible: 'Likely eligible',
  might_be_eligible: 'You might be eligible',
  check_with_authority: 'Check with the authority',
  not_eligible: 'Not eligible based on your answers'
};

/** "Expand all" / "Collapse all" for one section's cards. */
function SectionToggles({ schemes, setOpen, label }) {
  const ids = schemes.map((scheme) => scheme.id);
  return (
    <div className="schemes-section-toggles" role="group" aria-label={`Show or hide details: ${label}`}>
      <button type="button" className="outline-action schemes-expand-all" onClick={() => setOpen(ids, true)}>Expand all</button>
      <button type="button" className="outline-action schemes-collapse-all" onClick={() => setOpen(ids, false)}>Collapse all</button>
    </div>
  );
}

function ResultsStep({ data, onChange, profileAnswers, onSchemeChecked, announcement, openIds, toggleOpen, setOpen }) {
  const byName = (a, b) => a.name.localeCompare(b.name, 'en', { sensitivity: 'base' });
  const visible = SECTIONS.map((section) => ({ ...section, schemes: data.results.filter((scheme) => scheme.group === section.group).sort(byName) }));
  return (
    <div className="schemes-results">
      <p className="sr-only" aria-live="polite">{announcement}</p>
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
            <>
              <SectionToggles schemes={section.schemes} setOpen={setOpen} label={section.title} />
              <div className="schemes-card-grid">
                {section.schemes.map((scheme) => (
                  <SchemeCard scheme={scheme} key={`${scheme.id}-${scheme.group}`} open={openIds.has(scheme.id)}
                    onToggle={() => toggleOpen(scheme.id)} profileAnswers={profileAnswers} onChecked={onSchemeChecked} />
                ))}
              </div>
            </>
          ) : (
            <p className="schemes-empty">
              {section.group === 'likely_eligible'
                ? 'None yet. Answer the quick questions on the cards below to check a scheme further.'
                : 'None in the areas you chose.'}
            </p>
          )}
        </section>
      ))}
      {data.notEligible.length ? (
        <details className="schemes-not-eligible">
          <summary>Not eligible based on your answers ({data.notEligible.length})</summary>
          <SectionToggles schemes={data.notEligible} setOpen={setOpen} label="Not eligible" />
          <div className="schemes-card-grid">
            {[...data.notEligible].sort(byName).map((scheme) => (
              <SchemeCard scheme={scheme} key={scheme.id} open={openIds.has(scheme.id)} onToggle={() => toggleOpen(scheme.id)} />
            ))}
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
  const [announcement, setAnnouncement] = React.useState('');
  // Which result cards are expanded. Not remembered: every new search starts with all collapsed.
  const [openIds, setOpenIds] = React.useState(() => new Set());
  const toggleOpen = (id) => setOpenIds((current) => {
    const next = new Set(current);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    return next;
  });
  const setOpen = (ids, open) => setOpenIds((current) => {
    const next = new Set(current);
    ids.forEach((id) => (open ? next.add(id) : next.delete(id)));
    return next;
  });

  // A re-checked scheme replaces its card: it moves to its new section (or into "Not eligible").
  const onSchemeChecked = (updated) => {
    setResults((current) => {
      const results = current.results.filter((scheme) => scheme.id !== updated.id);
      const notEligible = current.notEligible.filter((scheme) => scheme.id !== updated.id);
      if (updated.group === 'not_eligible') notEligible.push(updated);
      else results.push(updated);
      return { ...current, results, notEligible };
    });
    setAnnouncement(`${updated.name}: now under "${SECTION_TITLES[updated.group]}".`);
  };
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
      setOpenIds(new Set());
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
          {step === 'results' && results ? (
            <ResultsStep data={results} onChange={() => setStep('questions')} profileAnswers={answers}
              onSchemeChecked={onSchemeChecked} announcement={announcement}
              openIds={openIds} toggleOpen={toggleOpen} setOpen={setOpen} />
          ) : null}
        </section>
      </div>
    </>
  );
}
