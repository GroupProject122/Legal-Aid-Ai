// Run with: npm test  (node --test, no extra dependencies)
import assert from 'node:assert/strict';
import test from 'node:test';

import { buildMatchRequest, parseWholeNumber } from './api.js';

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
