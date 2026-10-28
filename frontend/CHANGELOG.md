# Frontend Changelog

Notes on notable frontend changes so the team can see what moved and why.
Entries up to and including 2026-09-06 only touch `frontend/src/App.jsx` and
`frontend/src/styles.css`; later entries may add new files (noted per entry).

## 2026-10-28 — Free Legal Aid Check page (`#/legal-aid`)

New files: `src/legalaid/LegalAidCheck.jsx`, `src/legalaid/api.js`, `src/legalaid/options.js`.
Rules, sources, assumptions and the privacy design are in the root `CHANGELOG.md`'s "Free Legal
Aid Eligibility Checker" entry.

- **Where:**
  - a "Free Legal Aid Check" sidebar item (after Check a Message);
  - a home-page feature card;
  - an About page feature entry;
  - on the Ask page, a one-line link "Check if you qualify for free legal aid". It appears when
    the answer's `routing.domains` includes `constitutional_public_authority` and the user's own
    question (already on screen) mentions legal aid, a free lawyer, NALSA, DLSA or DSLSA. The
    link reuses the `.response-cyber-hint` style; nothing new is sent to the backend.
- **Wizard:**
  1. In Delhi?
  2. In the Supreme Court?
  3. Which of these apply? Checkboxes in plain language, with an exclusive "None of these".
  4. Age.
  5. Annual income, shown only when the API answers `needs: ["annual_income"]`. The eligibility
     rules are never duplicated in the frontend.

  Native radios, checkboxes and inputs inside a `fieldset`/`legend`. Focus moves to each new
  question's heading, and then to the result heading. Back and Next buttons; Enter submits.
- **Privacy:** step 1 says "Your answers are not saved." Nothing goes into `localStorage` or
  `sessionStorage`. The page never asks for certificates, Aadhaar or ID numbers.
- **Result card:**
  - green, red or grey for likely eligible, probably not eligible, or can't tell;
  - the reason, plus each matched rule with its source. Section 12 opens
    `#/rights/source/…/provision/section-12` in the source viewer; DSLSA rules open the official
    website in a new tab;
  - where to apply (`tel:` links for 1516 and 15100), what to bring, and alternatives when not
    eligible;
  - a "Good to know" box for assumptions, the disclaimer, "Rules last checked" and Start again.
- **Checked:**
  - with a headless-Chromium walkthrough against the running app, not added to the repo because
    the repo has no Playwright set up;
  - example 1 (Delhi, woman, 34) gives the green card, and the Section 12(c) link opens the
    viewer at Section 12;
  - example 3 at 375px, keyboard only, gives the red card with alternatives, and there is no
    horizontal scroll;
  - the Ask-page link appears for "free lawyer" and not for an RTI question (stubbed
    `/api/ask`).
- **Dark mode:** the app has no dark mode yet. The header's moon button has no handler and
  `styles.css` has no dark rules, so there was nothing to check against. This page's colours are
  `--legalaid-*` tokens on `:root`, ready to be redefined when a theme is added.

## 2026-10-28 — Check a Message page (`#/scam-check`)

New files: `src/scamcheck/ScamCheck.jsx`, `src/scamcheck/api.js`. Backend design, safety rules
and eval results are in the root `CHANGELOG.md`'s "Scam Message Checker" entry.

- **Where:** a "Check a Message" sidebar item (between Schemes and Helplines), a sixth home-page
  feature card, and an entry in the About page feature list. All are wired in `App.jsx`.
- **Form:**
  - a labelled textarea ("Paste the message here");
  - a live character count (2,000 max; turns red over the limit, and Check is then disabled);
  - the privacy line "We don't save your message, and we never open links in it.";
  - a Check button.
- Nothing is put in `localStorage` or `sessionStorage`.
- **Result card:**
  - the verdict is colour-coded: red for `high_risk`, amber for `warning_signs`, grey for
    `no_common_signs`, **never green**. The grey state's heading is "Check complete", and its
    body is the required cautious sentence;
  - warning signs are listed with the masked snippet and the matched words in a `<mark>`;
    AI-added signs are labelled "(found by AI)";
  - "What to do" is numbered steps: 1930 is a `tel:` link, and cybercrime.gov.in and Chakshu
    are linked in place. The RBI-circular step links to its paragraphs in the source viewer;
  - "Laws that may apply" link to `#/rights/source/<id>/provision/<id>`;
  - the disclaimer.
