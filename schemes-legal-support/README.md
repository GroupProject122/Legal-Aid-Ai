# Schemes & Legal Support

A web app that helps users discover Indian government schemes relevant to their
profile.

> **Status: end-to-end flow working (intake form → matched results).** The data
> model, the three-valued eligibility matching engine, a 5-scheme seed dataset,
> the `POST /match` + `GET /schemes/:schemeId` endpoints, and a React intake
> form + results screen are all built and tested. The seed schemes are
> hand-authored for testing (`verification_status: "needs_review"`), not sourced
> from official notifications.

## Layout

```
schemes-legal-support/
├── backend/    Node.js + Express + TypeScript API, Postgres via Prisma
├── frontend/   React + TypeScript, built with Vite
└── docs/
    └── data-model.md   UserProfile & Scheme schemas + eligibility grammar
```

Start with [`docs/data-model.md`](docs/data-model.md) — it defines the two core
schemas and the nested eligibility condition tree the matching engine will
consume.

## Prerequisites

- Node.js 20+ (tested on 24)
- npm 10+
- A running PostgreSQL 14+ instance

## Backend

```bash
cd backend
npm install

# Configure the DB connection + port
cp .env.example .env
#   then edit .env → set DATABASE_URL to your Postgres instance

# Generate the Prisma client from prisma/schema.prisma
npm run prisma:generate

# Create the tables (first run). Uses DATABASE_URL from .env.
npm run prisma:migrate       # interactive: name the migration, e.g. "init"
#   — or, without migration history:  npm run db:push

# Load the 5 sample schemes (idempotent upsert by scheme_id)
npm run prisma:seed

# Run the API in watch mode
npm run dev
```

### macOS: a local Postgres via Homebrew

```bash
brew install postgresql@17
brew services start postgresql@17
createdb schemes_legal_support     # if `createdb` isn't on PATH:
#   /opt/homebrew/opt/postgresql@17/bin/createdb schemes_legal_support
# then set DATABASE_URL in .env, e.g.
#   postgresql://<your-macos-user>@localhost:5432/schemes_legal_support?schema=public
```

The API listens on `http://localhost:4000` (override with `PORT` in `.env`).

Check it:

```bash
curl http://localhost:4000/health
# { "status": "ok", "service": "schemes-legal-support-backend",
#   "db": "up", "timestamp": "..." }
```

`db` reports `"up"` only if Postgres is reachable. The server still starts and
`/health` still returns `200` when the DB is down (`db: "down"`), so you can run
the backend before wiring up Postgres.

Other scripts: `npm run build` (compile to `dist/`), `npm start` (run the
compiled build), `npm run typecheck`, `npm test` (Vitest — unit + integration;
the integration tests need a migrated DB), `npm run prisma:studio` (browse the
DB).

### API

| Method & path            | Body / params                              | Returns |
|--------------------------|--------------------------------------------|---------|
| `GET /health`            | —                                          | liveness + `db` probe |
| `POST /match`            | any subset of `UserProfile` fields (JSON)  | `{ results: (Scheme & MatchResult)[] }` — eligible + maybe-eligible schemes, ranked |
| `GET /schemes/:schemeId` | `schemeId` slug, e.g. `pm-kisan`           | full scheme detail, or `404` |

`POST /match` validates the body with zod: unknown keys and out-of-range /
wrong-type values return `400` with a `details` breakdown; numeric strings
(`"40"`) are coerced. `MatchResult` carries `bucket`
(`likely_eligible` \| `possibly_eligible` \| `not_eligible`, though the last is
filtered out of `results`), `matched_hard_conditions`, `unknown_conditions`,
`matched_soft_conditions`, and a generated `reasoning` string.

```bash
curl -s -X POST http://localhost:4000/match -H 'Content-Type: application/json' \
  -d '{"occupation":"farmer","annual_family_income":150000}'
```

## Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite serves the app on `http://localhost:5173`: an optional 8-field intake form
that `POST`s to `http://localhost:4000/match` and a grouped results screen
(Likely / Possibly eligible). The backend must be running and seeded. Override
the API base URL with `VITE_API_BASE_URL` (see `.env.example`); it defaults to
`http://localhost:4000`.

Other scripts: `npm run build` (typecheck + production build to `dist/`),
`npm run preview` (serve the production build), `npm run typecheck`.

## Running both together

Two terminals:

```bash
# terminal 1
cd backend && npm run dev

# terminal 2
cd frontend && npm run dev
```

The frontend calls the API cross-origin (the backend enables permissive CORS in
dev). Add a `server.proxy` entry in `frontend/vite.config.ts` if you'd rather
route through the Vite origin.

## Admin (internal, no auth yet)

Open `http://localhost:5173/#/admin` (or the "Scheme admin →" link in the
public footer) for the scheme review tool: list every scheme with its
`verification_status`, and create/edit schemes with a structured builder for
the eligibility condition tree. Writes go through `POST` / `PUT /schemes`,
which run `validateScheme` (backend/src/validation/) and return the full list
of problems on a 400.

> **This admin screen and the write endpoints have NO authentication.** They
> must be put behind auth + authorization before any real deployment.

## Next steps

1. Add authentication/authorization in front of the admin UI and the
   `POST` / `PUT /schemes` endpoints.
2. Replace the hand-authored seed schemes with records sourced and verified
   against official notifications (`verification_status: "verified"`).
3. Persist submitted `UserProfile`s (the model exists; no write endpoint yet).
4. Frontend polish: field-level input hints, shareable result links, an
   accessible loading indicator on the results fetch.
