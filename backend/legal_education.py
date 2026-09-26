from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import legal_education_config as config
from config import DOCUMENTS_DIR, PROJECT_ROOT

MANIFEST_PATH = DOCUMENTS_DIR / "corpus_manifest.json"
CHUNKS_PATH = PROJECT_ROOT / "backend" / "parsed" / "legal_chunks.jsonl"


class LegalEducationError(ValueError):
    pass


@dataclass
class EducationIndex:
    categories: dict[str, dict[str, Any]]
    manifest_documents: dict[str, dict[str, Any]]
    source_id_to_file: dict[str, str]
    provisions_by_source: dict[str, dict[str, dict[str, Any]]]


_INDEX: EducationIndex | None = None
_INDEX_SOURCE_MTIMES: tuple[float, float] | None = None


def _current_source_mtimes() -> tuple[float, float]:
    """mtimes of the two files the index is built from. 0.0 for a file that doesn't exist yet
    (e.g. before the first `python ingest.py` run) rather than raising."""
    manifest_mtime = MANIFEST_PATH.stat().st_mtime if MANIFEST_PATH.exists() else 0.0
    chunks_mtime = CHUNKS_PATH.stat().st_mtime if CHUNKS_PATH.exists() else 0.0
    return (manifest_mtime, chunks_mtime)


def get_index() -> EducationIndex:
    """Lazily builds (or rebuilds) the in-memory index, and -- this is the actual fix for the
    corpus-staleness bug (2026-09-16) -- self-invalidates by comparing MANIFEST_PATH/CHUNKS_PATH's
    current mtimes against what was recorded at the last build, on every call (two cheap stat()
    syscalls). reset_index_cache() forces a rebuild explicitly and still exists for that (tests,
    or any future caller that wants an immediate rebuild without waiting on mtimes), but mtime
    comparison is what actually solves the original bug: `ingest.py` -- which is how the corpus
    changes reset_index_cache() was meant to react to -- runs as a separate OS process from the
    live `uvicorn main:app` server. A call to reset_index_cache() from inside ingest.py's process
    cannot reach this module's `_INDEX` global in the server's process; there is no shared memory
    between them. Comparing file mtimes works across that process boundary because it reads the
    filesystem, not another process's memory -- so it's the only mechanism here that actually
    achieves "reflected without requiring a manual backend restart", which is why it's the
    primary fix and not just a belt-and-suspenders addition alongside calling
    reset_index_cache() from ingest.py."""
    global _INDEX, _INDEX_SOURCE_MTIMES
    current_mtimes = _current_source_mtimes()
    if _INDEX is None or current_mtimes != _INDEX_SOURCE_MTIMES:
        _INDEX = build_index()
        _INDEX_SOURCE_MTIMES = current_mtimes
    return _INDEX


def reset_index_cache() -> None:
    global _INDEX, _INDEX_SOURCE_MTIMES
    _INDEX = None
    _INDEX_SOURCE_MTIMES = None


def build_index() -> EducationIndex:
    manifest_documents = load_manifest_documents()
    provisions_by_source = load_provisions()
    source_id_to_file = {source_id(source_file): source_file for source_file in manifest_documents}
    categories = {
        category_id: category_payload(category_id, category, manifest_documents, provisions_by_source)
        for category_id, category in config.CATEGORIES.items()
    }
    categories = {category_id: category for category_id, category in categories.items() if category["sources"]}
    return EducationIndex(categories, manifest_documents, source_id_to_file, provisions_by_source)


def list_categories() -> list[dict[str, Any]]:
    index = get_index()
    return [
        {
            "id": category_id,
            "title": category["title"],
            "description": category["description"],
            "icon": category.get("icon"),
        }
        for category_id, category in index.categories.items()
    ]


def get_category(category_id: str) -> dict[str, Any]:
    index = get_index()
    category = index.categories.get(clean_id(category_id))
    if category is None:
        raise LegalEducationError("Category not found.")
    return category


def get_source(source_id_value: str) -> dict[str, Any]:
    index = get_index()
    source_file = source_file_from_id(index, source_id_value)
    document = index.manifest_documents[source_file]
    provision_map = index.provisions_by_source.get(source_file, {})
    configured = config.IMPORTANT_PROVISIONS.get(source_file, [])
    provisions = [provision_map[provision_key(kind, number)] for kind, number in configured if provision_key(kind, number) in provision_map]
    return {
        **source_public_payload(document),
        "description": config.SOURCE_DESCRIPTIONS.get(source_file) or document.get("notes") or "",
        "what_this_law_covers": source_coverage_bullets(source_file, document),
        "important_provisions": [provision_summary(provision) for provision in provisions],
    }


