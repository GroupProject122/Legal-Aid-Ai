import React from 'react';
import { ArrowUpRight, CircleCheck, CircleHelp, CircleX, ExternalLink, Info, LockKeyhole, Phone, RotateCcw, Scale } from 'lucide-react';

import { HeaderControls, PageDivider, DocumentsBackgroundArt } from '../shared/PageChrome.jsx';
import { EligibilityError, checkEligibility } from './api.js';
import { CATEGORY_OPTIONS, MAX_AGE, MIN_AGE, RESULT_STYLES } from './options.js';

// Steps 1-4 are always asked. Step 5 (income) is only shown when the backend says it needs it,
// i.e. none of the ticked groups gives free legal aid on its own -- the rules live in the
// backend only, so the page never has to guess which answers "count".
const STEP_DELHI = 1;
const STEP_COURT = 2;
const STEP_CATEGORIES = 3;
const STEP_AGE = 4;
const STEP_INCOME = 5;
const NONE = 'none';

const EMPTY_ANSWERS = { inDelhi: null, supremeCourt: null, categories: [], age: '', income: '' };

const RESULT_ICONS = { eligible: CircleCheck, 'not-eligible': CircleX, unknown: CircleHelp };

function parseWholeNumber(value) {
  const trimmed = String(value).trim();
  return /^\d+$/.test(trimmed) ? Number(trimmed) : null;
}

function buildRequest(answers, includeIncome) {
  const request = {
    state: answers.inDelhi ? 'Delhi' : 'Other',
    court: answers.supremeCourt ? 'supreme_court' : 'other',
    categories: answers.categories.filter((value) => value !== NONE),
    age: parseWholeNumber(answers.age)
  };
  if (includeIncome) request.annual_income = parseWholeNumber(answers.income);
  return request;
}

function sourceHref(source) {
  return `#/rights/source/${encodeURIComponent(source.source_id)}/provision/${encodeURIComponent(source.provision_id)}`;
}

function SourceLink({ source }) {
  if (!source) return null;
  if (source.source_id && source.provision_id) {
    return (
      <a className="legalaid-source-link" href={sourceHref(source)}>
        <Scale size={14} aria-hidden="true" />
        {source.provision}, {source.title}
        <ArrowUpRight size={13} aria-hidden="true" />
      </a>
    );
  }
  if (source.url) {
    return (
      <a className="legalaid-source-link" href={source.url} target="_blank" rel="noreferrer">
        {source.title} (official website)
        <ExternalLink size={13} aria-hidden="true" />
      </a>
    );
  }
  return null;
}

