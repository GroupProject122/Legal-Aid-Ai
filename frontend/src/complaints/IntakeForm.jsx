import React from 'react';

import {
  EVICTION_GROUNDS,
  TENANCY_RELIEF_OPTIONS,
  DEFECT_OR_DEFICIENCY_TYPES,
  GOODS_RELIEF_OPTIONS,
  YES_NO,
  PLATFORM_OR_MEDIUM_OPTIONS,
  ADVERTISEMENT_CLAIM_TYPES,
  ADS_RELIEF_OPTIONS
} from './options.js';

/**
 * Per-scenario field schema driving the one shared form below (and reused by
 * DraftPreview.jsx to render a read-only summary of what was submitted). A
 * 4th scenario means adding one more entry here, not a 4th form component.
 *
 * type: 'text' | 'textarea' | 'date' | 'number' | 'select' | 'multiselect' | 'yesno'
 * showIf(values): field is required/visible only when this returns true —
 * mirrors backend/complaint_drafter.py's own conditionally-required fields.
 */
export const FIELD_SCHEMAS = {
  tenancy_eviction: [
    { name: 'tenant_name', label: 'Tenant name', type: 'text', required: true },
    { name: 'tenant_address', label: 'Tenant address', type: 'textarea', required: true },
    { name: 'landlord_name', label: 'Landlord name', type: 'text', required: true },
    { name: 'landlord_address', label: 'Landlord address', type: 'textarea', required: true },
    { name: 'property_address', label: 'Tenanted property address', type: 'textarea', required: true },
    {
      name: 'monthly_rent',
      label: 'Monthly rent (₹)',
      type: 'number',
      required: true,
      min: 0.01,
      hint: 'Must not exceed Rs. 3,500 for this Act to apply (Section 3).'
    },
    { name: 'tenancy_start_date', label: 'Tenancy start date', type: 'date', required: true },
    { name: 'grounds_for_eviction', label: 'Grounds for eviction', type: 'select', required: true, options: EVICTION_GROUNDS },
    { name: 'relief_sought', label: 'Relief sought', type: 'multiselect', required: true, options: TENANCY_RELIEF_OPTIONS },
    {
      name: 'arrears_amount',
      label: 'Arrears amount (₹)',
      type: 'number',
      required: true,
      min: 0.01,
      showIf: (v) => v.grounds_for_eviction === 'arrears'
    },
    {
      name: 'arrears_period_months',
      label: 'Arrears period (months)',
      type: 'number',
      required: true,
      min: 1,
      step: 1,
      showIf: (v) => v.grounds_for_eviction === 'arrears'
    },
    {
      name: 'subletting_details',
      label: 'Subletting details',
      type: 'textarea',
      required: true,
      showIf: (v) => v.grounds_for_eviction === 'subletting'
    },
    {
      name: 'damage_description',
      label: 'Damage description',
      type: 'textarea',
      required: true,
      showIf: (v) => v.grounds_for_eviction === 'damage'
    },
    {
      name: 'bona_fide_reason',
      label: 'Reason for bona fide requirement',
      type: 'textarea',
      required: true,
      showIf: (v) => v.grounds_for_eviction === 'bona_fide_requirement'
    }
  ],
  consumer_defective_goods: [
    { name: 'complainant_name', label: 'Your name', type: 'text', required: true },
    { name: 'complainant_address', label: 'Your address', type: 'textarea', required: true },
    { name: 'opposite_party_name', label: 'Seller / service provider name', type: 'text', required: true },
    { name: 'opposite_party_address', label: 'Seller / service provider address', type: 'textarea', required: true },
    { name: 'goods_or_service_description', label: 'Goods or service in question', type: 'text', required: true },
    { name: 'transaction_date', label: 'Date of transaction', type: 'date', required: true },
    { name: 'amount_paid', label: 'Amount paid (₹)', type: 'number', required: true, min: 0.01 },
    {
      name: 'defect_or_deficiency_type',
      label: 'Type of issue',
      type: 'select',
      required: true,
      options: DEFECT_OR_DEFICIENCY_TYPES
    },
    { name: 'defect_description', label: 'Describe the defect or deficiency', type: 'textarea', required: true },
    { name: 'prior_complaint_made', label: 'Did you already raise this with the seller?', type: 'yesno', required: true },
    {
      name: 'prior_complaint_response',
      label: 'What did they say?',
      type: 'textarea',
      required: true,
      showIf: (v) => v.prior_complaint_made === 'true'
    },
    { name: 'relief_sought', label: 'Relief sought', type: 'multiselect', required: true, options: GOODS_RELIEF_OPTIONS },
    {
      name: 'compensation_amount',
      label: 'Compensation amount (₹)',
      type: 'number',
      required: true,
      min: 0.01,
      showIf: (v) => (v.relief_sought || []).includes('compensation')
    }
  ],
  consumer_misleading_ads: [
    { name: 'complainant_name', label: 'Your name', type: 'text', required: true },
    { name: 'complainant_address', label: 'Your address', type: 'textarea', required: true },
    { name: 'opposite_party_name', label: 'Advertiser / seller name', type: 'text', required: true },
    { name: 'opposite_party_address', label: 'Advertiser / seller address', type: 'textarea', required: true },
    {
      name: 'advertisement_or_practice_description',
      label: 'Describe the advertisement or practice',
      type: 'textarea',
      required: true
    },
    {
      name: 'platform_or_medium',
      label: 'Platform or medium',
      type: 'select',
      required: true,
      options: PLATFORM_OR_MEDIUM_OPTIONS
    },
    { name: 'date_encountered', label: 'Date encountered', type: 'date', required: true },
    { name: 'claim_type', label: 'Type of claim', type: 'select', required: true, options: ADVERTISEMENT_CLAIM_TYPES },
    {
      name: 'how_it_caused_loss',
      label: 'How did this cause you loss or harm?',
      type: 'textarea',
      required: true,
      hint: 'Be specific — at least 20 characters. A vague description will be rejected.'
    },
    {
      name: 'amount_paid',
      label: 'Amount paid, if any (₹)',
      type: 'number',
      required: false,
      min: 0.01,
      hint: 'Leave blank if this did not involve a completed purchase.'
    },
    { name: 'relief_sought', label: 'Relief sought', type: 'multiselect', required: true, options: ADS_RELIEF_OPTIONS },
    {
      name: 'compensation_amount',
      label: 'Compensation amount (₹)',
      type: 'number',
      required: true,
      min: 0.01,
      showIf: (v) => (v.relief_sought || []).includes('compensation')
    }
  ]
};

