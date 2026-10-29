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

test('Tele-Law and the consumer e-filing portal (e-Jagriti) are listed with official https sources', () => {
  const teleLaw = helplines.find((entry) => entry.id === 'tele-law-14454');
  const eJagriti = helplines.find((entry) => entry.id === 'e-jagriti');
  assert.equal(teleLaw?.number, '14454');
  assert.equal(teleLaw?.domain, 'rights');
  assert.equal(eJagriti?.website, 'https://e-jagriti.gov.in');
  assert.equal(eJagriti?.domain, 'consumer');
});

test('every entry has an https source and a website or number', () => {
  for (const entry of helplines) {
    assert.match(entry.sourceUrl, /^https:\/\//, entry.id);
    assert.ok(entry.website || entry.number, entry.id);
    if (entry.website) assert.match(entry.website, /^https:\/\//, entry.id);
  }
});
