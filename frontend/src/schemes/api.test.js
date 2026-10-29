// Run with: npm test  (node --test, no extra dependencies)
import assert from 'node:assert/strict';
import test from 'node:test';

import { buildCheckAnswers, buildMatchRequest, parseWholeNumber } from './api.js';

test('skipped questions are left out of the request', () => {
  assert.deepEqual(buildMatchRequest({ age: '', gender: '', residence: 'rural', annualFamilyIncome: '' }, []), {
    residence: 'rural',
    areas: []
  });
});

test('numbers are parsed, including Indian digit grouping and a rupee sign', () => {
  assert.deepEqual(
    buildMatchRequest({ age: ' 25 ', annualFamilyIncome: '₹1,50,000', gender: 'female' }, ['housing']),
    { age: 25, annualFamilyIncome: 150000, gender: 'female', areas: ['housing'] }
  );
  assert.equal(parseWholeNumber('Rs. 6,00,000'), 600000);
});

test('values that are not whole numbers are treated as unanswered, not guessed', () => {
  for (const value of ['twenty', '25.5', '-3', '', null, undefined]) {
    assert.equal(parseWholeNumber(value), null);
  }
});

test('step 1 asks only the four questions that scheme rules use', async () => {
  const { STEP1_FIELDS, EMPTY_ANSWERS } = await import('./questions.js');
  assert.deepEqual([...STEP1_FIELDS].sort(), ['age', 'annualFamilyIncome', 'gender', 'residence']);
  assert.deepEqual(Object.keys(EMPTY_ANSWERS).sort(), [...STEP1_FIELDS].sort());
  // The API still takes the other two if they are ever sent.
  assert.deepEqual(buildMatchRequest({ socialCategory: 'sc', occupation: 'farmer' }, []), { socialCategory: 'sc', occupation: 'farmer', areas: [] });
});

test('quick-question answers: yes/no become true/false, numbers are parsed, blanks are left out', () => {
  const questions = [
    { field: 'familyOwnsPuccaHouseInIndia', type: 'yes_no' },
    { field: 'cultivableLandHectares', type: 'number' },
    { field: 'residence', type: 'choice' },
    { field: 'girlChildAge', type: 'number' }
  ];
  assert.deepEqual(
    buildCheckAnswers({ age: '30', annualFamilyIncome: '6,00,000', gender: '', residence: '' },
      { familyOwnsPuccaHouseInIndia: 'no', cultivableLandHectares: '1.5', residence: 'urban', girlChildAge: '' }, questions),
    { age: 30, annualFamilyIncome: 600000, familyOwnsPuccaHouseInIndia: false, cultivableLandHectares: 1.5, residence: 'urban' }
  );
});
