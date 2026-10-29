/**
 * The step-1 questions on the Schemes page: only the four that scheme rules actually use (see
 * backend/data/schemes_clean.json). The API still accepts socialCategory and occupation as
 * optional, so they can come back if a rule ever needs them.
 */
export const STEP1_FIELDS = ['age', 'annualFamilyIncome', 'gender', 'residence'];

export const EMPTY_ANSWERS = Object.fromEntries(STEP1_FIELDS.map((field) => [field, '']));
