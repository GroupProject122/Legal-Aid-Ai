# datasetcybernconsumer

Working / staging area for expanding the **cyber** and **consumer** legal corpora.
This is source-tracking, not the live corpus — the live corpus is `backend/documents/`.

## Layout

| Path | What it is |
|---|---|
| `cyber/` | Cyber legal-source PDFs collected for the corpus (statutes, rules, RBI/NPCI/CERT-In instruments, portal manuals) + 6 case-law PDFs (`case1`–`case6`) + `SOURCES_TO_UPLOAD.md` (the final acquisition record with links). |
| `consumer/` | Placeholder — consumer sources not started yet. |
| `test/` | Synthetic cyber Q&A / scenario dataset (1,000-row + 30-row, JSON + CSV) — candidate router / abstention **evaluation** set. Not training data, not ingested. See `test/30 row .../description.docx` for its design note. |
| `REQUIRED_SOURCES.md` | Full acquisition checklist for cyber **and** consumer, human-readable. |
| `required_sources.json` | Same list, machine-readable — `corpus_manifest.json`-ready metadata blocks. |

## Relationship to `backend/`

The cyber PDFs in `cyber/` (except `12_04_2021_Jorawer_..._on_12_October_2022.PDF`, a known-wrong
document kept for reference) were copied into `backend/documents/cyber/` and wired into
`backend/documents/corpus_manifest.json`. Case-law PDFs were copied to
`backend/documents/cyber/case_law/` but are **not** ingested yet (they await a judgment parser;
tracked under `pending_case_law` in the manifest).

Files here are intentionally kept as-is even after being copied to `backend/`, so the collection
and its provenance stay visible.
