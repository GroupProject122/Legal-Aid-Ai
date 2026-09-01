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


def get_index() -> EducationIndex:
    global _INDEX
    if _INDEX is None:
        _INDEX = build_index()
    return _INDEX


def reset_index_cache() -> None:
    global _INDEX
    _INDEX = None


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


def source_pdf_path(source_id_value: str) -> Path:
    index = get_index()
    source_file = source_file_from_id(index, source_id_value)
    path = (DOCUMENTS_DIR / source_file).resolve()
    root = DOCUMENTS_DIR.resolve()
    if root not in path.parents or not path.exists():
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