- **"I lost money -- what now?"** opens `#/ask?q=…` with a generic description plus the scam
  type. It deliberately does **not** include the pasted message, which may hold OTPs or account
  numbers. A "Helplines" button links to `#/helplines`.
- **Accessibility:** the result is in an `aria-live="polite"` region, and focus moves to the
  result heading (`tabIndex=-1`) after a check. Errors use `role="alert"`, and every interactive
  element has a visible `:focus-visible` outline.
- **Checked in headless Chrome** against the running dev servers, at 1280px and 390px:
  - no horizontal scroll at either width;
  - focus lands on the result heading;
  - the OTP from the pasted message is absent from the rendered result;
  - `tel:1930` and the source-viewer links are present;
  - the action buttons stack on phone.

  Both `high_risk` and `no_common_signs` states were screenshotted.
- **Dark mode: not checked, because the app has none.** The moon button in `HeaderControls` is
  decorative, and `styles.css` has no `prefers-color-scheme` rule. The new styles use `:root`
  tokens (`--scam-*`) so they can be themed when dark mode is added.

## 2026-10-28 — Case File download (My Cases + Ask page)

New files: `src/caseFile/api.js`, `src/caseFile/CaseFileButton.jsx`. Backend side and the
"assembled, not generated" design are in the root `CHANGELOG.md`'s "Case File export" entry.

- **Where:** a download icon button on every My Cases card (between Rename and Delete), and a
  "Download case file" pill next to "New Question" in the Ask page toolbar — shown only once the
  conversation is a saved case (has a case id); an unsaved conversation has nothing to export.
