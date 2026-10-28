"""Case File export: one saved case -> a DOCX (and PDF) the user can take to a lawyer or the
District Legal Services Authority.

ASSEMBLED, NOT GENERATED. No LLM call is made anywhere in this module, and nothing in the file is
written for it: every line is either something the user said (labelled "as stated by you"), a
document fact the user confirmed, text the app already produced and stored for that case (answer
fields, the stored case summary), a corpus excerpt the app already retrieved and verified, or the
fixed text in case_file_constants.py. Same reasoning as complaint_drafter.py's slot-fill design.

Split for testability:
  - load_case_for_export(case_id)        reads the DB (case, messages, linked documents)
  - build_case_file_context(case)        pure: case bundle -> template context dict
  - render_case_file_docx(context)       docxtpl render into memory (BytesIO), never to disk
  - complaint_drafter.convert_docx_bytes_to_pdf()  reused as-is for PDF (LibreOffice)

Privacy: every piece of user-originated or app-generated text passes through redact() (the
existing case_store.sanitize_text() + fact_sufficiency.sanitize_user_fact() patterns -- OTP, PIN,
CVV, password, Aadhaar-like and Luhn-valid card numbers) before it reaches the context. Corpus
excerpts are law text, not user text, and are left as-is. Nothing here logs case content.
"""
from __future__ import annotations

import datetime
import io
import logging
import re
from typing import Any

import jinja2
from docxtpl import DocxTemplate

import case_file_constants as constants
import case_store
import conversation_state
import fact_sufficiency
import legal_education
from complaint_drafter import TEMPLATES_DIR, PdfConversionError, convert_docx_bytes_to_pdf  # noqa: F401 (re-exported for main.py)

logger = logging.getLogger("legal_aid_ai.case_file")

CASE_FILE_TEMPLATE_PATH = TEMPLATES_DIR / "case_file_base.docx"

_STRICT_JINJA_ENV = jinja2.Environment(undefined=jinja2.StrictUndefined, autoescape=True)

SKIPPED_TURN_TYPES = {"small_talk", "acknowledgement"}
MONTHS = {
    name: index
    for index, names in enumerate(
        (
            ("january", "jan"), ("february", "feb"), ("march", "mar"), ("april", "apr"), ("may",),
            ("june", "jun"), ("july", "jul"), ("august", "aug"), ("september", "sep", "sept"),
            ("october", "oct"), ("november", "nov"), ("december", "dec"),
        ),
        start=1,
    )
    for name in names
}
_MONTH_RE = "|".join(sorted(MONTHS, key=len, reverse=True))
_ORDINAL = r"(?:st|nd|rd|th)?"
DAY_MONTH_YEAR = re.compile(rf"\b(\d{{1,2}}){_ORDINAL}\s+(?:of\s+)?({_MONTH_RE})\.?,?\s+(\d{{4}})\b", re.I)
MONTH_DAY_YEAR = re.compile(rf"\b({_MONTH_RE})\.?\s+(\d{{1,2}}){_ORDINAL},?\s+(\d{{4}})\b", re.I)
NUMERIC_DAY_FIRST = re.compile(r"\b(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})\b")
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


class CaseFileError(Exception):
    """Raised when a case file can't be produced (e.g. the case has no answers yet)."""


# --- Loading (the only part that touches the database) ---


def load_case_for_export(case_id: int, db_path=None) -> dict[str, Any] | None:
    """Case row + messages + documents linked to it. Read-only: nothing is written."""
    case = case_store.get_case(case_id, db_path)
    if case is None:
        return None
    messages = case_store.get_messages(case_id, db_path)
    context_ids = _referenced_context_ids(case, messages)
    return {**case, "messages": messages, "documents": _documents_for_case(case_id, context_ids, db_path)}


def _referenced_context_ids(case: dict[str, Any], messages: list[dict[str, Any]]) -> list[str]:
    ids: list[str] = []
    for message in messages:
        content = message.get("content")
        if message.get("role") == "assistant" and isinstance(content, dict):
            context_id = content.get("confirmed_fact_context_id")
            if context_id and context_id not in ids:
                ids.append(context_id)
    case_context_id = (case.get("confirmed_document_context") or {}).get("confirmed_fact_context_id")
    if case_context_id and case_context_id not in ids:
        ids.append(case_context_id)
    return ids


