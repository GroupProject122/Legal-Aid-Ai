# Legal Aid AI as ONE container (Hugging Face Spaces, Docker SDK; also runs anywhere with Docker).
# The React frontend is built in stage 1 and served by FastAPI from the same origin as /api.
# No secrets in the image: GEMINI_API_KEY and LEGAL_AID_ADMIN_PASSWORD come from the environment
# (Space secrets) at run time.

# --- 1. Frontend build ----------------------------------------------------------------------
FROM node:22-slim AS frontend
WORKDIR /build/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

# --- 2. App ---------------------------------------------------------------------------------
FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/app/.cache/huggingface

# LibreOffice (headless) turns the case-file / complaint DOCX into PDF. Fonts: Liberation is
# metric-compatible with Times New Roman (used by the templates); Noto covers Devanagari for Hindi
# and Hinglish text; DejaVu is the general fallback.
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        libreoffice-writer-nogui fonts-liberation fonts-noto-core fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face runs the container as user 1000.
RUN useradd -m -u 1000 user
WORKDIR /app

# CPU-only PyTorch first (sentence-transformers would otherwise pull the much larger CUDA build).
COPY backend/requirements.txt backend/requirements.txt
RUN pip install torch --index-url https://download.pytorch.org/whl/cpu \
    && pip install -r backend/requirements.txt

COPY --chown=user:user backend/ backend/
COPY --from=frontend --chown=user:user /build/frontend/dist frontend/dist

# Download the embedding model and build the vector store now, so startup is fast and needs no
# network. ingest.py (no flags) embeds the committed parsed/legal_chunks.jsonl; it does not
# re-parse the PDFs.
RUN cd backend && python ingest.py && chown -R user:user /app

USER user
WORKDIR /app/backend

# Deployment defaults (override with Space variables). GEMINI_API_KEY and LEGAL_AID_ADMIN_PASSWORD
# are deliberately not set here.
ENV PORT=7860 \
    LLM_PROVIDER=gemini \
    EMBEDDING_PROVIDER=local \
    GEMINI_MODEL=gemini-3.5-flash-lite \
    SERVE_FRONTEND=true \
    AUTH_COOKIE_SECURE=true \
    RATE_LIMIT_ENABLED=true \
    RATE_LIMIT_TRUST_PROXY=true \
    RATE_LIMIT_PER_MINUTE=10 \
    RATE_LIMIT_PER_DAY=100 \
    DEMO_DEPLOYMENT=true \
    HF_HUB_OFFLINE=1 \
    TRANSFORMERS_OFFLINE=1

EXPOSE 7860
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "7860"]
