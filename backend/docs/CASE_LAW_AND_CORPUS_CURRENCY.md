# Case law ingestion, the judgment parser, and corpus currency

Covers the work of 2026-09-24: making court judgments searchable for the first time, and making
the corpus tell the truth about which law is still in force.

Written for someone picking this up cold. It states what was built, how accurate it is, every
parameter and model involved, what it still cannot do, and where to start next.

---

## 1. What this does

Before this work the corpus held statutes, rules and guidelines only. Judgments had been
collected but sat inert in a `pending_case_law` holding area, excluded from ingestion, because
`ingest.py` had no parser that understood a judgment. A question like "what did the Supreme Court
hold about section 66A" could not be answered from the corpus at all.

Three things changed.

**Judgments are now searchable.** 23 judgments across all four domains are parsed, chunked,
embedded and retrievable — 2,186 chunks, about a third of the corpus.

**The corpus now flags law that is no longer in force.** Struck-down provisions and
partly-overruled judgments carry explicit warnings, bound to the chunk that reproduces them so
chunking cannot separate the text from the warning about it.

**Two long-standing retrieval defects were fixed at the root**, both found while validating the
above rather than looked for deliberately.

---

## 2. How accurate it is

Measured with the repository's own harness, `evaluate_retrieval.py`, against
`eval/retrieval_queries.json` (44 queries: 36 single-domain, 5 cross-domain, 3 non-legal).

| Metric | Before this work | After |
|---|---:|---:|
| Document Hit@5 | 94.4% | **97.2%** |
| MRR | 0.857 | **0.881** |
| Provision Hit@5 | 90.9% | 90.9% |
| Domain Hit@1 | 97.2% | 97.2% |
| Failing queries | 2 | **1** |

Per domain (Document Hit@5 / MRR):

| Domain | Before | After |
|---|---|---|
| constitutional_public_authority | 100% / 1.000 | 100% / 1.000 |
| consumer | 88.9% / 0.815 | 100% / 0.917 |
| cyber | 88.9% / 0.615 | 88.9% / 0.633 |
| tenancy | 100% / 1.000 | 100% / 1.000 |

Ingestion audit: **PASS, HIGH=0**, MEDIUM=96, LOW=3 over 6,697 chunks. The MEDIUM count rose
from 92 only because the section-boundary fix (§5.1) split provisions that were previously merged,
creating more individually-checked units. No case-law-specific findings in any audit bucket.

Test suite: **96 passing, 0 failing.**

### The one remaining eval failure, and why it was left

`cyber_07` — "someone shared private data online" — expects the Digital Personal Data Protection
**Rules, 2025**. Retrieval returns the Digital Personal Data Protection **Act, 2023** instead
(plus the IT Act, which the query also expects and which it does return).

`git log` shows `eval/retrieval_queries.json` was last touched in `3ed645c`, while the DPDP Act
was added to the corpus later in `0dbf941`. The expectation was therefore written when only the
Rules existed. The Act is the parent instrument that creates the obligations; the Rules are
procedural detail under it, so for this question the Act is arguably the better answer.

Retrieval was deliberately **not** tuned to rank Rules above their parent Act to satisfy this,
because that would make the system worse in general to satisfy one stale expectation. The correct
fix is to widen the expectation to accept either instrument — an edit to someone else's eval data,
left for them to make.

---

## 3. Models and parameters

### Models

