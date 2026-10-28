/**
 * Talks to POST /api/scam-check on the main FastAPI backend (backend/scam_checker.py).
 * `vite.config.js` proxies `/api` to http://localhost:8000 in dev.
 *
 * The message is sent once and never stored -- not here (no localStorage / sessionStorage),
 * and not by the backend.
 */
export const MAX_MESSAGE_CHARS = 2000;

export class ScamCheckError extends Error {
  constructor(message, status) {
    super(message);
    this.name = 'ScamCheckError';
    this.status = status;
  }
}

export async function checkMessage(message) {
  let response;
  try {
    response = await fetch('/api/scam-check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ message })
    });
  } catch {
    throw new ScamCheckError('Could not reach Legal Aid AI. Check your connection and try again.', 0);
  }
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }
  if (!response.ok) {
    const detail = typeof payload?.detail === 'string' ? payload.detail : 'The message could not be checked right now.';
    throw new ScamCheckError(detail, response.status);
  }
  if (!payload || typeof payload.verdict !== 'string') {
    throw new ScamCheckError('The message could not be checked right now.', response.status);
  }
  return payload;
}
