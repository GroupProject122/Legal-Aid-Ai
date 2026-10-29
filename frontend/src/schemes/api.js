/**
 * Talks to the main FastAPI backend (backend/schemes_matcher.py): GET /api/schemes/areas and
 * POST /api/schemes/match. `vite.config.js` proxies `/api` to http://localhost:8000.
 *
 * The answers are sent once and never stored -- not here (no localStorage / sessionStorage),
 * and not by the backend.
 */
export class SchemesError extends Error {
  constructor(message, status = 0, errors = []) {
    super(message);
    this.name = 'SchemesError';
    this.status = status;
    this.errors = errors;
  }
}

/**
 * The request body: only the questions the person answered (skipped ones are left out, so the
 * backend treats their rules as unknown), numbers parsed, and the chosen areas.
 */
export function buildMatchRequest(answers, areas = []) {
  const body = {};
  const age = parseWholeNumber(answers.age);
  if (age !== null) body.age = age;
  const income = parseWholeNumber(answers.annualFamilyIncome);
  if (income !== null) body.annualFamilyIncome = income;
  for (const field of ['gender', 'residence', 'socialCategory', 'occupation']) {
    if (answers[field]) body[field] = answers[field];
  }
  body.areas = [...areas];
  return body;
}

/** "1,50,000" / "150000" / " 25 " -> number; empty or not a whole number -> null. */
export function parseWholeNumber(value) {
  if (value === null || value === undefined) return null;
  const cleaned = String(value).replace(/[,\s₹]/g, '').replace(/^rs\.?/i, '');
  if (!/^\d+$/.test(cleaned)) return null;
  return Number(cleaned);
}

async function request(url, options) {
  let response;
  try {
    response = await fetch(url, options);
  } catch {
    throw new SchemesError('Could not reach Legal Aid AI. Check your connection and try again.');
  }
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok || !payload) {
    throw new SchemesError(payload?.detail || 'Something went wrong while finding schemes. Please try again.', response.status, payload?.errors || []);
  }
  return payload;
}

export function fetchAreas() {
  return request('/api/schemes/areas');
}

export function matchSchemes(answers, areas) {
  return request('/api/schemes/match', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(buildMatchRequest(answers, areas))
  });
}

/**
 * Answers for re-checking one scheme: the step-1 answers plus the card's quick-question answers
 * (yes/no as true/false, numbers parsed; unanswered questions are left out).
 */
export function buildCheckAnswers(profileAnswers, cardAnswers, questions) {
  const { areas: _areas, socialCategory: _category, occupation: _occupation, ...profile } = buildMatchRequest(profileAnswers, []);
  const answers = { ...profile };
  for (const question of questions) {
    const raw = cardAnswers[question.field];
    if (raw === undefined || raw === '') continue;
    if (question.type === 'yes_no') answers[question.field] = raw === 'yes';
    else if (question.type === 'number') {
      const cleaned = String(raw).replace(/[,\s₹%]/g, '');
      if (/^\d+(\.\d+)?$/.test(cleaned)) answers[question.field] = Number(cleaned);
    } else answers[question.field] = raw;
  }
  return answers;
}

export function checkScheme(schemeId, answers) {
  return request('/api/schemes/check', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ schemeId, answers })
  });
}