| Role | Model | Notes |
|---|---|---|
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` | 384 dimensions, runs locally, no API key |
| Vector index | FAISS | `backend/vectorstore/index.faiss`, git-ignored, rebuilt by `ingest.py` |
| Generation | `gemini-flash-lite-latest` | Only for answer generation, never retrieval |

Set via `config.py` / `.env`: `EMBEDDING_PROVIDER=local`, `LLM_PROVIDER=gemini`.

### Chunking (`ingest.py`)

| Parameter | Value | Meaning |
|---|---:|---|
| `CHUNK_SIZE` | 1000 | Base chunk size in characters |
| `CHUNK_OVERLAP` | 160 | Overlap between adjacent chunks |
| `STRUCTURED_CHILD_CHUNK_SIZE` | 2000 | Max size of one provision/paragraph before it is split |
| `STRUCTURED_CHILD_CHUNK_OVERLAP` | 120 | Overlap when splitting an oversized provision |
| `MIN_JUDGMENT_PARAGRAPHS` | 5 | Below this many validated paragraphs, a judgment is treated as prose |

### Retrieval scoring (`rag.py`)

| Parameter | Value | Added | Meaning |
|---|---:|---|---|
| `TOP_K` | 5 | existing | Chunks returned |
| `MIN_RELEVANCE_SCORE` | 0.30 | existing | Floor for admission |
| `RELEVANCE_WINDOW` | 0.14 | existing | Admission window below the top score |
| `DOCUMENT_DIVERSITY_CAP` | 2 | existing | Max chunks from one document in the result set |
| `PROCEDURAL_GUIDE_SUBSTANTIVE_PENALTY` | 0.20 | existing | Down-weights citizen manuals on substantive questions |
| `CASE_LAW_SUBSTANTIVE_PENALTY` | **0.18** | new | Down-weights judgments on questions not about case law (§5.2) |
| `TITLE_SUBJECT_MATCH_BOOST` | **0.25** | new | Boosts the instrument whose bracketed title subject the question names (§5.3) |

Both new values were tuned empirically against `evaluate_retrieval.py`, not chosen by intuition.
For the case-law penalty, 0.12 was too weak to fix the regression and 0.24 gave no measurable
gain over 0.18, so the smallest value that restored parity was taken — the goal is to seat
judgments *alongside* the governing provision, not to suppress them.

---

## 4. The judgment parser

`parse_case_law_document()` in `ingest.py`, registered for `document_type: "case_law"`.

### Two modes, chosen per document

The 23 judgments split almost evenly on whether their paragraph numbering is usable, so the mode
is detected rather than configured:

- **Paragraph mode** — one unit per numbered paragraph. Page span is the paragraph's own.
- **Prose mode** — one unit per page. Used when numbering is absent or too sparse to trust.
  Page-level units keep `page_start`/`page_end` meaningful for citation; a single
  whole-document unit would make every chunk of a 37-page judgment claim to span all 37 pages.

Result: 618 paragraph-mode chunks, 1,568 prose-mode chunks.

### Why detection is not just a regex

A bare `^\d+\.` pattern matched numbers as high as 999 in judgments whose real paragraph count is
far lower — footnote markers, fragments of quoted statutes, citation remnants. Two guards:

1. **Sequence validation** (`accept_judgment_paragraph`) — a candidate is accepted only if it
   continues the running sequence, allows a small forward gap, or restarts at 1. The restart case
   is real: Kesavananda and S.P. Gupta renumber from 1 for each judge's opinion.
2. **Density check** — paragraph mode requires at least one detected paragraph per page.
   Kesavananda yields only ~170 line-start boundaries across 721 pages because the text layer
   leaves most paragraph numbers mid-line; segmenting on those produced 15,000-character
   "paragraphs". Below one per page the numbering is not trustworthy and prose mode is used.

### Metadata

`case_name`, `citation`, `court`, `date`, `good_law` come from the manifest, never from parsing
the PDF text — a citation scraped from a PDF is far less reliable than a curated entry, and
`good_law` must never be guessed. They are carried into every chunk's metadata *and* prepended to
the chunk's text, so a chunk retrieved from mid-judgment still says what case it is.

### Indian Kanoon furniture

Stripped per page: the source footer (`Indian Kanoon - http://...`) and the
`Equivalent citations:` block, which runs to 10+ lines of parallel-citation soup in some
judgments and is pure retrieval noise given the authoritative citation is in the manifest.

