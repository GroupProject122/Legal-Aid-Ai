import { pickVoice, SPEECH_RATES } from './answerToSpeech.js';

/**
 * One speaker for the whole app, so only one reply is ever read at a time. Components subscribe
 * with useSyncExternalStore (see ListenControls.jsx); anything can call stopSpeech().
 *
 * Each chunk is its own SpeechSynthesisUtterance, spoken when the previous one ends. Pause
 * cancels the current chunk and remembers its index; resume re-speaks that chunk from its start
 * -- more reliable across chunks than speechSynthesis.pause()/resume(), which Chrome handles
 * poorly. A generation counter makes sure an utterance cancelled by pause/stop/speed change/new
 * playback can't advance or restart anything from its late onend/onerror callback.
 *
 * Long replies in Chrome need three more things, all here so a reply plays to the end:
 * - the utterance being spoken is held in `currentUtterance`: Chrome can garbage-collect an
 *   utterance nothing references and then never fire its onend, which silently stops playback;
 * - a chunk that fails (onerror) is skipped rather than ending the whole reply;
 * - a once-a-second tick: a keep-alive (pause()+resume() after 10 s of one chunk -- Chrome cuts
 *   continuous speech off at about 15 s) and a watchdog that moves on if Chrome has gone quiet
 *   without firing onend.
 */

const RATE_STORAGE_KEY = 'legalAidSpeechRate';
const KEEP_ALIVE_MS = 10000;
const STALL_MS = 1500;

const synth = typeof window !== 'undefined' && 'speechSynthesis' in window && typeof window.SpeechSynthesisUtterance === 'function'
  ? window.speechSynthesis
  : null;

export const speechSupported = Boolean(synth);

// On Android, speechSynthesis.pause() stops the utterance outright, so no keep-alive there.
const keepAliveSafe = typeof navigator !== 'undefined' && !/Android/i.test(navigator.userAgent || '');

let state = { activeId: null, status: 'idle', rate: readStoredRate() }; // status: idle | playing | paused
let chunks = [];
let index = 0;
let generation = 0;
let currentUtterance = null;
let chunkStartedAt = 0;
let lastKeepAliveAt = 0;
let ticker = null;
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
  if (state.status === 'playing') startTicker();
  else stopTicker();
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
    currentUtterance = null;
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
  utterance.onerror = () => {
    // Our own cancel() calls (pause, stop, speed change, another reply) always bump the
    // generation first, so they stop here. Any other failure skips just this chunk.
    if (myGeneration === generation) speakFrom(index + 1);
  };
  currentUtterance = utterance;
  chunkStartedAt = Date.now();
  lastKeepAliveAt = chunkStartedAt;
  synth.speak(utterance);
}

function tick() {
  if (state.status !== 'playing' || !currentUtterance) return;
  const now = Date.now();
  if (!synth.speaking && !synth.pending && now - chunkStartedAt > STALL_MS) {
    speakFrom(index + 1); // went quiet without onend: carry on with the next chunk
    return;
  }
  if (keepAliveSafe && synth.speaking && !synth.paused && now - lastKeepAliveAt >= KEEP_ALIVE_MS) {
    lastKeepAliveAt = now;
    synth.pause();
    synth.resume();
  }
}

function startTicker() {
  if (!ticker) ticker = window.setInterval(tick, 1000);
}

function stopTicker() {
  if (ticker) window.clearInterval(ticker);
  ticker = null;
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
  currentUtterance = null;
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
  currentUtterance = null;
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
  // Apply to the chunk being read now: cancel it and read it again at the new speed.
  if (state.status === 'playing') {
    generation += 1;
    synth.cancel();
    speakFrom(index);
  }
}

if (synth && typeof window !== 'undefined') {
  // Leaving or reloading the page: browsers otherwise keep speaking after navigation.
  window.addEventListener('pagehide', stopSpeech);
}
