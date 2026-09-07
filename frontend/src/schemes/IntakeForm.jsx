import React from 'react';

import {
  CATEGORIES,
  EDUCATION_LEVELS,
  GENDERS,
  GOV_EMPLOYEE_GRADES,
  INDIAN_STATES,
  LAND_HOLDINGS,
  OCCUPATIONS,
  SUPPORT_TYPES,
  YES_NO
} from './options.js';

const FIELD_COUNT = 12;

const EMPTY = {
  state: '',
  age: '',
  gender: '',
  annual_family_income: '',
  occupation: '',
  education_level: '',
  category: '',
  support_type_needed: '',
  land_holding: '',
  paid_income_tax_last_year: '',
  monthly_pension: '',
  government_employee_grade: ''
};

function toValues(profile) {
  return {
    ...EMPTY,
    state: profile.state ?? '',
    age: profile.age != null ? String(profile.age) : '',
    gender: profile.gender ?? '',
    annual_family_income:
      profile.annual_family_income != null ? String(profile.annual_family_income) : '',
    occupation: profile.occupation ?? '',
    education_level: profile.education_level ?? '',
    category: profile.category ?? '',
    support_type_needed: profile.support_type_needed ?? '',
    land_holding: profile.land_holding ?? '',
    paid_income_tax_last_year:
      profile.paid_income_tax_last_year == null
        ? ''
        : String(profile.paid_income_tax_last_year),
    monthly_pension: profile.monthly_pension != null ? String(profile.monthly_pension) : '',
    government_employee_grade: profile.government_employee_grade ?? ''
  };
}

/** Only include fields the user actually filled in — everything is optional. */
function toProfile(values) {
  const profile = {};
  if (values.state) profile.state = values.state;
  if (values.gender) profile.gender = values.gender;
  if (values.occupation) profile.occupation = values.occupation;
  if (values.education_level) profile.education_level = values.education_level;
  if (values.category) profile.category = values.category;
  if (values.support_type_needed) profile.support_type_needed = values.support_type_needed;
  if (values.land_holding) profile.land_holding = values.land_holding;
  if (values.government_employee_grade)
    profile.government_employee_grade = values.government_employee_grade;

  if (values.paid_income_tax_last_year) {
    profile.paid_income_tax_last_year = values.paid_income_tax_last_year === 'true';
  }

  if (values.age.trim() !== '' && Number.isFinite(Number(values.age))) {
    profile.age = Number(values.age);
  }
  if (
    values.annual_family_income.trim() !== '' &&
    Number.isFinite(Number(values.annual_family_income))
  ) {
    profile.annual_family_income = Number(values.annual_family_income);
  }
  if (
    values.monthly_pension.trim() !== '' &&
    Number.isFinite(Number(values.monthly_pension))
  ) {
    profile.monthly_pension = Number(values.monthly_pension);
  }
  return profile;
}

function SelectField({ id, label, value, hint, options, onChange }) {
  return (
    <div className="scheme-field">
      <label htmlFor={id}>{label}</label>
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">— No preference —</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {hint ? <p className="scheme-note">{hint}</p> : null}
    </div>
  );
}

