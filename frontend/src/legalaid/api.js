/**
 * Talks to POST /api/legal-aid/eligibility on the main FastAPI backend
 * (backend/legal_aid_eligibility.py). `vite.config.js` proxies `/api` to http://localhost:8000.
 *
 * The answers (caste, disability, HIV status, income) are sent once and never stored -- not
 * here (no localStorage / sessionStorage), and not by the backend.
 */
export class EligibilityError extends Error {
  constructor(message, status, errors = []) {
    super(message);
    this.name = 'EligibilityError';
    this.status = status;
    this.errors = errors;
  }
}

export async function checkEligibility(answers) {
  let response;
  try {
    response = await fetch('/api/legal-aid/eligibility', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(answers)
    });
  } catch {
    throw new EligibilityError('Could not reach Legal Aid AI. Check your connection and try again.', 0);
  }
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const errors = Array.isArray(payload?.errors) ? payload.errors : [];
    const detail = errors.length
      ? errors.map((error) => error.message).join(' ')
      : (typeof payload?.detail === 'string' ? payload.detail : 'The check could not be completed right now.');
    throw new EligibilityError(detail, response.status, errors);
  }
  if (!payload || typeof payload.result !== 'string') {
    throw new EligibilityError('The check could not be completed right now.', response.status);
  }
  return payload;
}
