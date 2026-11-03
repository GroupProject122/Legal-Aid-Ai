"""One-time authoring script that generates backend/ipc_bns_map.json, the IPC -> BNS lookup the
assistant uses to answer questions framed under the repealed Indian Penal Code.

Inputs (both under documents/ipc_bns_mapping/, neither of which is ingested into the RAG index):
- bns_ipc_correspondence_table_bprd.pdf -- BPR&D's BNS-to-IPC correspondence table. This is the
  source of every mapping. It is a four-column table (BNS section, subject, IPC section(s),
  summary of comparison) whose plain-text extraction interleaves the columns, so rows are rebuilt
  from each text fragment's x/y position instead.
- indian_penal_code_1860.pdf -- the final amended IPC. Only its arrangement of sections is read,
  to get every IPC section's title and to find the sections the table never mentions: those were
  either repealed before the BNS or dropped by it (377, 497, ...), and a lookup must say so rather
  than come back empty.

It also writes parsed/bns_reference_chunks.jsonl: every BNS section, chunked by ingest.py's own
parser. Only a 30-section BNS extract is in the search index (the full Sanhita was retrieval noise
for cyber questions), so when a user's IPC citation maps to any other BNS section, rag.py takes
that section's text from this file instead. It is never embedded or searched on its own.

Run manually (`python build_ipc_bns_map.py`) whenever either PDF, the BNS PDF or ingest.py's
statute parser changes; ipc_bns.py and rag.py load the outputs at request time.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from config import BASE_DIR, DOCUMENTS_DIR

logger = logging.getLogger("legal_aid_ai.build_ipc_bns_map")

MAPPING_DIR = DOCUMENTS_DIR / "ipc_bns_mapping"
TABLE_PDF = MAPPING_DIR / "bns_ipc_correspondence_table_bprd.pdf"
IPC_PDF = MAPPING_DIR / "indian_penal_code_1860.pdf"
OUTPUT_PATH = BASE_DIR / "ipc_bns_map.json"
BNS_SOURCE_FILE = "cyber/bharatiya_nyaya_sanhita_2023.pdf"
BNS_REFERENCE_PATH = BASE_DIR / "parsed" / "bns_reference_chunks.jsonl"
BNS_SECTION_COUNT = 358

BNS_COMMENCEMENT_DATE = "2024-07-01"

# x-ranges (PDF points) of the table's four columns; identical on every page of the BPR&D PDF.
TABLE_COLUMNS = (("bns", 0, 105), ("subject", 105, 300), ("ipc", 300, 348), ("summary", 348, 10_000))
FOOTER_MAX_Y = 80
FIRST_PAGE_HEADER_MIN_Y = 597
SAME_LINE_TOLERANCE = 3

NEW_IN_BNS_CELLS = {"-", "new", "new sub-section", "new sub - section"}
IPC_SECTION_RE = re.compile(r"\d+[A-Z]{0,2}")

# Every statement in the map carries a source, so an answer never presents our own reading as the
# government's mapping:
#   bprd_table      -- stated in the BPR&D correspondence table
#   bns_text        -- not in the table; our reading of the official BNS text (quoted in the note)
#   dataset_reading -- not in the table; our reading of another Act in this dataset
#   not_in_dataset  -- general legal knowledge with no document in this dataset behind it
NOT_IN_TABLE = "Not listed in the government (BPR&D) correspondence table."

# IPC sections the BPR&D table never names. The BNS text shows where each went, but linking them
# is our reading, so they are tagged bns_text rather than passed off as table entries.
TABLE_GAPS = {
    "143": {
        "section": "189(2)",
        "note": f"{NOT_IN_TABLE} Our reading of the BNS text: BNS 189(2) defines a member of an unlawful "
        "assembly and says \"such member shall be punished with imprisonment of either description for a "
        "term which may extend to six months, or with fine, or with both\", which is the IPC 143 punishment.",
    },
    "376DA": {
        "section": "70(2)",
        "note": f"{NOT_IN_TABLE} Our reading of the BNS text: BNS 70(2) covers gang rape \"where a woman "
        "under eighteen years of age is raped\", which includes the under-sixteen victims of IPC 376DA. "
        "The table maps only IPC 376DB (under twelve) to BNS 70(2).",
    },
    "444": {
        "section": "331",
        "note": f"{NOT_IN_TABLE} Our reading of the BNS text: the BNS has no separate 'by night' definition; "
        "BNS 331(2), (4), (6) and (8) use \"after sunset and before sunrise\" instead.",
    },
    "446": {
        "section": "331",
        "note": f"{NOT_IN_TABLE} Our reading of the BNS text: the BNS has no separate 'by night' definition; "
        "BNS 331(2), (4), (6) and (8) use \"after sunset and before sunrise\" instead.",
    },
}

# Context for IPC sections with no BNS counterpart. Sections not listed here get only NOT_IN_TABLE.
LEGAL_METROLOGY_NOTE = {
    "source": "dataset_reading",
    "text": "Our reading of the Legal Metrology Act, 2009 (in this dataset): section 25 penalises using a "
    "non-standard weight or measure and section 27 its manufacture or sale.",
}
OMISSION_NOTES = {
    "124A": [
        {"source": "bprd_table", "text": "The table lists BNS 152 (act endangering sovereignty, unity and integrity "
         "of India) as a newly added section. It does not say that BNS 152 replaces sedition."},
    ],
    "309": [
        {"source": "bprd_table", "text": "The table lists BNS 226 (attempt to commit suicide to compel or restrain "
         "a public servant from discharging official duty) as a newly added section."},
    ],
    "377": [
        {"source": "bprd_table", "text": "The table states that \"section 377 IPC has been excluded altogether\" "
         "(remark under BNS 308(6))."},
        {"source": "not_in_dataset", "text": "Not from the government data or any document in this dataset: the "
         "Supreme Court read section 377 down in Navtej Singh Johar v. Union of India (2018)."},
    ],
    "497": [
        {"source": "not_in_dataset", "text": "Not from the government data or any document in this dataset: the "
         "Supreme Court struck section 497 down in Joseph Shine v. Union of India (2018)."},
    ],
    "264": [LEGAL_METROLOGY_NOTE],
    "265": [LEGAL_METROLOGY_NOTE],
    "266": [LEGAL_METROLOGY_NOTE],
    "267": [LEGAL_METROLOGY_NOTE],
}


def column_for(x: float) -> str:
    for name, low, high in TABLE_COLUMNS:
        if low <= x < high:
            return name
    return "summary"


def page_lines(page: Any, page_number: int) -> list[dict[str, str]]:
    """One dict per visual line, mapping column name -> the text in that column on that line."""
    fragments: list[tuple[float, float, str]] = []

    def visit(text: str, cm: list[float], tm: list[float], _font: Any, _size: Any) -> None:
        if text.strip():
            fragments.append((tm[4] * cm[0] + cm[4], tm[5] * cm[3] + cm[5], text))

    page.extract_text(visitor_text=visit)
    fragments = [f for f in fragments if f[1] > FOOTER_MAX_Y and "Anil Kishore Yadav" not in f[2]]
    if page_number == 1:
        fragments = [f for f in fragments if f[1] < FIRST_PAGE_HEADER_MIN_Y]
    fragments.sort(key=lambda f: (-f[1], f[0]))

    grouped: list[tuple[float, list[tuple[float, str]]]] = []
    for x, y, text in fragments:
        if grouped and abs(grouped[-1][0] - y) <= SAME_LINE_TOLERANCE:
            grouped[-1][1].append((x, text))
        else:
            grouped.append((y, [(x, text)]))
    lines = []
    for _y, parts in grouped:
        cells: dict[str, list[str]] = {}
        for x, text in sorted(parts):
            cells.setdefault(column_for(x), []).append(text)
        lines.append({name: " ".join(texts) for name, texts in cells.items()})
    return lines


def starts_new_row(bns_text: str, current: dict[str, Any] | None) -> bool:
    compact = bns_text.replace(" ", "")
    if not compact:
        return False
    # "Explanation to section 5" wraps over four lines; its trailing "5" is not a new row.
    if current and current["bns"].replace(" ", "").lower().endswith("tosection"):
        return False
    return bool(re.match(r"^\d", compact)) or compact.lower().startswith("explanati")


def clean(text: str) -> str:
    text = text.replace("�", '"').replace("“", '"').replace("”", '"').replace("‘", "'").replace("’", "'")
    text = re.sub(r"\s+", " ", text).strip()
    text = re.sub(r"\s+([.,;:])", r"\1", text)
    # Extraction spaces out hyphenated words ("sub - section"); a real dash precedes a capital.
    return re.sub(r"(\w)(?: - | -|- )([a-z])", r"\1-\2", text)


def read_table_rows(pdf_path: Path) -> list[dict[str, Any]]:
    reader = PdfReader(str(pdf_path))
    rows: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None
    for page_number, page in enumerate(reader.pages, start=1):
        for line in page_lines(page, page_number):
            if starts_new_row(line.get("bns", ""), current):
                current = {"bns": "", "subject": "", "ipc": "", "summary": "", "page": page_number}
                rows.append(current)
            if current is None:
                continue
            for column, text in line.items():
                current[column] = f"{current[column]} {text}".strip()

    previous_summary = ""
    for row in rows:
        bns = re.sub(r"\s+", "", row["bns"])
        explanation = re.fullmatch(r"(?i)explanationtosection(\d+)", bns)
        row["bns"] = f"{explanation.group(1)} Explanation" if explanation else bns
        row["subject"] = clean(row["subject"])
        row["ipc"] = re.sub(r"\s+", " ", row["ipc"]).strip()
        summary = clean(row["summary"])
        # The table writes "Ditto." when a row's comparison is the same as the row above.
        if re.fullmatch(r"(?i)d\s*itto\.?", summary):
            summary = previous_summary
        row["summary"] = previous_summary = summary
    return rows


def parse_ipc_cell(cell: str) -> list[str]:
    """IPC section numbers named in one table cell, with subsection/clause detail dropped.

    Handles the forms the table uses: "420", "29 and 29A", "68 & 69", "428/ 429",
    "230 to 232, 246 to 249, 255, 489A", "376(1) & 376(2)", "228A (1)/(2)", "23 Clause-1",
    "498A Explanation", "171 - I" (= 171I), and the "23 7 to 241" extraction split of 237."""
    if cell.strip().lower() in NEW_IN_BNS_CELLS or not cell.strip():
        return []
    text = re.sub(r"(\d+) (\d+)(?= to)", r"\1\2", cell)
    text = re.sub(r"\(\s*\d+\s*\)", "", text)
    text = re.sub(r"(?i)clause\s*-?\s*\d+|explanat\s*ion", "", text)
    text = re.sub(r"(\d+)\s*-\s*([A-Z])\b", r"\1\2", text)
    sections: list[str] = []
    for part in re.split(r",|&|/|\band\b", text):
        part = part.strip()
        span = re.fullmatch(r"(\d+)\s*to\s*(\d+)", part)
        if span:
            sections.extend(str(n) for n in range(int(span.group(1)), int(span.group(2)) + 1))
        else:
            sections.extend(IPC_SECTION_RE.findall(part))
    return list(dict.fromkeys(sections))


# A summary that only reports the IPC section becoming a BNS sub-section is a renumbering, not a
# change to the offence.
RENUMBERED_ONLY_RE = re.compile(
    r"^(the )?(ipc )?section is included as (a )?sub-?section( in (the )?bns)?,?( sans heading)?\.?"
    r"( no other changes?\.?)?$",
    re.I,
)


def change_type(ipc_sections: list[str], summary: str) -> str:
    if not ipc_sections:
        return "new"
    lowered = summary.lower()
    if lowered.startswith(("no change", "formal change")) or RENUMBERED_ONLY_RE.match(summary):
        return "unchanged"
    return "modified"


def read_ipc_sections(pdf_path: Path) -> dict[str, str]:
    """IPC section number -> title, from the Act's arrangement of sections (1 through 511)."""
    reader = PdfReader(str(pdf_path))
    text = "\n".join(page.extract_text() or "" for page in reader.pages[:20])
    arrangement = text[text.find("ARRANGEMENT OF SECTIONS"):]
    sections: dict[str, str] = {}
    for line in arrangement.splitlines():
        match = re.match(r"^\s*(\d+[A-Z]{0,2})\.\s*(\D.*)", line)
        if match:
            title = clean(match.group(2)).rstrip(".")
            # The Act titles a punishment section just "Punishment" under the offence above it.
            if title == "Punishment" and sections:
                previous = list(sections.values())[-1]
                title = f"Punishment for {previous[0].lower()}{previous[1:]}"
            sections[match.group(1)] = title
            if match.group(1) == "511":
                break
    return sections


