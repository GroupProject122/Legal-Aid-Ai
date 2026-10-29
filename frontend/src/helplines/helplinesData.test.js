// Run with: npm test  (node --test, no extra dependencies)
import assert from 'node:assert/strict';
import test from 'node:test';

import helplines from './helplinesData.js';

test('the 112 / ERSS entry is not listed (owner decision, 2026-10-29)', () => {
  assert.equal(helplines.some((entry) => entry.id === 'erss-112' || entry.number === '112'), false);
  assert.equal(helplines.some((entry) => /Emergency Response Support System|\bERSS\b/.test(entry.name)), false);
});

test('the Urgent section still has entries, each with a number to call', () => {
  const urgent = helplines.filter((entry) => entry.domain === 'urgent');
  assert.ok(urgent.length > 0);
  for (const entry of urgent) assert.match(entry.number, /^\d+$/);
});