- **Disabled state:** a case with no answers yet (only a clarification question, an
  acknowledgement, or nothing) gets `aria-disabled="true"` rather than `disabled`, so it stays
  focusable, plus a tooltip ("Available once Legal Aid AI has answered a question in this
  case.") that shows on hover *and* keyboard focus, linked via `aria-describedby`. My Cases reads
  the new `has_answers` field from `GET /api/cases`; the Ask page uses `isAnswerResponse()`
  (App.jsx), which mirrors the backend's `case_store.is_answer_content()`.
- **Confirmation dialog:** shows the "not legal advice / not reviewed by a lawyer" notice
  prominently before anything downloads, a one-paragraph description of what's in the file,
  then "Download PDF" (primary) and "Word (.docx)". Focus starts on "Download PDF"; Tab is
  trapped in the dialog; Escape closes it and returns focus to the button that opened it.
- **PDF unavailable (503, LibreOffice missing):** the dialog says so, disables the PDF button,
  promotes "Word (.docx)" to the primary style and moves focus to it.
- Reuses `saveBlob()` from `complaints/api.js` for the actual download.
- **Checked in headless Chrome** (scratch backend + fixture cases): 390px phone width (no
  horizontal scroll on My Cases or Ask; dialog fits; buttons stack), 1366px desktop, keyboard-only
  open → Tab cycle → Escape → focus return, a real PDF download with the expected filename, and
  the 503 → Word fallback path. A mobile-only mismatch (New Question stretched full-width, the new
  pill didn't) was found that way and fixed.
- **Dark mode:** the app has no dark theme anywhere (no `prefers-color-scheme` rules, no toggle),
  so there was nothing to check against; the new UI uses the existing light palette.

## 2026-10-28 — Ask page microphone wired up

The Ask page's mic button (`ChatComposer` in `App.jsx`) existed in the UI already but had no
`onClick` — clicking it did nothing. It's now wired to actually record and transcribe a spoken
question, via the new backend endpoint in the root `CHANGELOG.md`'s "Voice input" entry.

- **Flow:** click mic → browser's `getUserMedia({ audio: true })` prompts for mic permission →
  `MediaRecorder` records (preferring `audio/webm;codecs=opus`, falling back through `audio/webm`
  / `audio/mp4` / the browser default via `MediaRecorder.isTypeSupported`) → click again (now
  labelled "Stop recording") to stop → the recorded blob is POSTed to `/api/transcribe` → on
  success the transcript is inserted into the question textbox (appended to anything already
  typed, not auto-submitted) so the user can review or edit it before pressing "Ask AI" — voice
  input never bypasses that review step.
- **States:** idle (mic icon) → recording (stop-square icon, pulsing red, `aria-label="Stop
  recording"`) → transcribing (spinning loader icon, button disabled) → back to idle. Recording
  stream tracks are always released (`stream.getTracks().forEach(track => track.stop())`) on
  stop, including on unmount.
- **Fails safe, visibly:** unsupported browser (`MediaRecorder` missing), denied mic permission,
  or a failed/empty-result transcription all show a small inline error bubble above the mic
  button (`"Microphone access was denied. Please type your question instead."`, etc.), auto-
  clearing after 6 seconds, and the button always returns to idle so typing still works. No
  `alert()`/`confirm()` — the viewer can't rely on those being reliable across browsers, and an
  inline message fits this app's existing style better.
- **Bug found and fixed during live verification:** the recording-state red styling
  (`.composer-mic-recording`) was being silently overridden by the plain
  `.composer-icon-button:hover`/`:focus-visible` rule, because both were single-class selectors
  of equal specificity and the button is focused right after being clicked — so the pulsing red
  state never actually appeared, even though the right class was applied. Fixed by scoping the
  recording-state rule to `.composer-icon-button.composer-mic-recording` (and its own `:hover`/
  `:focus-visible` variants) so it wins regardless of focus state. Confirmed via
  `getComputedStyle()` in a live Playwright run, before and after the fix.
- **Live-verified with a real (fake-device) microphone**, not just unit-tested: Playwright +
  Chromium's `--use-fake-device-for-media-stream` / `--use-file-for-fake-audio-capture=<wav>`
  flags fed a synthesized Hinglish recording into a real `getUserMedia()` call, through the actual
  mic button, through `/api/transcribe`, back into the textbox — confirmed Latin-letter Hinglish
  text appeared, not Devanagari. Also confirmed the denied-permission path end-to-end
  (`--deny-permission-prompts`, no grant): the inline error appeared and the button returned to
  idle. `npm run build` stayed clean throughout.
- **60-second recording cap:** a recording auto-stops after `MIC_MAX_RECORDING_MS` (60000) if the
  user doesn't click stop themselves, matching the backend's 2 MB limit (see root `CHANGELOG.md`)
  so a forgotten-open mic can't record indefinitely or produce a clip the backend would reject.
- **First-use privacy note:** the first time ever (tracked via a `localStorage` flag, read/write
  both wrapped in `try`/`catch` since storage can be unavailable — a private window, blocked site
  data — in which case the note just shows again next time rather than crashing) a recording
  successfully starts, a one-time note appears next to the mic button: *"Your voice is sent to
  Google's Gemini AI to turn it into text. It isn't saved or stored."* It auto-clears after 8
  seconds and never shows again on that browser. Live-verified via Playwright: shown on first use,
  absent on second use in the same (non-cleared) browser storage.
- **Browser `en-IN` speech-recognition fallback on a 503:** if `/api/transcribe` returns 503
  (Gemini itself is unavailable — see root `CHANGELOG.md`'s "Why 503 is its own status"), the mic
  button doesn't just fail — it starts the browser's own `SpeechRecognition`/
  `webkitSpeechRecognition` API with `lang = "en-IN"`, shows a notice explaining the switch
  ("Gemini voice service is busy, so this is using your browser's built-in recognition instead.
  Please speak again."), and the user speaks their question a second time, live, into that engine
  instead. If the browser has no `SpeechRecognition` API at all, it falls back further to the
  normal inline error message. `stopRecording()` now stops whichever engine is active (our own
  `MediaRecorder` or the browser's `SpeechRecognition`), and both are stopped on unmount.
  **Live-verified the detection and hand-off** (route-intercepted a real 503 response and
  confirmed the fallback notice appeared, `SpeechRecognition.start()` was reached, and the button
  entered the correct "listening" state) — **not** independently verified that Chromium's bundled
  speech backend in this sandboxed test environment actually returns a recognized transcript
  end-to-end (Playwright's Chromium build doesn't ship the API keys a full Chrome install has for
  its speech service), so real recognition quality from this fallback needs a check in an actual
  Chrome/Edge browser — see the new manual checklist in `backend/docs/`.

## 2026-10-28 — New Helplines page, voice-mic hint, shared page chrome extracted

### Helplines page (`#/helplines`)
A new, static (frontend-only, no backend calls) page listing official Indian helplines and
complaint portals, grouped by the app's four legal domains plus "Urgent". Every number and URL
was checked against an official government source before being added; see each entry's "official
source" link on the page, and the per-entry sourcing notes below.

- **New files:** `frontend/src/helplines/helplinesData.js` (the data — name, number/website,
  what it handles, when to use it, official source URL, last-verified date, per entry) and
  `frontend/src/helplines/Helplines.jsx` (the page component). Same data-file/component split
  as the existing (but unrouted — see below) `frontend/src/rights/rightsData.js` +
  `Rights.jsx`, since it's a clean pattern for static content.
- **New file:** `frontend/src/shared/PageChrome.jsx` — `HeaderControls`, `PageDivider`,
  `DocumentsBackgroundArt`, and the five `Vintage*` watermark SVG components, pulled out of
  `App.jsx` (previously module-local, unexported) so `Helplines.jsx` can reuse the same page
  chrome as every other page without a circular import between it and `App.jsx`. `App.jsx` now
  imports these from `./shared/PageChrome.jsx` instead of defining them; no visual or behavioral
  change to any existing page.
- **Content:** Urgent (ERSS 112, Women Helpline 181, Child Helpline 1098, Elderline 14567),
  Cyber (National Cyber Crime Helpline 1930 + cybercrime.gov.in), Consumer (National Consumer
  Helpline 1915/1800-11-4000, RBI Complaint Management System cms.rbi.org.in), Legal aid & rights
  (NALSA Helpline 15100, RTI Online rtionline.gov.in — labeled central-authorities-only, since
  that's what the portal itself says). **Tenancy has no dedicated national helpline** — rather
  than invent one, the page says so plainly and points to NALSA (15100) and, Delhi only per the
  task's explicit scope, the Delhi State Legal Services Authority (DSLSA, 1516) — no other
  state-specific numbers were added.
- Numbers are `tel:` links; websites open in a new tab with `rel="noreferrer"`. An "In an
  emergency, call 112" banner sits at the top. Filter chips (All / Urgent / Cyber / Consumer /
  Legal aid & rights) filter the four helpline sections; there is deliberately no "Tenancy" chip
  (nothing to filter to) — the tenancy explanation always renders, regardless of filter, so the
  honest "no helpline exists" disclosure isn't hidden behind a specific chip.
- Added to the sidebar nav (`navItems`) and as a 5th card in the home page's "How Legal Aid AI
  helps" feature grid (`.features` grid changed from a fixed 4-column layout to
  `repeat(auto-fit, minmax(190px, 1fr))` so it reflows cleanly at 5 cards and any count after).
- **Orphaned code found, not touched:** `frontend/src/rights/Rights.jsx` +
  `frontend/src/rights/rightsData.js` exist, are fully committed, and have real CSS
  (`.rights-page`/`.rights-card`/etc.), but `Rights.jsx` is never imported or routed anywhere in
  `App.jsx` — the live "Know Your Rights" page is the separate, backend-driven
  `LegalAwarenessPage`. Helplines follows the *data-file* half of that pattern (a real, good
  idea) but not its *visual* styling, which is a raw, unthemed prototype (no `--serif`/`--mocha`
  tokens, hardcoded colors, a `/rights-page-bg.png` background image, no dark-mode handling) —
  Helplines is styled to match the actually-live `documents-page-header`/`rights-panel` system
  instead, for visual consistency with the rest of the app.
- **Dark mode:** does not exist anywhere in this codebase. The header's theme-toggle button
  (`<Moon>` icon, `aria-label="Toggle theme"`) has no `onClick` and no CSS reads
  `prefers-color-scheme`/`data-theme`/any hue-rotate filter — confirmed by grep, not assumed.
  Helplines was built and checked only in the one theme that actually exists.

### Ask page — cyber helpline hint
In `LegalAIResponse` (the answer-rendering component), when a real (non-clarification) answer's
`routing.domains` includes `"cyber"` — a field the frontend already receives with every answer,
no backend or pipeline change — a one-line hint now renders above the disclaimer: "Lost money to
online fraud? Call 1930 as soon as possible.", linking to `#/helplines`.

### Verified
- `npm run build`: clean, no new warnings, both before and after this change.
- No Playwright setup exists in this repo (checked: no `playwright.config.*`, no
  `@playwright/test` dependency). Checked manually instead, using Playwright as a standalone
  tool (not added as a project dependency): desktop (1200px) and phone (390px) widths; all 10
  helpline cards render with correct `tel:`/website links (spot-checked 1930 → `tel:1930`);
  filter chips correctly narrow to the selected domain's section and the tenancy section stays
  visible through every filter; the home-page feature card and sidebar nav link both navigate to
  `#/helplines`; zero console/page errors. Not checked: dark mode (doesn't exist, see above) and
  the Ask-page cyber hint's live rendering (needs a real `routing.domains` including `"cyber"`
  from a real answer, which needs a working Gemini quota at verification time — the JSX/CSS was
  reviewed by hand instead).

## 2026-09-06 — Home page redesign, new content sections, motion pass

### Layout & visual cleanup (Home)
- Stripped ornament: removed the double inset "frame" borders on the panel, the
  per-card corner brackets, the `⌘` glyphs in the hero, the `◇` dividers, the
  oversized quote-mark footer, and 5 of the 7 scattered background watermark sketches.
- Hero rebuilt as a clean stack: small uppercase kicker → serif title → sans subtitle.
- Search box narrowed to a focused ~640px with flat styling and a single icon.
- "Browse by topic" pills and the four "How Legal Aid AI helps" cards restyled with
  lighter borders and a frosted-glass background that clears on hover.
- Consistent vertical rhythm via one flex `gap` on the centered content column.

### Sidebar & top controls (all pages)
- Sidebar width 300px → 240px. Removed the inset frames, corner brackets, the laurel
  marks around the logo, the large watermark, the `◇` divider, and the heavy shadow.
- Nav links: serif 1.45rem → sans 0.92rem; removed the slide-on-hover; the active
  item is now a flat solid fill instead of a gradient with stacked inset shadows.
- Top-right controls (theme / notifications / avatar): 52px gradient orbs → 36px flat,
  transparent, with a subtle hover tint only. Icons scaled down to match.

### New Home content (built from the real pages)
Below the fold, a run of scroll-revealed sections:
- **What you can do here** — a row of jump chips that smooth-scroll to each of five
  alternating feature sections: Documents, Summarize Document, My Cases,
  Know Your Rights, Schemes. Each has a real description of what that page does, a
  three-point capability list, a CTA button, and (for Know Your Rights) topic chips.
- **How it works** — three steps.
- **Why your privacy matters** / **Need help?** — two larger cards with detail lists
  (session-scoped data; NALSA / Tele-Law / State Legal Services Authority).
- A slow **marquee** strip of legal topics (pauses on hover).
- A proper **footer**: brand mark, about text, and quick links to Ask a Question,
  Know Your Rights, Schemes, and About Us.

### Pages that were empty stubs, now filled
- **About Us** (`#/about`): what the tool is, what you can do (in nav order),
  how it works, and a privacy note.
- **Schemes** (`#/schemes`): NALSA free legal aid, National Consumer Helpline (1915),
  Cyber Crime Reporting Portal (1930), Tele-Law, e-Daakhil, and the State Legal
  Services Authority — each linking out to the official site.
- Both reuse the shared parchment page background and the Know Your Rights panel styles.

### Motion & interaction (Home)
- Masked reveal on the hero title (slides up from a clip on load).
- Scroll-reveal system using `IntersectionObserver` with expo easing; feature
  sections stagger their text then their side panel.
- Background watermark parallax on scroll (`requestAnimationFrame`).
- `scroll-behavior: smooth` plus smooth-scrolling jump chips.
- Hover micro-interactions: CTA lift + arrow slide, magnetic pull on the primary
  CTA buttons, frosted cards/pills that clear on hover, edge-faded marquee.
- **Custom cursor (Home only):** a crisp dot at the exact pointer plus a soft
  trailing circle (radial fill, no border, no shadow) that eases behind it, grows
  over interactive elements, and shrinks on click. The native cursor is hidden on
  Home and restored on every other page; text inputs keep the I-beam.
- All of the above respects `prefers-reduced-motion`; the custom cursor and the
  magnetic effect are also disabled on touch / coarse-pointer devices.
