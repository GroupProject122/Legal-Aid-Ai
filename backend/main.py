from __future__ import annotations

import logging
import re
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel
from starlette.exceptions import HTTPException as StarletteHTTPException

import clarification
import case_store
import claim_verifier
import corpus_gap
import conversation_state
import document_extractor
import document_facts
import document_store
import document_summarizer
import domain_router
import fact_sufficiency
import grounded_answer
import legal_education
from config import DISCLAIMER, FRONTEND_ORIGINS, LLM_PROVIDER
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
    document_store.init_db()
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
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
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
    case_id: int | None = None
    clarification_state_id: str | None = None
    confirmed_fact_context_id: str | None = None
    conversation_state_id: str | None = None


class DocumentFactRequest(BaseModel):
    extraction: dict


class ConfirmFactsRequest(BaseModel):
    fact_extraction_id: str
    confirmed_facts: dict
    document_id: int | None = None


class RenameDocumentRequest(BaseModel):
    filename: str


class RenameCaseRequest(BaseModel):
    title: str


@app.get("/api/health")
def health() -> dict:
    return {
        "status": "ok",
        "knowledge_base_loaded": rag.loaded,
    }


@app.get("/api/cases")
def list_saved_cases() -> list[dict]:
    return case_store.list_cases()


@app.delete("/api/cases")
def delete_all_saved_cases() -> dict:
    deleted_count = case_store.delete_all_cases()
    logger.info("All saved cases deleted count=%s", deleted_count)
    return {"status": "deleted", "deleted_count": deleted_count}


@app.patch("/api/cases/{case_id}/rename")
def rename_saved_case(case_id: int, request: RenameCaseRequest) -> dict:
    try:
        case = case_store.rename_case(case_id, request.title)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    logger.info("Saved case renamed case_id=%s", case_id)
    return {
        "id": case["id"],
        "title": case["title"],
        "created_at": case["created_at"],
        "updated_at": case["updated_at"],
        "primary_domain": case["primary_domain"],
    }


@app.get("/api/cases/{case_id}")
def open_saved_case(case_id: int) -> dict:
    case = case_store.get_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    conversation_state.restore_state(case.get("conversation_state"))
    return {
        "case": {
            "id": case["id"],
            "title": case["title"],
            "created_at": case["created_at"],
            "updated_at": case["updated_at"],
            "primary_domain": case["primary_domain"],
        },
        "messages": case_store.get_messages(case_id),
        "conversation_state": case.get("conversation_state"),
        "confirmed_document_context": case.get("confirmed_document_context"),
    }


@app.delete("/api/cases/{case_id}")
def delete_saved_case(case_id: int) -> dict:
    if not case_store.delete_case(case_id):
        raise HTTPException(status_code=404, detail="Case not found.")
    logger.info("Saved case deleted case_id=%s", case_id)
    return {"status": "deleted", "case_id": case_id}


@app.get("/api/documents")
def list_uploaded_documents() -> list[dict]:
    return document_store.list_documents()


@app.get("/api/documents/{document_id}")
def view_uploaded_document(document_id: int) -> dict:
    try:
        document = document_store.require_document(document_id)
        return document_public_payload(document, include_extraction=True)
    except document_store.DocumentStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/documents/{document_id}/file")
def get_uploaded_document_file(document_id: int) -> FileResponse:
    try:
        document = document_store.require_document(document_id)
        storage_path = document_store.safe_storage_path(document["storage_path"])
        return FileResponse(
            storage_path,
            media_type=document.get("mime_type") or "application/octet-stream",
            filename=document["filename"],
        )
    except document_store.DocumentStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/documents/{document_id}/summary")
def get_document_summary(document_id: int) -> dict:
    try:
        document = document_store.require_document(document_id)
    except document_store.DocumentStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if not document.get("summary_text"):
        return {
            "document_id": document_id,
            "status": "summary_not_generated",
            "summary": None,
            "cached": False,
        }
    return {
        "document_id": document_id,
        "status": "success",
        "summary": document["summary_text"],
        "cached": True,
        "summary_generated_at": document.get("summary_generated_at"),
    }


