/**
 * Talks to the Schemes & Legal Support backend (a separate Node service).
 *
 * Base URL comes from `VITE_SCHEMES_API_BASE_URL`, defaulting to the
 * `/schemes-api` path — which `vite.config.js` proxies to
 * http://localhost:4000 in dev, mirroring how `/api` proxies to the Python
 * backend. In production set the env var to the deployed origin.
 */
const BASE_URL = (
  import.meta.env.VITE_SCHEMES_API_BASE_URL ?? "/schemes-api"
).replace(/\/+$/, "");

/** One error type the UI can catch for every failure mode of `postMatch`. */
export class ApiError extends Error {
  constructor(message, status, details) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function isRecord(value) {
  return typeof value === "object" && value !== null;
}

/**
 * POST the (partial) profile to the schemes backend and return the ranked
 * matches. Network failures, non-2xx responses and unexpected payloads all
 * surface as an `ApiError`.
 */
export async function postMatch(profile) {
  let response;
  try {
    response = await fetch(`${BASE_URL}/match`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(profile),
    });
  } catch (cause) {
    throw new ApiError(
      "Couldn't reach the schemes service. Make sure the schemes backend is running.",
      0,
      cause,
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
      typeof rec.error === "string"
        ? rec.error
        : `The schemes service returned an error (HTTP ${response.status}).`;
    throw new ApiError(message, response.status, rec.details);
  }

  const results = isRecord(body) ? body.results : undefined;
  if (!Array.isArray(results)) {
    throw new ApiError("The schemes service returned an unexpected response.", 200);
  }
  return results;
}