def is_repealed_title(title: str) -> bool:
    return bool(re.fullmatch(r"\[?\s*(repealed|omitted)\s*\.?\s*\]?\.?", title.strip(), re.I))


def build_map() -> dict[str, Any]:
    rows = [row for row in read_table_rows(TABLE_PDF) if row["bns"] != "2" or row["ipc"]]
    ipc_titles = read_ipc_sections(IPC_PDF)
    logger.info("Read %d correspondence rows and %d IPC sections", len(rows), len(ipc_titles))

    bns_to_ipc: dict[str, dict[str, Any]] = {}
    ipc_to_bns: dict[str, dict[str, Any]] = {}
    for row in rows:
        ipc_sections = parse_ipc_cell(row["ipc"])
        kind = change_type(ipc_sections, row["summary"])
        bns_to_ipc[row["bns"]] = {
            "subject": row["subject"],
            "ipc": ipc_sections,
            "ipc_as_written": row["ipc"] or None,
            "change_type": kind,
            "change_summary": row["summary"],
            "table_page": row["page"],
        }
        for section in ipc_sections:
            entry = ipc_to_bns.setdefault(section, {"ipc_title": ipc_titles.get(section), "status": "mapped", "bns": []})
            entry["bns"].append({
                "section": row["bns"],
                "subject": row["subject"],
                "change_type": kind,
                "change_summary": row["summary"],
                "source": "bprd_table",
            })

    for section, gap in TABLE_GAPS.items():
        if section in ipc_to_bns:
            logger.warning("IPC %s is now in the correspondence table; drop it from TABLE_GAPS", section)
            continue
        target = next((key for key in bns_to_ipc if key == gap["section"] or key.startswith(f"{gap['section']}(")), None)
        ipc_to_bns[section] = {
            "ipc_title": ipc_titles.get(section),
            "status": "mapped",
            "bns": [{
                "section": gap["section"],
                "subject": bns_to_ipc[target]["subject"] if target else None,
                "change_type": "modified",
                "change_summary": gap["note"],
                "source": "bns_text",
            }],
        }

    for section, title in ipc_titles.items():
        if section in ipc_to_bns:
            continue
        if is_repealed_title(title):
            ipc_to_bns[section] = {
                "ipc_title": None,
                "status": "repealed_before_bns",
                "bns": [],
                "notes": [{"source": "ipc_text", "text": "Marked \"[Repealed.]\" or \"[Omitted.]\" in the IPC text itself."}],
            }
            continue
        ipc_to_bns[section] = {
            "ipc_title": title,
            "status": "no_bns_equivalent",
            "bns": [],
            "notes": [{"source": "bprd_table", "text": NOT_IN_TABLE}, *OMISSION_NOTES.get(section, [])],
        }

    # A few sections (171I, 376AB, ...) are missing from the IPC PDF's own arrangement of
    # sections; the table's subject line is the best title available for them.
    for section, entry in ipc_to_bns.items():
        if not entry["ipc_title"] and entry["status"] == "mapped":
            entry["ipc_title"] = entry["bns"][0]["subject"]
            logger.info("IPC %s title taken from the correspondence table", section)

    return {
        "description": (
            "IPC 1860 -> BNS 2023 correspondence. The BNS replaced the IPC on "
            f"{BNS_COMMENCEMENT_DATE}; offences committed before that date are still tried under the IPC."
        ),
        "bns_commencement_date": BNS_COMMENCEMENT_DATE,
        "sources": {
            "correspondence_table": "BPR&D, Correspondence Table and Comparison Summary of the BNS, 2023 to the IPC, 1860 "
            "(https://bprd.mha.gov.in/uploads/pdf/COMPARISON%20SUMMARY%20BNS%20to%20IPC%20.pdf)",
            "ipc_text": "The Indian Penal Code, 1860 (Act 45 of 1860), as amended to Act 22 of 2018, "
            "Legislative Department (via https://commons.wikimedia.org/wiki/File:The_Indian_Penal_Code.pdf)",
        },
        "source_tags": {
            "bprd_table": "Stated in the BPR&D correspondence table.",
            "bns_text": "Not in the table; our reading of the official BNS text, quoted in the note.",
            "dataset_reading": "Not in the table; our reading of another Act in this dataset.",
            "ipc_text": "Read from the IPC text itself.",
            "not_in_dataset": "General legal knowledge; no document in this dataset supports it.",
        },
        "generated_by": "backend/build_ipc_bns_map.py",
        "ipc_to_bns": dict(sorted(ipc_to_bns.items(), key=lambda item: section_sort_key(item[0]))),
        "bns_to_ipc": bns_to_ipc,
    }


