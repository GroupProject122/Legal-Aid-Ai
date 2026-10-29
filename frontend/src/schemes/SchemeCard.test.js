// Run with: npm test  (node --test). Renders SchemeCard with react-dom/server. The .jsx is
// compiled on the fly with esbuild (which ships with Vite) into node_modules/.cache, so 'react'
// and 'lucide-react' resolve normally -- no extra test dependency.
import assert from 'node:assert/strict';
import { mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import test from 'node:test';
import { fileURLToPath, pathToFileURL } from 'node:url';

import { build } from 'esbuild';
import React from 'react';
import { renderToStaticMarkup } from 'react-dom/server';

const here = dirname(fileURLToPath(import.meta.url));
const outDir = join(here, '..', '..', 'node_modules', '.cache', 'schemes-card-test');
mkdirSync(outDir, { recursive: true });
const outFile = join(outDir, 'SchemeCard.mjs');
await build({
  entryPoints: [join(here, 'SchemeCard.jsx')],
  outfile: outFile,
  bundle: true,
  format: 'esm',
  platform: 'node',
  jsx: 'automatic',
  external: ['react', 'react-dom', 'lucide-react'],
  logLevel: 'silent'
});
const { default: SchemeCard } = await import(pathToFileURL(outFile).href);

const scheme = {
  id: 'PMAY-U-2.0',
  name: 'Pradhan Mantri Awas Yojana - Urban 2.0',
  category: 'housing',
  area: 'Housing',
  benefits: 'Housing assistance through applicable scheme components for eligible urban households. Second sentence here.',
  eligibilitySummary: 'Eligible urban households.',
  group: 'might_be_eligible',
  reason: 'Nothing in your answers rules this out.',
  questions: [{ field: 'familyOwnsPuccaHouseInIndia', question: 'Does anyone in your family own a pucca (permanent) house anywhere in India?', type: 'yes_no' }],
  authorityChecks: [],
  whatTheyMayAsk: ['Your age'],
  officialUrl: 'https://pmay-urban.gov.in/',
  sourceUrl: 'https://pmay-urban.gov.in/',
  lastVerified: null
};

const render = (open) => renderToStaticMarkup(React.createElement(SchemeCard, { scheme, open, onToggle() {}, profileAnswers: {}, onChecked() {} }));

function toggleButton(html) {
  return html.match(/<button type="button" class="schemes-card-toggle"[^>]*>/)[0];
}

function detailsOpeningTag(html, id) {
  return html.match(new RegExp(`<div id="${id.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}"[^>]*>`))[0];
}

test('collapsed: name heading, badge, one-line summary, chevron button with aria-expanded=false; details hidden', () => {
  const html = render(false);
  assert.match(html, /<h4>Pradhan Mantri Awas Yojana - Urban 2\.0<\/h4>/);
  assert.match(html, /class="schemes-badge schemes-badge-might_be_eligible">You might be eligible</);
  assert.match(html, /class="schemes-card-summary">Housing assistance through applicable scheme components for eligible urban households\.</);
  const button = toggleButton(html);
  assert.match(button, /aria-expanded="false"/);
  assert.match(button, /aria-label="Show details for Pradhan Mantri Awas Yojana - Urban 2\.0"/);
  const controls = button.match(/aria-controls="([^"]+)"/)[1];
  assert.match(detailsOpeningTag(html, controls), /hidden=""/);
  assert.doesNotMatch(html, /class="schemes-card[^"]*is-open/);
});

test('expanded: aria-expanded=true, details visible with everything, no summary line', () => {
  const html = render(true);
  const button = toggleButton(html);
  assert.match(button, /aria-expanded="true"/);
  assert.match(button, /aria-label="Hide details for/);
  const controls = button.match(/aria-controls="([^"]+)"/)[1];
  assert.doesNotMatch(detailsOpeningTag(html, controls), /hidden/);
  assert.doesNotMatch(html, /schemes-card-summary/);
  for (const part of ['Second sentence here.', 'Nothing in your answers rules this out.', 'Quick questions',
    'Does anyone in your family own a pucca', 'What they may ask you', 'Official website', 'Not yet verified']) {
    assert.ok(html.includes(part), part);
  }
  assert.match(html, /class="schemes-card schemes-card-might_be_eligible is-open"/);
});

test('the toggle is a real button and the name stays a heading in both states', () => {
  for (const open of [false, true]) {
    const html = render(open);
    assert.equal((html.match(/<button type="button" class="schemes-card-toggle"/g) || []).length, 1);
    assert.equal((html.match(/<h4>/g) || []).length, 1);
  }
});
