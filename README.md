# Legal Aid AI

Frontend pages are in the `frontend/` Vite app. The backend is a small FastAPI RAG MVP for Indian consumer-law questions using only PDFs placed in `backend/documents/`.

The default backend setup uses local SentenceTransformer embeddings with FAISS retrieval, then sends only the retrieved context to Gemini for structured answer generation.

## Backend Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

On Windows:

```powershell
cd backend
py -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

Add your Gemini API key in `backend/.env`:

```text
GEMINI_API_KEY=your_gemini_key_here
GEMINI_MODEL=gemini-flash-lite-latest
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_PROVIDER=local
LLM_PROVIDER=gemini
```

The two legal PDFs should be placed in:

```text
backend/documents/
```

Expected files for this MVP:

```text
backend/documents/consumer_protection_act_2019.pdf
backend/documents/consumer_protection_general_rules_2020.pdf
```

## Ingest PDFs

Because the MVP now uses SentenceTransformer embeddings, any vector store created with a previous embedding provider must be rebuilt. Running `python ingest.py` removes and recreates `backend/vectorstore/` using the configured local embedding model.

```bash
cd backend
source .venv/bin/activate
python ingest.py
```

The ingestion script extracts PDF text page by page, chunks it with a 1000-character chunk size and 160-character overlap, embeds the chunks locally with `sentence-transformers/all-MiniLM-L6-v2`, and stores a FAISS index in `backend/vectorstore/`. The API loads this index and does not recreate it on each question.

## Run Backend

```bash
cd backend
source .venv/bin/activate
uvicorn main:app --reload --port 8000
```

## User Accounts

People sign up with an email address or a phone number and a password (Sign in, top right). Saved cases and uploaded documents belong to the account that created them, and no other account can see them. Guests can still ask questions, but their conversations are not saved.

Cases and documents saved before accounts existed are given to an **admin account** (`admin@legalaid.local`) the first time the backend starts. Nothing is deleted. To choose the admin password:

```bash
cd backend
python set_admin_password.py
```

Optional settings in `backend/.env`:

```bash
LEGAL_AID_ADMIN_EMAIL=admin@legalaid.local   # admin sign-in email (used when the admin account is first created)
LEGAL_AID_ADMIN_PASSWORD=...                 # otherwise a random one is generated and printed once in the backend log
AUTH_COOKIE_SECURE=true                      # set when serving over HTTPS
```

## Run Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, then use the Ask Question page. The frontend calls `POST /api/ask` through the Vite dev proxy.

## Case File export

From **My Cases** (download icon on each case) or inside an open case on the **Ask** page
("Download case file"), a user can download a saved case as a PDF or Word file to take to a
lawyer or the District Legal Services Authority. It is **assembled, not generated**: no LLM call
is made; every line comes from the saved conversation, user-confirmed document facts, or corpus
sources that passed claim verification. See `backend/case_file.py` and the 2026-10-28 entry in
`CHANGELOG.md`.

| Endpoint | Returns |
| --- | --- |
| `GET /api/cases/{case_id}/case-file.pdf` | PDF (`application/pdf`) |
| `GET /api/cases/{case_id}/case-file.docx` | Word document |

Both need a signed-in user and use the same check as `GET /api/cases/{case_id}`: `401` for a
guest, `404` for an unknown case or one that belongs to someone else, and `409` if the case has no
answers yet. Files are generated per request and streamed back; nothing is
stored. The filename is `case-file-<short-title>-<YYYY-MM-DD>.<ext>`.

**PDF needs LibreOffice** (`soffice` on `PATH`), the same requirement as the Complaint Drafter's
PDF download. On macOS: `brew install --cask libreoffice`; on Debian/Ubuntu:
`sudo apt install libreoffice-writer`. Without it, the `.pdf` endpoint returns `503` with a
message telling the user to download the Word version instead, and the UI offers that option.
DOCX export has no extra requirement.

The template lives at `backend/templates/case_file_base.docx`; regenerate it with
`python -c "import build_templates as b; b.build_case_file_base_template()"` from `backend/`.
Evaluation: `python evaluate_case_file.py` (5 fixture cases, writes
`eval/case_file_evaluation.{json,md}`).

## Check a Message (scam checker)

The **Check a Message** page (`#/scam-check`) lets a user paste a suspicious SMS, WhatsApp or
email message and see the warning signs found in it, what to do next, and corpus provisions that
may apply. Backend: `backend/scam_checker.py`.

| Endpoint | Body | Returns |
| --- | --- | --- |
| `POST /api/scam-check` | `{"message": "<up to 2,000 characters>"}` | `verdict` (`high_risk` / `warning_signs` / `no_common_signs`), `headline`, `signs_found[]` (`rule_id`, `explanation`, masked `snippet`, `highlight`, `source` = `rule`/`ai`, `strength`), `scam_type`, `ai_explanation`, `what_to_do[]`, `laws_that_may_apply[]` (each with a source-viewer `api_url`), `ai_check`, `note`, `disclaimer` |

