/**
 * Turns an assistant reply into text for the browser's speechSynthesis, and splits it into
 * sentence-sized chunks. Pure functions only -- no DOM, no speechSynthesis -- so they can be
 * unit-tested with `node --test` (see answerToSpeech.test.js).
 *
 * What is read: every section the reply card shows, in the same order as on screen, each
 * introduced by its visible heading ("In short.", "Suggested next steps." ...). Skipped: the
 * sources list, citation brackets, the disclaimer, and the raw text of URLs (read as "the link
 * shown on screen"). responseSpeechSections() mirrors LegalAIResponse in App.jsx -- change both
 * together.
 */

const LINK_PHRASE = 'the link shown on screen';

// Shown on screen when a field is missing, so they are read too. App.jsx renders these same
// constants, which keeps what is heard identical to what is seen.
export const DISPLAY_FALLBACKS = {
  summary: 'The available legal sources do not contain enough information to answer this reliably.',
  technicalError: 'Legal Aid AI could not process your request right now. Please check that the backend and Gemini API are configured correctly and try again.',
  offlineNotice: 'You are currently offline. Retrieving the relevant legal section, case, corpus, and law locally from the database and local files.',
  offlineNoMatches: 'No relevant sections were found in the local legal corpus for this question.',
  offlineNoExcerpt: 'No excerpt is available for this source.',
  conversational: 'You can ask a follow-up question whenever you like.'
};

/**
 * The reply as [{ heading, items, ordered }], in screen order, empty sections left out.
 * `hints` are the extra one-line links the card shows under some answers (the 1930 line, the
 * free-legal-aid check); App.jsx decides which are visible and passes their text.
 */
export function responseSpeechSections(response, { hints = [] } = {}) {
  if (!response) return [];
  const answer = response.answer || {};
  const sections = [];
  const add = (heading, values, { ordered = false } = {}) => {
    const items = listItems(values);
    if (items.length) sections.push({ heading, items, ordered });
  };

  if (response.offline) {
    const sources = response.sources || [];
    add('Offline mode', [response.offline_notice || DISPLAY_FALLBACKS.offlineNotice]);
    // "Sections matched to your question" is the list of source cards: skipped like any sources list.
    if (sources.length) {
      add('The section text, as retrieved', sources.flatMap((source) => [
        [source.document, source.section, source.page ? `page ${source.page}` : null].map(cleanText).filter(Boolean).join(', '),
        source.full_text || source.excerpt || DISPLAY_FALLBACKS.offlineNoExcerpt
      ]));
    } else {
      add('No local matches', [DISPLAY_FALLBACKS.offlineNoMatches]);
    }
    return sections;
  }

  if (response.technical_error) {
    add('Request could not be processed', [cleanText(answer.issue_summary) || DISPLAY_FALLBACKS.technicalError]);
    add('What to check', answer.next_steps || answer.suggested_next_steps, { ordered: true });
    return sections;
  }

  const turnType = response.conversation?.turn_type;
  if (turnType === 'acknowledgement' || turnType === 'small_talk') {
    add('', [cleanText(answer.issue_summary) || DISPLAY_FALLBACKS.conversational]);
    return sections;
  }

  add('In short', [cleanText(answer.issue_summary) || DISPLAY_FALLBACKS.summary]);
  add('What this may involve', answer.what_this_may_involve);
  const clarificationQuestion = cleanText(response.clarification?.question);
  if (clarificationQuestion) {
    // A clarification question replaces the rest of the answer on screen.
    add('Clarification needed', [clarificationQuestion]);
    return sections;
  }
  add('Your possible rights', answer.possible_rights || answer.possible_legal_position);
  add('Suggested next steps', answer.next_steps || answer.suggested_next_steps, { ordered: true });
  add('Evidence to preserve', answer.evidence_to_preserve);
  add('Where to approach', answer.where_to_approach);
  add('Limitations', answer.limitations);
  // "Sources used" sits here on screen: skipped.
  add('Document facts used', (response.document_evidence_used || []).map((fact) => [
    [cleanText(fact.label), cleanText(fact.value)].filter(Boolean).join(': '),
    fact.source_page ? `document page ${fact.source_page}` : null
  ].filter(Boolean).join(', ')));
  add('', hints);
  return sections;
}

export function answerToSpeechText(response, options) {
  const parts = [];
  for (const section of responseSpeechSections(response, options)) {
    if (section.heading) parts.push(`${section.heading}.`);
    section.items.forEach((item, position) => {
      parts.push(ensureSentence(section.ordered ? `Step ${position + 1}. ${item}` : item));
    });
  }
  return parts.join(' ');
}

/** True when the reply has anything to read; the Listen button is hidden otherwise. */
export function isSpeakableResponse(response, options) {
  return Boolean(answerToSpeechText(response, options));
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
    .replace(/<svg\b[^>]*>.*?<\/svg>/gis, ' ')
    .replace(/\*\*(.*?)\*\*/g, '$1')
    .replace(/__(.*?)__/g, '$1')
    .replace(/`([^`]*)`/g, '$1')
    .replace(/\s+/g, ' ')
    .trim();
}

/** Normalises one piece of answer text for listening. Exported for tests. */
export function speakable(value) {
  let text = cleanText(value)
    // List numbering at the start ("1. ", "Step 2:") -- steps get a spoken "Step N." instead.
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
    .replace(/(?:₹|\bRs\.?|\bINR)\s*(\d(?:[\d,]*\d)?(?:\.\d+)?)/gi, '$1 rupees')
    .replace(/\be\.g\.,?/gi, 'for example')
    .replace(/\bi\.e\.,?/gi, 'that is')
    .replace(/\betc\./gi, 'and so on');

  // Separators some voices read out by name ("middle dot", "em dash").
  text = text.replace(/\s*[·—|]\s*/g, ', ');

  return text.replace(/\s+/g, ' ').replace(/\s+([.,;:])/g, '$1').replace(/,{2,}/g, ',').trim();
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
