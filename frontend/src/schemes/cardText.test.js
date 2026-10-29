// Run with: npm test  (node --test, no extra dependencies)
import assert from 'node:assert/strict';
import test from 'node:test';

import { benefitSummary, GROUP_LABELS } from './cardText.js';

test('the summary is the first sentence of the benefits', () => {
  assert.equal(
    benefitSummary('Collateral-free institutional credit for eligible micro-enterprise activities. Loan categories include Shishu, Kishore, Tarun and Tarun Plus.'),
    'Collateral-free institutional credit for eligible micro-enterprise activities.'
  );
  assert.equal(benefitSummary('₹6,000 per year in three instalments for eligible farmer families.'), '₹6,000 per year in three instalments for eligible farmer families.');
});

test('a long first sentence is cut at a word with an ellipsis', () => {
  const summary = benefitSummary('Support for eligible children who lost both parents, surviving parent, or legal guardian due to COVID-19, subject to the scheme\'s specific conditions.', 80);
  assert.ok(summary.length <= 80, summary);
  assert.ok(summary.endsWith('…'));
  assert.ok(!summary.endsWith(' …') && !summary.endsWith(',…'));
});

test('every result group has a badge label', () => {
  assert.deepEqual(Object.keys(GROUP_LABELS).sort(), ['check_with_authority', 'likely_eligible', 'might_be_eligible', 'not_eligible']);
});