Empty, non-text or oversized input returns `422`. Fixed rules decide the verdict; one Gemini
call can only *add* weak warning signs. If Gemini fails, the rules-only result comes back with a
note. There is no "safe" verdict. The message is never stored or logged, and links in it are
never opened. Evaluation: `python evaluate_scam_checker.py` (rules only) and
`python evaluate_scam_checker.py --with-gemini --delay 5`. Add
`--cases eval/scam_check_cases_heldout.json --tag heldout` for the held-out set. Results are in
`eval/scam_check_evaluation_*.{json,md}`.

## Free Legal Aid Check

The **Free Legal Aid Check** page (`#/legal-aid`) is a short wizard that tells a user whether
they are likely entitled to free legal services, why (with the legal source), and where to apply.
Backend: `backend/legal_aid_eligibility.py`. Fixed rules only, with no Gemini call and no login.

| Endpoint | Body | Returns |
| --- | --- | --- |
| `POST /api/legal-aid/eligibility` | `{"state": "Delhi", "court": "other" \| "supreme_court", "categories": [...], "age": 0-120, "annual_income": >= 0 (optional)}` | `result` (`likely_eligible` / `likely_not_eligible` / `cannot_determine`), `headline`, `reason`, `matched_rules[]` (`rule_id`, `jurisdiction`, `reason`, `source`), `where_to_apply[]`, `documents_to_bring[]`, `alternatives[]` (only when not eligible), `needs[]` (`["annual_income"]` when income is required), `notes[]`, `disclaimer`, `last_verified` |

`categories` values: `sc_st`, `trafficking_or_begar`, `woman`, `disability`, `disaster_victim`,
`industrial_workman`, `in_custody`, `transgender`, `acid_attack_victim`, `hiv_aids`,
`defence_family`. "Child" is worked out from `age` (under 18). Invalid input returns `422` with
`{"detail", "errors": [{"field", "message"}]}`. Section 12 sources link to the source viewer;
Delhi-only rules link to the DSLSA website. Income limits are in one place: `LIMITS` in the
module. Delhi only: other states and Supreme Court cases return `cannot_determine`, pointing to
the right authority. The answers are never stored or logged. Evaluation:
`python evaluate_legal_aid_eligibility.py` (writes
`eval/legal_aid_eligibility_evaluation.{json,md}`).

The **Schemes** page (`#/schemes`) is served by the same frontend but talks to a
**separate** backend — see the next section. If the schemes backend isn't
running, every other page still works; only the Schemes search fails (with a
clear error).

## Schemes & Legal Support (second backend)

`schemes-legal-support/` is a self-contained service: a **Node/Express** API
(`schemes-legal-support/backend`, port **4001**) backed by **PostgreSQL**, plus
an internal-only admin tool (`schemes-legal-support/frontend`, not linked from
the main app). The main `frontend/` **Schemes** page consumes its `POST /match`
endpoint.

One-time setup (needs a local Postgres — on macOS: `brew install postgresql@17
&& brew services start postgresql@17 && createdb schemes_legal_support`):

```bash
cd schemes-legal-support/backend
npm install
cp .env.example .env          # then set DATABASE_URL for your Postgres
npx prisma migrate dev        # create tables
npm run prisma:seed           # load the sample schemes
```

Run it (third terminal):

```bash
cd schemes-legal-support/backend
npm run dev                   # Express API on http://localhost:4001
```

### All services at once (3 terminals)

| Terminal | Command | Port | Serves |
|----------|---------|------|--------|
| 1 | `cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000` | **8000** | Python RAG API (`/api/*`) |
| 2 | `cd schemes-legal-support/backend && npm run dev` | **4001** | Node schemes API (`/match`, `/schemes`) |
| 3 | `cd frontend && npm run dev` | **4000** | the single React app |

Ports 8000, 4001 and 4000 don't overlap, so all three run together. The Vite
dev server (port set in `frontend/vite.config.js`) proxies both backends, so the
browser only ever talks to `:4000`:

- `/api/*`         → `http://localhost:8000` (Python)
- `/schemes-api/*` → `http://localhost:4001` (Node; the `/schemes-api` prefix is
  stripped before forwarding)

To point the Schemes page at a non-default schemes backend (e.g. in
production), set `VITE_SCHEMES_API_BASE_URL` in `frontend/.env` — see
`frontend/.env.example`. Left unset, it uses the `/schemes-api` proxy path.

The admin scheme-entry tool stays in `schemes-legal-support/frontend`
(`npm run dev` there, then open `#/admin`) and is deliberately not linked from
the main app's navigation. **It has no authentication — do not expose it.**

## Local Development Fallback

For a local smoke test without a Gemini API key, you may use the development-only response template:

```text
EMBEDDING_PROVIDER=local
LLM_PROVIDER=local
```

This still uses the local SentenceTransformer FAISS retrieval flow, but it does not call Gemini. Use `LLM_PROVIDER=gemini` with `GEMINI_API_KEY` for real generated answers.
# Legal-Aid-Ai
