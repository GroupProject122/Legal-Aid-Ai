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

## Run Frontend

In another terminal:

```bash
cd frontend
npm install
npm run dev
```

Open the Vite URL, then use the Ask Question page. The frontend calls `POST /api/ask` through the Vite dev proxy.

The **Schemes** page (`#/schemes`) is served by the same frontend but talks to a
**separate** backend — see the next section. If the schemes backend isn't
running, every other page still works; only the Schemes search fails (with a
clear error).

## Schemes & Legal Support (second backend)

`schemes-legal-support/` is a self-contained service: a **Node/Express** API
(`schemes-legal-support/backend`, port **4000**) backed by **PostgreSQL**, plus
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
npm run dev                   # Express API on http://localhost:4000
```

### All services at once (3 terminals)

| Terminal | Command | Port | Serves |
|----------|---------|------|--------|
| 1 | `cd backend && source .venv/bin/activate && uvicorn main:app --reload --port 8000` | **8000** | Python RAG API (`/api/*`) |
| 2 | `cd schemes-legal-support/backend && npm run dev` | **4000** | Node schemes API (`/match`, `/schemes`) |
| 3 | `cd frontend && npm run dev` | **5173** | the single React app |

Ports 8000, 4000 and 5173 don't overlap, so all three run together. The Vite
dev server proxies both backends, so the browser only ever talks to `:5173`:

- `/api/*`         → `http://localhost:8000` (Python)
- `/schemes-api/*` → `http://localhost:4000` (Node; the `/schemes-api` prefix is
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
