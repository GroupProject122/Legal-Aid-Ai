# Voice input — manual test checklist

`POST /api/transcribe` and the Ask page's mic button are covered by automated tests
(`backend/tests/test_voice_transcription.py`, `backend/tests/test_transcribe_endpoint.py`) and by
a Playwright run against a synthesized voice clip — but automated testing in this environment has
no real microphone or human voice. Transcription *quality* on real speech, accents, and real
devices needs a human tester, in a real Chrome/Edge/Safari browser, with a real microphone.

Run through all 15 clips below at least once before relying on this feature for a demo. For each,
speak the phrase naturally (don't over-enunciate), click the mic once to start, click again to
stop, and record what landed in the question box.

| # | What to say | Checking for | Pass? |
|---|---|---|---|
| 1 | "My landlord is not returning my security deposit." | Plain English, straightforward case | |
| 2 | "Mera landlord deposit nahi de raha." | Hinglish comes back in Latin letters, not Devanagari | |
| 3 | "Mujhe RTI ka jawab nahi mila, ab kya karu?" | Longer mixed Hindi/English sentence, question mark intonation doesn't break it | |
| 4 | Say the same sentence as #3 but in actual spoken Hindi (not Hinglish-accented English) | Still comes back in Latin letters (tests the Devanagari retry path for real, not mocked) | |
| 5 | "Consumer complaint." (very short, 1-2 words) | Doesn't error out on a very short clip; returns something or a clear "no speech" message | |
| 6 | Stay silent for 3-4 seconds, then stop | Returns the "No speech was detected" message, not a blank/garbled result | |
| 7 | "Someone hacked my Instagram and is asking for money, I don't know what to do, can you help me understand what are my options here" (long, 15-20s) | Full sentence comes through, not cut off; check latency is still reasonable | |
| 8 | Speak with noticeable background noise (TV, traffic, fan) | Transcript is still usable, or fails cleanly with a message rather than silently returning garbage | |
| 9 | Speak quietly / far from the mic | Same as above — usable or a clean failure, not garbage text sent to the pipeline | |
| 10 | A sentence mixing in a number/date: "Maine 15 August ko application diya tha" | Numbers/dates survive the transcription | |
| 11 | Click mic, then click stop within under 1 second (accidental tap) | No crash; either a short/empty transcript message or a very short real transcript | |
| 12 | Click mic, start speaking, then deny the permission prompt if your browser re-asks (or test on a profile where mic permission is blocked at the OS level) | Clean inline error ("Microphone access was denied...") and the button returns to idle | |
| 13 | Start a recording, then immediately navigate away from the Ask page (or close the tab) before stopping | No crash in the console; the mic stream is released (check the browser's mic-in-use indicator turns off) | |
| 14 | Record continuously for the full 60 seconds without stopping manually | Recording auto-stops at 60s and the clip is still sent for transcription | |
| 15 | Test in at least two different browsers (e.g. Chrome and Safari, or Chrome and Firefox) on the same device | Confirms the recorder's MIME-type fallback (`audio/webm` vs `audio/mp4` vs browser default) works on both | |

**Also worth one manual check, not a 60-second clip:** temporarily block network access to
`generativelanguage.googleapis.com` (or revoke the API key) and try clip #1 again — confirms the
endpoint actually returns 503 under a real failure (not just the mocked one used in automated
tests) and that the mic button correctly attempts the browser's own `en-IN` speech recognition as
a fallback. This requires a real Chrome/Edge build (Playwright's bundled Chromium does not ship
a working speech-recognition backend, so this path could only be wiring-tested, not fully
verified, during development — see the CHANGELOG entry for what was and wasn't confirmed).

## What "pass" means here

This checklist is about **not failing badly**, not about perfect transcription. Minor
misheard words are expected and fine — the transcript lands in an editable text box the user
reviews before sending. A "pass" means: no crash, no Devanagari text reaching the box, no
silent/blank submission, and a clear message whenever something couldn't be transcribed.