def _documents_for_case(case_id: int, context_ids: list[str], db_path=None) -> list[dict[str, Any]]:
    """documents.case_id has never actually been populated by the upload flow, so a document is
    linked to a case by the confirmed-fact context id it produced: confirm-facts stores that id
    on the document row, and every answer that used those facts stores the same id on the
    assistant message. Exact id match -- no filename or content guessing. Checks sqlite_master
    rather than calling document_store.init_db(), which would create the upload directory."""
    with case_store.connect(db_path) as conn:
        if not conn.execute("SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'documents'").fetchone():
            return []
        clauses = ["case_id = ?"]
        params: list[Any] = [case_id]
        for context_id in context_ids:
            clauses.append("confirmed_fact_context_json LIKE ?")
            params.append(f'%"{context_id}"%')
        rows = conn.execute(
            f"SELECT id, display_filename, created_at, case_id, confirmed_fact_context_json FROM documents "  # noqa: S608
            f"WHERE {' OR '.join(clauses)} ORDER BY created_at ASC, id ASC",
            params,
        ).fetchall()
    documents = []
    for row in rows:
        confirmed = case_store.json_loads(row["confirmed_fact_context_json"]) or {}
        context_id = confirmed.get("confirmed_fact_context_id")
        if row["case_id"] != case_id and context_id not in context_ids:
            continue  # LIKE matched a substring elsewhere in the JSON; not actually this context
        documents.append(
            {
                "id": row["id"],
                "filename": row["display_filename"],
                "created_at": row["created_at"],
                "confirmed_fact_context_id": context_id,
                "confirmed_facts": confirmed.get("confirmed_facts") or {},
            }
        )
    return documents


# --- Pure assembly ---