export function IntakeForm({ initialProfile, submitting, errorMessage, onSubmit }) {
  const [values, setValues] = React.useState(() => toValues(initialProfile));

  const set = (key) => (value) =>
    setValues((current) => ({ ...current, [key]: value }));

  const filledCount = Object.values(values).filter((value) => value.trim() !== '').length;

  const handleSubmit = (event) => {
    event.preventDefault();
    if (submitting) return;
    onSubmit(toProfile(values));
  };

  return (
    <form className="scheme-form" onSubmit={handleSubmit} noValidate>
      <p className="scheme-intro">
        Every question is optional. Answer what you can — even a few details are enough to
        start, and you&rsquo;ll still see schemes you <em>might</em> qualify for.
      </p>

      <div className="scheme-field-grid">
        <SelectField
          id="scheme-state"
          label="State / Union Territory"
          value={values.state}
          options={INDIAN_STATES}
          onChange={set('state')}
        />

        <div className="scheme-field">
          <label htmlFor="scheme-age">Age</label>
          <input
            id="scheme-age"
            type="number"
            inputMode="numeric"
            min={0}
            max={120}
            placeholder="e.g. 34"
            value={values.age}
            onChange={(event) => set('age')(event.target.value)}
          />
        </div>

        <fieldset className="scheme-field scheme-gender">
          <legend>Gender</legend>
          <div className="scheme-radio-row">
            {[{ value: '', label: 'Skip' }, ...GENDERS].map((option) => (
              <label key={option.value || 'skip'} className="scheme-radio">
                <input
                  type="radio"
                  name="scheme-gender"
                  value={option.value}
                  checked={values.gender === option.value}
                  onChange={(event) => set('gender')(event.target.value)}
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="scheme-field">
          <label htmlFor="scheme-income">Annual family income (₹)</label>
          <input
            id="scheme-income"
            type="number"
            inputMode="numeric"
            min={0}
            step={1000}
            placeholder="e.g. 150000"
            value={values.annual_family_income}
            onChange={(event) => set('annual_family_income')(event.target.value)}
          />
          <p className="scheme-note">Total for your whole household, per year.</p>
        </div>

        <SelectField
          id="scheme-occupation"
          label="Occupation"
          value={values.occupation}
          options={OCCUPATIONS}
          onChange={set('occupation')}
        />

        <SelectField
          id="scheme-education"
          label="Education level"
          value={values.education_level}
          options={EDUCATION_LEVELS}
          onChange={set('education_level')}
        />

        <SelectField
          id="scheme-category"
          label="Category"
          value={values.category}
          hint="Social category, used by many reservation-based schemes."
          options={CATEGORIES}
          onChange={set('category')}
        />

        <SelectField
          id="scheme-support"
          label="Kind of support you need"
          value={values.support_type_needed}
          options={SUPPORT_TYPES}
          onChange={set('support_type_needed')}
        />

        <p className="scheme-subhead">
          A few more details — only matter for some schemes (e.g. PM-KISAN). Leave blank if
          unsure.
        </p>

        <SelectField
          id="scheme-land"
          label="Land holding"
          value={values.land_holding}
          hint="Whether your family holds cultivable land, and how."
          options={LAND_HOLDINGS}
          onChange={set('land_holding')}
        />

        <SelectField
          id="scheme-tax"
          label="Paid income tax last year?"
          value={values.paid_income_tax_last_year}
          options={YES_NO}
          onChange={set('paid_income_tax_last_year')}
        />

        <div className="scheme-field">
          <label htmlFor="scheme-pension">Monthly pension (₹)</label>
          <input
            id="scheme-pension"
            type="number"
            inputMode="numeric"
            min={0}
            step={500}
            placeholder="e.g. 0"
            value={values.monthly_pension}
            onChange={(event) => set('monthly_pension')(event.target.value)}
          />
          <p className="scheme-note">Enter 0 if you receive no pension.</p>
        </div>

        <SelectField
          id="scheme-gov-grade"
          label="Government employee grade"
          value={values.government_employee_grade}
          options={GOV_EMPLOYEE_GRADES}
          onChange={set('government_employee_grade')}
        />
      </div>

      {errorMessage ? (
        <p className="scheme-error" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <div className="scheme-actions">
        <button type="submit" className="ask-button" disabled={submitting}>
          {submitting ? 'Searching…' : 'Search with what I have'}
        </button>
        <button
          type="button"
          className="scheme-clear"
          onClick={() => setValues(EMPTY)}
          disabled={submitting}
        >
          Clear all
        </button>
        <span className="scheme-count">
          {filledCount === 0
            ? 'Nothing filled in yet — that’s fine.'
            : `${filledCount} of ${FIELD_COUNT} filled in`}
        </span>
      </div>
    </form>
  );
}