function emptyValues(scenario) {
  const values = {};
  for (const field of FIELD_SCHEMAS[scenario]) {
    values[field.name] = field.type === 'multiselect' ? [] : '';
  }
  return values;
}

/**
 * Coerce string-based form state into the JSON payload the backend expects,
 * dropping fields hidden by their showIf condition -- a stale value from a
 * previously-selected ground/claim type must not be silently sent once it's
 * no longer relevant.
 */
export function buildIntakePayload(scenario, values) {
  const payload = {};
  for (const field of FIELD_SCHEMAS[scenario]) {
    if (field.showIf && !field.showIf(values)) continue;
    const raw = values[field.name];
    if (field.type === 'multiselect') {
      if (Array.isArray(raw) && raw.length > 0) payload[field.name] = raw;
      continue;
    }
    if (raw === '' || raw == null) continue;
    if (field.type === 'number') {
      const num = Number(raw);
      if (Number.isFinite(num)) payload[field.name] = num;
      continue;
    }
    if (field.type === 'yesno') {
      payload[field.name] = raw === 'true';
      continue;
    }
    payload[field.name] = raw;
  }
  return payload;
}

function RequiredMark({ required }) {
  return required ? <span className="complaint-required"> *</span> : null;
}

function FieldMessage({ hint, error }) {
  return (
    <>
      {hint ? <p className="scheme-note">{hint}</p> : null}
      {error ? <p className="complaint-field-message" role="alert">{error}</p> : null}
    </>
  );
}

function TextField({ field, value, onChange, error }) {
  return (
    <div className={`scheme-field complaint-field ${error ? 'complaint-field-error' : ''}`}>
      <label htmlFor={`complaint-${field.name}`}>{field.label}<RequiredMark required={field.required} /></label>
      <input id={`complaint-${field.name}`} type="text" value={value} onChange={(event) => onChange(event.target.value)} />
      <FieldMessage hint={field.hint} error={error} />
    </div>
  );
}

function TextareaField({ field, value, onChange, error }) {
  return (
    <div className={`scheme-field complaint-field complaint-field-wide ${error ? 'complaint-field-error' : ''}`}>
      <label htmlFor={`complaint-${field.name}`}>{field.label}<RequiredMark required={field.required} /></label>
      <textarea id={`complaint-${field.name}`} rows={3} value={value} onChange={(event) => onChange(event.target.value)} />
      <FieldMessage hint={field.hint} error={error} />
    </div>
  );
}

function DateField({ field, value, onChange, error }) {
  return (
    <div className={`scheme-field complaint-field ${error ? 'complaint-field-error' : ''}`}>
      <label htmlFor={`complaint-${field.name}`}>{field.label}<RequiredMark required={field.required} /></label>
      <input id={`complaint-${field.name}`} type="date" value={value} onChange={(event) => onChange(event.target.value)} />
      <FieldMessage hint={field.hint} error={error} />
    </div>
  );
}

function NumberField({ field, value, onChange, error }) {
  return (
    <div className={`scheme-field complaint-field ${error ? 'complaint-field-error' : ''}`}>
      <label htmlFor={`complaint-${field.name}`}>{field.label}<RequiredMark required={field.required} /></label>
      <input
        id={`complaint-${field.name}`}
        type="number"
        inputMode="decimal"
        min={field.min ?? 0}
        step={field.step ?? 0.01}
        value={value}
        onChange={(event) => onChange(event.target.value)}
      />
      <FieldMessage hint={field.hint} error={error} />
    </div>
  );
}

