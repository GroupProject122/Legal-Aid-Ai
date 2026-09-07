import { useState, type FormEvent } from "react";

import {
  CATEGORIES,
  EDUCATION_LEVELS,
  GENDERS,
  GOV_EMPLOYEE_GRADES,
  INDIAN_STATES,
  LAND_HOLDINGS,
  OCCUPATIONS,
  SUPPORT_TYPES,
  YES_NO,
  type Option,
} from "../options";
import type { UserProfile } from "../types";

type FieldKey = keyof UserProfile;
type FormValues = Record<FieldKey, string>;

const FIELD_COUNT = 12;

const EMPTY: FormValues = {
  state: "",
  age: "",
  gender: "",
  annual_family_income: "",
  occupation: "",
  education_level: "",
  category: "",
  support_type_needed: "",
  land_holding: "",
  paid_income_tax_last_year: "",
  monthly_pension: "",
  government_employee_grade: "",
};

function toValues(profile: Partial<UserProfile>): FormValues {
  return {
    ...EMPTY,
    state: profile.state ?? "",
    age: profile.age != null ? String(profile.age) : "",
    gender: profile.gender ?? "",
    annual_family_income:
      profile.annual_family_income != null
        ? String(profile.annual_family_income)
        : "",
    occupation: profile.occupation ?? "",
    education_level: profile.education_level ?? "",
    category: profile.category ?? "",
    support_type_needed: profile.support_type_needed ?? "",
    land_holding: profile.land_holding ?? "",
    paid_income_tax_last_year:
      profile.paid_income_tax_last_year == null
        ? ""
        : String(profile.paid_income_tax_last_year),
    monthly_pension:
      profile.monthly_pension != null ? String(profile.monthly_pension) : "",
    government_employee_grade: profile.government_employee_grade ?? "",
  };
}

/** Only include fields the user actually filled in — everything is optional. */
function toProfile(values: FormValues): Partial<UserProfile> {
  const profile: Partial<UserProfile> = {};
  if (values.state) profile.state = values.state;
  if (values.gender) profile.gender = values.gender as UserProfile["gender"];
  if (values.occupation)
    profile.occupation = values.occupation as UserProfile["occupation"];
  if (values.education_level)
    profile.education_level =
      values.education_level as UserProfile["education_level"];
  if (values.category)
    profile.category = values.category as UserProfile["category"];
  if (values.support_type_needed)
    profile.support_type_needed =
      values.support_type_needed as UserProfile["support_type_needed"];
  if (values.land_holding)
    profile.land_holding = values.land_holding as UserProfile["land_holding"];
  if (values.government_employee_grade)
    profile.government_employee_grade =
      values.government_employee_grade as UserProfile["government_employee_grade"];

  if (values.paid_income_tax_last_year) {
    profile.paid_income_tax_last_year =
      values.paid_income_tax_last_year === "true";
  }

  if (values.age.trim() !== "" && Number.isFinite(Number(values.age))) {
    profile.age = Number(values.age);
  }
  if (
    values.annual_family_income.trim() !== "" &&
    Number.isFinite(Number(values.annual_family_income))
  ) {
    profile.annual_family_income = Number(values.annual_family_income);
  }
  if (
    values.monthly_pension.trim() !== "" &&
    Number.isFinite(Number(values.monthly_pension))
  ) {
    profile.monthly_pension = Number(values.monthly_pension);
  }
  return profile;
}

interface SelectFieldProps {
  id: FieldKey;
  label: string;
  value: string;
  hint?: string;
  options: Option[];
  onChange: (value: string) => void;
}

function SelectField({
  id,
  label,
  value,
  hint,
  options,
  onChange,
}: SelectFieldProps) {
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      <select
        id={id}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      >
        <option value="">— No preference —</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {hint ? <p className="hint">{hint}</p> : null}
    </div>
  );
}

interface IntakeFormProps {
  initialProfile: Partial<UserProfile>;
  submitting: boolean;
  errorMessage: string | null;
  onSubmit: (profile: Partial<UserProfile>) => void;
}

