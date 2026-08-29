# Legal Aid AI

Frontend pages are in the project root Vite app. The backend is a small FastAPI RAG MVP for Indian consumer-law questions using only PDFs placed in `backend/documents/`.

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
npm run dev
```

Open the Vite URL, then use the Ask Question page. The frontend calls `POST /api/ask` through the Vite dev proxy.

## Local Development Fallback

For a local smoke test without a Gemini API key, you may use the development-only response template:

```text
EMBEDDING_PROVIDER=local
LLM_PROVIDER=local
```

This still uses the local SentenceTransformer FAISS retrieval flow, but it does not call Gemini. Use `LLM_PROVIDER=gemini` with `GEMINI_API_KEY` for real generated answers.
# Legal-Aid-Ai
