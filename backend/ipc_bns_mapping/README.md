# IPC to BNS mapping

Lets Legal Aid AI handle questions framed under the repealed **Indian Penal Code, 1860 (IPC)** by
answering in terms of the **Bharatiya Nyaya Sanhita, 2023 (BNS)**, which replaced it on
1 July 2024. A user who writes "my FIR is under 420 IPC" gets BNS 318(4), the BNS text, and which
law applies to their case.

## What is in this folder

| File | What it does |
|---|---|
| `ipc_bns.py` | Runtime lookup. Finds IPC citations in text, maps them to BNS, builds the notes shown to the user, the answer-prompt block and the retrieval terms. |
| `build_ipc_bns_map.py` | One-time builder. Reads the two source PDFs and writes the two data files below. |
| `ipc_bns_map.json` | The map: every IPC section (573) to its BNS section(s), and every BNS row back to IPC, with a change summary and a source label. |
| `bns_reference_chunks.jsonl` | All 358 BNS sections, chunked by `ingest.py`'s own parser. Used when a mapped BNS section is not in the search index. Never embedded or searched on its own. |
| `sources/bns_ipc_correspondence_table_bprd.pdf` | BPR&D's official BNS-to-IPC correspondence table ([link](https://bprd.mha.gov.in/uploads/pdf/COMPARISON%20SUMMARY%20BNS%20to%20IPC%20.pdf)). The source of every mapping. |
| `sources/indian_penal_code_1860.pdf` | The final amended IPC (to Act 22 of 2018), Legislative Department, via [Wikimedia Commons](https://commons.wikimedia.org/wiki/File:The_Indian_Penal_Code.pdf). Used for IPC section titles and to find sections the table never mentions. |
| `tests/` | 68 tests for the lookup, the map, the reference file, retrieval and the `/api/ask` lookup reply. |

## The mapping

| Status | IPC sections | Example |
|---|---|---|
| Has a BNS equivalent | 538 | 420 -> 318(4), 354D -> 78, 506 -> 351(2)/(3), 498A -> 85 + 86 |
| Repealed before the BNS | 21 | 161-165A (moved to the Prevention of Corruption Act) |
| No BNS equivalent | 16 | 124A sedition, 309, 377, 497 |

Each mapping is also marked **unchanged** (renumbered only, e.g. 420) or **modified** (e.g. 170
now has a minimum sentence), so an answer never says the law changed when only the number did.

### Every statement carries its source

| Label | Meaning |
|---|---|
| `bprd_table` | Stated in the BPR&D correspondence table. |
| `bns_text` | Not in the table; our reading of the official BNS text, quoted in the note. Used for IPC 143, 376DA, 444 and 446, which the table never names. |
| `dataset_reading` | Not in the table; our reading of another Act in this dataset (Legal Metrology Act for IPC 264-267). |
| `ipc_text` | Read from the IPC itself (sections marked "[Repealed.]"). |
| `not_in_dataset` | General legal knowledge with no document in this dataset behind it (the Navtej Johar and Joseph Shine judgments). Said explicitly in the note. |

## How it is wired into the app

- **Retrieval** (`rag.py`): when a question cites IPC sections, the mapped BNS sections are added
  to the query, always added as candidates, and boosted past the low-priority penalty the BNS
  extract carries. Sections outside the indexed 30-section extract come from
  `bns_reference_chunks.jsonl`.
- **Answer** (`grounded_answer.py`): the model gets an `IPC TO BNS MAPPING` block and a rule to
  state it only as given, in the "In short" reply, plus the before/after 1 July 2024 rule (quoted
  from BNS 358).
- **API** (`main.py`):
  - IPC citations are read from what the user wrote (and confirmed documents such as an FIR),
    not from the AI case summary.
  - The mapping is attached to the response from the map, so the claim verifier cannot strip it.
  - A short lookup ("what is IPC 302 now?") is answered before routing, without Gemini.
  - An out-of-scope reply still carries the mapping.
- **Frontend** (`frontend/src/App.jsx`): an "IPC to BNS" section under "In short".

## Parser fixes in `ingest.py`

`ingest.py` is shared by every document, so these changes stay there, but they were made for this
work:

- Section headings with a typographic apostrophe ("89. ... woman's consent .-"), a short title
  followed by the heading dash ("63. Rape.-", "114. Hurt.-"), or no space before the title
  ("255.-Public servant") were missed and merged into the previous section.
- Contents pages after page 6 that continue a contents run (the BNS's run to page 15) were parsed
  as sections, creating text-less chunks.
- Numbered footnotes naming a section ("1. Section 66A has been struck down ...") were read as
  section headings.

Effect on a full re-parse:

- BNS extract: 21 table-of-contents chunks removed.
- Real sections recovered: Sale of Goods Act 41/46/47, Slum Areas Act 27, Transfer of Property
  Act 49/65A/109.
- Two false "section 1" footnotes removed (IT Act, Registration Act).
- No other document changed, and the retrieval evaluation was unchanged (MRR 0.88).

## Commands (run from `backend/`)

```bash
# Rebuild the map and the BNS reference after changing a source PDF, the BNS PDF or ingest.py's parser
python -m ipc_bns_mapping.build_ipc_bns_map

# Tests: this folder only, or together with the main suite
python -m pytest ipc_bns_mapping/tests
python -m pytest tests ipc_bns_mapping/tests
```

`python -m pytest tests` alone does **not** run this folder's tests. The tests here use the same
isolated temporary database as `tests/` (through `tests/conftest.py`).

## Known limits

- The four `bns_text` mappings (IPC 143, 376DA, 444, 446) are our reading of the BNS, not the
  government's; check them against an official source before relying on them.
- The direct lookup reply runs only at the start of a new chat; inside an ongoing case, IPC
  questions go through the normal pipeline, which still attaches the mapping.
- Answers and notes are in English.