def get_provision(source_id_value: str, provision_id: str) -> dict[str, Any]:
    index = get_index()
    source_file = source_file_from_id(index, source_id_value)
    provision = index.provisions_by_source.get(source_file, {}).get(clean_id(provision_id))
    if provision is None:
        raise LegalEducationError("This provision is not currently available in the local legal corpus.")
    document = index.manifest_documents[source_file]
    return {
        **provision_summary(provision),
        "plain_language_explanation": plain_language_explanation(provision),
        "official_excerpt": excerpt(provision.get("text", "")),
        "source": source_public_payload(document),
        "page": provision.get("page"),
        "page_start": provision.get("page_start"),
        "page_end": provision.get("page_end"),
        "chunk_id": provision.get("chunk_id"),
    }


def search_provisions(query: str, limit: int = 20) -> list[dict[str, Any]]:
    """Case-insensitive search across every provision's title and text, for every source that
    belongs to a displayed category -- lets the frontend deep-link straight to a matched
    provision, skipping the category -> source -> provision browse. Deliberately scoped to
    provisions reachable through that same browse hierarchy (a source not in any displayed
    category is skipped), not every provision in provisions_by_source -- search is a shortcut
    into the existing hierarchy, not a door to content that isn't otherwise browsable."""
    index = get_index()
    needle = query.strip().lower()
    if not needle:
        return []

    source_file_to_category_id = {
        source["source_file"]: category_id
        for category_id, category in index.categories.items()
        for source in category["sources"]
    }

    matches: list[dict[str, Any]] = []
    for source_file, provisions in index.provisions_by_source.items():
        category_id = source_file_to_category_id.get(source_file)
        document = index.manifest_documents.get(source_file)
        if category_id is None or document is None:
            continue
        for provision in provisions.values():
            title = provision.get("title") or ""
            text = provision.get("text") or ""
            title_hit = needle in title.lower()
            if not title_hit and needle not in text.lower():
                continue
            matches.append(
                {
                    "category_id": category_id,
                    "category_title": index.categories[category_id]["title"],
                    "source_id": source_id(source_file),
                    "source_short_title": document.get("short_title") or document.get("document_title"),
                    "provision_id": provision["id"],
                    "provision_label": provision["label"],
                    "provision_title": provision.get("title"),
                    "excerpt": excerpt(text, limit=220),
                    "_title_hit": title_hit,
                }
            )

    matches.sort(
        key=lambda item: (
            0 if item["_title_hit"] else 1,  # a title match is more relevant than a text-only match
            item["category_title"],
            item["source_short_title"] or "",
            item["provision_label"],
        )
    )
    for item in matches:
        del item["_title_hit"]
    return matches[:limit]


def source_pdf_path(source_id_value: str) -> Path:
    index = get_index()
    source_file = source_file_from_id(index, source_id_value)
    path = (DOCUMENTS_DIR / source_file).resolve()
    root = DOCUMENTS_DIR.resolve()
    if root not in path.parents or not path.exists():
        raise LegalEducationError("Source PDF is not available.")
    return path


def corpus_pdf_path(source_file: str) -> Path:
    """Resolve a cited corpus PDF, allowing only active manifest documents inside documents/."""
    documents = load_manifest_documents()
    source_file = str(source_file or "").replace("\\", "/").strip()
    if source_file not in documents or source_file.startswith("archive/") or not source_file.lower().endswith(".pdf"):
        raise LegalEducationError("Source PDF is not available.")
    path = (DOCUMENTS_DIR / source_file).resolve()
    if DOCUMENTS_DIR.resolve() not in path.parents or not path.exists():
        raise LegalEducationError("Source PDF is not available.")
    return path


def load_manifest_documents() -> dict[str, dict[str, Any]]:
    data = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return {item["source_file"]: item for item in data.get("documents", []) if item.get("source_file")}


def load_provisions() -> dict[str, dict[str, dict[str, Any]]]:
    by_source: dict[str, dict[str, dict[str, Any]]] = {}
    with CHUNKS_PATH.open(encoding="utf-8") as handle:
        for line in handle:
            chunk = json.loads(line)
            source_file = chunk.get("source_file") or chunk.get("source")
            kind, number, title = provision_identity(chunk)
            if not source_file or not kind or not number:
                continue
            key = provision_key(kind, number)
            source_items = by_source.setdefault(source_file, {})
            if key not in source_items:
                source_items[key] = {
                    "id": key,
                    "kind": kind,
                    "number": number,
                    "label": provision_label(kind, number),
                    "title": title or provision_label(kind, number),
                    "page": chunk.get("page"),
                    "page_start": chunk.get("page_start") or chunk.get("page"),
                    "page_end": chunk.get("page_end") or chunk.get("page"),
                    "chunk_id": chunk.get("chunk_id"),
                    "text": chunk.get("text", ""),
                }
            elif len(source_items[key].get("text", "")) < 1200:
                source_items[key]["text"] = f"{source_items[key].get('text', '')}\n\n{chunk.get('text', '')}".strip()
                source_items[key]["page_end"] = chunk.get("page_end") or chunk.get("page") or source_items[key].get("page_end")
    return by_source


