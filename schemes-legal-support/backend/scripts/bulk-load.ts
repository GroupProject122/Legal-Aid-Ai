/**
 * One-time internal helper: bulk-load scheme records through `POST /schemes`.
 *
 *   npm run bulk-load                       # reads scripts/schemes-batch.json
 *   npm run bulk-load -- path/to/file.json  # or an explicit path
 *
 * The API server must already be running locally (`npm run dev`). The input
 * file is a JSON array of scheme objects in the exact shape POST /schemes
 * expects. Each scheme is validated server-side; a failure is reported but does
 * NOT stop the batch — every result is printed at the end.
 *
 * No retries, no dedup. If a scheme_id already exists the server returns 409
 * and it shows up as a failure.
 */
import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const API_BASE = process.env.SCHEMES_API_BASE_URL ?? "http://localhost:4000";
const DEFAULT_FILE = resolve(__dirname, "schemes-batch.json");

interface PostResult {
  schemeId: string;
  ok: boolean;
  status: number;
  /** Validator `errors` array, or a single-element fallback message. */
  errors: string[];
}

async function postScheme(scheme: unknown): Promise<PostResult> {
  const schemeId =
    scheme && typeof scheme === "object" && "scheme_id" in scheme
      ? String((scheme as Record<string, unknown>).scheme_id)
      : "<no scheme_id>";

  let response: Response;
  try {
    response = await fetch(`${API_BASE}/schemes`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(scheme),
    });
  } catch (err) {
    return {
      schemeId,
      ok: false,
      status: 0,
      errors: [`could not reach ${API_BASE} (${(err as Error).message})`],
    };
  }

  let body: unknown = null;
  try {
    body = await response.json();
  } catch {
    // non-JSON body
  }
  const rec = (body ?? {}) as Record<string, unknown>;

  if (response.ok) {
    return { schemeId, ok: true, status: response.status, errors: [] };
  }

  const errors = Array.isArray(rec.errors)
    ? (rec.errors as string[])
    : [typeof rec.error === "string" ? rec.error : `HTTP ${response.status}`];
  return { schemeId, ok: false, status: response.status, errors };
}

async function main(): Promise<void> {
  const fileArg = process.argv[2];
  const file = fileArg ? resolve(process.cwd(), fileArg) : DEFAULT_FILE;

  let parsed: unknown;
  try {
    parsed = JSON.parse(readFileSync(file, "utf8"));
  } catch (err) {
    console.error(`Could not read/parse ${file}: ${(err as Error).message}`);
    process.exit(1);
  }
  if (!Array.isArray(parsed)) {
    console.error(`Expected a JSON array of scheme objects in ${file}.`);
    process.exit(1);
  }

  console.log(`Loading ${parsed.length} scheme(s) from ${file}`);
  console.log(`POST ${API_BASE}/schemes\n`);

  const results: PostResult[] = [];
  for (const scheme of parsed) {
    results.push(await postScheme(scheme));
  }

  for (const result of results) {
    if (result.ok) {
      console.log(`✅ ${result.schemeId} created`);
    } else {
      console.log(`❌ ${result.schemeId} failed:`);
      for (const message of result.errors) console.log(`   - ${message}`);
    }
  }

  const created = results.filter((r) => r.ok).length;
  const failed = results.length - created;
  console.log(
    `\n${created} created, ${failed} failed (${results.length} total)`,
  );
}

void main();
