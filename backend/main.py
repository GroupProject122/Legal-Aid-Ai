from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

from config import FRONTEND_ORIGINS
from rag import (
    ConfigurationError,
    LLMError,
    RAGError,
    VectorStoreIncompatibleError,
    VectorStoreMissingError,
    rag,
    validate_question,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
logger = logging.getLogger("legal_aid_ai.api")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    try:
        rag.load()
    except VectorStoreMissingError:
        logger.warning("Vector store not found. Run `python ingest.py` before asking questions.")
    except VectorStoreIncompatibleError:
        logger.warning("Vector store is incompatible with the configured embedding provider/model. Run `python ingest.py` to rebuild it.")
    except Exception:
        logger.exception("Vector store failed to load during startup")
    yield


app = FastAPI(title="Legal Aid AI Consumer Law RAG", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=FRONTEND_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
    detail = exc.detail if isinstance(exc.detail, str) else "The request could not be processed."
    return JSONResponse(status_code=exc.status_code, content={"detail": detail})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    logger.warning("Request validation failed: %s", exc)
    return JSONResponse(status_code=422, content={"detail": "The request format is invalid."})


@app.exception_handler(Exception)
async def unhandled_exception_handler(_request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled API exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Legal Aid AI could not process your request right now."},
    )


class AskRequest(BaseModel):
    question: str


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "knowledge_base_loaded": rag.loaded,
    }


@app.post("/api/ask")
def ask(request: AskRequest) -> dict:
    try:
        validate_question(request.question)
        return rag.answer(request.question)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except VectorStoreMissingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except VectorStoreIncompatibleError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RAGError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected API error")
        raise HTTPException(status_code=500, detail="Something went wrong while processing the question.") from exc
