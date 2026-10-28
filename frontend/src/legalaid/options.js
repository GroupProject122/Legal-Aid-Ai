// Plain-language labels for the "Which of these apply to you?" step. Values must match
// backend/legal_aid_eligibility.py's Category enum exactly. "Child" is deliberately not here:
// the backend works it out from the age the user gives (under 18), and nothing else -- gender
// included -- is ever inferred. The user ticks what applies.
//
// Never ask for certificates, Aadhaar or any ID number on this page.
export const CATEGORY_OPTIONS = [
  { value: 'woman', label: 'I am a woman' },
  { value: 'sc_st', label: 'I belong to a Scheduled Caste or Scheduled Tribe (SC/ST)' },
  { value: 'disability', label: 'I have a disability' },
  { value: 'in_custody', label: 'I am in custody', hint: 'Jail, lock-up, protective home, juvenile home, or a psychiatric hospital or nursing home.' },
  { value: 'industrial_workman', label: 'I am an industrial worker (workman)' },
  { value: 'trafficking_or_begar', label: 'I am a victim of human trafficking or forced unpaid labour (begar)' },
  { value: 'disaster_victim', label: 'I am a victim of a disaster or violence', hint: 'Mass disaster, ethnic violence, caste atrocity, flood, drought, earthquake or industrial disaster.' },
  { value: 'transgender', label: 'I am a transgender person' },
  { value: 'acid_attack_victim', label: 'I am an acid attack survivor' },
  { value: 'hiv_aids', label: 'I am living with, or affected by, HIV/AIDS' },
  { value: 'defence_family', label: 'I am serving or retired defence personnel, or from their family' }
];

export const RESULT_STYLES = {
  likely_eligible: { label: 'Likely eligible', tone: 'eligible' },
  likely_not_eligible: { label: 'Probably not eligible', tone: 'not-eligible' },
  cannot_determine: { label: 'We can’t tell from here', tone: 'unknown' }
};

export const MIN_AGE = 0;
export const MAX_AGE = 120;
