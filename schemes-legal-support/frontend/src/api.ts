import type {
  MatchedScheme,
  Scheme,
  SchemeInput,
  UserProfile,
  VerificationStatus,
} from "./types";

const BASE_URL = (
  import.meta.env.VITE_API_BASE_URL ?? "http://localhost:4000"
).replace(/\/+$/, "");

/**
 * Thrown for every API failure mode so callers have one thing to catch.
 * For a failed scheme validation, `details` holds the backend's `errors`
 * string array (the reviewer's checklist).
 */
export class ApiError extends Error {
  readonly status: number;
  readonly details?: unknown;

  constructor(message: string, status: number, details?: unknown) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

/** fetch + JSON parse + uniform error handling. Returns the parsed body. */
async function requestJson(
  path: string,
  init?: RequestInit,
): Promise<unknown> {
  let response: Response;
  try {
    response = await fetch(`${BASE_URL}${path}`, init);
  } catch (cause) {
    throw new ApiError(
      `Couldn't reach the server at ${BASE_URL}. Make sure the backend is running.`,
      0,
      cause,
    );
  }

  let body: unknown = null;
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
        : `The server returned an error (HTTP ${response.status}).`;
    const details = Array.isArray(rec.errors) ? rec.errors : rec.details;
    throw new ApiError(message, response.status, details);
  }

  return body;
}

// --- public matching flow ------------------------------------------------

export async function postMatch(
  profile: Partial<UserProfile>,
): Promise<MatchedScheme[]> {
  const body = await requestJson("/match", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(profile),
  });
  const results = isRecord(body) ? body.results : undefined;
  if (!Array.isArray(results)) {
    throw new ApiError("The server returned a response in an unexpected format.", 200);
  }
  return results as MatchedScheme[];
}

// --- admin: scheme CRUD ------------------------------------------------

export async function listSchemes(
  status?: VerificationStatus,
): Promise<Scheme[]> {
  const qs = status ? `?verification_status=${encodeURIComponent(status)}` : "";
  const body = await requestJson(`/schemes${qs}`);
  const schemes = isRecord(body) ? body.schemes : undefined;
  if (!Array.isArray(schemes)) {
    throw new ApiError("GET /schemes returned an unexpected shape.", 200);
  }
  return schemes as Scheme[];
}

export async function createScheme(input: SchemeInput): Promise<Scheme> {
  return (await requestJson("/schemes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  })) as Scheme;
}

export async function updateScheme(
  schemeId: string,
  input: SchemeInput,
): Promise<Scheme> {
  return (await requestJson(`/schemes/${encodeURIComponent(schemeId)}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  })) as Scheme;
}