function GuidanceItem({ item }) {
  return (
    <li>
      <strong>{item.name}</strong>
      {item.detail ? <span> {item.detail}</span> : null}
      {item.phone ? (
        <span className="legalaid-phone">
          {' '}<a href={`tel:${item.phone}`}><Phone size={13} aria-hidden="true" /> {item.phone}</a>
        </span>
      ) : null}
      {item.url ? (
        <span>
          {' '}<a className="legalaid-source-link" href={item.url} target="_blank" rel="noreferrer">
            {item.url.replace(/^https?:\/\//, '').replace(/\/$/, '')}
            <ExternalLink size={13} aria-hidden="true" />
          </a>
        </span>
      ) : null}
      {item.source ? <span className="legalaid-item-source"> Source: <SourceLink source={item.source} /></span> : null}
    </li>
  );
}

function ResultCard({ result, headingRef, onRestart }) {
  const style = RESULT_STYLES[result.result] || RESULT_STYLES.cannot_determine;
  const Icon = RESULT_ICONS[style.tone];

  return (
    <section className={`rights-panel legalaid-result legalaid-result-${style.tone}`} aria-labelledby="legalaid-result-heading">
      <div className="legalaid-verdict">
        <Icon size={30} strokeWidth={1.7} aria-hidden="true" />
        <div>
          <p className="legalaid-verdict-label">{style.label}</p>
          <h3 id="legalaid-result-heading" tabIndex={-1} ref={headingRef}>{result.headline}</h3>
          <p>{result.reason}</p>
        </div>
      </div>

      {result.matched_rules?.length ? (
        <div className="legalaid-section">
          <h4>Why</h4>
          <ul className="legalaid-rule-list">
            {result.matched_rules.map((rule) => (
              <li key={rule.rule_id}>
                <p>{rule.reason}</p>
                <SourceLink source={rule.source} />
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <div className="legalaid-section">
        <h4>Where to apply</h4>
        <ul className="legalaid-guidance-list">
          {result.where_to_apply.map((item) => <GuidanceItem item={item} key={item.name} />)}
        </ul>
      </div>

      <div className="legalaid-section">
        <h4>What to bring</h4>
        <ul className="legalaid-guidance-list">
          {result.documents_to_bring.map((item) => (
            <li key={item.text}>
              {item.text}
              {item.source ? <span className="legalaid-item-source"> Source: <SourceLink source={item.source} /></span> : null}
            </li>
          ))}
        </ul>
      </div>

      {result.alternatives?.length ? (
        <div className="legalaid-section">
          <h4>Other free help you can still get</h4>
          <ul className="legalaid-guidance-list">
            {result.alternatives.map((item) => <GuidanceItem item={item} key={item.name} />)}
          </ul>
        </div>
      ) : null}

      {result.notes?.length ? (
        <div className="legalaid-notes">
          <Info size={16} aria-hidden="true" />
          <div>
            <p><strong>Good to know</strong></p>
            {result.notes.map((note) => <p key={note}>{note}</p>)}
          </div>
        </div>
      ) : null}

      <p className="helpline-disclaimer legalaid-disclaimer">{result.disclaimer}</p>
      <p className="legalaid-verified">Rules last checked: {result.last_verified}</p>

      <button type="button" className="ask-button legalaid-restart" onClick={onRestart}>
        <RotateCcw size={16} aria-hidden="true" /> Start again
      </button>
    </section>
  );
}

function YesNo({ name, value, onChange }) {
  return (
    <div className="legalaid-choice-row">
      {[[true, 'Yes'], [false, 'No']].map(([optionValue, label]) => (
        <label key={label} className={`legalaid-choice ${value === optionValue ? 'is-selected' : ''}`}>
          <input type="radio" name={name} checked={value === optionValue} onChange={() => onChange(optionValue)} />
          {label}
        </label>
      ))}
    </div>
  );
}

export default function LegalAidCheck() {
  const [step, setStep] = React.useState(STEP_DELHI);
  const [answers, setAnswers] = React.useState(EMPTY_ANSWERS);
  const [result, setResult] = React.useState(null);
  const [error, setError] = React.useState('');
  const [isChecking, setIsChecking] = React.useState(false);
  const stepHeadingRef = React.useRef(null);
  const resultHeadingRef = React.useRef(null);
  const isFirstRender = React.useRef(true);

  React.useEffect(() => {
    if (isFirstRender.current) {
      isFirstRender.current = false;
      return;
    }
    if (result) resultHeadingRef.current?.focus();
    else stepHeadingRef.current?.focus();
  }, [step, result]);

  const update = (patch) => {
    setAnswers((current) => ({ ...current, ...patch }));
    setError('');
  };

  const toggleCategory = (value) => {
    setAnswers((current) => {
      if (value === NONE) return { ...current, categories: current.categories.includes(NONE) ? [] : [NONE] };
      const withoutNone = current.categories.filter((item) => item !== NONE);
      const categories = withoutNone.includes(value) ? withoutNone.filter((item) => item !== value) : [...withoutNone, value];
      return { ...current, categories };
    });
    setError('');
  };

  const age = parseWholeNumber(answers.age);
  const ageValid = age !== null && age >= MIN_AGE && age <= MAX_AGE;
  const income = parseWholeNumber(answers.income);
  const incomeValid = income !== null;

  const canContinue = {
    [STEP_DELHI]: answers.inDelhi !== null,
    [STEP_COURT]: answers.supremeCourt !== null,
    [STEP_CATEGORIES]: answers.categories.length > 0,
    [STEP_AGE]: ageValid,
    [STEP_INCOME]: incomeValid
  }[step];

  const submit = async (includeIncome) => {
    setIsChecking(true);
    setError('');
    try {
      const response = await checkEligibility(buildRequest(answers, includeIncome));
      if (!includeIncome && response.needs?.includes('annual_income')) {
        setStep(STEP_INCOME);
      } else {
        setResult(response);
      }
    } catch (err) {
      setError(err instanceof EligibilityError ? err.message : 'The check could not be completed right now.');
    } finally {
      setIsChecking(false);
    }
  };

  const handleSubmit = (event) => {
    event.preventDefault();
    if (!canContinue || isChecking) return;
    if (step === STEP_AGE) submit(false);
    else if (step === STEP_INCOME) submit(true);
    else setStep(step + 1);
  };

  const restart = () => {
    setAnswers(EMPTY_ANSWERS);
    setResult(null);
    setError('');
    setStep(STEP_DELHI);
  };

  const stepTitle = {
    [STEP_DELHI]: 'Is your case in Delhi?',
    [STEP_COURT]: 'Is your case in the Supreme Court?',
    [STEP_CATEGORIES]: 'Which of these apply to you?',
    [STEP_AGE]: 'How old are you?',
    [STEP_INCOME]: 'What is your yearly income?'
  }[step];

  return (
    <>
      <DocumentsBackgroundArt />
      <HeaderControls />
      <div className="rights-content-frame">
        <header className="documents-page-header">
          <div className="header-ornament-line"><span /><i>◇</i></div>
          <h2>Free Legal Aid Check</h2>
          <div className="header-ornament-line"><i>◇</i><span /></div>
          <p>Answer a few questions to see if you are likely to get a free lawyer, why, and where to apply.</p>
          <PageDivider />
        </header>

        {result ? (
          <div aria-live="polite">
            <ResultCard result={result} headingRef={resultHeadingRef} onRestart={restart} />
          </div>
        ) : (
          <form className="rights-panel legalaid-form" onSubmit={handleSubmit} noValidate>
            <p className="legalaid-progress">Question {step}{step < STEP_INCOME ? ' of 4' : ' (last one)'}</p>
            <fieldset className="legalaid-fieldset">
              <legend>
                <h3 tabIndex={-1} ref={stepHeadingRef}>{stepTitle}</h3>
              </legend>

              {step === STEP_DELHI ? (
                <>
                  <p className="legalaid-help">Where the case is (or will be) filed, or where you live if no case is filed yet.</p>
                  <YesNo name="legalaid-delhi" value={answers.inDelhi} onChange={(value) => update({ inDelhi: value })} />
                  <p className="legalaid-privacy"><LockKeyhole size={14} aria-hidden="true" /> Your answers are not saved.</p>
                </>
              ) : null}

              {step === STEP_COURT ? (
                <>
                  <p className="legalaid-help">Choose "No" for any other court, tribunal or authority, or if no case is filed yet.</p>
                  <YesNo name="legalaid-court" value={answers.supremeCourt} onChange={(value) => update({ supremeCourt: value })} />
                </>
              ) : null}

              {step === STEP_CATEGORIES ? (
                <>
                  <p className="legalaid-help">Tick all that apply. You don't need to show any proof here. Under 18? We'll work that out from your age next.</p>
                  <div className="legalaid-checkbox-list">
                    {CATEGORY_OPTIONS.map((option) => (
                      <label key={option.value} className={`legalaid-checkbox ${answers.categories.includes(option.value) ? 'is-selected' : ''}`}>
                        <input
                          type="checkbox"
                          checked={answers.categories.includes(option.value)}
                          onChange={() => toggleCategory(option.value)}
                        />
                        <span>
                          {option.label}
                          {option.hint ? <small>{option.hint}</small> : null}
                        </span>
                      </label>
                    ))}
                    <label className={`legalaid-checkbox legalaid-checkbox-none ${answers.categories.includes(NONE) ? 'is-selected' : ''}`}>
                      <input type="checkbox" checked={answers.categories.includes(NONE)} onChange={() => toggleCategory(NONE)} />
                      <span>None of these</span>
                    </label>
                  </div>
                </>
              ) : null}

              {step === STEP_AGE ? (
                <div className="legalaid-number-field">
                  <label htmlFor="legalaid-age">Age in years</label>
                  <input
                    id="legalaid-age"
                    type="text"
                    inputMode="numeric"
                    autoComplete="off"
                    value={answers.age}
                    onChange={(event) => update({ age: event.target.value })}
                    aria-invalid={answers.age !== '' && !ageValid}
                    aria-describedby="legalaid-age-help"
                  />
                  <p id="legalaid-age-help" className="legalaid-help">
                    {answers.age !== '' && !ageValid ? `Enter a whole number from ${MIN_AGE} to ${MAX_AGE}.` : 'A whole number, for example 34.'}
                  </p>
                </div>
              ) : null}

              {step === STEP_INCOME ? (
                <div className="legalaid-number-field">
                  <label htmlFor="legalaid-income">Your own yearly income, in rupees</label>
                  <div className="legalaid-rupee-input">
                    <span aria-hidden="true">₹</span>
                    <input
                      id="legalaid-income"
                      type="text"
                      inputMode="numeric"
                      autoComplete="off"
                      value={answers.income}
                      onChange={(event) => update({ income: event.target.value.replace(/[,\s]/g, '') })}
                      aria-invalid={answers.income !== '' && !incomeValid}
                      aria-describedby="legalaid-income-help"
                    />
                  </div>
                  <p id="legalaid-income-help" className="legalaid-help">
                    {answers.income !== '' && !incomeValid
                      ? 'Enter digits only, for example 240000.'
                      : 'Your total income for a year, from all work and other sources. Enter 0 if you have none.'}
                  </p>
                </div>
              ) : null}
            </fieldset>

            {error ? <p className="scam-error" role="alert">{error}</p> : null}

            <div className="legalaid-nav">
              {step > STEP_DELHI ? (
                <button type="button" className="helpline-action legalaid-back" onClick={() => { setError(''); setStep(step === STEP_INCOME ? STEP_AGE : step - 1); }}>
                  Back
                </button>
              ) : null}
              <button type="submit" className="ask-button" disabled={!canContinue || isChecking}>
                {isChecking ? 'Checking…' : step >= STEP_AGE ? 'See result' : 'Next'}
              </button>
            </div>
          </form>
        )}
      </div>
    </>
  );
}
