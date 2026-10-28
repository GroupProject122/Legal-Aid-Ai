"""Turns a retrieved chunk's stored text into something a person can read in the source viewer.

Stored chunk text is shaped for search, not reading:
- ingest.enrich_chunk_text() puts a search heading in front of provision chunks ("Manual Section
  5.1.4.1 — To report a complaint..."), which repeats the provision's own first line;
- PDF extraction keeps the page's hard line wraps, so sentences break mid-way
  ("...ready before registering\nyour complaint:").

readable_source_text() drops the repeated heading and re-joins wrapped lines, while keeping real
structure: list items ("i.", "a.", "(1)", "•"), numbered provisions, headings and paragraph
breaks. Case-law header lines (case name, a NOTE that a decision is not good law, "Paragraph N")
are kept -- the good-law note in particular must stay visible.
"""
from __future__ import annotations

import re

# The heading enrich_chunk_text() adds for provision-structured chunks: "<Label> <number> — <title>".
ENRICHMENT_HEADING_RE = re.compile(
    r"^(?:Manual\s+)?(?:Section|Rule|Article|Regulation|Guideline|Clause|Heading|Provision|Paragraph)\s+"
    r"[\w.()/-]+\s+—\s+"
)
# A line that starts a new structural unit and so must stay on its own line.
STRUCTURE_START_RE = re.compile(
    r"""^\s*(?:
        \(?[0-9]{1,3}[A-Z]?[.)]\s                   # 1.  2)  (3)  12A.
      | \([0-9]{1,3}[A-Z]?\)(?=\S)                  # (2)If  -- India Code omits the space
      | \(?[ivxlcdm]{1,6}[.)]\s                     # i.  (iv)  ii)
      | \([a-z]{1,2}\)\s | [a-z][.)]\s              # (a)  a.  b)
      | \d+(?:\.\d+)+\s                             # 5.1.4.1
      | [•●▪◦*–-]\s                                 # bullets
      | (?:CHAPTER|PART|SCHEDULE|Section|Rule|Article|Regulation|Explanation|Illustration|Provided|NOTE)\b
      | Note\s*\d*\s*:
    )""",
    re.VERBOSE | re.IGNORECASE,
)
SENTENCE_END_RE = re.compile(r"[.:;?!]['\")\]]?$")
# Running page header/footer lines from the source PDF ("USER MANUAL FOR ... Page 22 of 91").
PAGE_FURNITURE_RE = re.compile(r"^(?:[A-Z0-9 ,.&()'-]{6,}\s+)?Page\s+\d+\s+of\s+\d+$|^Page\s+\d+$", re.IGNORECASE)
# Sub-sections / clauses the India Code text layer runs together on one line:
# "...service. (1)No landlord ... to him.(2)If a landlord ..." -> one line each.
INLINE_SUBSECTION_RE = re.compile(r"(?<=[.;:—])\s*(?=\(\d{1,3}[A-Z]?\)\s*[A-Z]|Explanation\s*[.:-])")


def normalized(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", text.lower())


def drop_repeated_heading(lines: list[str]) -> list[str]:
    """Remove the search heading when the provision's own text repeats it right after."""
    # The heading follows any Part / Chapter lines enrich_chunk_text() put before it, so look at
    # the first few lines, not only the first. Part / Chapter lines are kept as useful context.
    content = [index for index, line in enumerate(lines) if line.strip()]
    for position, index in enumerate(content[:3]):
        heading = lines[index].strip()
        if not ENRICHMENT_HEADING_RE.match(heading):
            continue
        title = ENRICHMENT_HEADING_RE.sub("", heading).strip()
        following = normalized(" ".join(lines[later] for later in content[position + 1 : position + 3]))
        if title and normalized(title)[:40] in following:
            return lines[:index] + lines[index + 1 :]
        return lines
    return lines


def strip_page_furniture(lines: list[str]) -> list[str]:
    """Drop "Page N of M" lines and the all-capitals running header printed just above them."""
    kept: list[str] = []
    for line in lines:
        stripped = line.strip()
        if PAGE_FURNITURE_RE.match(stripped):
            if kept and len(kept[-1].strip()) >= 20 and kept[-1].strip().upper() == kept[-1].strip() and re.search(r"[A-Z]{4}", kept[-1]):
                kept.pop()
            continue
        kept.append(line)
    return kept


def readable_source_text(text: str, max_chars: int = 6000) -> str:
    raw_lines = [line.rstrip() for line in str(text or "").replace("\r\n", "\n").split("\n")]
    lines = drop_repeated_heading(raw_lines)
    lines = strip_page_furniture(lines)
    lines = [part for line in lines for part in INLINE_SUBSECTION_RE.sub("\n", line).split("\n")]
    paragraphs: list[str] = []
    current = ""
    for line in lines:
        stripped = line.strip()
        if not stripped:
            if current:
                paragraphs.append(current)
                current = ""
            continue
        if not current:
            current = stripped
        elif STRUCTURE_START_RE.match(stripped):
            paragraphs.append(current)
            current = stripped
        elif current.endswith("-") and stripped[:1].islower():
            current = current[:-1] + stripped  # re-join a word hyphenated across the wrap
        elif SENTENCE_END_RE.search(current) and stripped[:1].isupper():
            paragraphs.append(current)
            current = stripped
        else:
            current = f"{current} {stripped}"
    if current:
        paragraphs.append(current)
    result = "\n".join(re.sub(r"[ \t]+", " ", paragraph) for paragraph in paragraphs).strip()
    if len(result) > max_chars:
        result = result[: max_chars - 1].rsplit(" ", 1)[0] + "…"
    return result