def provision_identity(chunk: dict[str, Any]) -> tuple[str | None, str | None, str | None]:
    fields = (
        ("section", "section_number", "section_title"),
        ("article", "article_number", "article_title"),
        ("rule", "rule_number", "rule_title"),
        ("regulation", "regulation_number", "regulation_title"),
        ("guideline", "guideline_number", "guideline_title"),
        ("provision", "provision_number", "provision_title"),
    )
    for kind, number_key, title_key in fields:
        number = chunk.get(number_key)
        if number:
            return kind, str(number), chunk.get(title_key)
    return None, None, None


def category_payload(
    category_id: str,
    category: dict[str, Any],
    manifest_documents: dict[str, dict[str, Any]],
    provisions_by_source: dict[str, dict[str, dict[str, Any]]],
) -> dict[str, Any]:
    sources = []
    for source_file in category.get("source_files", []):
        document = manifest_documents.get(source_file)
        if not document:
            continue
        configured = config.IMPORTANT_PROVISIONS.get(source_file, [])
        available_count = sum(
            1 for kind, number in configured if provision_key(kind, number) in provisions_by_source.get(source_file, {})
        )
        sources.append({**source_public_payload(document), "important_provision_count": available_count})
    return {
        "id": category_id,
        "title": category["title"],
        "description": category["description"],
        "icon": category.get("icon"),
        "limitation": category.get("limitation"),
        "overview": list(category.get("overview", [])),
        "common_issues": list(category.get("common_issues", [])),
        "what_you_can_do": list(category.get("what_you_can_do", [])),
        "sources": sources,
        "disclaimer": "This information is for general legal awareness and does not constitute professional legal advice. For guidance on your specific situation, ask a question.",
    }


def source_public_payload(document: dict[str, Any]) -> dict[str, Any]:
    source_file = document["source_file"]
    return {
        "id": source_id(source_file),
        "source_file": source_file,
        "document_title": document.get("document_title"),
        "short_title": document.get("short_title") or document.get("document_title"),
        "jurisdiction": document.get("jurisdiction"),
        "year": document.get("year"),
        "document_type": document.get("document_type"),
        "authority_level": document.get("authority_level"),
        "domain": document.get("domain"),
        "status": document.get("status"),
        "retrieval_priority": document.get("retrieval_priority"),
    }


def provision_summary(provision: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": provision["id"],
        "kind": provision["kind"],
        "number": provision["number"],
        "label": provision["label"],
        "title": provision.get("title"),
        "page": provision.get("page"),
        "page_start": provision.get("page_start"),
        "page_end": provision.get("page_end"),
        "chunk_id": provision.get("chunk_id"),
    }


def plain_language_explanation(provision: dict[str, Any]) -> str:
    title = provision.get("title") or provision.get("label")
    label = provision.get("label")
    text = (provision.get("text") or "").lower()
    if "refund" in text or "replace" in text or "compensation" in text:
        return f"{label} describes possible remedies or orders connected with {title.lower()}."
    if "appeal" in text:
        return f"{label} explains an appeal mechanism connected with {title.lower()}."
    if "complaint" in text:
        return f"{label} explains how a complaint-related process may work for {title.lower()}."
    if "right" in text or "entitled" in text:
        return f"{label} sets out a right or entitlement connected with {title.lower()}."
    if "punishment" in text or "penalty" in text:
        return f"{label} deals with consequences or penalties connected with {title.lower()}."
    if "duty" in text or "obligation" in text:
        return f"{label} describes duties or obligations connected with {title.lower()}."
    return f"{label} is an available provision in the current legal corpus about {title.lower()}."


def source_coverage_bullets(source_file: str, document: dict[str, Any]) -> list[str]:
    description = config.SOURCE_DESCRIPTIONS.get(source_file) or document.get("notes") or ""
    parts = [part.strip() for part in re.split(r",| and ", description) if part.strip()]
    return parts[:5] or [description]


def source_file_from_id(index: EducationIndex, source_id_value: str) -> str:
    source_file = index.source_id_to_file.get(clean_id(source_id_value))
    if source_file is None:
        raise LegalEducationError("Source not found.")
    return source_file


def source_id(source_file: str) -> str:
    slug = Path(source_file).with_suffix("").as_posix()
    return clean_id(slug.replace("/", "__"))


def provision_key(kind: str, number: str) -> str:
    return clean_id(f"{kind}-{number}")


def provision_label(kind: str, number: str) -> str:
    labels = {
        "section": "Section",
        "article": "Article",
        "rule": "Rule",
        "regulation": "Regulation",
        "guideline": "Guideline",
        "provision": "Provision",
    }
    return f"{labels.get(kind, kind.title())} {number}"


def clean_id(value: str) -> str:
    return re.sub(r"[^a-z0-9_-]+", "-", str(value or "").lower()).strip("-")


def excerpt(text: str, limit: int = 900) -> str:
    cleaned = re.sub(r"\s+", " ", text or "").strip()
    if len(cleaned) <= limit:
        return cleaned
    return cleaned[: limit - 1].rsplit(" ", 1)[0] + "..."
