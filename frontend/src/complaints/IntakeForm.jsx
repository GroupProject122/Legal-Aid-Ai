import React from 'react';

import { AutoGrowTextarea } from '../AutoGrowTextarea.jsx';

import {
  EVICTION_GROUNDS,
  TENANCY_RELIEF_OPTIONS,
  DEFECT_OR_DEFICIENCY_TYPES,
  GOODS_RELIEF_OPTIONS,
  YES_NO,
  PLATFORM_OR_MEDIUM_OPTIONS,
  ADVERTISEMENT_CLAIM_TYPES,
  ADS_RELIEF_OPTIONS,
  PREFERRED_MODE_OPTIONS,
  PIO_RESPONSE_TYPE_OPTIONS,
  RESPONDENT_RELATIONSHIP_OPTIONS,
  ESSENTIAL_SUPPLY_TYPE_OPTIONS,
  ACCOUNT_CATEGORY_OPTIONS
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
      currency: true,
      required: true,
      min: 0.01,
      hint: 'Must not exceed Rs. 3,500 for this Act to apply (Section 3).'
    },
    { name: 'tenancy_start_date', label: 'Tenancy start date', type: 'date', required: true },
    {
      name: 'grounds_for_eviction',
      label: 'Grounds for eviction',
      type: 'multiselect',
      required: true,
      options: EVICTION_GROUNDS,
      hint: 'Select one or more. The document will list them in Section 14(1)’s own order, not the order you pick them in.'
    },
    { name: 'relief_sought', label: 'Relief sought', type: 'multiselect', required: true, options: TENANCY_RELIEF_OPTIONS },
    {
      name: 'arrears_amount',
      label: 'Arrears amount (₹)',
      type: 'number',
      currency: true,
      required: true,
      min: 0.01,
      showIf: (v) => (v.grounds_for_eviction || []).includes('arrears')
    },
    {
      name: 'arrears_period_months',
      label: 'Arrears period (months)',
      type: 'number',
      required: true,
      min: 1,
      step: 1,
      showIf: (v) => (v.grounds_for_eviction || []).includes('arrears')
    },
    {
      name: 'subletting_details',
      label: 'Subletting details',
      type: 'textarea',
      required: true,
      showIf: (v) => (v.grounds_for_eviction || []).includes('subletting')
    },
    {
      name: 'damage_description',
      label: 'Damage description',
      type: 'textarea',
      required: true,
      showIf: (v) => (v.grounds_for_eviction || []).includes('damage')
    },
    {
      name: 'bona_fide_reason',
      label: 'Reason for bona fide requirement',
      type: 'textarea',
      required: true,
      showIf: (v) => (v.grounds_for_eviction || []).includes('bona_fide_requirement')
    }
  ],
  consumer_defective_goods: [
    { name: 'complainant_name', label: 'Your name', type: 'text', required: true },
    { name: 'complainant_address', label: 'Your address', type: 'textarea', required: true },
    { name: 'opposite_party_name', label: 'Seller / service provider name', type: 'text', required: true },
    { name: 'opposite_party_address', label: 'Seller / service provider address', type: 'textarea', required: true },
    { name: 'goods_or_service_description', label: 'Goods or service in question', type: 'text', required: true },
    { name: 'transaction_date', label: 'Date of transaction', type: 'date', required: true },
    { name: 'amount_paid', label: 'Amount paid (₹)', type: 'number', currency: true, required: true, min: 0.01 },
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
      currency: true,
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
      currency: true,
      required: false,
      min: 0.01,
      hint: 'Leave blank if this did not involve a completed purchase.'
    },
    { name: 'relief_sought', label: 'Relief sought', type: 'multiselect', required: true, options: ADS_RELIEF_OPTIONS },
    {
      name: 'compensation_amount',
      label: 'Compensation amount (₹)',
      type: 'number',
      currency: true,
      required: true,
      min: 0.01,
      showIf: (v) => (v.relief_sought || []).includes('compensation')
    }
  ],
  rti_application: [
    { name: 'applicant_name', label: 'Your name', type: 'text', required: true },
    { name: 'applicant_address', label: 'Your address', type: 'textarea', required: true },
    {
      name: 'public_authority_name',
      label: 'Government office / public authority',
      type: 'text',
      required: true,
      hint: 'The department, office, or authority that holds the information -- your application is addressed to its Public Information Officer.'
    },
    { name: 'public_authority_address', label: 'Public authority address', type: 'textarea', required: true },
    {
      name: 'information_sought',
      label: 'What information are you requesting?',
      type: 'textarea',
      required: true,
      hint: 'Be specific — at least 20 characters. You are not required to explain why you want this information (Section 6(2) of the Act).'
    },
    {
      name: 'preferred_mode',
      label: 'How would you like to receive it?',
      type: 'select',
      required: true,
      options: PREFERRED_MODE_OPTIONS
    },
    {
      name: 'is_bpl_applicant',
      label: 'Do you belong to a family below the poverty line (BPL)?',
      type: 'yesno',
      required: true,
      hint: 'BPL applicants are exempt from the application fee under Section 7(5) of the Act.'
    }
  ],
  rti_first_appeal: [
    { name: 'appellant_name', label: 'Your name', type: 'text', required: true },
    { name: 'appellant_address', label: 'Your address', type: 'textarea', required: true },
    {
      name: 'public_authority_name',
      label: 'Government office / public authority',
      type: 'text',
      required: true,
      hint: 'The same office your original RTI request was addressed to.'
    },
    { name: 'public_authority_address', label: 'Public authority address', type: 'textarea', required: true },
    {
      name: 'information_originally_sought',
      label: 'What information did you originally request?',
      type: 'textarea',
      required: true
    },
    { name: 'original_application_date', label: 'Date you filed the original RTI request', type: 'date', required: true },
    {
      name: 'pio_response_type',
      label: "What was the Public Information Officer's response?",
      type: 'select',
      required: true,
      options: PIO_RESPONSE_TYPE_OPTIONS
    },
    {
      name: 'pio_response_date',
      label: 'Date of that response',
      type: 'date',
      required: true,
      showIf: (v) => v.pio_response_type && v.pio_response_type !== 'no_response_received'
    },
    {
      name: 'grounds_for_appeal',
      label: 'Why are you appealing?',
      type: 'textarea',
      required: true,
      hint: 'Be specific — at least 20 characters.'
    }
  ],
  senior_citizen_maintenance: [
    { name: 'applicant_name', label: 'Your name', type: 'text', required: true },
    { name: 'applicant_address', label: 'Your address', type: 'textarea', required: true },
    { name: 'applicant_age', label: 'Your age', type: 'number', required: true, min: 60, step: 1, hint: 'Must be 60 or above.' },
    {
      name: 'respondent_relationship',
      label: 'Who are you filing this against?',
      type: 'select',
      required: true,
      options: RESPONDENT_RELATIONSHIP_OPTIONS
    },
    { name: 'respondent_name', label: 'Their name', type: 'text', required: true },
    { name: 'respondent_address', label: 'Their address', type: 'textarea', required: true },
    {
      name: 'relative_property_connection',
      label: 'How do they hold or stand to inherit your property?',
      type: 'textarea',
      required: true,
      showIf: (v) => v.respondent_relationship === 'relative_of_childless_senior_citizen'
    },
    {
      name: 'neglect_description',
      label: 'Describe how they have neglected or refused to maintain you',
      type: 'textarea',
      required: true,
      hint: 'Be specific — at least 20 characters.'
    },
    {
      name: 'requested_monthly_maintenance_amount',
      label: 'Requested monthly maintenance (₹)',
      type: 'number',
      currency: true,
      required: true,
      min: 0.01,
      hint: 'Cannot exceed Rs. 10,000/month — the statutory ceiling under Section 9(2) of the Act.'
    }
  ],
  tenant_essential_supply: [
    { name: 'tenant_name', label: 'Your name', type: 'text', required: true },
    { name: 'tenant_address', label: 'Your address', type: 'textarea', required: true },
    { name: 'landlord_name', label: 'Landlord name', type: 'text', required: true },
    { name: 'landlord_address', label: 'Landlord address', type: 'textarea', required: true },
    { name: 'property_address', label: 'Tenanted property address', type: 'textarea', required: true },
    {
      name: 'essential_supply_type',
      label: 'Which supply/service was cut off or withheld?',
      type: 'select',
      required: true,
      options: ESSENTIAL_SUPPLY_TYPE_OPTIONS
    },
    { name: 'date_supply_cut_off', label: 'Date this happened', type: 'date', required: true },
    {
      name: 'how_supply_was_cut_off',
      label: 'Describe what the landlord did',
      type: 'textarea',
      required: true,
      hint: 'Be specific — at least 20 characters.'
    },
    {
      name: 'landlord_stated_reason',
      label: 'What reason (if any) did the landlord give?',
      type: 'textarea',
      required: false
    }
  ],
  bank_fraud_complaint: [
    { name: 'complainant_name', label: 'Your name', type: 'text', required: true },
    { name: 'complainant_address', label: 'Your address', type: 'textarea', required: true },
    { name: 'bank_name', label: 'Bank name', type: 'text', required: true },
    { name: 'bank_branch_address', label: 'Bank branch address', type: 'textarea', required: true },
    {
      name: 'account_category',
      label: 'Account / card type',
      type: 'select',
      required: true,
      options: ACCOUNT_CATEGORY_OPTIONS
    },
    { name: 'transaction_date', label: 'Date of the unauthorized transaction', type: 'date', required: true },
    { name: 'transaction_amount', label: 'Transaction amount (₹)', type: 'number', currency: true, required: true, min: 0.01 },
    {
      name: 'bank_communication_date',
      label: "Date you received the bank's alert/communication about it",
      type: 'date',
      required: true
    },
    {
      name: 'date_first_reported_to_bank',
      label: 'Date you first reported it to the bank',
      type: 'date',
      required: true,
      hint: 'Your liability tier is calculated from the gap between these two dates.'
    },
    {
      name: 'unauthorized_transaction_description',
      label: 'Describe the transaction and why it was unauthorized',
      type: 'textarea',
      required: true,
      hint: 'Be specific — at least 20 characters.'
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
      <AutoGrowTextarea id={`complaint-${field.name}`} singleLine value={value} onChange={(event) => onChange(event.target.value)} />
      <FieldMessage hint={field.hint} error={error} />
    </div>
  );
}

function TextareaField({ field, value, onChange, error }) {
  return (
    <div className={`scheme-field complaint-field complaint-field-wide ${error ? 'complaint-field-error' : ''}`}>
      <label htmlFor={`complaint-${field.name}`}>{field.label}<RequiredMark required={field.required} /></label>
      <AutoGrowTextarea id={`complaint-${field.name}`} rows={3} value={value} onChange={(event) => onChange(event.target.value)} />
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