def section_sort_key(section: str) -> tuple[int, str]:
    match = re.match(r"(\d+)(.*)", section)
    return (int(match.group(1)), match.group(2)) if match else (10_000, section)


def build_bns_reference_chunks() -> list[dict[str, Any]]:
    """Every BNS section as ingest.py would chunk it without the manifest's extract filter."""
    import ingest  # heavy (faiss, embeddings); only this step needs it

    entry = next(item for item in ingest.load_manifest_documents() if item["source_file"] == BNS_SOURCE_FILE)
    full_entry = {key: value for key, value in entry.items() if key != "extract"}
    parsed = [ingest.jsonl_record_from_chunk(chunk) for chunk in ingest.parse_document(DOCUMENTS_DIR / BNS_SOURCE_FILE, full_entry)]
    # Keep the enacted sections only: the parser also emits the unnumbered front matter, and after
    # section 358 the Statement of Objects and Reasons, whose numbered paragraphs it reads as
    # sections ("6. The Notes on Clauses ...") -- which would put that text under BNS 6 and 7.
    records = []
    for record in parsed:
        if record.get("section_number"):
            records.append(record)
        if record.get("section_number") == str(BNS_SECTION_COUNT) and record.get("provision_chunk_index") == record.get("provision_chunk_count"):
            record["text"] = record["text"].split("STATEMENT OF OBJECTS AND REASONS")[0].rstrip()
            break
    present = {record["section_number"] for record in records}
    missing = [number for number in map(str, range(1, BNS_SECTION_COUNT + 1)) if number not in present]
    if missing:
        # A missed heading merges that section into the one before it; an IPC lookup would then
        # quote the wrong section's text, so stop rather than write an incomplete reference.
        raise RuntimeError(f"ingest.py's parser found no heading for BNS sections {missing}")
    for number, record in enumerate(records, start=1):
        # Distinct from the indexed extract's ids, which come from the same parser but a shorter sequence.
        record["chunk_id"] = f"bns_reference__chunk_{number:04d}"
    return records


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    reference = build_bns_reference_chunks()
    BNS_REFERENCE_PATH.write_text("".join(json.dumps(record, ensure_ascii=False) + "\n" for record in reference), encoding="utf-8")
    logger.info("Wrote %s: %d chunks", BNS_REFERENCE_PATH.name, len(reference))
    mapping = build_map()
    OUTPUT_PATH.write_text(json.dumps(mapping, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    statuses: dict[str, int] = {}
    for entry in mapping["ipc_to_bns"].values():
        statuses[entry["status"]] = statuses.get(entry["status"], 0) + 1
    logger.info("Wrote %s: %d BNS rows, IPC sections by status %s", OUTPUT_PATH.name, len(mapping["bns_to_ipc"]), statuses)


if __name__ == "__main__":
    main()