function SelectField({ field, value, onChange, error }) {
  return (
    <div className={`scheme-field complaint-field ${error ? 'complaint-field-error' : ''}`}>
      <label htmlFor={`complaint-${field.name}`}>{field.label}<RequiredMark required={field.required} /></label>
      <select id={`complaint-${field.name}`} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">— Select —</option>
        {field.options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
      <FieldMessage hint={field.hint} error={error} />
    </div>
  );
}

function YesNoField({ field, value, onChange, error }) {
  return (
    <fieldset className={`scheme-field complaint-field ${error ? 'complaint-field-error' : ''}`}>
      <legend>{field.label}<RequiredMark required={field.required} /></legend>
      <div className="scheme-radio-row">
        {YES_NO.map((option) => (
          <label key={option.value} className="scheme-radio">
            <input
              type="radio"
              name={`complaint-${field.name}`}
              value={option.value}
              checked={value === option.value}
              onChange={(event) => onChange(event.target.value)}
            />
            {option.label}
          </label>
        ))}
      </div>
      <FieldMessage error={error} />
    </fieldset>
  );
}

function MultiSelectField({ field, value, onChange, error }) {
  const selected = Array.isArray(value) ? value : [];
  const toggle = (optionValue) => {
    onChange(selected.includes(optionValue) ? selected.filter((item) => item !== optionValue) : [...selected, optionValue]);
  };
  return (
    <fieldset className={`scheme-field complaint-field complaint-field-wide ${error ? 'complaint-field-error' : ''}`}>
      <legend>{field.label}<RequiredMark required={field.required} /></legend>
      <div className="complaint-checkbox-row">
        {field.options.map((option) => (
          <div className="complaint-checkbox-option" key={option.value}>
            <label className="scheme-radio">
              <input type="checkbox" checked={selected.includes(option.value)} onChange={() => toggle(option.value)} />
              {option.label}
            </label>
            {/* Advisory only (e.g. compensation relief in the misleading-ads scenario) --
                does not block submission, just a hint at the point of choice. */}
            {option.hint ? <p className="scheme-note complaint-option-hint">{option.hint}</p> : null}
          </div>
        ))}
      </div>
      <FieldMessage error={error} />
    </fieldset>
  );
}

function FieldControl({ field, value, onChange, error }) {
  switch (field.type) {
    case 'textarea':
      return <TextareaField field={field} value={value} onChange={onChange} error={error} />;
    case 'date':
      return <DateField field={field} value={value} onChange={onChange} error={error} />;
    case 'number':
      return <NumberField field={field} value={value} onChange={onChange} error={error} />;
    case 'select':
      return <SelectField field={field} value={value} onChange={onChange} error={error} />;
    case 'yesno':
      return <YesNoField field={field} value={value} onChange={onChange} error={error} />;
    case 'multiselect':
      return <MultiSelectField field={field} value={value} onChange={onChange} error={error} />;
    default:
      return <TextField field={field} value={value} onChange={onChange} error={error} />;
  }
}

/**
 * `errorField` is the backend's own structured field name for the current
 * `errorMessage` (from `ApiError.field` -- see complaints/api.js), not
 * something this component derives from the message text. When it's null
 * (a general error, not about one particular field), the message renders as
 * a form-level banner instead of next to a field.
 */
export function IntakeForm({ scenario, submitting, errorMessage, errorField, onSubmit }) {
  const [values, setValues] = React.useState(() => emptyValues(scenario));

  // Reset whenever a different scenario card is picked.
  React.useEffect(() => {
    setValues(emptyValues(scenario));
  }, [scenario]);

  const fields = FIELD_SCHEMAS[scenario];

  const set = (name) => (value) => setValues((current) => ({ ...current, [name]: value }));

  const handleSubmit = (event) => {
    event.preventDefault();
    if (submitting) return;
    onSubmit(buildIntakePayload(scenario, values));
  };

  return (
    <form className="scheme-form complaint-form" onSubmit={handleSubmit} noValidate>
      <div className="scheme-field-grid complaint-field-grid">
        {fields
          .filter((field) => !field.showIf || field.showIf(values))
          .map((field) => (
            <FieldControl
              key={field.name}
              field={field}
              value={values[field.name]}
              onChange={set(field.name)}
              error={errorField === field.name ? errorMessage : null}
            />
          ))}
      </div>

      {errorMessage && !errorField ? <p className="scheme-error" role="alert">{errorMessage}</p> : null}

      <div className="scheme-actions">
        <button type="submit" className="ask-button" disabled={submitting}>
          {submitting ? 'Drafting…' : 'Generate draft'}
        </button>
      </div>
    </form>
  );
}
