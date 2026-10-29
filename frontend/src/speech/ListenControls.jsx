import React from 'react';
import { Pause, Play, Square, Volume2 } from 'lucide-react';

import { answerToSpeechText, isSpeakableAnswer, SPEECH_RATES, splitIntoChunks } from './answerToSpeech.js';
import { getSnapshot, pause, play, resume, setRate, speechSupported, stopSpeech, subscribe } from './speechController.js';

export function useSpeechState() {
  return React.useSyncExternalStore(subscribe, getSnapshot, getSnapshot);
}

/**
 * "Listen" for one assistant answer. Renders nothing when the browser has no speechSynthesis or
 * the answer isn't a full answer (clarification question, error, offline result). Never
 * auto-plays: speech only starts from the Listen button.
 */
export function ListenControls({ speechId, response }) {
  const speech = useSpeechState();
  const text = React.useMemo(() => answerToSpeechText(response), [response]);
  if (!speechSupported || !isSpeakableAnswer(response) || !text) return null;

  const isActive = speech.activeId === speechId;
  const isPlaying = isActive && speech.status === 'playing';
  const isPaused = isActive && speech.status === 'paused';

  if (!isActive) {
    return (
      <div className="listen-controls">
        <button
          type="button"
          className="listen-button"
          aria-pressed="false"
          aria-label="Listen to this answer"
          onClick={() => play(speechId, splitIntoChunks(text))}
        >
          <Volume2 size={15} strokeWidth={1.9} aria-hidden="true" />
          <span>Listen</span>
        </button>
      </div>
    );
  }

  return (
    <div className="listen-controls is-active" role="group" aria-label="Reading this answer aloud">
      <span className="listen-status" role="status">
        <Volume2 size={14} strokeWidth={1.9} aria-hidden="true" />
        {isPaused ? 'Paused' : 'Reading aloud'}
      </span>
      <button
        type="button"
        className="listen-button"
        aria-pressed={isPlaying}
        aria-label={isPlaying ? 'Pause reading' : 'Resume reading'}
        onClick={isPlaying ? pause : resume}
      >
        {isPlaying ? <Pause size={15} strokeWidth={1.9} aria-hidden="true" /> : <Play size={15} strokeWidth={1.9} aria-hidden="true" />}
        <span>{isPlaying ? 'Pause' : 'Resume'}</span>
      </button>
      <button type="button" className="listen-button" aria-label="Stop reading" onClick={stopSpeech}>
        <Square size={13} strokeWidth={1.9} aria-hidden="true" />
        <span>Stop</span>
      </button>
      <div className="listen-rates" role="group" aria-label="Reading speed">
        {SPEECH_RATES.map((rate) => (
          <button
            type="button"
            key={rate}
            className="listen-rate"
            aria-pressed={speech.rate === rate}
            aria-label={`Speed ${rate}x`}
            onClick={() => setRate(rate)}
          >
            {rate}x
          </button>
        ))}
      </div>
    </div>
  );
}