---

## 5. The three fixes found while validating

### 5.1 Amendment footnote markers hid 17 sections (root cause of a documented limitation)

India Code prints a provision inserted by a later amendment wrapped in a footnote marker:

```
1[66A. Punishment for sending offensive messages through communication service, etc.
```

The line does not begin with the section number, so a `^`-anchored boundary pattern never saw it.
In the IT Act alone this hid **17 sections** — including s.43A (compensation for failure to
protect data), s.66 (computer related offences), s.66A, s.69 (interception) and s.72A. Their text
was still indexed, but merged into whichever earlier section did match, so provision metadata
pointed at the wrong section: the chunk containing s.66A was tagged `section_number=65`.

This is the cause of the "ss. 43–47 and 65–66A merge into adjacent chunks" limitation recorded in
the changelog. Fixed by allowing an optional `AMENDMENT_FOOTNOTE_PREFIX` in the section, article,
rule and regulation boundary patterns. All 17 now tag correctly.

This changed **every statute in the corpus**, not only the IT Act — the `N[` convention is
standard India Code formatting.

### 5.2 Case law displaced the statutes it interprets

Case law carries `authority_level: primary` — jurisprudentially correct, a Supreme Court judgment
*is* primary authority — which made judgments compete head-on with statutes. Ingesting them
regressed Document Hit@5 from 94.4% to 91.7% and MRR from 0.857 to 0.817.

Concretely, on eval query `cyber_05` ("intermediary failed to remove unlawful content"),
Mrs X v. Union of India took the top slot at rerank 0.9263 and filled 8 of the top 10 candidate
slots, burying the IT Intermediary Guidelines Rules that actually impose the takedown duty.

Fixed with `CASE_LAW_SUBSTANTIVE_PENALTY`, applied in **both** `authority_level_boost()` and
`relevance_gate_score()` — a rerank-only penalty cannot rescue a chunk the admission gate already
excluded. The penalty is skipped entirely when the question is itself about case law, so
"what did the Supreme Court hold in…" still ranks judgments on their merits.

### 5.3 Specific rules lost to their parent Act

Indian subordinate legislation distinguishes itself in brackets — Consumer Protection
**(Direct Selling)** Rules, 2021 against Consumer Protection **(E-Commerce)** Rules, 2020 — and
everything outside the brackets is shared with the parent Act. Semantic similarity therefore
favours the Act, which repeats the general language the query also uses.

On `consumer_06` ("direct selling company refusing refund") the Direct Selling Rules did not make
the result set at all, despite the query naming its subject outright. `TITLE_SUBJECT_MATCH_BOOST`
fires only when the question contains the phrase that distinguishes an instrument from its
siblings. The query now returns the Consumer Protection Act **and** the Direct Selling Rules
together.

---

## 6. Corpus currency

### Void provisions

A statute PDF reproduces struck-down text as ordinary body text; the footnote saying it is void is
a separate line that chunking can separate from it. That is exactly what happened to IT Act
s.66A — the offence text and the note recording that the Supreme Court voided it in 2015 landed in
different chunks, so retrieving the offence alone presented a dead provision as live law.

A `void_provisions` field on a manifest entry binds a warning to the provision's own chunk. A
corpus-wide scan for struck-down/repealed/overruled text found three statutes needing it:

| Document | Provision | Status |
|---|---|---|
| Information Technology Act, 2000 | s.66A | Struck down — Shreya Singhal v. Union of India (2015) 5 SCC 1 |
| Delhi Rent Control Act, 1958 | s.14(1)(e) proviso | Partly struck down — Satyawati Sharma (2008) 5 SCC 287 |
| Constitution of India | 99th Amendment (NJAC) | Struck down — SC Advocates-on-Record Assn, AIR 2016 SC 117 |

The text is kept, not deleted. People still ask about s.66A, and police have continued to invoke
it; removing it would leave the tool unable to explain that it is dead.

