// Run with: npm test  (node --test, no extra dependencies)
import assert from 'node:assert/strict';
import test from 'node:test';

import {
  answerToSpeechText,
  DISPLAY_FALLBACKS,
  isSpeakableResponse,
  pickVoice,
  responseSpeechSections,
  speakable,
  splitIntoChunks
} from './answerToSpeech.js';

const answer = (fields, extra = {}) => ({ answer: fields, sources: [{ document: 'The Information Technology Act, 2000', section: 'Section 66C', page: 12 }], ...extra });

const fullAnswer = answer(
  {
    issue_summary: 'This may be identity theft.',
    what_this_may_involve: ['Someone used your details'],
    possible_rights: ['You can report it'],
    suggested_next_steps: ['Call 1930 immediately', 'Change your passwords'],
    evidence_to_preserve: ['Screenshots of the messages'],
    where_to_approach: ['National Cyber Crime Reporting Portal'],
    limitations: ['Based only on what you told us']
  },
  {
    document_evidence_used: [{ label: 'Amount', value: 'Rs. 25,000', source_page: 2 }],
    disclaimer: 'This is legal information, not professional legal advice.'
  }
);

test('reads every visible section, in screen order, each after its heading', () => {
  assert.equal(
    answerToSpeechText(fullAnswer, { hints: ['Lost money to online fraud? Call 1930 as soon as possible.'] }),
    'In short. This may be identity theft. ' +
      'What this may involve. Someone used your details. ' +
      'Your possible rights. You can report it. ' +
      'Suggested next steps. Step 1. Call 1930 immediately. Step 2. Change your passwords. ' +
      'Evidence to preserve. Screenshots of the messages. ' +
      'Where to approach. National Cyber Crime Reporting Portal. ' +
      'Limitations. Based only on what you told us. ' +
      'Document facts used. Amount: 25,000 rupees, document page 2. ' +
      'Lost money to online fraud? Call 1930 as soon as possible.'
  );
});

test('never reads the sources list, the disclaimer or disclaimer-like list items', () => {
  const text = answerToSpeechText(answer(
    { issue_summary: 'Summary.', suggested_next_steps: ['This is legal information, not legal advice.', 'File a complaint'] },
    { disclaimer: 'This is legal information, not professional legal advice.' }
  ));
  assert.doesNotMatch(text, /legal advice|Information Technology Act|Sources used|Section 66C|page 12/);
  assert.equal(text, 'In short. Summary. Suggested next steps. Step 1. File a complaint.');
});

test('empty sections are skipped, heading and all', () => {
  assert.equal(
    answerToSpeechText(answer({ issue_summary: 'Only a summary', what_this_may_involve: [], suggested_next_steps: ['', '  '], where_to_approach: [] })),
    'In short. Only a summary.'
  );
  assert.equal(answerToSpeechText(answer({ issue_summary: 'Summary.', next_steps: ['Keep the bill'] })), 'In short. Summary. Suggested next steps. Step 1. Keep the bill.');
});

test('a missing summary is read as the fallback shown on screen', () => {
  assert.equal(answerToSpeechText(answer({})), `In short. ${DISPLAY_FALLBACKS.summary}`);
});

test('clarification question: In short, What this may involve, then the question -- nothing after', () => {
  const text = answerToSpeechText(answer(
    { issue_summary: 'I need one detail.', what_this_may_involve: ['A deposit dispute'], suggested_next_steps: ['Hidden on screen'] },
    { clarification: { needed: true, question: 'Which city do you live in?' } }
  ), { hints: [] });
  assert.equal(text, 'In short. I need one detail. What this may involve. A deposit dispute. Clarification needed. Which city do you live in?');
});

test('out-of-scope / cannot-answer replies are read like any answer', () => {
  const text = answerToSpeechText(answer(
    { issue_summary: 'I can only help with Indian consumer, tenancy, cyber and fundamental-rights questions.', suggested_next_steps: ['Ask a lawyer about this'] },
    { insufficient_context: true, routing: { status: 'out_of_scope', domains: [] } }
  ));
  assert.equal(text, 'In short. I can only help with Indian consumer, tenancy, cyber and fundamental-rights questions. Suggested next steps. Step 1. Ask a lawyer about this.');
});

test('technical-error reply: its own headings', () => {
  assert.equal(
    answerToSpeechText({ answer: { issue_summary: '', next_steps: ['Check the backend.'] }, technical_error: true }),
    `Request could not be processed. ${DISPLAY_FALLBACKS.technicalError} What to check. Step 1. Check the backend.`
  );
});

test('offline result: notice, then each retrieved section text; the matched-sources list is skipped', () => {
  const text = answerToSpeechText({
    offline: true,
    offline_notice: 'You are offline.',
    sources: [{ document: 'Consumer Protection Act, 2019', section: 'S. 35', page: 20, full_text: 'A complaint may be filed.' }]
  });
  assert.equal(text, 'Offline mode. You are offline. The section text, as retrieved. Consumer Protection Act, 2019, Section 35, page 20. A complaint may be filed.');
  assert.equal(answerToSpeechText({ offline: true, sources: [] }), `Offline mode. ${DISPLAY_FALLBACKS.offlineNotice} No local matches. ${DISPLAY_FALLBACKS.offlineNoMatches}`);
});

test('short conversational reply is read without a heading', () => {
  assert.equal(answerToSpeechText({ answer: { issue_summary: 'You are welcome.' }, conversation: { turn_type: 'acknowledgement' } }), 'You are welcome.');
});

test('every kind of reply is speakable; nothing to read only for no response', () => {
  assert.equal(isSpeakableResponse(answer({ issue_summary: 'x' }, { clarification: { needed: true, question: 'Which city?' } })), true);
  assert.equal(isSpeakableResponse({ answer: {}, technical_error: true }), true);
  assert.equal(isSpeakableResponse({ offline: true, sources: [] }), true);
  assert.equal(isSpeakableResponse(null), false);
  assert.deepEqual(responseSpeechSections(undefined), []);
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
  assert.equal(speakable('Rs. 25,000, paid by UPI'), '25,000 rupees, paid by UPI');
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
