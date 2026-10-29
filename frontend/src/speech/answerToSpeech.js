/**
 * Turns an Ask-page answer into text for the browser's speechSynthesis, and splits it into
 * sentence-sized chunks. Pure functions only -- no DOM, no speechSynthesis -- so they can be
 * unit-tested with `node --test` (see answerToSpeech.test.js).
 *
 * What is read, in order: "In short" (answer.issue_summary), then the suggested next steps, then
 * where to approach -- the parts a listener can act on. Skipped: sources, citation brackets,
 * disclaimers, limitations, and the raw text of URLs (read as "the link shown on screen").
 */

const LINK_PHRASE = 'the link shown on screen';

// Same rule the answer card uses to decide it is a full answer rather than a clarification
// question, a technical error, an offline result or a one-line acknowledgement.
export function isSpeakableAnswer(response) {
  if (!response || response.technical_error || response.offline) return false;
  if (response.clarification?.needed || response.clarification?.question) return false;
  const answer = response.answer || {};
  return Boolean(cleanText(answer.issue_summary));
}

export function answerToSpeechText(response) {
  if (!isSpeakableAnswer(response)) return '';
  const answer = response.answer || {};
  const parts = [ensureSentence(speakable(answer.issue_summary))];
  const steps = listItems(answer.next_steps || answer.suggested_next_steps);
  if (steps.length) parts.push('Suggested next steps.', ...steps.map(ensureSentence));
  const places = listItems(answer.where_to_approach);
  if (places.length) parts.push('Where to approach.', ...places.map(ensureSentence));
  return parts.filter(Boolean).join(' ');
}

function listItems(values) {
  return (Array.isArray(values) ? values : [])
    .map(speakable)
    .filter((item) => item && !isDisclaimer(item));
}

function isDisclaimer(text) {
  return /\b(not (professional )?legal advice|legal information,? not|does not constitute)\b/i.test(text);
}

function cleanText(value) {
  return String(value || '')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/__(.*?)__/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Normalises one piece of answer text for listening. Exported for tests. */
export function speakable(value) {
  let text = cleanText(value)
    // List numbering at the start ("1. ", "Step 2:") -- the voice reads items in order anyway.
    .replace(/^\s*(?:step\s*)?\d+\s*[).:-]\s+/i, '');

  // Citation brackets: "[1]", "[Source 2]", "[IT Act, s. 66C]".
  text = text.replace(/\s*\[[^\]]{1,80}\]/g, '');

  // Links: full URLs, www., and bare official-style domains ("cybercrime.gov.in/...").
  text = text
    .replace(/\bhttps?:\/\/\S+/gi, LINK_PHRASE)
    .replace(/\bwww\.\S+/gi, LINK_PHRASE)
    .replace(/\b[a-z0-9-]+(?:\.[a-z0-9-]+)*\.(?:gov\.in|nic\.in|org\.in|co\.in|in|com|org|net)\b(?:\/\S*)?/gi, LINK_PHRASE)
    .replace(new RegExp(`(${LINK_PHRASE})[.,;:)]+(?=\\s|$)`, 'g'), '$1');

  // Legal abbreviations, so "S. 69" is read "Section 69" rather than "S" followed by 69.
  text = text
    .replace(/\bu\/s\.?\s*/gi, 'under Section ')
    .replace(/\br\/w\b\.?/gi, 'read with')
    .replace(/\bSs\.\s*(?=\d)/g, 'Sections ')
    .replace(/\b(?:Secs?|S)\.\s*(?=\d)/gi, 'Section ')
    .replace(/\bArts?\.\s*(?=\d)/gi, 'Article ')
    .replace(/\bRegs?\.\s*(?=\d)/gi, 'Regulation ')
    .replace(/\bCls?\.\s*(?=\d)/gi, 'Clause ')
    .replace(/\bsub-s(?:ec)?\.\s*(?=\()/gi, 'sub-section ')
    .replace(/\bNo\.\s*(?=\d)/g, 'number ');

  // Money and common Latin abbreviations.
  text = text
    .replace(/(?:₹|\bRs\.?|\bINR)\s*([\d,]+(?:\.\d+)?)/gi, '$1 rupees')
    .replace(/\be\.g\.,?/gi, 'for example')
    .replace(/\bi\.e\.,?/gi, 'that is')
    .replace(/\betc\./gi, 'and so on');

  return text.replace(/\s+/g, ' ').replace(/\s+([.,;:])/g, '$1').trim();
}

function ensureSentence(text) {
  if (!text) return '';
  return /[.!?]$/.test(text) ? text : `${text}.`;
}

/**
 * Splits text into chunks no longer than maxLength: by sentence first, then at clause breaks
 * (; , :) for an over-long sentence, then by words. Chrome stops speaking a single long
 * utterance after roughly 15 seconds, so each chunk becomes its own SpeechSynthesisUtterance.
 */
export function splitIntoChunks(text, maxLength = 200) {
  const sentences = String(text || '')
    .replace(/\s+/g, ' ')
    .trim()
    .split(/(?<=[.!?])\s+(?=[A-Z0-9"“(])/)
    .map((sentence) => sentence.trim())
    .filter(Boolean);
  const chunks = [];
  for (const sentence of sentences) {
    if (sentence.length <= maxLength) {
      chunks.push(sentence);
      continue;
    }
    let current = '';
    for (const piece of sentence.split(/(?<=[;,:])\s+/)) {
      if (piece.length > maxLength) {
        if (current) chunks.push(current);
        current = '';
        chunks.push(...splitByWords(piece, maxLength));
      } else if (!current) {
        current = piece;
      } else if (current.length + 1 + piece.length <= maxLength) {
        current = `${current} ${piece}`;
      } else {
        chunks.push(current);
        current = piece;
      }
    }
    if (current) chunks.push(current);
  }
  return chunks;
}

function splitByWords(text, maxLength) {
  const out = [];
  let current = '';
  for (const word of text.split(' ')) {
    if (current && current.length + 1 + word.length > maxLength) {
      out.push(current);
      current = word;
    } else {
      current = current ? `${current} ${word}` : word;
    }
  }
  if (current) out.push(current);
  return out;
}

/** Picks an Indian English voice if there is one, else any English voice, else none (browser default). */
export function pickVoice(voices) {
  const list = Array.isArray(voices) ? voices : [];
  const lang = (voice) => String(voice.lang || '').replace('_', '-').toLowerCase();
  return list.find((voice) => lang(voice) === 'en-in')
    || list.find((voice) => lang(voice).startsWith('en'))
    || null;
}

export const SPEECH_RATES = [0.75, 1, 1.25];