### Judgments that are not wholly good law

**S.P. Gupta v. Union of India** was flagged `good_law: "partial"`. Its locus standi / PIL holding
survives and is the foundation of public interest litigation; its judicial-appointments holding
was overruled by the Second Judges Case (1993), which established the collegium. All 249 of its
chunks carry a warning line. Its curated extract deliberately targets the surviving PIL material
and steers away from the overruled appointments reasoning — 81 retained mentions of `locus standi`
against single digits for the appointments terms.

**Vishaka v. State of Rajasthan** carries a `superseded_by` note: not overruled, but its guidelines
were expressly interim and the POSH Act 2013 now occupies the field. That Act is **not yet in the
corpus** — see §8.

### `good_law` is now readable by code

`good_law` was being dropped at retrieval: `RetrievedChunk` had no such field, so no downstream
code *could* act on it. It is now carried on the dataclass alongside `case_name`, `citation`,
`court` and `paragraph_number`, and `grounded_answer.currency_warning()` emits a labelled
`CURRENCY_WARNING:` line into the prompt, with a matching system-prompt rule forbidding the model
from presenting such material as creating a present-day offence or liability.

### Curated extracts

Four judgments and one statute are ingested as extracts rather than in full, because ingesting
them whole made a small number of documents dominate the index:

| Document | Full | Extract | Selection |
|---|---:|---:|---|
| Kesavananda Bharati (721 pp) | 1,575 | 293 | by doctrinal terms |
| S.P. Gupta (641 pp) | 1,420 | 249 | by doctrinal terms, steered to the surviving holding |
| Puttaswamy (266 pp) | 644 | 325 | by doctrinal terms |
| Maneka Gandhi (150 pp) | 356 | 239 | by doctrinal terms |
| Bharatiya Nyaya Sanhita | 665 | 72 | by **named section** |

Term-density selection is the wrong tool for a numbered statute: on the BNS it kept the long
definitions clause while dropping voyeurism, stalking, forgery and criminal intimidation — the very
offences the extract exists for. `keep_provisions` names sections exactly. The BNS extract now
covers 30 named sections (voyeurism 77, stalking 78, obscenity 294/296, cheating and personation
318–319, forgery 336–340, criminal intimidation 351, defamation 356, extortion 308, the
electronic-record offences 210/241/340, impersonating a public servant 204, plus the definitions,
abetment, conspiracy and attempt provisions those depend on).

This delivers the `bns_2023_cyber_extract.pdf` the changelog had listed as pending, without a
separately maintained PDF.

---

## 7. Corpus as it stands

**6,697 chunks across 82 documents.** 98.58% structure-aware.

| Domain | Chunks |
|---|---:|
| constitutional_public_authority | 3,195 |
| cyber | 1,613 |
| tenancy | 1,032 |
| consumer | 857 |

Case law: **2,186 chunks over 23 judgments** — cyber 6, consumer 4, tenancy 5,
constitutional_public_authority 8.

Note the corpus is *smaller* than the 7,175 it peaked at while gaining all 23 judgments: the BNS
trim paid for most of the case law.

### Rebuilding

`backend/vectorstore/` is git-ignored. After pulling:

```bash
cd backend
python ingest.py            # re-embeds the committed parsed chunks (~4 min for 6,697)
```

Only if you change a PDF or the manifest:

```bash
python ingest.py --parse-only   # re-parses PDFs -> parsed/legal_chunks.jsonl
python ingest.py                # then re-embeds
python audit_ingestion.py       # quality check
```

---

## 8. Limitations

Ordered roughly by how much they matter.

**One source format only.** All 23 judgments are Indian Kanoon exports. The footer stripping,
citation-block removal and numbering heuristics are calibrated to that format. A judgment from the
official Supreme Court site, a High Court PDF, or anything scanned would likely parse poorly or
not at all. **There is no OCR** — `document_extractor.py` detects scanned input but does not
handle it. This was a conscious decision: writing format handling for layouts nobody has in hand
means guessing at structures that cannot be verified.

