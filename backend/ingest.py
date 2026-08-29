from __future__ import annotations

import json
import logging
import re
import shutil
from pathlib import Path

import faiss
from pypdf import PdfReader

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DOCUMENTS_DIR,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    INDEX_PATH,
    METADATA_PATH,
    VECTORSTORE_DIR,
)
from rag import embed_texts

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

HEADING_RE = re.compile(
    r"(?m)(^|\n)(?P<number>\d{1,3})\.\s+"
    r"(?P<title>[A-Z][A-Za-z0-9 ,()/'&-]{2,120}?)\s*(?:[.—-]|—)"
)
BARE_NUMBER_RE = re.compile(r"(?m)(^|\n)(?P<number>\d{1,3})\.\s+(?=\(\d+\))")
CHAPTER_RE = re.compile(r"(?m)(^|\n)(CHAPTER\s+[IVXLCDM]+(?:\s+[A-Z][A-Z\\s-]{2,80})?)")


def document_title(path: Path) -> str:
    return TITLE_MAP.get(path.name.lower(), path.stem.replace("_", " ").title())


def clean_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def is_arrangement_page(text: str, pdf_path: Path, page_index: int) -> bool:
    lowered = text.lower()
    if "arrangement of sections" in lowered:
        return True
    if pdf_path.name.lower() == "consumer_protection_act_2019.pdf" and page_index <= 3:
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
    if metadata.get("chapter"):
        lines.append(metadata["chapter"])
    label = "Rule" if metadata.get("rule_number") else "Section"
    number = metadata.get("rule_number") or metadata.get("section_number")
    title = metadata.get("rule_title") or metadata.get("section_title")
    if number:
        heading = f"{label} {number}"
        if title:
            heading += f" — {title}"
        lines.append(heading)
    if not lines:
        return text
    prefix = "\n".join(lines)
    return f"{prefix}\n{text}"


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


def extract_pdf_chunks(pdf_path: Path) -> list[dict]:
    try:
        reader = PdfReader(str(pdf_path))
    except Exception as exc:
        logger.exception("Could not read PDF %s", pdf_path.name)
        raise ValueError(f"Could not read PDF: {pdf_path.name}") from exc

    chunks: list[dict] = []
    title = document_title(pdf_path)
    active_metadata: dict = {
        "chapter": None,
        "section_number": None,
        "section_title": None,
        "rule_number": None,
        "rule_title": None,
    }
    for page_index, page in enumerate(reader.pages, start=1):
        text = clean_text(page.extract_text() or "")
        if not text:
            continue
        if is_arrangement_page(text, pdf_path, page_index):
            logger.info("Skipping arrangement/contents page %s in %s", page_index, pdf_path.name)
            continue
        page_segments = iter_page_segments(text, active_metadata, title)
        chunk_index = 1
        for segment in page_segments:
            metadata = segment["metadata"]
            for chunk in chunk_text(segment["text"]):
                chunks.append(
                    {
                        "text": enrich_chunk_text(chunk, metadata),
                        "source": pdf_path.name,
                        "document_title": title,
                        "page": page_index,
                        "page_start": page_index,
                        "page_end": page_index,
                        "chapter": metadata.get("chapter"),
                        "section_number": metadata.get("section_number"),
                        "section_title": metadata.get("section_title"),
                        "rule_number": metadata.get("rule_number"),
                        "rule_title": metadata.get("rule_title"),
                        "chunk": chunk_index,
                    }
                )
                chunk_index += 1
    return chunks


def ingest() -> dict:
    DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
    pdf_paths = sorted(DOCUMENTS_DIR.glob("*.pdf"))
    if not pdf_paths:
        raise FileNotFoundError(f"No PDF documents found in {DOCUMENTS_DIR}")

    all_chunks: list[dict] = []
    for pdf_path in pdf_paths:
        pdf_chunks = extract_pdf_chunks(pdf_path)
        logger.info("Loaded %s pages/chunks from %s: %s chunks", "text", pdf_path.name, len(pdf_chunks))
        all_chunks.extend(pdf_chunks)

    if not all_chunks:
        raise ValueError("No extractable text found in the provided PDFs.")

    texts = [chunk["text"] for chunk in all_chunks]
    vectors = embed_texts(texts)
    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    if VECTORSTORE_DIR.exists():
        logger.info(
            "Removing existing vector store so it can be rebuilt with %s (%s)",
            EMBEDDING_PROVIDER,
            EMBEDDING_MODEL,
        )
        shutil.rmtree(VECTORSTORE_DIR)
    VECTORSTORE_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    metadata = {
        "embedding_provider": EMBEDDING_PROVIDER,
        "embedding_model": EMBEDDING_MODEL,
        "embedding_dimension": int(vectors.shape[1]),
        "chunking_strategy": "page-bounded section-aware heading split with 1000-character fallback chunks",
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "document_count": len(pdf_paths),
        "chunk_count": len(all_chunks),
        "chunks": all_chunks,
    }
    with METADATA_PATH.open("w", encoding="utf-8") as file:
        json.dump(metadata, file, ensure_ascii=False)

    logger.info("Created %s chunks from %s documents", len(all_chunks), len(pdf_paths))
    logger.info("Vector store saved to %s", VECTORSTORE_DIR)
    return metadata


if __name__ == "__main__":
    ingest()