@app.post("/api/documents/{document_id}/summarize")
def summarize_uploaded_document(document_id: int) -> dict:
    try:
        document = document_store.require_document(document_id)
    except document_store.DocumentStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    if document.get("summary_text"):
        return {
            "document_id": document_id,
            "status": "success",
            "summary": document["summary_text"],
            "cached": True,
            "summary_generated_at": document.get("summary_generated_at"),
        }

    result = document_summarizer.summarize_document(document.get("extraction") or {})
    status = result.get("status") or "summary_unavailable"
    if status == "success" and result.get("summary"):
        document = document_store.update_summary(
            document_id,
            summary_text=result["summary"],
            summary_status="success",
            summary_model=result.get("model"),
        )
        logger.info(
            "Document summary completed document_id=%s status=success cached=false calls=%s latency_ms=%s",
            document_id,
            result.get("gemini_calls"),
            result.get("latency_ms"),
        )
        return {
            "document_id": document_id,
            "status": "success",
            "summary": document["summary_text"],
            "cached": False,
            "summary_generated_at": document.get("summary_generated_at"),
        }

    document_store.update_summary(document_id, summary_text=None, summary_status=status, summary_model=result.get("model"))
    logger.info(
        "Document summary unavailable document_id=%s status=%s calls=%s latency_ms=%s",
        document_id,
        status,
        result.get("gemini_calls"),
        result.get("latency_ms"),
    )
    return {
        "document_id": document_id,
        "status": status,
        "summary": None,
        "cached": False,
        "message": result.get("message") or "The document summary could not be generated right now.",
    }


@app.patch("/api/documents/{document_id}/rename")
def rename_uploaded_document(document_id: int, request: RenameDocumentRequest) -> dict:
    try:
        document = document_store.rename_document(document_id, request.filename)
        logger.info("Document renamed document_id=%s type=%s", document_id, document.get("file_type"))
        return document_public_payload(document, include_extraction=False)
    except document_store.DocumentStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/documents/{document_id}")
def delete_uploaded_document(document_id: int) -> dict:
    try:
        document_store.delete_document(document_id)
        logger.info("Document deleted document_id=%s", document_id)
        return {"status": "deleted", "document_id": document_id}
    except document_store.DocumentStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/legal-awareness/categories")
def legal_awareness_categories() -> list[dict]:
    return legal_education.list_categories()


@app.get("/api/legal-awareness/categories/{category_id}")
def legal_awareness_category(category_id: str) -> dict:
    try:
        return legal_education.get_category(category_id)
    except legal_education.LegalEducationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/legal-awareness/sources/{source_id}")
def legal_awareness_source(source_id: str) -> dict:
    try:
        return legal_education.get_source(source_id)
    except legal_education.LegalEducationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/legal-awareness/sources/{source_id}/provisions/{provision_id}")
def legal_awareness_provision(source_id: str, provision_id: str) -> dict:
    try:
        return legal_education.get_provision(source_id, provision_id)
    except legal_education.LegalEducationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/legal-awareness/sources/{source_id}/file")
def legal_awareness_source_file(source_id: str) -> FileResponse:
    try:
        source_path = legal_education.source_pdf_path(source_id)
        source = legal_education.get_source(source_id)
        return FileResponse(source_path, media_type="application/pdf", filename=source["source_file"].split("/")[-1])
    except legal_education.LegalEducationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/ask")
