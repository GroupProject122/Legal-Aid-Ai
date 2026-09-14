/**
 * Talks to the Complaint Drafter endpoints on the main Python FastAPI backend
 * (backend/complaint_drafter_router.py). Unlike schemes/api.js, this is the
 * same backend `/api/ask` etc. already use — `vite.config.js` proxies `/api`
 * to http://localhost:8000 in dev, so no separate base-URL env var is needed.
 */
const BASE_URL = '/api/complaint-drafter';

const SCENARIO_PATHS = {
  tenancy_eviction: 'tenancy-eviction',
  consumer_defective_goods: 'consumer-defective-goods',
  consumer_misleading_ads: 'consumer-misleading-ads'
};

/**
 * One error type the UI can catch for every failure mode below.
 *
 * `field` is the backend's own structured field name for a validation error
 * (backend/complaint_drafter_router.py's `{"detail": message, "field": ...}`
 * body) -- complaint_drafter.py's hard validators raise with an explicit
 * pydantic `loc` (see `_raise_field_validation_error`), so this is real data
 * read off the error, not a guess made by scanning the message text for a
 * field name. `null` for errors that aren't about one particular field
 * (network failures, 500s, unexpected responses).
 */
export class ApiError extends Error {
  constructor(message, status, field = null, details = null) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.field = field;
    this.details = details;
  }
}

function isRecord(value) {
  return typeof value === 'object' && value !== null;
}

function scenarioPath(scenario) {
  const path = SCENARIO_PATHS[scenario];
  if (!path) throw new ApiError(`Unknown complaint scenario: ${scenario}`, 0);
  return path;
}

/**
 * POST { intake } to one JSON endpoint (`validate` or `draft`) for a scenario.
 * Network failures, non-2xx responses and unexpected payloads all surface as
 * an `ApiError` whose `message` is the backend's own detail string where one
 * was returned (e.g. a hard-validator message like the Rs. 3,500 rent cap),
 * not a generic "invalid input" message.
 */
async function postJson(scenario, action, intake) {
  let response;
  try {
    response = await fetch(`${BASE_URL}/${scenarioPath(scenario)}/${action}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intake })
    });
  } catch (cause) {
    throw new ApiError(
      "Couldn't reach the complaint drafter service. Make sure the backend is running.",
      0,
      null,
      cause
    );
  }

  let body = null;
  const raw = await response.text();
  if (raw) {
    try {
      body = JSON.parse(raw);
    } catch {
      // non-JSON; handled below
    }
  }

  if (!response.ok) {
    const rec = isRecord(body) ? body : {};
    const message =
      typeof rec.detail === 'string'
        ? rec.detail
        : `The complaint drafter service returned an error (HTTP ${response.status}).`;
    const field = typeof rec.field === 'string' ? rec.field : null;
    throw new ApiError(message, response.status, field);
  }

  if (!isRecord(body)) {
    throw new ApiError('The complaint drafter service returned an unexpected response.', 200);
  }
  return body;
}

/** Validate an intake without generating a document. Resolves to { status, ... } on success. */
export function validateIntake(scenario, intake) {
  return postJson(scenario, 'validate', intake);
}

/** Validate + assemble a draft and return its citation metadata (no file bytes). */
export function generateDraft(scenario, intake) {
  return postJson(scenario, 'draft', intake);
}

function filenameFromDisposition(response, fallback) {
  const disposition = response.headers.get('content-disposition') || '';
  const match = /filename="?([^"]+)"?/i.exec(disposition);
  return match ? match[1] : fallback;
}

/**
 * POST { intake } to a binary download endpoint (`draft/docx` or `draft/pdf`)
 * and return the file as a Blob + suggested filename. Re-validates and
 * re-assembles the draft server-side (the backend is stateless — there is no
 * saved draft to fetch by id), so this can hard-fail the same way `draft`
 * can (e.g. an unresolved citation), and additionally with a 503 if
 * LibreOffice is unavailable for PDF conversion.
 */
async function downloadFile(scenario, format, intake) {
  let response;
  try {
    response = await fetch(`${BASE_URL}/${scenarioPath(scenario)}/draft/${format}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ intake })
    });
  } catch (cause) {
    throw new ApiError(
      "Couldn't reach the complaint drafter service. Make sure the backend is running.",
      0,
      null,
      cause
    );
  }

  if (!response.ok) {
    let detail;
    try {
      const body = await response.json();
      detail = isRecord(body) && typeof body.detail === 'string' ? body.detail : undefined;
    } catch {
      // non-JSON error body; fall through to the generic message
    }
    // Download failures (unresolved citation, LibreOffice unavailable for PDF) aren't
    // per-field validation errors, so there's no `field` here -- the caller already
    // re-submitted a validated intake by the time it gets to downloading a file.
    throw new ApiError(
      detail || `The complaint drafter service returned an error (HTTP ${response.status}).`,
      response.status
    );
  }

  const blob = await response.blob();
  return { blob, filename: filenameFromDisposition(response, `complaint.${format}`) };
}

export function downloadDocx(scenario, intake) {
  return downloadFile(scenario, 'docx', intake);
}

export function downloadPdf(scenario, intake) {
  return downloadFile(scenario, 'pdf', intake);
}

/** Trigger a browser save for a Blob returned by downloadDocx/downloadPdf. */
export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