**`good_law` describes the judgment, not the provisions it discusses.** Shreya Singhal is
`good_law: true` — correctly, the judgment stands — even though the section it struck down is
dead. Provision-level currency is handled separately and manually through `void_provisions`. A
struck-down provision nobody has noticed yet will not be flagged.

**Curated extract terms are hand-chosen.** For the four trimmed judgments the retained material
was verified to contain the main holdings, but there is no guarantee nothing important was
dropped. That check is open-ended by nature.

**Bare-identifier queries are still weak.** "section 66A" as a standalone query retrieves poorly —
MiniLM does not preserve distinctive identifier tokens well. Semantically richer phrasing works.
§5.1 fixed the *metadata* so identifier lookup is now possible, but no identifier-aware retrieval
path was built on top of it.

**Cyber MRR remains below the other domains** at 0.633 against 1.000 for tenancy and
constitutional. Judgments still sometimes sit above the governing provision inside the top 5.
Arguably correct behaviour, but it is a real difference.

**One mangled chunk in Puttaswamy.** A diagram extracted as word soup. It rides inside an
otherwise-valid page unit. Word soup is unlikely to rank for real questions, so it was left.

**A known upstream limitation is untouched:** `detect_domain_signals()` returns a zero score for
some plainly cyber phrasings such as "rights after online payment fraud", so those queries never
reach the cyber-specific candidate-depth widening. Recorded in the changelog by a teammate; not
addressed here.

**`requirements.txt` is stale for Python 3.13.** The pinned `faiss-cpu==1.8.0.post1` and
`numpy==1.26.4` have no wheels. This work ran on faiss-cpu 1.15, numpy 2.3, torch 2.14,
sentence-transformers 6.0. Separately, `docxtpl` is listed but not installed in this environment,
which makes 13 test modules fail to import — unrelated to anything here.

---

## 9. Where to pick this up

Roughly in order of value for effort.

**1. Update the `cyber_07` eval expectation.** Smallest useful change. Widen
`eval/retrieval_queries.json` to accept the DPDP Act *or* Rules, then the suite is clean at
Hit@5 97.2%. See §2.

**2. Add the POSH Act 2013.** Vishaka is in the corpus and flagged as superseded by it, but the
Act itself is missing — so a workplace-harassment question currently has no current law to land
on. One PDF plus a manifest entry.

**3. Make something enforce `good_law`.** The plumbing now exists and the prompt carries a
`CURRENCY_WARNING`, but nothing *prevents* a struck-down provision being cited. `claim_verifier.py`
is the natural place: reject a claim whose only source is a chunk flagged not-current.

**4. Identifier-aware retrieval.** §5.1 made provision metadata correct, so a query naming
"section 66A" or "s.43A" can now be matched against `section_number` directly rather than relying
on embeddings. This would close the bare-identifier gap and likely lift Provision Hit@5 above its
current 90.9%.

**5. Widen the eval set for case law.** `eval/retrieval_queries.json` has no case-law queries at
all — every case-law claim in this document rests on manual spot checks. Adding a handful per
domain would turn that into a measured number, and would catch a future regression in the judgment
parser the way the existing suite caught §5.2.

**6. Re-run the other evaluators.** Only `evaluate_retrieval.py` was re-run. The end-to-end,
grounded-answer and claim-verification evaluators need a Gemini key and were not exercised; their
recorded results predate case law being in the corpus.

**7. Constitution trimming — a judgment call, deliberately not made.** At 1,442 chunks it is the
largest document in the corpus, and much of it (state finance, official languages, boundaries) has
no bearing on legal aid. But it is the primary document of its own domain and almost any article
could be asked about. The `extract` mechanism from §6 would do it if wanted; the decision is
whose corpus it is.