def build_case_file_context(
    case: dict[str, Any],
    generated_on: datetime.date | None = None,
    manifest: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """`case` is load_case_for_export()'s bundle. `manifest` (source_file -> corpus manifest entry)
    is injectable for tests; defaults to the live corpus manifest."""
    generated_on = generated_on or datetime.date.today()
    if manifest is None:
        manifest = legal_education.load_manifest_documents()
    messages = case.get("messages") or []
    turns = _turns(messages)
    answers = [turn for turn in turns if turn["is_answer"]]
    if not answers:
        raise CaseFileError("This case has no answers yet, so there is nothing to put in a case file.")

    notes: list[str] = []
    facts = _facts(case, turns)
    timeline, used_numeric_dates = _timeline(facts)
    laws, law_notes = _laws(answers, manifest)
    notes.extend(law_notes)
    if not timeline:
        notes.append("No timeline is included: none of the facts above has a full date (day, month and year).")
    elif used_numeric_dates:
        notes.append("Dates written with numbers only (like 05/03/2026) are read day first, the usual Indian format.")

    where_to_go = _dedupe_text(item for turn in answers for item in turn["answer"].get("where_to_approach") or [])
    evidence_items = _dedupe_text(item for turn in answers for item in turn["answer"].get("evidence_to_preserve") or [])
    uploaded_documents = [
        {"name": redact(document["filename"]), "date": _display_timestamp(document["created_at"])}
        for document in case.get("documents") or []
    ]

    context = {
        "heading": constants.CASE_FILE_HEADING,
        "notice": constants.NOT_LEGAL_ADVICE_NOTICE,
        "how_made": constants.HOW_THIS_FILE_WAS_MADE,
        "title": redact(case.get("title") or "Legal Question"),
        "legal_areas": _legal_areas(case),
        "case_created_display": _display_timestamp(case.get("created_at")),
        "generated_on_display": _display_date(generated_on),
        "situation": _situation(case, turns),
        "facts": [{"text": fact["text"], "label": fact["label"], "stated_on": fact["stated_on"]} for fact in facts],
        "timeline": timeline,
        "laws": laws,
        "where_to_go": where_to_go,
        "evidence_items": evidence_items,
        "uploaded_documents": uploaded_documents,
        "lawyer_questions": list(constants.LAWYER_QUESTIONS),
        "free_help": [dict(item) for item in constants.FREE_LEGAL_HELP],
        "appendix": _appendix(turns),
        "notes": notes,
    }
    context["sections"] = present_sections(context)
    return context


def present_sections(context: dict[str, Any]) -> list[str]:
    """Section ids in file order, mirroring the template's own conditionals. Deadlines and the
    forum finder aren't listed because those features don't exist in the app yet (see
    CHANGELOG) -- the template has no heading for them at all."""
    sections = ["cover", "situation", "facts"]
    if context["timeline"]:
        sections.append("timeline")
    if context["laws"]:
        sections.append("laws")
    if context["where_to_go"]:
        sections.append("where_to_go")
    if context["evidence_items"] or context["uploaded_documents"]:
        sections.append("evidence")
    sections.extend(["lawyer_questions", "free_legal_help", "appendix"])
    return sections


def redact(text: Any) -> str:
    cleaned = CONTROL_CHARS.sub(" ", str(text or ""))
    cleaned = case_store.sanitize_text(cleaned)
    cleaned = fact_sufficiency.sanitize_user_fact(cleaned)
    # The card-number pattern consumes the space after the number ("[...omitted]was linked").
    return re.sub(r"(omitted\])(?=\w)", r"\1 ", cleaned)


def _turns(messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """One entry per user message, paired with the assistant message that answered it (if any)
    and the turn type the app recorded for it at the time."""
    turns = []
    previous_assistant: dict[str, Any] | None = None
    for index, message in enumerate(messages):
        if message.get("role") != "user":
            if isinstance(message.get("content"), dict):
                previous_assistant = message["content"]
            continue
        reply = messages[index + 1] if index + 1 < len(messages) and messages[index + 1].get("role") == "assistant" else None
        content = reply.get("content") if reply and isinstance(reply.get("content"), dict) else {}
        asked = (previous_assistant or {}).get("clarification") or {}
        turns.append(
            {
                "text": redact(message.get("content")),
                "created_at": message.get("created_at"),
                "reply": content,
                "answer": content.get("answer") if isinstance(content.get("answer"), dict) else {},
                "is_answer": case_store.is_answer_content(content),
                "turn_type": _recorded_turn_type(content),
                "answering_question": redact(asked.get("question")) if asked.get("needed") and asked.get("question") else None,
            }
        )
    return turns


def _recorded_turn_type(content: dict[str, Any]) -> str | None:
    conversation = content.get("conversation") or {}
    state = content.get("conversation_state") or {}
    return conversation.get("turn_type") or state.get("last_user_intent")


def _fact_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def _facts(case: dict[str, Any], turns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """User facts in the order given, with document facts inserted at the turn their document was
    first used. Corrections replay the app's own conversation_state.apply_correction() at each
    turn the app RECORDED as a correction (the stored turn type) -- the same rule the live state
    applied, minus its 12-fact cap -- rather than re-deciding here what was corrected."""
    contexts = _document_contexts(case, turns)
    facts: list[dict[str, Any]] = []
    seen_contexts: set[str] = set()

    def add_document_facts(context_id: str) -> None:
        if context_id in seen_contexts or context_id not in contexts:
            return
        seen_contexts.add(context_id)
        context = contexts[context_id]
        for text in context["facts"]:
            facts.append({"text": text, "label": context["label"], "stated_on": context["date"], "kind": "document"})

    # The case-level context was attached when the case was created or later updated. If no
    # answer recorded using it, we can't place it more precisely than "before the conversation".
    turn_context_ids = {turn["reply"].get("confirmed_fact_context_id") for turn in turns}
    for context_id in contexts:
        if context_id not in turn_context_ids:
            add_document_facts(context_id)

    for turn in turns:
        context_id = turn["reply"].get("confirmed_fact_context_id")
        if context_id:
            add_document_facts(context_id)
        text = turn["text"]
        lowered = text.lower()
        if not text or turn["turn_type"] in SKIPPED_TURN_TYPES or case_store.is_small_talk(text):
            continue
        stated_on = _display_timestamp(turn["created_at"])
        if turn["turn_type"] == "correction":
            facts = [fact for fact in facts if fact["kind"] == "document" or _survives_correction(fact["text"], text)]
            facts.append({"text": text, "label": "As stated by you (your correction)", "stated_on": stated_on, "kind": "user"})
            continue
        if turn["turn_type"] == "follow_up_question" and (
            conversation_state.is_question_like(lowered) or not conversation_state.has_fact_content(lowered)
        ):
            continue  # a question, not a fact -- it appears in the conversation record instead
        label = "As stated by you"
        if turn["answering_question"]:
            label = f"As stated by you, answering: “{turn['answering_question']}”"
        facts.append({"text": text, "label": label, "stated_on": stated_on, "kind": "user"})

    output, seen = [], set()
    for fact in facts:
        key = _fact_key(fact["text"])
        if key and key not in seen:
            seen.add(key)
            output.append(fact)
    return output


def _survives_correction(fact_text: str, correction: str) -> bool:
    # One fact at a time so apply_correction()'s MAX_FACTS cap can never drop anything here.
    kept = conversation_state.apply_correction([fact_text], correction)
    return _fact_key(fact_text) in {_fact_key(item) for item in kept}


def _document_contexts(case: dict[str, Any], turns: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """confirmed_fact_context_id -> the confirmed facts and which document they came from.
    Preference: the document row's own confirmed facts (full set, and it knows the filename) ->
    the case's stored confirmed context -> the facts an answer recorded using."""
    by_document = {doc["confirmed_fact_context_id"]: doc for doc in case.get("documents") or [] if doc.get("confirmed_fact_context_id")}
    case_context = case.get("confirmed_document_context") or {}
    contexts: dict[str, dict[str, Any]] = {}

    def register(context_id: str | None, confirmed_facts: dict[str, Any] | None, evidence: list[dict[str, Any]] | None = None) -> None:
        if not context_id or context_id in contexts:
            return
        document = by_document.get(context_id)
        if document and document.get("confirmed_facts"):
            confirmed_facts = document["confirmed_facts"]
        if confirmed_facts:
            pairs = [
                (item.get("label"), item.get("value"))
                for category, items in confirmed_facts.items()
                if isinstance(items, list) and category not in {"uncertain_items", "warnings"}
                for item in items
                if isinstance(item, dict)
            ]
            document_type = confirmed_facts.get("document_type")
        else:
            pairs = [(item.get("label"), item.get("value")) for item in evidence or [] if isinstance(item, dict)]
            document_type = next((item.get("document_type") for item in evidence or [] if isinstance(item, dict)), None)
        texts = [f"{_pretty_label(label)}: {redact(value)}" for label, value in pairs if str(value or "").strip()]
        if not texts:
            return
        if document:
            label = f"From your document “{redact(document['filename'])}” (facts you confirmed)"
        else:
            kind = str(document_type or "").replace("_", " ").strip()
            label = f"From a document you confirmed ({kind})" if kind and kind != "unknown" else "From a document you confirmed"
        # No date on document facts: the only date we have is the upload date, which would read
        # as the document's own date. Upload dates are listed under "Documents already uploaded".
        contexts[context_id] = {"facts": texts, "label": label, "date": None}

    register(case_context.get("confirmed_fact_context_id"), case_context.get("confirmed_facts"))
    for turn in turns:
        reply = turn["reply"]
        register(reply.get("confirmed_fact_context_id"), None, reply.get("document_evidence_used"))
    return contexts


def _pretty_label(label: Any) -> str:
    text = re.sub(r"\s+", " ", str(label or "fact").replace("_", " ")).strip()
    return text[:1].upper() + text[1:]


def explicit_dates(text: str) -> list[tuple[datetime.date, bool]]:
    """Every FULL date (day + month + year) written in `text`, as (date, was_numeric). Partial
    dates ("March 2026", "last week", "5/3/26") are ignored -- never estimated or completed."""
    found: list[tuple[int, datetime.date, bool]] = []

    def add(position: int, year: str, month: int | str, day: str, numeric: bool) -> None:
        try:
            found.append((position, datetime.date(int(year), int(month), int(day)), numeric))
        except ValueError:
            pass  # e.g. 31 February -- not a real date, so not a timeline entry

    for match in DAY_MONTH_YEAR.finditer(text):
        add(match.start(), match.group(3), MONTHS[match.group(2).lower()], match.group(1), False)
    for match in MONTH_DAY_YEAR.finditer(text):
        add(match.start(), match.group(3), MONTHS[match.group(1).lower()], match.group(2), False)
    for match in NUMERIC_DAY_FIRST.finditer(text):
        add(match.start(), match.group(3), match.group(2), match.group(1), True)
    for match in ISO_DATE.finditer(text):
        add(match.start(), match.group(1), match.group(2), match.group(3), False)
    output: list[tuple[datetime.date, bool]] = []
    for _position, date, numeric in sorted(found, key=lambda item: item[0]):
        if date not in {existing for existing, _ in output}:
            output.append((date, numeric))
    return output


def _timeline(facts: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], bool]:
    entries = []
    used_numeric = False
    for order, fact in enumerate(facts):
        for date, numeric in explicit_dates(fact["text"]):
            used_numeric = used_numeric or numeric
            entries.append((date, order, {"date_display": _display_date(date), "text": fact["text"], "label": fact["label"]}))
    entries.sort(key=lambda item: (item[0], item[1]))
    return [entry for _date, _order, entry in entries], used_numeric


def _laws(answers: list[dict[str, Any]], manifest: dict[str, dict[str, Any]]) -> tuple[list[dict[str, Any]], list[str]]:
    laws: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    excluded_unverified = 0
    answers_without_record = 0
    for turn in answers:
        reply = turn["reply"]
        sources = [source for source in reply.get("sources") or [] if isinstance(source, dict)]
        verification = reply.get("verification")
        if not isinstance(verification, dict):
            if sources:
                answers_without_record += 1
            continue
        verified_ids = set(verification.get("verified_source_chunk_ids") or [])
        for source in sources:
            if source.get("chunk_id") not in verified_ids:
                excluded_unverified += 1
                continue
            source_file = source.get("source_file") or ""
            title = str(source.get("document_title") or source.get("document") or source_file).strip()
            provision = str(source.get("provision") or source.get("section") or "").strip()
            key = (source_file or title.lower(), provision.lower())
            if key in seen:
                continue
            seen.add(key)
            entry = manifest.get(source_file) or {}
            authority, warning = authority_label(entry)
            if not provision and entry.get("document_type") == "case_law" and entry.get("citation"):
                provision = str(entry["citation"])
            laws.append(
                {
                    "title": title,
                    "provision": provision,
                    "authority": authority,
                    "warning": warning,
                    "excerpt": CONTROL_CHARS.sub(" ", str(source.get("excerpt") or "")).strip(),
                    "pages": _page_label(source),
                    "source_file": source_file,
                    "chunk_id": source.get("chunk_id"),
                }
            )
    notes = []
    if excluded_unverified:
        notes.append(
            f"{_count(excluded_unverified, 'source reference')} shown in the app {'was' if excluded_unverified == 1 else 'were'} "
            "left out of “Laws that may apply” because no statement in the answer that cited "
            f"{'it' if excluded_unverified == 1 else 'them'} passed the app's source check."
        )
    if answers_without_record:
        notes.append(
            f"Sources from {_count(answers_without_record, 'earlier answer')} are not listed: "
            f"{'it was' if answers_without_record == 1 else 'those answers were'} saved before the app began recording "
            "which sources passed its source check, so they can't be shown here as checked."
        )
    return laws, notes


def _count(number: int, noun: str) -> str:
    return f"{number} {noun}{'' if number == 1 else 's'}"


def authority_label(entry: dict[str, Any]) -> tuple[str, str | None]:
    document_type = (entry.get("document_type") or "").lower()
    authority = (entry.get("authority_level") or "").lower()
    if document_type == "case_law":
        return constants.CASE_LAW_LABEL, constants.GOOD_LAW_WARNINGS.get(entry.get("good_law"))
    if authority == "secondary_summary":
        return constants.COMPILED_SUMMARY_LABEL, None
    if authority == "official_guidance":
        return constants.OFFICIAL_GUIDANCE_LABEL, None
    if authority == "procedural_guide":
        return constants.PROCEDURAL_GUIDE_LABEL, None
    if authority == "supporting" or document_type.startswith("supporting_"):
        return constants.SUPPORTING_LAW_LABEL, None
    if authority == "primary":
        return constants.PRIMARY_LABELS_BY_DOCUMENT_TYPE.get(document_type, constants.DEFAULT_PRIMARY_LABEL), None
    return "Source type not recorded", None


def _page_label(source: dict[str, Any]) -> str:
    start = source.get("page_start") or source.get("page")
    end = source.get("page_end") or start
    if not start:
        return ""
    return f"p. {start}" if start == end else f"pp. {start}–{end}"


def _situation(case: dict[str, Any], turns: list[dict[str, Any]]) -> dict[str, str]:
    summary = redact((case.get("conversation_state") or {}).get("case_summary")).strip()
    if summary:
        return {"label": "Summary Legal Aid AI recorded during your conversation, based on what you told it", "text": summary}
    first = next((turn["text"] for turn in turns if turn["text"]), "")
    return {"label": "Your first message, as you wrote it", "text": first}


def _legal_areas(case: dict[str, Any]) -> str:
    domains = list((case.get("conversation_state") or {}).get("domains") or [])
    if case.get("primary_domain") and case["primary_domain"] not in domains:
        domains.insert(0, case["primary_domain"])
    labels = [constants.DOMAIN_LABELS.get(domain, str(domain).replace("_", " ").title()) for domain in domains if domain]
    return ", ".join(dict.fromkeys(labels)) or "Not classified"


def _appendix(turns: list[dict[str, Any]]) -> list[dict[str, str]]:
    entries = []
    for turn in turns:
        if not turn["text"] or turn["turn_type"] in SKIPPED_TURN_TYPES or case_store.is_small_talk(turn["text"]):
            continue
        reply = turn["reply"]
        clarification = reply.get("clarification") or {}
        if turn["is_answer"]:
            label, text = "In short", turn["answer"].get("issue_summary")
        elif reply.get("technical_error"):
            label, text = "App's reply", "The app could not answer this message because of a technical error."
        elif clarification.get("needed") and clarification.get("question"):
            label, text = "The app asked", clarification.get("question")
        elif turn["answer"].get("issue_summary"):
            label, text = "App's reply", turn["answer"].get("issue_summary")
        else:
            continue
        entries.append(
            {"date": _display_timestamp(turn["created_at"]), "question": turn["text"], "answer_label": label, "short_answer": redact(text)}
        )
    return entries


def _dedupe_text(values) -> list[str]:
    output, seen = [], set()
    for value in values:
        text = redact(value).strip()
        key = _fact_key(text)
        if key and key not in seen:
            seen.add(key)
            output.append(text)
    return output


def _display_date(date: datetime.date) -> str:
    return f"{date.day} {date.strftime('%B %Y')}"


def _display_timestamp(value: Any) -> str | None:
    if not value:
        return None
    try:
        return _display_date(datetime.datetime.strptime(str(value)[:10], "%Y-%m-%d").date())
    except ValueError:
        return None


# --- Rendering ---


def render_case_file_docx(context: dict[str, Any]) -> bytes:
    if not CASE_FILE_TEMPLATE_PATH.exists():
        raise CaseFileError(
            f"Case file template not found: {CASE_FILE_TEMPLATE_PATH}. Run "
            "build_templates.build_case_file_base_template() to generate it."
        )
    doc = DocxTemplate(str(CASE_FILE_TEMPLATE_PATH))
    # autoescape: user text can contain & and <, which would otherwise corrupt the DOCX XML.
    doc.render(context, jinja_env=_STRICT_JINJA_ENV, autoescape=True)
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()


def render_case_file_pdf(context: dict[str, Any]) -> bytes:
    """LibreOffice needs real files, so convert_docx_bytes_to_pdf() uses a TemporaryDirectory that
    is deleted as soon as the conversion returns -- the PDF itself is returned as bytes."""
    return convert_docx_bytes_to_pdf(render_case_file_docx(context))


def case_file_filename(title: str, generated_on: datetime.date, extension: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", str(title or "").lower()).strip("-")[:40].strip("-") or "case"
    return f"case-file-{slug}-{generated_on.isoformat()}.{extension}"