def ask(request: AskRequest) -> dict:
    try:
        question = validate_question(request.question)
        persisted_case = load_persisted_case(request.case_id)
        if (
            request.case_id is None
            and request.conversation_state_id is None
            and request.clarification_state_id is None
            and case_store.is_small_talk(question)
        ):
            return no_case_small_talk_response()

        active_case = conversation_state.get_state(request.conversation_state_id)
        if active_case is None and persisted_case:
            active_case = conversation_state.restore_state(persisted_case.get("conversation_state"))
        effective_conversation_state_id = active_case.conversation_state_id if active_case else request.conversation_state_id

        if request.clarification_state_id:
            response = continue_clarification(request.clarification_state_id, question, effective_conversation_state_id)
            return persist_case_turn(request.case_id, question, response)

        confirmed_context = load_confirmed_document_context(request.confirmed_fact_context_id)
        if confirmed_context is None and persisted_case and persisted_case.get("confirmed_document_context"):
            confirmed_context = persisted_case.get("confirmed_document_context")
        if active_case is not None and confirmed_context is None and active_case.confirmed_document_context_id:
            confirmed_context = load_confirmed_document_context(active_case.confirmed_document_context_id)
        if active_case is not None:
            response = handle_active_case_turn(question, active_case, confirmed_context)
            return persist_case_turn(request.case_id, question, response, confirmed_context)

        conflict = detect_document_fact_conflict(question, confirmed_context)
        if conflict:
            response = document_fact_conflict_response(conflict)
            return persist_case_turn(request.case_id, question, response, confirmed_context)

        routing_text = document_facts.combined_question_with_confirmed_facts(question, confirmed_context)
        route = domain_router.route_issue(routing_text)
        logger.info(
            "Router decision status=%s domains=%s primary=%s confidence=%s latency_ms=%s",
            route.status,
            route.domains,
            route.primary_domain,
            route.confidence,
            route.latency_ms,
        )
        if route.status == "classified":
            response = with_routing(handle_classified_issue(question, route, confirmed_context), route)
            return persist_case_turn(request.case_id, question, response, confirmed_context)
        if route.status == "unclear":
            state, clarification_question = clarification.start_clarification(question, route)
            logger.info(
                "Clarification started state_id=%s reason=%s latency_ms=%s",
                state.state_id,
                clarification_question.reason_code,
                clarification_question.latency_ms,
            )
            response = clarification_response(route, state, clarification_question)
            return persist_case_turn(request.case_id, question, response, confirmed_context)
        response = router_minimal_response(route)
        return persist_case_turn(request.case_id, question, response, confirmed_context)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except VectorStoreMissingError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except VectorStoreIncompatibleError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except document_facts.DocumentFactError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except RAGError as exc:
        raise HTTPException(status_code=exc.status_code, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected API error")
        raise HTTPException(status_code=500, detail="Something went wrong while processing the question.") from exc


@app.post("/api/documents/extract")
async def extract_uploaded_document(file: UploadFile = File(...)) -> dict:
    try:
        content = await file.read(document_extractor.max_upload_bytes() + 1)
        result = document_extractor.extract_document(
            filename=file.filename or "uploaded_document",
            content=content,
            content_type=file.content_type,
        )
        payload = result.to_dict()
        if result.file_type and result.status != "unsupported":
            stored_document = document_store.create_uploaded_document(
                original_filename=file.filename or result.filename,
                content=content,
                mime_type=file.content_type,
                extraction=payload,
            )
            payload["document_id"] = stored_document["id"]
        logger.info(
            "Document extraction completed document_id=%s type=%s size=%s status=%s latency_ms=%s",
            payload.get("document_id"),
            result.file_type,
            result.size_bytes,
            result.status,
            result.processing_time_ms,
        )
        return payload
    except document_extractor.DocumentExtractionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except document_store.DocumentStoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected document extraction error")
        raise HTTPException(status_code=500, detail="Legal Aid AI could not extract text from this document right now.") from exc


@app.post("/api/documents/extract-facts")
def extract_document_facts(request: DocumentFactRequest) -> dict:
    try:
        result = document_facts.extract_facts_from_extraction(request.extraction)
        logger.info(
            "Document fact extraction endpoint completed status=%s confirmation_required=%s",
            result.get("status"),
            result.get("confirmation_required"),
        )
        return result
    except Exception as exc:
        logger.exception("Unexpected document fact extraction error")
        raise HTTPException(status_code=500, detail="Legal Aid AI could not identify facts from this document right now.") from exc


@app.post("/api/documents/confirm-facts")
def confirm_document_facts(request: ConfirmFactsRequest) -> dict:
    try:
        confirmed = document_facts.confirm_facts(request.fact_extraction_id, request.confirmed_facts)
        if request.document_id is not None:
            document_store.update_confirmed_fact_context(request.document_id, confirmed.to_dict())
        logger.info("Document facts confirmed fact_extraction_id=%s", request.fact_extraction_id)
        return confirmed.to_dict()
    except document_facts.DocumentFactError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except document_store.DocumentStoreError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("Unexpected document fact confirmation error")
        raise HTTPException(status_code=500, detail="Legal Aid AI could not confirm these document facts right now.") from exc


def load_persisted_case(case_id: int | None) -> dict | None:
    if case_id is None:
        return None
    stored_case = case_store.get_case(case_id)
    if stored_case is None:
        raise HTTPException(status_code=404, detail="Case not found.")
    return stored_case


def persist_case_turn(
    case_id: int | None,
    question: str,
    response: dict,
    confirmed_context: dict | None = None,
) -> dict:
    if case_id is None and not case_store.should_create_case_for_response(question, response):
        return response

    effective_case_id = case_id
    if effective_case_id is None:
        routing = response.get("routing") or {}
        effective_case_id = case_store.create_case(
            question,
            primary_domain=routing.get("primary_domain"),
            conversation_state=response.get("conversation_state"),
            confirmed_document_context=confirmed_context,
        )

    case_store.save_message(effective_case_id, "user", case_store.user_content_for_storage(question))
    case_store.save_message(effective_case_id, "assistant", case_store.assistant_content_for_storage(response))
    routing = response.get("routing") or {}
    case_store.update_case_metadata(
        effective_case_id,
        primary_domain=routing.get("primary_domain"),
        conversation_state=response.get("conversation_state"),
        confirmed_document_context=confirmed_context,
    )
    response["case_id"] = effective_case_id
    return response


def no_case_small_talk_response() -> dict:
    return {
        "answer": {
            "issue_summary": "Hello. You can start by describing the legal issue you need help with.",
            "possible_rights": [],
            "next_steps": [],
        },
        "sources": [],
        "confidence": "high",
        "insufficient_context": False,
        "disclaimer": DISCLAIMER,
        "conversation": {"turn_type": "small_talk"},
    }


def document_public_payload(document: dict, include_extraction: bool = False) -> dict:
    payload = {
        "id": document["id"],
        "filename": document["filename"],
        "file_type": document["file_type"],
        "mime_type": document.get("mime_type"),
        "size_bytes": document["size_bytes"],
        "created_at": document["created_at"],
        "updated_at": document["updated_at"],
        "extraction_status": document.get("extraction_status"),
        "summary_status": document.get("summary_status"),
        "summary_generated_at": document.get("summary_generated_at"),
        "confirmed_fact_context": document.get("confirmed_fact_context"),
        "case_id": document.get("case_id"),
    }
    if include_extraction:
        extraction = document.get("extraction") or {}
        payload["extraction"] = {
            "status": extraction.get("status"),
            "filename": extraction.get("filename"),
            "file_type": extraction.get("file_type"),
            "size_bytes": extraction.get("size_bytes"),
            "page_count": extraction.get("page_count"),
            "character_count": extraction.get("character_count"),
            "text": extraction.get("text", ""),
            "pages": extraction.get("pages", []),
            "warnings": extraction.get("warnings", []),
            "document_id": document["id"],
        }
        payload["file_url"] = f"/api/documents/{document['id']}/file"
    return payload


def load_confirmed_document_context(context_id: str | None) -> dict | None:
    if not context_id:
        return None
    context = document_facts.require_confirmed_context(context_id)
    logger.info(
        "Confirmed document context attached context_id=%s document_type=%s fact_count=%s",
        context_id,
        context.get("document_type"),
        len(document_facts.document_evidence_payload(context)),
    )
    return context


def continue_clarification(state_id: str, answer: str, conversation_state_id: str | None = None) -> dict:
    fact_state = fact_sufficiency.get_state(state_id)
    if fact_state is not None:
        return continue_fact_clarification(fact_state, answer, conversation_state_id)

    state = clarification.get_state(state_id)
    if state is None:
        route = domain_router.fallback_unclear_decision()
        return router_minimal_response(route)

    progress = clarification.record_answer(state, answer)
    route = domain_router.route_issue(state.accumulated_context)
    logger.info(
        "Clarification continued state_id=%s progress=%s route_status=%s domains=%s",
        state_id,
        progress.progress,
        route.status,
        route.domains,
    )
    if route.status == "classified":
        clarification.clear_state(state_id)
        return with_routing(handle_classified_issue(state.accumulated_context, route, conversation_state_id=conversation_state_id), route)
    if route.status in {"unsupported", "out_of_scope"}:
        clarification.clear_state(state_id)
        return router_minimal_response(route)
    if progress.safe_exit:
        clarification.clear_state(state_id)
        return insufficient_detail_response()

    question = clarification.generate_next_question(state, route, progress)
    return clarification_response(route, state, question, progress.progress)


def handle_active_case_turn(
    question: str,
    active_case: conversation_state.ActiveCaseState,
    confirmed_context: dict | None = None,
) -> dict:
    classification = conversation_state.classify_turn(question, active_case)
    logger.info(
        "Conversation turn classified state_id=%s turn_type=%s confidence=%s",
        active_case.conversation_state_id,
        classification.turn_type,
        classification.confidence,
    )
    if classification.turn_type in {"small_talk", "acknowledgement"}:
        active_case.last_user_intent = classification.turn_type
        return with_conversation_state(conversation_state.acknowledgement_response(active_case), active_case)
    if classification.turn_type in {"additional_fact", "correction"}:
        conversation_state.apply_turn_to_state(active_case, question, classification)
        message = "Got it — I've added that to the current case." if classification.turn_type == "additional_fact" else "Got it — I've updated the current case with your correction."
        return with_conversation_state(conversation_state.acknowledgement_response(active_case, message), active_case)

    if classification.turn_type == "new_issue":
        conversation_state.clear_state(active_case.conversation_state_id)
        return handle_new_issue_without_active_context(question, confirmed_context)

    conversation_state.apply_turn_to_state(active_case, question, classification)
    document_fact_lines = document_facts.confirmed_fact_lines(confirmed_context)
    combined_message = conversation_state.pipeline_message(question, active_case, document_fact_lines)
    route = domain_router.route_issue(combined_message)
    if route.status == "classified":
        return with_routing(
            handle_classified_issue(
                combined_message,
                route,
                confirmed_context,
                original_message=question,
                conversation_case=active_case,
            ),
            route,
        )
    if route.status == "unclear":
        state, clarification_question = clarification.start_clarification(combined_message, route)
        active_case.clarification_state_id = state.state_id
        return with_conversation_state(clarification_response(route, state, clarification_question), active_case)
    return with_conversation_state(router_minimal_response(route), active_case)


def handle_new_issue_without_active_context(question: str, confirmed_context: dict | None = None) -> dict:
    conflict = detect_document_fact_conflict(question, confirmed_context)
    if conflict:
        return document_fact_conflict_response(conflict)
    routing_text = document_facts.combined_question_with_confirmed_facts(question, confirmed_context)
    route = domain_router.route_issue(routing_text)
    if route.status == "classified":
        return with_routing(handle_classified_issue(question, route, confirmed_context), route)
    if route.status == "unclear":
        state, clarification_question = clarification.start_clarification(question, route)
        return clarification_response(route, state, clarification_question)
    return router_minimal_response(route)


def handle_classified_issue(
    message: str,
    route: domain_router.RouteDecision,
    confirmed_context: dict | None = None,
    original_message: str | None = None,
    conversation_case: conversation_state.ActiveCaseState | None = None,
    conversation_state_id: str | None = None,
) -> dict:
    document_fact_lines = document_facts.confirmed_fact_lines(confirmed_context)
    context, fact_result = fact_sufficiency.start_fact_check(
        message,
        route,
        document_fact_lines=document_fact_lines,
        confirmed_fact_context_id=confirmed_context.get("confirmed_fact_context_id") if confirmed_context else None,
    )
    logger.info(
        "Fact sufficiency status=%s domains=%s needs_clarification=%s latency_ms=%s",
        fact_result.status,
        route.domains,
        fact_result.needs_fact_clarification,
        fact_result.latency_ms,
    )
    if fact_result.status == "sufficient":
        active_case = conversation_case or conversation_state.get_state(conversation_state_id)
        if confirmed_context:
            return answer_grounded_from_context(
                original_message=message,
                user_question=original_message,
                context=context,
                fact_result=fact_result,
                confirmed_context=confirmed_context,
                conversation_case=active_case,
                route=route,
            )
        if active_case is None and original_message is None:
            response = answer_grounded_from_context(
                original_message=message,
                context=context,
                fact_result=fact_result,
            )
            return attach_active_case_state(response, None, route, fact_sufficiency.retrieval_query(context, fact_result), message, confirmed_context)
        return answer_grounded_from_context(
            original_message=message,
            user_question=original_message,
            context=context,
            fact_result=fact_result,
            conversation_case=active_case,
            route=route,
        )
    response = fact_clarification_response(route, context, fact_result)
    active_case = conversation_case or conversation_state.get_state(conversation_state_id)
    if active_case:
        active_case.clarification_state_id = context.state_id
        return with_conversation_state(response, active_case)
    return response


def continue_fact_clarification(
    context: fact_sufficiency.CaseContext,
    answer: str,
    conversation_state_id: str | None = None,
) -> dict:
    progress, fact_result = fact_sufficiency.continue_fact_check(context, answer)
    logger.info(
        "Fact clarification continued state_id=%s progress=%s status=%s",
        context.state_id,
        progress.progress,
        fact_result.status,
    )
    if fact_result.status == "sufficient":
        fact_sufficiency.clear_state(context.state_id)
        confirmed_context = document_facts.get_confirmed_context(context.confirmed_fact_context_id)
        active_case = conversation_state.get_state(conversation_state_id)
        if confirmed_context:
            return answer_grounded_from_context(
                original_message=context.original_message,
                user_question=answer,
                context=context,
                fact_result=fact_result,
                confirmed_context=confirmed_context,
                conversation_case=active_case,
            )
        if active_case is None:
            return answer_grounded_from_context(
                original_message=context.original_message,
                context=context,
                fact_result=fact_result,
            )
        return answer_grounded_from_context(
            original_message=context.original_message,
            user_question=answer,
            context=context,
            fact_result=fact_result,
            conversation_case=active_case,
        )
    if progress.safe_exit:
        fact_sufficiency.clear_state(context.state_id)
        return insufficient_fact_detail_response()
    return fact_clarification_response(None, context, fact_result, progress.progress)


def answer_grounded_from_context(
    original_message: str,
    context: fact_sufficiency.CaseContext,
    fact_result: fact_sufficiency.FactSufficiencyResult,
    confirmed_context: dict | None = None,
    user_question: str | None = None,
    conversation_case: conversation_state.ActiveCaseState | None = None,
    route: domain_router.RouteDecision | None = None,
) -> dict:
    retrieval_text = fact_sufficiency.retrieval_query(context, fact_result)
    chunks = rag.retrieve(retrieval_text)
    if not chunks:
        return grounded_answer.insufficient_response("I do not have enough retrieved legal material to answer this reliably.")
    pre_gap = corpus_gap.pre_generation_check(retrieval_text, context.domains, chunks)
    if not pre_gap.allow_grounded_answer:
        response = corpus_gap.abstention_response(pre_gap)
        return attach_active_case_state(response, conversation_case, route, retrieval_text, user_question or original_message, confirmed_context)
    if LLM_PROVIDER == "local":
        answer = rag.answer(retrieval_text, skip_scope_check=True)
        attach_document_evidence(answer, confirmed_context)
        response = corpus_gap.apply_gap_to_response(answer, pre_gap)
        return attach_active_case_state(response, conversation_case, route, retrieval_text, user_question or original_message, confirmed_context)
    if LLM_PROVIDER != "gemini":
        raise ConfigurationError(f"Unsupported LLM provider: {LLM_PROVIDER}")
    try:
        answer = grounded_answer.generate_grounded_answer(
            original_message=original_message,
            normalized_case_summary=retrieval_text,
            domains=context.domains,
            chunks=chunks,
            confirmed_case_facts=document_facts.confirmed_fact_lines(confirmed_context),
        )
        verified_answer = claim_verifier.verify_and_sanitize_response(answer, chunks)
        attach_document_evidence(verified_answer, confirmed_context)
        final_gap = corpus_gap.post_generation_check(verified_answer, pre_gap)
        if not final_gap.allow_grounded_answer:
            response = corpus_gap.abstention_response(final_gap)
            return attach_active_case_state(response, conversation_case, route, retrieval_text, user_question or original_message, confirmed_context)
        response = corpus_gap.apply_gap_to_response(verified_answer, final_gap)
        return attach_active_case_state(response, conversation_case, route, retrieval_text, user_question or original_message, confirmed_context)
    except grounded_answer.GroundedAnswerConfigurationError as exc:
        raise ConfigurationError(str(exc)) from exc
    except grounded_answer.GroundedAnswerError as exc:
        raise LLMError(str(exc)) from exc


def clarification_response(
    route: domain_router.RouteDecision,
    state: clarification.ClarificationState,
    question: clarification.ClarificationQuestion,
    progress: str | None = None,
) -> dict:
    return {
        "answer": {
            "issue_summary": route.issue_summary
            or "I need a little more detail about what happened before I can point you to the relevant law.",
            "possible_rights": [],
            "next_steps": [question.question],
        },
        "sources": [],
        "confidence": route.confidence,
        "insufficient_context": True,
        "disclaimer": DISCLAIMER,
        "clarification": {
            "needed": True,
            "state_id": state.state_id,
            "question": question.question,
            "progress": progress,
        },
        "routing": route_public_payload(route),
    }


def fact_clarification_response(
    route: domain_router.RouteDecision | None,
    context: fact_sufficiency.CaseContext,
    fact_result: fact_sufficiency.FactSufficiencyResult,
    progress: str | None = None,
) -> dict:
    question = fact_result.question or "Please briefly describe what happened."
    issue_summary = (
        fact_result.reason
        or (route.issue_summary if route else None)
        or context.issue_summary
        or "I need one more detail about what happened before I retrieve legal sources."
    )
    return {
        "answer": {
            "issue_summary": issue_summary,
            "possible_rights": [],
            "next_steps": [question],
        },
        "sources": [],
        "confidence": route.confidence if route else "low",
        "insufficient_context": True,
        "disclaimer": DISCLAIMER,
        "clarification": {
            "needed": True,
            "state_id": context.state_id,
            "question": question,
            "progress": progress,
            "type": "fact_sufficiency",
        },
        "routing": route_public_payload(route) if route else None,
    }


def insufficient_fact_detail_response() -> dict:
    return {
        "answer": {
            "issue_summary": "I still do not have enough factual detail to retrieve useful legal sources.",
            "possible_rights": [],
            "next_steps": ["Please briefly describe what happened."],
        },
        "sources": [],
        "confidence": "low",
        "insufficient_context": True,
        "disclaimer": DISCLAIMER,
        "clarification": {"needed": False, "state_id": None, "question": None, "progress": "none", "type": "fact_sufficiency"},
    }


def insufficient_detail_response() -> dict:
    return {
        "answer": {
            "issue_summary": "I still do not have enough factual detail to identify the supported legal area reliably.",
            "possible_rights": [],
            "next_steps": ["Please briefly tell me who is involved and what happened."],
        },
        "sources": [],
        "confidence": "low",
        "insufficient_context": True,
        "disclaimer": DISCLAIMER,
        "clarification": {"needed": False, "state_id": None, "question": None, "progress": "none"},
    }


def attach_document_evidence(response: dict, confirmed_context: dict | None) -> None:
    evidence = document_facts.document_evidence_payload(confirmed_context)
    if not evidence:
        return
    response["document_evidence_used"] = evidence
    response["confirmed_fact_context_id"] = confirmed_context.get("confirmed_fact_context_id") if confirmed_context else None


def detect_document_fact_conflict(question: str, confirmed_context: dict | None) -> str | None:
    if not confirmed_context:
        return None
    question_amounts = normalized_amounts(question)
    document_amounts = normalized_amounts(" ".join(document_facts.confirmed_values(confirmed_context, {"amounts"})))
    if question_amounts and document_amounts and question_amounts.isdisjoint(document_amounts):
        return "Your confirmed document facts show a different amount than your message. Which amount should I use?"
    question_dates = normalized_dates(question)
    document_dates = normalized_dates(" ".join(document_facts.confirmed_values(confirmed_context, {"dates"})))
    if question_dates and document_dates and question_dates.isdisjoint(document_dates):
        return "Your confirmed document facts show a different date than your message. Which date should I use?"
    return None


def normalized_amounts(text: str) -> set[str]:
    values = set()
    for match in re.findall(r"(?:rs\.?|inr|₹)\s*[\d,]+|\b\d{3,}(?:,\d{2,3})*\b", text or "", flags=re.I):
        digits = re.sub(r"\D", "", match)
        if digits:
            values.add(digits)
    return values


def normalized_dates(text: str) -> set[str]:
    month_names = (
        "january|february|march|april|may|june|july|august|september|october|november|december|"
        "jan|feb|mar|apr|jun|jul|aug|sep|sept|oct|nov|dec"
    )
    dates = set()
    for match in re.findall(rf"\b\d{{1,2}}\s+(?:{month_names})\s+\d{{4}}\b", text or "", flags=re.I):
        dates.add(re.sub(r"\s+", " ", match.lower()))
    for match in re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", text or ""):
        dates.add(match)
    return dates


def document_fact_conflict_response(question: str) -> dict:
    return {
        "answer": {
            "issue_summary": "I found a conflict between your typed message and confirmed document facts.",
            "possible_rights": [],
            "next_steps": [question],
        },
        "sources": [],
        "document_evidence_used": [],
        "confidence": "low",
        "insufficient_context": True,
        "disclaimer": DISCLAIMER,
        "clarification": {"needed": True, "state_id": None, "question": question, "type": "document_fact_conflict"},
    }


def router_minimal_response(route: domain_router.RouteDecision) -> dict:
    messages = {
        "unclear": "I need a little more detail about what happened before I can point you to the relevant law.",
        "unsupported": "This issue appears to be legal, but it is outside the legal areas currently supported by this Legal Aid AI corpus.",
        "out_of_scope": "This Legal Aid AI workflow is designed for legal-information queries.",
    }
    next_steps = {
        "unclear": ["Please share a few more details about what happened, who was involved, and what outcome you need."],
        "unsupported": ["For this issue, consider speaking with a qualified legal professional or using a legal resource focused on that area."],
        "out_of_scope": ["Try asking a legal-information question related to consumer, cyber, tenancy, or public-authority issues."],
    }
    message = messages.get(route.status, messages["unclear"])
    return {
        "answer": {
            "issue_summary": route.issue_summary or message,
            "possible_rights": [],
            "next_steps": next_steps.get(route.status, next_steps["unclear"]),
        },
        "sources": [],
        "confidence": route.confidence,
        "insufficient_context": route.status != "classified",
        "disclaimer": DISCLAIMER,
        "routing": route_public_payload(route),
    }


def with_routing(response: dict, route: domain_router.RouteDecision) -> dict:
    response["routing"] = route_public_payload(route)
    return response


def attach_active_case_state(
    response: dict,
    active_case: conversation_state.ActiveCaseState | None,
    route: domain_router.RouteDecision | None,
    case_summary: str,
    latest_message: str,
    confirmed_context: dict | None = None,
) -> dict:
    context_id = confirmed_context.get("confirmed_fact_context_id") if confirmed_context else None
    if active_case is None and route is not None and route.status == "classified":
        active_case = conversation_state.create_state(
            domains=route.domains,
            primary_domain=route.primary_domain,
            case_summary=case_summary,
            known_facts=[latest_message, case_summary],
            confirmed_document_context_id=context_id,
            last_user_intent="new_issue",
            last_issue_addressed=latest_message,
        )
    elif active_case is not None:
        conversation_state.update_state_after_answer(
            active_case,
            route or active_case,
            case_summary,
            latest_message,
            confirmed_document_context_id=context_id,
        )
    if active_case is not None:
        return with_conversation_state(response, active_case)
    return response


def with_conversation_state(response: dict, active_case: conversation_state.ActiveCaseState) -> dict:
    response["conversation_state_id"] = active_case.conversation_state_id
    response["conversation_state"] = conversation_state.compact_state_payload(active_case)
    if "disclaimer" not in response:
        response["disclaimer"] = DISCLAIMER
    return response


def route_public_payload(route: domain_router.RouteDecision) -> dict:
    return {
        "status": route.status,
        "domains": list(route.domains),
        "primary_domain": route.primary_domain,
        "confidence": route.confidence,
    }
