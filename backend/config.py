from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = BASE_DIR.parent
DOCUMENTS_DIR = BASE_DIR / "documents"
VECTORSTORE_DIR = BASE_DIR / "vectorstore"
INDEX_PATH = VECTORSTORE_DIR / "index.faiss"
METADATA_PATH = VECTORSTORE_DIR / "metadata.json"

load_dotenv(BASE_DIR / ".env")


def _csv_env(name: str, default: str) -> list[str]:
    return [item.strip() for item in os.getenv(name, default).split(",") if item.strip()]


GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-flash-lite-latest")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2")

# Defaults use local embeddings and Gemini generation. CHAT_PROVIDER is accepted
# for compatibility with the previous backend config.
EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "local").lower()
LLM_PROVIDER = os.getenv("LLM_PROVIDER", os.getenv("CHAT_PROVIDER", "gemini")).lower()

FRONTEND_ORIGINS = _csv_env(
    "FRONTEND_ORIGINS",
    "http://localhost:5173,http://localhost:5174",
)

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "160"))
TOP_K = int(os.getenv("TOP_K", "5"))
MAX_QUESTION_CHARS = int(os.getenv("MAX_QUESTION_CHARS", "2000"))
MAX_UPLOAD_SIZE_MB = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

DISCLAIMER = "This is legal information, not professional legal advice."
