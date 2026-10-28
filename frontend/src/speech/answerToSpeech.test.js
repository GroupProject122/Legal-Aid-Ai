// Run with: npm test  (node --test, no extra dependencies)
import assert from 'node:assert/strict';
import test from 'node:test';

import { answerToSpeechText, isSpeakableAnswer, pickVoice, speakable, splitIntoChunks } from './answerToSpeech.js';

const answer = (fields, extra = {}) => ({ answer: fields, sources: [{ document: 'The Information Technology Act, 2000' }], ...extra });

test('reads In short, then next steps, then where to approach -- in that order', () => {
  const text = answerToSpeechText(answer({
    issue_summary: 'This may be identity theft.',
    what_this_may_involve: ['Not read aloud.'],
    suggested_next_steps: ['Call 1930 immediately', 'Change your passwords'],
    where_to_approach: ['National Cyber Crime Reporting Portal'],
    evidence_to_preserve: ['Not read either'],
    limitations: ['Not read'],
  }));
  assert.equal(
    text,
    'This may be identity theft. Suggested next steps. Call 1930 immediately. Change your passwords. ' +
      'Where to approach. National Cyber Crime Reporting Portal.'
  );
});

test('uses legacy next_steps when suggested_next_steps is absent', () => {
  assert.match(answerToSpeechText(answer({ issue_summary: 'Summary.', next_steps: ['Keep the bill'] })), /Suggested next steps\. Keep the bill\.$/);
});

test('omits empty sections entirely', () => {
  assert.equal(answerToSpeechText(answer({ issue_summary: 'Only a summary', suggested_next_steps: [], where_to_approach: [] })), 'Only a summary.');
});

test('never reads sources, disclaimers or limitations', () => {
  const response = answer(
    { issue_summary: 'Summary.', suggested_next_steps: ['This is legal information, not legal advice.', 'File a complaint'] },
    { disclaimer: 'This is legal information, not professional legal advice.' }
  );
  const text = answerToSpeechText(response);
  assert.doesNotMatch(text, /legal advice|Information Technology Act/);
  assert.match(text, /File a complaint\./);
});

test('clarification questions, errors, offline results and empty answers are not speakable', () => {
  assert.equal(isSpeakableAnswer(answer({ issue_summary: 'x' }, { clarification: { needed: true, question: 'Which city?' } })), false);
  assert.equal(isSpeakableAnswer(answer({ issue_summary: 'x' }, { technical_error: true })), false);
  assert.equal(isSpeakableAnswer(answer({ issue_summary: 'x' }, { offline: true })), false);
  assert.equal(isSpeakableAnswer(answer({ issue_summary: '' })), false);
  assert.equal(isSpeakableAnswer(null), false);
  assert.equal(answerToSpeechText(answer({ issue_summary: 'x' }, { technical_error: true })), '');
});

test('links are replaced by "the link shown on screen"', () => {
  assert.equal(speakable('Report it at https://cybercrime.gov.in/Webform/Index.aspx today.'), 'Report it at the link shown on screen today.');
  assert.equal(speakable('Visit www.consumerhelpline.gov.in.'), 'Visit the link shown on screen');
  assert.equal(speakable('File on cybercrime.gov.in or edaakhil.nic.in/complaint'), 'File on the link shown on screen or the link shown on screen');
});

test('citation brackets are dropped', () => {
  assert.equal(speakable('You may claim compensation [1] under the Act [IT Act, s. 43].'), 'You may claim compensation under the Act.');
});

test('section numbers and legal abbreviations are read naturally', () => {
  assert.equal(speakable('See S. 69 and Sec. 66C'), 'See Section 69 and Section 66C');
  assert.equal(speakable('Ss. 66C and 66D apply'), 'Sections 66C and 66D apply');
  assert.equal(speakable('punishable u/s 420 r/w Art. 21'), 'punishable under Section 420 read with Article 21');
  assert.equal(speakable('Reg. 7 of the NALSA Regulations'), 'Regulation 7 of the NALSA Regulations');
  assert.equal(speakable('Section 69 already spelled out'), 'Section 69 already spelled out');
});

test('money and Latin abbreviations', () => {
  assert.equal(speakable('Claim Rs. 25,000 or ₹5000'), 'Claim 25,000 rupees or 5000 rupees');
  assert.equal(speakable('Keep proof, e.g. receipts, i.e. originals'), 'Keep proof, for example receipts, that is originals');
});

test('markdown and list numbering are stripped', () => {
  assert.equal(speakable('1. **Call** the `1930` helpline'), 'Call the 1930 helpline');
});

test('Hinglish in Latin letters passes through unchanged', () => {
  assert.equal(speakable('Bank ko turant call karein'), 'Bank ko turant call karein');
});

test('chunks stay under the limit and keep every word, in order', () => {
  const long = `${'This sentence is quite long and keeps going, with clauses; and more clauses, until it passes the limit'.repeat(3)}. Short one. Another short one!`;
  const chunks = splitIntoChunks(long, 80);
  assert.ok(chunks.length > 3);
  assert.ok(chunks.every((chunk) => chunk.length <= 80), chunks.map((c) => c.length).join(','));
  assert.equal(chunks.join(' ').replace(/\s+/g, ' '), long.replace(/\s+/g, ' '));
});

test('sentences are chunk boundaries; Section numbers do not split', () => {
  assert.deepEqual(splitIntoChunks('Read Section 69. Then call 1930. Done.'), ['Read Section 69.', 'Then call 1930.', 'Done.']);
  assert.deepEqual(splitIntoChunks(''), []);
});

test('voice choice: en-IN first, then any English voice, else none', () => {
  const voices = [{ lang: 'hi-IN' }, { lang: 'en-US', name: 'US' }, { lang: 'en_IN', name: 'India' }];
  assert.equal(pickVoice(voices).name, 'India');
  assert.equal(pickVoice([{ lang: 'fr-FR' }, { lang: 'en-GB', name: 'UK' }]).name, 'UK');
  assert.equal(pickVoice([{ lang: 'fr-FR' }]), null);
  assert.equal(pickVoice(undefined), null);
});