export function IntakeForm({
  initialProfile,
  submitting,
  errorMessage,
  onSubmit,
}: IntakeFormProps) {
  const [values, setValues] = useState<FormValues>(() =>
    toValues(initialProfile),
  );

  const set = (key: FieldKey) => (value: string) =>
    setValues((current) => ({ ...current, [key]: value }));

  const filledCount = Object.values(values).filter(
    (value) => value.trim() !== "",
  ).length;

  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    if (submitting) return;
    onSubmit(toProfile(values));
  };

  return (
    <form className="intake" onSubmit={handleSubmit} noValidate>
      <p className="intake-intro">
        Every question is optional. Answer what you can — even a few details are
        enough to start, and you&rsquo;ll still see schemes you <em>might</em>{" "}
        qualify for.
      </p>

      <div className="field-grid">
        <SelectField
          id="state"
          label="State / Union Territory"
          value={values.state}
          options={INDIAN_STATES}
          onChange={set("state")}
        />

        <div className="field">
          <label htmlFor="age">Age</label>
          <input
            id="age"
            type="number"
            inputMode="numeric"
            min={0}
            max={120}
            placeholder="e.g. 34"
            value={values.age}
            onChange={(event) => set("age")(event.target.value)}
          />
        </div>

        <fieldset className="field gender-field">
          <legend>Gender</legend>
          <div className="radio-row">
            {[{ value: "", label: "Skip" }, ...GENDERS].map((option) => (
              <label key={option.value || "skip"} className="radio">
                <input
                  type="radio"
                  name="gender"
                  value={option.value}
                  checked={values.gender === option.value}
                  onChange={(event) => set("gender")(event.target.value)}
                />
                {option.label}
              </label>
            ))}
          </div>
        </fieldset>

        <div className="field">
          <label htmlFor="annual_family_income">Annual family income (₹)</label>
          <input
            id="annual_family_income"
            type="number"
            inputMode="numeric"
            min={0}
            step={1000}
            placeholder="e.g. 150000"
            value={values.annual_family_income}
            onChange={(event) =>
              set("annual_family_income")(event.target.value)
            }
          />
          <p className="hint">Total for your whole household, per year.</p>
        </div>

        <SelectField
          id="occupation"
          label="Occupation"
          value={values.occupation}
          options={OCCUPATIONS}
          onChange={set("occupation")}
        />

        <SelectField
          id="education_level"
          label="Education level"
          value={values.education_level}
          options={EDUCATION_LEVELS}
          onChange={set("education_level")}
        />

        <SelectField
          id="category"
          label="Category"
          value={values.category}
          hint="Social category, used by many reservation-based schemes."
          options={CATEGORIES}
          onChange={set("category")}
        />

        <SelectField
          id="support_type_needed"
          label="Kind of support you need"
          value={values.support_type_needed}
          options={SUPPORT_TYPES}
          onChange={set("support_type_needed")}
        />

        <p className="intake-subhead" style={{ gridColumn: "1 / -1" }}>
          A few more details — only matter for some schemes (e.g. PM-KISAN).
          Leave blank if unsure.
        </p>

        <SelectField
          id="land_holding"
          label="Land holding"
          value={values.land_holding}
          hint="Whether your family holds cultivable land, and how."
          options={LAND_HOLDINGS}
          onChange={set("land_holding")}
        />

        <SelectField
          id="paid_income_tax_last_year"
          label="Paid income tax last year?"
          value={values.paid_income_tax_last_year}
          options={YES_NO}
          onChange={set("paid_income_tax_last_year")}
        />

        <div className="field">
          <label htmlFor="monthly_pension">Monthly pension (₹)</label>
          <input
            id="monthly_pension"
            type="number"
            inputMode="numeric"
            min={0}
            step={500}
            placeholder="e.g. 0"
            value={values.monthly_pension}
            onChange={(event) => set("monthly_pension")(event.target.value)}
          />
          <p className="hint">Enter 0 if you receive no pension.</p>
        </div>

        <SelectField
          id="government_employee_grade"
          label="Government employee grade"
          value={values.government_employee_grade}
          options={GOV_EMPLOYEE_GRADES}
          onChange={set("government_employee_grade")}
        />
      </div>

      {errorMessage ? (
        <p className="error" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <div className="intake-actions">
        <button type="submit" className="btn-primary" disabled={submitting}>
          {submitting ? "Searching…" : "Search with what I have →"}
        </button>
        <button
          type="button"
          className="btn-link"
          onClick={() => setValues(EMPTY)}
          disabled={submitting}
        >
          Clear all
        </button>
        <span className="filled-count">
          {filledCount === 0
            ? "Nothing filled in yet — that’s fine."
            : `${filledCount} of ${FIELD_COUNT} filled in`}
        </span>
      </div>
    </form>
  );
}
