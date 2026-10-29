import { pickVoice, SPEECH_RATES } from './answerToSpeech.js';

/**
 * One speaker for the whole app, so only one answer is ever read at a time. Components subscribe
 * with useSyncExternalStore (see ListenControls.jsx); anything can call stopSpeech().
 *
 * Each chunk is its own SpeechSynthesisUtterance (Chrome cuts long utterances off). Pause cancels
 * the current chunk and remembers its index; resume re-speaks that chunk from its start -- more
 * reliable across chunks than speechSynthesis.pause()/resume(), which Chrome handles poorly.
 * A generation counter makes sure an utterance cancelled by pause/stop/new playback can't
 * advance or restart anything from its late onend/onerror callback.
 */

const RATE_STORAGE_KEY = 'legalAidSpeechRate';

const synth = typeof window !== 'undefined' && 'speechSynthesis' in window && typeof window.SpeechSynthesisUtterance === 'function'
  ? window.speechSynthesis
  : null;

export const speechSupported = Boolean(synth);

let state = { activeId: null, status: 'idle', rate: readStoredRate() }; // status: idle | playing | paused
let chunks = [];
let index = 0;
let generation = 0;
const listeners = new Set();

function readStoredRate() {
  try {
    const stored = Number(window.localStorage.getItem(RATE_STORAGE_KEY));
    return SPEECH_RATES.includes(stored) ? stored : 1;
  } catch {
    return 1;
  }
}

function setState(next) {
  state = { ...state, ...next };
  listeners.forEach((listener) => listener());
}

export function subscribe(listener) {
  listeners.add(listener);
  return () => listeners.delete(listener);
}

export function getSnapshot() {
  return state;
}

// Voices load asynchronously in Chrome: getVoices() is often empty until voiceschanged fires.
let voices = synth ? synth.getVoices() : [];
if (synth) {
  synth.addEventListener?.('voiceschanged', () => {
    voices = synth.getVoices();
  });
}

function speakFrom(position) {
  const myGeneration = ++generation;
  index = position;
  if (index >= chunks.length) {
    setState({ activeId: null, status: 'idle' });
    return;
  }
  const utterance = new window.SpeechSynthesisUtterance(chunks[index]);
  const voice = pickVoice(voices.length ? voices : synth.getVoices());
  if (voice) {
    utterance.voice = voice;
    utterance.lang = voice.lang;
  } else {
    utterance.lang = 'en-IN';
  }
  utterance.rate = state.rate;
  utterance.onend = () => {
    if (myGeneration === generation) speakFrom(index + 1);
  };
  utterance.onerror = (event) => {
    // "interrupted"/"canceled" are our own cancel() calls; anything else ends playback.
    if (myGeneration !== generation || event?.error === 'interrupted' || event?.error === 'canceled') return;
    setState({ activeId: null, status: 'idle' });
  };
  synth.speak(utterance);
}

export function play(id, textChunks) {
  if (!synth || !textChunks.length) return;
  generation += 1;
  synth.cancel();
  chunks = textChunks;
  setState({ activeId: id, status: 'playing' });
  speakFrom(0);
}

export function pause() {
  if (!synth || state.status !== 'playing') return;
  generation += 1; // the cancelled chunk's onend must not advance
  synth.cancel();
  setState({ status: 'paused' });
}

export function resume() {
  if (!synth || state.status !== 'paused') return;
  setState({ status: 'playing' });
  speakFrom(index);
}

export function stopSpeech() {
  if (!synth) return;
  generation += 1;
  synth.cancel();
  chunks = [];
  index = 0;
  if (state.activeId !== null || state.status !== 'idle') setState({ activeId: null, status: 'idle' });
}

export function setRate(rate) {
  if (!SPEECH_RATES.includes(rate)) return;
  try {
    window.localStorage.setItem(RATE_STORAGE_KEY, String(rate));
  } catch {
    // Storage unavailable (private window, blocked site data): the speed still applies this visit.
  }
  setState({ rate });
  // Apply to the chunk being read now: restart it at the new speed.
  if (state.status === 'playing') speakFrom(index);
}

if (synth && typeof window !== 'undefined') {
  // Leaving or reloading the page: browsers otherwise keep speaking after navigation.
  window.addEventListener('pagehide', stopSpeech);
}
