from __future__ import annotations

import argparse
import json
import logging
import re
import time
from collections import Counter
from collections.abc import Callable
from pathlib import Path

import faiss
import numpy as np
from pypdf import PdfReader

from config import (
    BASE_DIR,
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DOCUMENTS_DIR,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    INDEX_PATH,
    METADATA_PATH,
    VECTORSTORE_DIR,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger("legal_aid_ai.ingest")


TITLE_MAP = {
    "cpa.pdf": "Consumer Protection Act, 2019",
    "eng201935.pdf": "Consumer Protection (General) Rules, 2020",
    "consumer_protection_act_2019.pdf": "Consumer Protection Act, 2019",
    "consumer_protection_general_rules_2020.pdf": "Consumer Protection Act, 2019 and Consumer Protection Rules compilation",
    "cdrc_general_rules_2020.pdf": "Consumer Protection (Consumer Disputes Redressal Commissions) Rules, 2020 and Consumer Protection (General) Rules, 2020",
    "consumer_commission_procedure_regulations_2020.pdf": "Consumer Protection (Consumer Commission Procedure) Regulations, 2020",
    "ecommerce_rules_2020.pdf": "Consumer Protection (E-Commerce) Rules, 2020",
    "ecommerce_amendment_rules_2021.pdf": "Consumer Protection (E-Commerce) (Amendment) Rules, 2021",
    "jurisdiction_rules_2021.pdf": "Consumer Protection (Jurisdiction of the District Commission, the State Commission and the National Commission) Rules, 2021",
    "mediation_rules_2020.pdf": "Consumer Protection (Mediation) Rules, 2020",
    "direct_selling_rules_2021.pdf": "Consumer Protection (Direct Selling) Rules, 2021",
    "misleading_ads_guidelines_2022.pdf": "Guidelines for Prevention of Misleading Advertisements and Endorsements for Misleading Advertisements, 2022",
    "dark_patterns_guidelines_2023.pdf": "Guidelines for Prevention and Regulation of Dark Patterns, 2023",
}
CORPUS_MANIFEST_PATH = DOCUMENTS_DIR / "corpus_manifest.json"
PARSED_DIR = BASE_DIR / "parsed"
LEGAL_CHUNKS_PATH = PARSED_DIR / "legal_chunks.jsonl"
PARSE_SUMMARY_PATH = PARSED_DIR / "parse_summary.json"
MANIFEST_METADATA_FIELDS = (
    "domain",
    "jurisdiction",
    "document_title",
    "short_title",
    "document_type",
    "status",
    "authority_level",
    "year",
    "source_file",
    "retrieval_priority",
    "cross_domain_relevance",
)
JSONL_RECORD_FIELDS = (
    "chunk_id",
    "text",
    "domain",
    "jurisdiction",
    "document_title",
    "short_title",
    "document_type",
    "status",
    "authority_level",
    "year",
    "source_file",
    "retrieval_priority",
    "cross_domain_relevance",
    "structure_type",
    "section_number",
    "section_title",
    "article_number",
    "article_title",
    "rule_number",
    "rule_title",
    "regulation_number",
    "regulation_title",
    "guideline_number",
    "guideline_title",
    "heading_number",
    "heading_title",
    "provision_number",
    "provision_title",
    "chapter",
    "part",
    "page",
    "page_start",
    "page_end",
    "provision_chunk_index",
    "provision_chunk_count",
    "source",
    "chunk",
    "parser_family",
)
STATUTE_PARSER_TYPES = {
    "statute",
    "supporting_criminal_law",
    "supporting_criminal_procedure",
    "supporting_property_law",
    "supporting_document_registration_law",
}

HEADING_RE = re.compile(
    r"(?m)(^|\n)(?P<number>\d{1,3})\.\s+"
    r"(?P<title>[A-Z][A-Za-z0-9 ,()/'&-]{2,120}?)\s*(?:[.—-]|—)"
)
BARE_NUMBER_RE = re.compile(r"(?m)(^|\n)(?P<number>\d{1,3})\.\s+(?=\(\d+\))")
CHAPTER_RE = re.compile(r"(?m)(^|\n)(CHAPTER\s+[IVXLCDM]+(?:\s+[A-Z][A-Z\\s-]{2,80})?)")
PART_RE = re.compile(r"^(PART\s+[IVXLCDM]+(?:\s+[A-Z][A-Z\s-]{2,80})?)$")
CHAPTER_LINE_RE = re.compile(r"^(CHAPTER\s+[IVXLCDM]+(?:\s+[A-Z][A-Z\s-]{2,80})?)$")
SCHEDULE_RE = re.compile(r"^(?P<title>(?:THE\s+)?(?:FIRST|SECOND|THIRD|FOURTH|FIFTH|SIXTH|SEVENTH|EIGHTH|NINTH|TENTH)?\s*SCHEDULE)\b", re.I)
ANNEXURE_RE = re.compile(r"^(?P<title>ANNEXURE\s+[A-Z0-9]+)\b", re.I)
PREAMBLE_RE = re.compile(r"^PREAMBLE$", re.I)
SECTION_BOUNDARY_RE = re.compile(
    r"^(?:SECTION\s+)?(?P<number>\d{1,3}[A-Z]?(?:-[A-Z])?)\.\s+"
    r"(?P<title>[A-Z][A-Za-z0-9 ,()/'&:;-]{2,180})(?:[.—-]|$)"
)
ARTICLE_BOUNDARY_RE = re.compile(
    r"^(?:ARTICLE\s+)?(?P<number>\d{1,3}[A-Z]?)\.\s+"
    r"(?P<title>[A-Z][A-Za-z0-9 ,()/'&:;-]{2,180})(?:[.—-]|$)"
)
RULE_BOUNDARY_RE = re.compile(
    r"^(?:RULE\s+)?(?P<number>\d{1,3}[A-Z]?)\.\s+"
    r"(?P<title>[A-Z][A-Za-z0-9 ,()/'&:;-]{2,180})(?:[.—-]|$)"
)
REGULATION_BOUNDARY_RE = re.compile(
    r"^(?:REGULATION\s+)?(?P<number>\d{1,3}[A-Z]?)\.\s+"
    r"(?P<title>[A-Z][A-Za-z0-9 ,()/'&:;-]{2,180})(?:[.—-]|$)"
)
GUIDELINE_BOUNDARY_RE = re.compile(
    r"^(?P<number>\d{1,3}[A-Z]?)\.\s+"
    r"(?P<title>[A-Z][A-Za-z0-9 ,()/'&:;-]{2,180})(?:[.—-]|$)"
)
MANUAL_HEADING_RE = re.compile(r"^(?P<number>\d+(?:\.\d+)*)\s+(?P<title>[A-Z][A-Za-z0-9 ,()/'&:;-]{3,140})$")
STRUCTURED_CHILD_CHUNK_SIZE = CHUNK_SIZE * 2
STRUCTURED_CHILD_CHUNK_OVERLAP = min(120, CHUNK_OVERLAP)
GAZETTE_STRUCTURE_PARSERS = {"rules", "regulations", "guidelines", "amendment_rules"}
GAZETTE_PAGE_HEADER_RE = re.compile(
    r"\b\d+\s+THE GAZETTE OF INDIA\s*:\s*EXTRAORDINARY\s*\[[^\]]+\]",
    re.I,
)
HINDI_GAZETTE_PAGE_HEADER_RE = re.compile(
    r"\[भाग\s+[^\]]+\]\s*भारत का रा[जि]पत्र\s*:\s*असाधारण\s*\d*"
)
GAZETTE_FURNITURE_LINE_RE = re.compile(
    r"^(?:"
    r"EXTRAORDINARY|"
    r"PUBLISHED BY AUTHORITY|"
    r"xxxGIDHxxx|"
    r"xxxGIDExxx|"
    r"(?:रजि|रजज)स्ट्री सं\..*REGD\. No\..*|"
    r"REGD\. No\..*|"
    r"No\.\s*\d+\]\s*NEW DELHI.*|"
    r"सी\.जी\.-.*|"
    r"CG-DL-.*|"
    r"Uploaded by Dte\..*|"
    r"and Published by the Controller of Publications.*"
    r")$",
    re.I,
)


def load_corpus_manifest() -> dict:
    if not CORPUS_MANIFEST_PATH.exists():
        return {}
    with CORPUS_MANIFEST_PATH.open("r", encoding="utf-8") as file:
        return json.load(file)


def load_manifest_documents() -> list[dict]:
    return load_corpus_manifest().get("documents", [])


def manifest_entry_for(path: Path) -> dict | None:
    try:
        relative = path.relative_to(DOCUMENTS_DIR).as_posix()
    except ValueError:
        relative = path.name
    for entry in load_manifest_documents():
        if entry.get("source_file") == relative:
            return entry
    return None


def document_title(path: Path) -> str:
    manifest_entry = manifest_entry_for(path)
    if manifest_entry and manifest_entry.get("document_title"):
        return manifest_entry["document_title"]
    return TITLE_MAP.get(path.name.lower(), path.stem.replace("_", " ").title())


def fallback_manifest_entry(pdf_path: Path) -> dict:
    try:
        source_file = pdf_path.relative_to(DOCUMENTS_DIR).as_posix()
    except ValueError:
        source_file = pdf_path.name
    return {
        "source_file": source_file,
        "document_title": document_title(pdf_path),
        "short_title": pdf_path.stem.replace("_", " ").title(),
        "domain": None,
        "document_type": "statute",
        "jurisdiction": None,
        "status": "active",
        "authority_level": "primary",
        "year": None,
        "cross_domain_relevance": [],
        "retrieval_priority": "medium",
        "notes": "Parsed without corpus manifest metadata.",
    }


def discover_document_entries(include_manual_verification: bool = False) -> tuple[list[tuple[Path, dict]], list[dict]]:
    manifest_documents = load_manifest_documents()
    documents: list[tuple[Path, dict]] = []
    skipped: list[dict] = []
    if manifest_documents:
        for entry in manifest_documents:
            source_file = entry.get("source_file")
            if not source_file:
                skipped.append({"source_file": None, "reason": "missing source_file in manifest"})
                continue
            if source_file.startswith("archive/"):
                skipped.append({"source_file": source_file, "reason": "archived document"})
                continue
            if entry.get("status") == "manual_verification_required" and not include_manual_verification:
                skipped.append({"source_file": source_file, "reason": "manual_verification_required"})
                continue
            pdf_path = DOCUMENTS_DIR / source_file
            if pdf_path.exists():
                documents.append((pdf_path, entry))
            else:
                logger.warning("Manifest PDF path does not exist and will be skipped: %s", source_file)
                skipped.append({"source_file": source_file, "reason": "file missing"})
        return sorted(documents, key=lambda item: item[0].as_posix()), skipped

    pdf_paths = sorted(
        path
        for path in DOCUMENTS_DIR.rglob("*.pdf")
        if "archive" not in path.relative_to(DOCUMENTS_DIR).parts
    )
    return [(path, fallback_manifest_entry(path)) for path in pdf_paths], skipped


def discover_pdf_paths() -> list[Path]:
    return [path for path, _entry in discover_document_entries()[0]]


def normalized_document_name(source_file: str) -> str:
    stem = source_file.removesuffix(".pdf")
    normalized = re.sub(r"[^a-zA-Z0-9]+", "_", stem).strip("_").lower()
    return normalized or "document"


def manifest_chunk_metadata(entry: dict, source_file: str) -> dict:
    metadata = {field: entry.get(field) for field in MANIFEST_METADATA_FIELDS}
    metadata["source_file"] = source_file
    metadata["cross_domain_relevance"] = list(entry.get("cross_domain_relevance") or [])
    metadata["document_title"] = entry.get("document_title") or document_title(DOCUMENTS_DIR / source_file)
    metadata["short_title"] = entry.get("short_title") or metadata["document_title"]
    return metadata


def clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def remove_gazette_page_furniture(text: str) -> str:
    text = GAZETTE_PAGE_HEADER_RE.sub("", text)
    text = HINDI_GAZETTE_PAGE_HEADER_RE.sub("", text)
    kept_lines = []
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if GAZETTE_FURNITURE_LINE_RE.match(line):
            continue
        kept_lines.append(line)
    return clean_text("\n".join(kept_lines))


def contains_devanagari(text: str) -> bool:
    return bool(re.search(r"[\u0900-\u097F]", text))


def trim_bilingual_gazette_front_matter(
    pages: list[tuple[int, str]],
    parser_family: str | None,
) -> list[tuple[int, str]]:
    if parser_family not in GAZETTE_STRUCTURE_PARSERS:
        return pages

    combined_before_marker = []
    english_marker_re = re.compile(
        r"\b(?:MINISTRY OF|CENTRAL CONSUMER PROTECTION AUTHORITY)\b",
        re.I,
    )
    for index, (page_number, text) in enumerate(pages):
        marker = english_marker_re.search(text)
        if not marker:
            combined_before_marker.append(text)
            continue

        before_marker = "\n".join(combined_before_marker + [text[: marker.start()]])
        after_marker = text[marker.start():]
        looks_like_english_notification = bool(
            re.search(r"\b(?:NOTIFICATION|G\.S\.R\.|F\. No\.)\b", after_marker[:1200], re.I)
        )
        if contains_devanagari(before_marker) and looks_like_english_notification:
            trimmed_pages = [(page_number, clean_text(after_marker))]
            trimmed_pages.extend(pages[index + 1 :])
            return [(page, page_text) for page, page_text in trimmed_pages if page_text]
        return pages
    return pages


def is_arrangement_page(text: str, pdf_path: Path, page_index: int) -> bool:
    lowered = text.lower()
    if "arrangement of sections" in lowered or "arrangement of articles" in lowered:
        return True
    if pdf_path.name.lower() == "constitution_of_india.pdf" and 4 <= page_index <= 21:
        return True
    if pdf_path.name.lower() == "consumer_protection_act_2019.pdf" and page_index <= 3:
        return True
    if page_index <= 6:
        heading_count = sum(
            len(pattern.findall(text))
            for pattern in (SECTION_BOUNDARY_RE, ARTICLE_BOUNDARY_RE, RULE_BOUNDARY_RE, REGULATION_BOUNDARY_RE)
        )
        starts_like_contents_continuation = bool(
            re.search(r"(?m)^\s*\d*\s*(SECTIONS|ARTICLES)\s*$", text)
        )
        lacks_substantive_enactment_text = not any(
            marker in lowered for marker in ("an act to", "be it enacted", "in exercise of the powers")
        )
        if lacks_substantive_enactment_text and (starts_like_contents_continuation or heading_count >= 8):
            return True
    return False


def chunk_text(text: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    if chunk_size <= overlap:
        raise ValueError("chunk_size must be greater than overlap")
    chunks: list[str] = []
    start = 0
    while start < len(text):
        end = min(start + chunk_size, len(text))
        candidate = text[start:end]
        if end < len(text):
            split_at = max(candidate.rfind("\n\n"), candidate.rfind(". "), candidate.rfind("; "))
            if split_at > chunk_size * 0.55:
                end = start + split_at + 1
                candidate = text[start:end]
        candidate = candidate.strip()
        if candidate:
            chunks.append(candidate)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def normalize_heading_title(title: str | None) -> str | None:
    if not title:
        return None
    cleaned = re.sub(r"\s+", " ", title).strip(" .—-")
    return cleaned or None


def heading_label(document: str) -> str:
    return "Rule" if "rules" in document.lower() else "Section"


def enrich_chunk_text(text: str, metadata: dict) -> str:
    lines: list[str] = []
    if metadata.get("part"):
        lines.append(metadata["part"])
    if metadata.get("chapter"):
        lines.append(metadata["chapter"])
    label, number, title = provision_label_number_title(metadata)
    if number:
        heading = f"{label} {number}"
        if title:
            heading += f" — {title}"
        lines.append(heading)
    if not lines:
        return text
    prefix = "\n".join(lines)
    return f"{prefix}\n{text}"


def provision_label_number_title(metadata: dict) -> tuple[str, str | None, str | None]:
    if metadata.get("article_number"):
        return "Article", metadata.get("article_number"), metadata.get("article_title")
    if metadata.get("rule_number"):
        return "Rule", metadata.get("rule_number"), metadata.get("rule_title")
    if metadata.get("regulation_number"):
        return "Regulation", metadata.get("regulation_number"), metadata.get("regulation_title")
    if metadata.get("guideline_number"):
        return "Guideline", metadata.get("guideline_number"), metadata.get("guideline_title")
    if metadata.get("section_number"):
        return "Section", metadata.get("section_number"), metadata.get("section_title")
    if metadata.get("provision_number"):
        label = str(metadata.get("structure_type") or "Provision").replace("_", " ").title()
        return label, metadata.get("provision_number"), metadata.get("provision_title")
    return "Section", None, None


def parser_boundary_pattern(parser_family: str) -> tuple[str, re.Pattern | None]:
    if parser_family == "constitution":
        return "article", ARTICLE_BOUNDARY_RE
    if parser_family == "rules":
        return "rule", RULE_BOUNDARY_RE
    if parser_family == "regulations":
        return "regulation", REGULATION_BOUNDARY_RE
    if parser_family == "guidelines":
        return "guideline", GUIDELINE_BOUNDARY_RE
    if parser_family == "amendment_rules":
        return "rule", RULE_BOUNDARY_RE
    if parser_family == "manual":
        return "manual_section", MANUAL_HEADING_RE
    return "section", SECTION_BOUNDARY_RE


def update_context_from_line(line: str, context: dict) -> bool:
    stripped = line.strip()
    part_match = PART_RE.match(stripped)
    if part_match:
        context["part"] = re.sub(r"\s+", " ", part_match.group(1)).strip()
        context["chapter"] = None
        return True
    chapter_match = CHAPTER_LINE_RE.match(stripped)
    if chapter_match:
        context["chapter"] = re.sub(r"\s+", " ", chapter_match.group(1)).strip()
        return True
    return False


def schedule_or_annexure_metadata(line: str) -> dict | None:
    stripped = line.strip()
    if PREAMBLE_RE.match(stripped):
        return {
            "structure_type": "preamble",
            "provision_number": None,
            "provision_title": "Preamble",
        }
    schedule_match = SCHEDULE_RE.match(stripped)
    if schedule_match:
        return {
            "structure_type": "schedule",
            "provision_number": None,
            "provision_title": normalize_heading_title(schedule_match.group("title")),
        }
    annexure_match = ANNEXURE_RE.match(stripped)
    if annexure_match:
        return {
            "structure_type": "annexure",
            "provision_number": None,
            "provision_title": normalize_heading_title(annexure_match.group("title")),
        }
    return None


def provision_metadata_from_match(structure_type: str, match: re.Match) -> dict:
    number = match.group("number")
    title = normalize_heading_title(match.groupdict().get("title"))
    metadata = {
        "structure_type": structure_type,
        "provision_number": number,
        "provision_title": title,
    }
    if structure_type == "section":
        metadata.update({"section_number": number, "section_title": title})
    elif structure_type == "article":
        metadata.update({"article_number": number, "article_title": title})
    elif structure_type == "rule":
        metadata.update({"rule_number": number, "rule_title": title})
    elif structure_type == "regulation":
        metadata.update({"regulation_number": number, "regulation_title": title})
    elif structure_type == "guideline":
        metadata.update({"guideline_number": number, "guideline_title": title})
    elif structure_type == "manual_section":
        metadata.update({"heading_number": number, "heading_title": title})
    return metadata


def is_probable_false_boundary(match: re.Match) -> bool:
    title = normalize_heading_title(match.groupdict().get("title")) or ""
    lowered = title.lower()
    false_prefixes = (
        "subs",
        "ins",
        "omitted",
        "rep",
        "cl",
        "art",
        "ibid",
    )
    if lowered in false_prefixes or lowered.startswith(tuple(f"{prefix}." for prefix in false_prefixes)):
        return True
    if len(title) <= 4 and title.replace(".", "").isalpha():
        return True
    return False


def fresh_structure_metadata(structure_type: str = "fallback") -> dict:
    return {
        "structure_type": structure_type,
        "part": None,
        "chapter": None,
        "section_number": None,
        "section_title": None,
        "article_number": None,
        "article_title": None,
        "rule_number": None,
        "rule_title": None,
        "regulation_number": None,
        "regulation_title": None,
        "guideline_number": None,
        "guideline_title": None,
        "heading_number": None,
        "heading_title": None,
        "provision_number": None,
        "provision_title": None,
    }


def legal_units_from_pages(pdf_path: Path, pages: list[tuple[int, str]], parser_family: str) -> list[dict]:
    structure_type, boundary_pattern = parser_boundary_pattern(parser_family)
    context = {"part": None, "chapter": None}
    units: list[dict] = []
    current: dict | None = None

    def start_unit(page_number: int, metadata: dict, first_line: str) -> None:
        nonlocal current
        if current and current["lines"]:
            units.append(current)
        merged_metadata = {**fresh_structure_metadata(metadata.get("structure_type", "fallback")), **metadata}
        merged_metadata["part"] = context.get("part")
        merged_metadata["chapter"] = context.get("chapter")
        current = {
            "page_start": page_number,
            "page_end": page_number,
            "lines": [first_line],
            "metadata": merged_metadata,
        }

    for page_number, text in pages:
        if is_arrangement_page(text, pdf_path, page_number):
            logger.info("Skipping arrangement/contents page %s in %s", page_number, pdf_path.name)
            continue
        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue
            if update_context_from_line(line, context):
                if current and current["metadata"].get("structure_type") == "fallback" and not current["lines"]:
                    current["metadata"]["part"] = context.get("part")
                    current["metadata"]["chapter"] = context.get("chapter")
                continue

            neutral_metadata = schedule_or_annexure_metadata(line)
            if neutral_metadata:
                start_unit(page_number, neutral_metadata, line)
                continue

            boundary_match = boundary_pattern.match(line) if boundary_pattern else None
            if boundary_match and not is_probable_false_boundary(boundary_match):
                start_unit(page_number, provision_metadata_from_match(structure_type, boundary_match), line)
                continue

            if current is None:
                start_unit(page_number, {"structure_type": "fallback"}, line)
            else:
                current["lines"].append(line)
                current["page_end"] = page_number

    if current and current["lines"]:
        units.append(current)
    return units


def chunk_legal_unit(unit: dict) -> list[dict]:
    text = clean_text("\n".join(unit["lines"]))
    if not text:
        return []
    if len(text) <= STRUCTURED_CHILD_CHUNK_SIZE:
        return [
            {
                "text": text,
                "metadata": unit["metadata"],
                "page_start": unit["page_start"],
                "page_end": unit["page_end"],
                "provision_chunk_index": 1,
                "provision_chunk_count": 1,
            }
        ]

    child_texts = chunk_text(
        text,
        chunk_size=STRUCTURED_CHILD_CHUNK_SIZE,
        overlap=STRUCTURED_CHILD_CHUNK_OVERLAP,
    )
    return [
        {
            "text": child_text,
            "metadata": unit["metadata"],
            "page_start": unit["page_start"],
            "page_end": unit["page_end"],
            "provision_chunk_index": index,
            "provision_chunk_count": len(child_texts),
        }
        for index, child_text in enumerate(child_texts, start=1)
    ]


def iter_page_segments(text: str, active: dict, document: str) -> list[dict]:
    events: list[tuple[int, int, str, re.Match]] = []
    for match in HEADING_RE.finditer(text):
        events.append((match.start("number"), match.end(), "heading", match))
    for match in BARE_NUMBER_RE.finditer(text):
        if not any(abs(match.start("number") - existing[0]) < 3 for existing in events):
            events.append((match.start("number"), match.end(), "bare", match))
    for match in CHAPTER_RE.finditer(text):
        events.append((match.start(2), match.end(2), "chapter", match))
    events.sort(key=lambda item: item[0])

    segments: list[dict] = []
    cursor = 0
    current = active.copy()
    label = heading_label(document)

    for start, _end, kind, match in events:
        if start > cursor:
            segment_text = text[cursor:start].strip()
            if segment_text:
                segments.append({"text": segment_text, "metadata": current.copy()})
        if kind == "chapter":
            current["chapter"] = re.sub(r"\s+", " ", match.group(2)).strip()
            current.update({
                "section_number": None,
                "section_title": None,
                "rule_number": None,
                "rule_title": None,
            })
        else:
            number = match.group("number")
            title = normalize_heading_title(match.groupdict().get("title"))
            if label == "Rule":
                current.update({"rule_number": number, "rule_title": title})
            else:
                current.update({"section_number": number, "section_title": title})
        cursor = start

    tail = text[cursor:].strip()
    if tail:
        segments.append({"text": tail, "metadata": current.copy()})
    active.update(current)
    return segments


def extract_pdf_chunks(pdf_path: Path, manifest_entry: dict | None = None, parser_family: str | None = None) -> list[dict]:
    try:
        reader = PdfReader(str(pdf_path))
    except Exception as exc:
        logger.exception("Could not read PDF %s", pdf_path.name)
        raise ValueError(f"Could not read PDF: {pdf_path.name}") from exc

    chunks: list[dict] = []
    manifest_entry = manifest_entry or fallback_manifest_entry(pdf_path)
    source_file = manifest_entry["source_file"]
    title = manifest_entry.get("document_title") or document_title(pdf_path)
    chunk_base_metadata = manifest_chunk_metadata(manifest_entry, source_file)
    document_slug = normalized_document_name(source_file)
    effective_parser_family = parser_family or "statute"
    pages = []
    for page_index, page in enumerate(reader.pages, start=1):
        page_text = clean_text(page.extract_text() or "")
        if effective_parser_family in GAZETTE_STRUCTURE_PARSERS:
            page_text = remove_gazette_page_furniture(page_text)
        if page_text:
            pages.append((page_index, page_text))
    pages = trim_bilingual_gazette_front_matter(pages, effective_parser_family)
    units = legal_units_from_pages(pdf_path, pages, effective_parser_family)
    chunk_sequence = 1
    for unit in units:
        for child_chunk in chunk_legal_unit(unit):
            structure_metadata = child_chunk["metadata"]
            chunk_metadata = {
                **chunk_base_metadata,
                **structure_metadata,
                "chunk_id": f"{document_slug}__chunk_{chunk_sequence:04d}",
                "text": enrich_chunk_text(child_chunk["text"], structure_metadata),
                "source": source_file,
                "page": child_chunk["page_start"],
                "page_start": child_chunk["page_start"],
                "page_end": child_chunk["page_end"],
                "chunk": chunk_sequence,
                "parser_family": effective_parser_family,
                "provision_chunk_index": child_chunk["provision_chunk_index"],
                "provision_chunk_count": child_chunk["provision_chunk_count"],
            }
            chunks.append(chunk_metadata)
            chunk_sequence += 1
    return chunks


def parse_existing_chunking(pdf_path: Path, manifest_entry: dict, parser_family: str) -> list[dict]:
    return extract_pdf_chunks(pdf_path, manifest_entry=manifest_entry, parser_family=parser_family)


def parse_statute_document(pdf_path: Path, manifest_entry: dict) -> list[dict]:
    return parse_existing_chunking(pdf_path, manifest_entry, "statute")


def parse_constitution_document(pdf_path: Path, manifest_entry: dict) -> list[dict]:
    return parse_existing_chunking(pdf_path, manifest_entry, "constitution")


def parse_rules_document(pdf_path: Path, manifest_entry: dict) -> list[dict]:
    return parse_existing_chunking(pdf_path, manifest_entry, "rules")


def parse_regulations_document(pdf_path: Path, manifest_entry: dict) -> list[dict]:
    return parse_existing_chunking(pdf_path, manifest_entry, "regulations")


def parse_guidelines_document(pdf_path: Path, manifest_entry: dict) -> list[dict]:
    return parse_existing_chunking(pdf_path, manifest_entry, "guidelines")


def parse_amendment_rules_document(pdf_path: Path, manifest_entry: dict) -> list[dict]:
    return parse_existing_chunking(pdf_path, manifest_entry, "amendment_rules")


def parse_manual_document(pdf_path: Path, manifest_entry: dict) -> list[dict]:
    return parse_existing_chunking(pdf_path, manifest_entry, "manual")


def parser_for_document_type(document_type: str) -> Callable[[Path, dict], list[dict]]:
    if document_type in STATUTE_PARSER_TYPES:
        return parse_statute_document
    parser_map: dict[str, Callable[[Path, dict], list[dict]]] = {
        "constitution": parse_constitution_document,
        "rules": parse_rules_document,
        "regulations": parse_regulations_document,
        "guidelines": parse_guidelines_document,
        "amendment_rules": parse_amendment_rules_document,
        "procedural_user_guide": parse_manual_document,
    }
    try:
        return parser_map[document_type]
    except KeyError as exc:
        raise ValueError(f"Unsupported document_type in corpus manifest: {document_type}") from exc


def parse_document(pdf_path: Path, manifest_entry: dict) -> list[dict]:
    parser = parser_for_document_type(manifest_entry.get("document_type") or "")
    return parser(pdf_path, manifest_entry)


def parse_documents(pdf_paths: list[Path] | None = None) -> dict:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    skipped_documents: list[dict] = []
    if pdf_paths is None:
        document_entries, skipped_documents = discover_document_entries()
    else:
        document_entries = [(path, fallback_manifest_entry(path)) for path in pdf_paths]

    if not document_entries:
        raise FileNotFoundError(f"No PDF documents found in {DOCUMENTS_DIR}")

    all_chunks: list[dict] = []
    parsed_documents: list[dict] = []
    for pdf_path, manifest_entry in document_entries:
        pdf_chunks = parse_document(pdf_path, manifest_entry)
        parser_family = pdf_chunks[0].get("parser_family") if pdf_chunks else manifest_entry.get("document_type")
        structure_counts = Counter(chunk.get("structure_type") for chunk in pdf_chunks)
        fallback_count = structure_counts.get("fallback", 0)
        structure_aware_count = len(pdf_chunks) - fallback_count
        logger.info(
            "Loaded text pages/chunks from %s via %s parser: %s chunks (%s structure-aware, %s fallback)",
            manifest_entry.get("source_file", pdf_path.name),
            parser_family,
            len(pdf_chunks),
            structure_aware_count,
            fallback_count,
        )
        parsed_documents.append(
            {
                "source_file": manifest_entry.get("source_file", pdf_path.name),
                "document_title": manifest_entry.get("document_title") or document_title(pdf_path),
                "document_type": manifest_entry.get("document_type"),
                "domain": manifest_entry.get("domain"),
                "status": manifest_entry.get("status"),
                "parser_family": parser_family,
                "chunk_count": len(pdf_chunks),
                "structure_aware_chunk_count": structure_aware_count,
                "fallback_chunk_count": fallback_count,
                "chunks_by_structure_type": dict(structure_counts),
            }
        )
        all_chunks.extend(pdf_chunks)

    if not all_chunks:
        raise ValueError("No extractable text found in the provided PDFs.")

    chunks_by_structure_type = dict(Counter(chunk.get("structure_type") for chunk in all_chunks))
    fallback_chunk_count = chunks_by_structure_type.get("fallback", 0)
    structure_aware_chunk_count = len(all_chunks) - fallback_chunk_count
    metadata = {
        "chunking_strategy": "manifest-driven legal-structure-aware units with long-provision child chunks and fallback chunks",
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "document_count": len(document_entries),
        "chunk_count": len(all_chunks),
        "structure_aware_chunk_count": structure_aware_chunk_count,
        "fallback_chunk_count": fallback_chunk_count,
        "structure_aware_percentage": round(structure_aware_chunk_count / len(all_chunks) * 100, 2),
        "fallback_percentage": round(fallback_chunk_count / len(all_chunks) * 100, 2),
        "parsed_documents": parsed_documents,
        "skipped_documents": skipped_documents,
        "chunks_per_domain": dict(Counter(chunk.get("domain") for chunk in all_chunks)),
        "chunks_per_document_type": dict(Counter(chunk.get("document_type") for chunk in all_chunks)),
        "chunks_by_structure_type": chunks_by_structure_type,
        "chunks": all_chunks,
    }
    logger.info("Parsed %s chunks from %s documents", len(all_chunks), len(document_entries))
    if skipped_documents:
        logger.info("Skipped documents: %s", skipped_documents)
    logger.info("Chunks per domain: %s", metadata["chunks_per_domain"])
    logger.info("Chunks per document type: %s", metadata["chunks_per_document_type"])
    logger.info("Chunks by structure type: %s", metadata["chunks_by_structure_type"])
    logger.info(
        "Structure-aware chunks: %s (%.2f%%); fallback chunks: %s (%.2f%%)",
        structure_aware_chunk_count,
        metadata["structure_aware_percentage"],
        fallback_chunk_count,
        metadata["fallback_percentage"],
    )
    return metadata


def jsonl_record_from_chunk(chunk: dict) -> dict:
    record = {field: chunk.get(field) for field in JSONL_RECORD_FIELDS}
    record["cross_domain_relevance"] = list(record.get("cross_domain_relevance") or [])
    return record


def parse_summary_from_metadata(parsed_metadata: dict) -> dict:
    document_summaries = []
    for document in parsed_metadata.get("parsed_documents", []):
        document_summaries.append(
            {
                "source_file": document.get("source_file"),
                "domain": document.get("domain"),
                "document_type": document.get("document_type"),
                "total_chunks": document.get("chunk_count", 0),
                "structure_aware_chunks": document.get("structure_aware_chunk_count", 0),
                "fallback_chunks": document.get("fallback_chunk_count", 0),
            }
        )

    return {
        "documents_parsed": parsed_metadata.get("document_count", 0),
        "documents_skipped": parsed_metadata.get("skipped_documents", []),
        "total_chunks": parsed_metadata.get("chunk_count", 0),
        "structure_aware_chunks": parsed_metadata.get("structure_aware_chunk_count", 0),
        "fallback_chunks": parsed_metadata.get("fallback_chunk_count", 0),
        "structure_aware_percentage": parsed_metadata.get("structure_aware_percentage", 0),
        "chunks_by_domain": parsed_metadata.get("chunks_per_domain", {}),
        "chunks_by_structure_type": parsed_metadata.get("chunks_by_structure_type", {}),
        "chunks_by_document_type": parsed_metadata.get("chunks_per_document_type", {}),
        "documents": document_summaries,
    }


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = path.with_suffix(path.suffix + ".tmp")
    temp_path.write_text(text, encoding="utf-8")
    temp_path.replace(path)


def validate_parse_outputs(chunks_path: Path, parsed_metadata: dict) -> dict:
    records = []
    with chunks_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL record at line {line_number}: {exc}") from exc
            records.append(record)

    expected_count = parsed_metadata.get("chunk_count", 0)
    if len(records) != expected_count:
        raise ValueError(f"JSONL record count {len(records)} does not match parsed chunk count {expected_count}")

    chunk_ids = [record.get("chunk_id") for record in records]
    if any(not chunk_id for chunk_id in chunk_ids):
        raise ValueError("Every JSONL record must have a non-empty chunk_id")
    if len(set(chunk_ids)) != len(chunk_ids):
        raise ValueError("JSONL chunk_id values must be unique")

    for record in records:
        if not str(record.get("text") or "").strip():
            raise ValueError(f"Chunk {record.get('chunk_id')} has empty text")
        source_file = record.get("source_file")
        if not source_file:
            raise ValueError(f"Chunk {record.get('chunk_id')} is missing source_file")
        if str(source_file).startswith("archive/"):
            raise ValueError(f"Archived document appeared in parse output: {source_file}")
        if record.get("status") == "manual_verification_required":
            raise ValueError(f"Manual-verification document appeared in parse output: {source_file}")

    return {
        "record_count": len(records),
        "unique_chunk_ids": len(set(chunk_ids)),
    }


def write_parse_outputs(
    parsed_metadata: dict,
    chunks_path: Path | None = None,
    summary_path: Path | None = None,
) -> dict:
    chunks_path = chunks_path or LEGAL_CHUNKS_PATH
    summary_path = summary_path or PARSE_SUMMARY_PATH
    records = [jsonl_record_from_chunk(chunk) for chunk in parsed_metadata.get("chunks", [])]
    jsonl_text = "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        for record in records
    )
    atomic_write_text(chunks_path, jsonl_text)

    summary = parse_summary_from_metadata(parsed_metadata)
    atomic_write_text(
        summary_path,
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    )
    validation = validate_parse_outputs(chunks_path, parsed_metadata)
    logger.info("Parse JSONL saved to %s (%s records)", chunks_path, validation["record_count"])
    logger.info("Parse summary saved to %s", summary_path)
    return {
        "chunks_path": chunks_path.as_posix(),
        "summary_path": summary_path.as_posix(),
        "summary": summary,
        "validation": validation,
    }


def load_legal_chunks_jsonl(chunks_path: Path = LEGAL_CHUNKS_PATH) -> list[dict]:
    if not chunks_path.exists():
        raise FileNotFoundError(f"Parsed chunk JSONL not found: {chunks_path}. Run `python ingest.py --parse-only` first.")

    chunks: list[dict] = []
    with chunks_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                chunks.append(json.loads(line))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL record at line {line_number}: {exc}") from exc
    return chunks


def validate_chunks_for_indexing(chunks: list[dict]) -> dict:
    if not chunks:
        raise ValueError("Parsed chunk JSONL contains no records.")

    chunk_ids = [chunk.get("chunk_id") for chunk in chunks]
    if any(not chunk_id for chunk_id in chunk_ids):
        raise ValueError("Every chunk must have a non-empty chunk_id before indexing.")
    if len(set(chunk_ids)) != len(chunk_ids):
        raise ValueError("Chunk IDs must be unique before indexing.")

    for chunk in chunks:
        if not str(chunk.get("text") or "").strip():
            raise ValueError(f"Chunk {chunk.get('chunk_id')} has empty text.")
        source_file = chunk.get("source_file")
        if not source_file:
            raise ValueError(f"Chunk {chunk.get('chunk_id')} is missing source_file.")
        if str(source_file).startswith("archive/"):
            raise ValueError(f"Archived document cannot be indexed: {source_file}")
        if chunk.get("status") == "manual_verification_required":
            raise ValueError(f"Manual-verification document cannot be indexed: {source_file}")

    return {
        "chunk_count": len(chunks),
        "unique_chunk_ids": len(set(chunk_ids)),
        "document_count": len({chunk.get("source_file") for chunk in chunks}),
    }


def metadata_from_jsonl_chunks(chunks: list[dict], chunks_path: Path = LEGAL_CHUNKS_PATH) -> dict:
    chunks_by_structure_type = dict(Counter(chunk.get("structure_type") for chunk in chunks))
    fallback_chunk_count = chunks_by_structure_type.get("fallback", 0)
    structure_aware_chunk_count = len(chunks) - fallback_chunk_count
    document_sources = sorted({chunk.get("source_file") for chunk in chunks})
    return {
        "chunking_strategy": "frozen parsed legal_chunks.jsonl",
        "indexing_source": chunks_path.as_posix(),
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "document_count": len(document_sources),
        "chunk_count": len(chunks),
        "structure_aware_chunk_count": structure_aware_chunk_count,
        "fallback_chunk_count": fallback_chunk_count,
        "structure_aware_percentage": round(structure_aware_chunk_count / len(chunks) * 100, 2),
        "fallback_percentage": round(fallback_chunk_count / len(chunks) * 100, 2),
        "chunks_per_domain": dict(Counter(chunk.get("domain") for chunk in chunks)),
        "chunks_per_document_type": dict(Counter(chunk.get("document_type") for chunk in chunks)),
        "chunks_by_structure_type": chunks_by_structure_type,
        "source_files": document_sources,
        "chunks": chunks,
    }


def validate_embeddings(vectors) -> dict:
    if vectors.ndim != 2:
        raise ValueError("Embeddings must be a two-dimensional array.")
    if vectors.shape[0] == 0:
        raise ValueError("Embeddings contain no rows.")
    if vectors.shape[1] != 384:
        raise ValueError(f"Expected embedding dimension 384, got {vectors.shape[1]}.")
    if not bool((vectors != 0).any(axis=1).all()):
        raise ValueError("Embeddings contain one or more empty vector rows.")
    if not bool(np.isfinite(vectors).all()):
        raise ValueError("Embeddings contain NaN or infinite values.")
    return {
        "vector_count": int(vectors.shape[0]),
        "embedding_dimension": int(vectors.shape[1]),
    }


def validate_saved_vector_store(index_path: Path, metadata_path: Path) -> dict:
    index = faiss.read_index(str(index_path))
    with metadata_path.open("r", encoding="utf-8") as file:
        metadata = json.load(file)
    chunks = metadata.get("chunks", [])
    chunk_ids = [chunk.get("chunk_id") for chunk in chunks]
    if index.ntotal != len(chunks):
        raise ValueError(f"FAISS vector count {index.ntotal} does not match metadata count {len(chunks)}.")
    if index.d != 384:
        raise ValueError(f"Expected FAISS dimension 384, got {index.d}.")
    if len(set(chunk_ids)) != len(chunk_ids):
        raise ValueError("Saved metadata chunk IDs are not unique.")
    for position in (0, len(chunks) // 2, len(chunks) - 1):
        if position < 0:
            continue
        if not chunks[position].get("chunk_id"):
            raise ValueError(f"Metadata record at FAISS position {position} has no chunk_id.")
    return {
        "faiss_vector_count": int(index.ntotal),
        "metadata_record_count": len(chunks),
        "faiss_dimension": int(index.d),
        "alignment_sample_positions": [
            {
                "position": position,
                "chunk_id": chunks[position].get("chunk_id"),
                "source_file": chunks[position].get("source_file"),
            }
            for position in (0, len(chunks) // 2, len(chunks) - 1)
            if 0 <= position < len(chunks)
        ],
    }


def write_vector_store_safely(index: faiss.Index, metadata: dict) -> dict:
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    temp_index_path = VECTORSTORE_DIR / f"{INDEX_PATH.name}.tmp"
    temp_metadata_path = VECTORSTORE_DIR / f"{METADATA_PATH.name}.tmp"
    faiss.write_index(index, str(temp_index_path))
    with temp_metadata_path.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False)

    validation = validate_saved_vector_store(temp_index_path, temp_metadata_path)
    temp_index_path.replace(INDEX_PATH)
    temp_metadata_path.replace(METADATA_PATH)
    validation["index_path"] = INDEX_PATH.as_posix()
    validation["metadata_path"] = METADATA_PATH.as_posix()
    return validation


def write_metadata_safely(metadata: dict) -> None:
    temp_metadata_path = VECTORSTORE_DIR / f"{METADATA_PATH.name}.tmp"
    with temp_metadata_path.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False)
    temp_metadata_path.replace(METADATA_PATH)


def build_vector_store_from_jsonl(chunks_path: Path = LEGAL_CHUNKS_PATH) -> dict:
    from rag import embed_texts

    started_at = time.perf_counter()
    all_chunks = load_legal_chunks_jsonl(chunks_path)
    pre_index_validation = validate_chunks_for_indexing(all_chunks)
    parsed_metadata = metadata_from_jsonl_chunks(all_chunks, chunks_path)
    texts = [chunk["text"] for chunk in all_chunks]
    embedding_started_at = time.perf_counter()
    vectors = embed_texts(texts)
    embedding_time_seconds = round(time.perf_counter() - embedding_started_at, 2)
    embedding_validation = validate_embeddings(vectors)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    metadata = {
        "embedding_provider": EMBEDDING_PROVIDER,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": int(vectors.shape[1]),
        "faiss_index_type": "IndexFlatIP",
        **parsed_metadata,
    }
    saved_validation = write_vector_store_safely(index, metadata)
    total_time_seconds = round(time.perf_counter() - started_at, 2)
    index_build = {
        "pre_index_validation": pre_index_validation,
        "embedding_validation": embedding_validation,
        "saved_validation": saved_validation,
        "embedding_time_seconds": embedding_time_seconds,
        "total_time_seconds": total_time_seconds,
        "index_file_size_bytes": INDEX_PATH.stat().st_size,
        "metadata_file_size_bytes": METADATA_PATH.stat().st_size,
    }
    metadata["index_build"] = index_build
    write_metadata_safely(metadata)
    index_build["metadata_file_size_bytes"] = METADATA_PATH.stat().st_size
    metadata["index_build"] = index_build
    write_metadata_safely(metadata)

    logger.info(
        "Indexed %s chunks from %s documents using %s (%s dimensions)",
        metadata["chunk_count"],
        metadata["document_count"],
        EMBEDDING_MODEL,
        metadata["embedding_dimension"],
    )
    logger.info("Vector store saved to %s", VECTORSTORE_DIR)
    logger.info("Embedding time: %.2fs; total indexing time: %.2fs", embedding_time_seconds, total_time_seconds)
    return metadata


def build_vector_store(parsed_metadata: dict) -> dict:
    return build_vector_store_from_jsonl()


def ingest(parse_only: bool = False) -> dict:
    if parse_only:
        parsed_metadata = parse_documents()
        parsed_metadata["parse_outputs"] = write_parse_outputs(parsed_metadata)
        logger.info("Parse-only mode complete. Embeddings and FAISS vector store were not generated.")
        return parsed_metadata
    logger.info("Building vector store from frozen parsed chunks: %s", LEGAL_CHUNKS_PATH)
    return build_vector_store_from_jsonl()


def main(argv: list[str] | None = None) -> dict:
    parser = argparse.ArgumentParser(description="Parse legal PDFs and optionally build the FAISS vector store.")
    parser.add_argument(
        "--parse-only",
        action="store_true",
        help="Parse PDFs and create chunks without generating embeddings or modifying the vector store.",
    )
    args = parser.parse_args(argv)
    return ingest(parse_only=args.parse_only)


if __name__ == "__main__":
    main()
