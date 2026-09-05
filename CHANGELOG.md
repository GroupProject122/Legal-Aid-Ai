# Changelog

Notable changes to Legal Aid AI. Newest first. Frontend-only detail also lives in
[`frontend/CHANGELOG.md`](frontend/CHANGELOG.md).

## Unreleased — branch `chore/move-frontend-folder`

Three independent pieces of work, all on this branch, not yet merged to `main`.

---

### Backend — cyber corpus expansion

**Where it reflects:** `backend/documents/cyber/`, `backend/documents/corpus_manifest.json`,
`backend/parsed/*`, and the staging area `datasetcybernconsumer/` (see its `README.md`).

**Added to `backend/documents/cyber/` (now in the active retrieval index):**

| File | Type | Why |
|---|---|---|
| `digital_personal_data_protection_act_2023.pdf` | statute | The DPDP **Act** (only the 2025 Rules were present before) |
| `it_spdi_rules_2011.pdf` | rules | Body-corporate data-security duties (IT Act s.43A) |
| `it_blocking_rules_2009.pdf` | rules | s.69A takedown/blocking process |
| `it_interception_rules_2009.pdf` | rules | s.69 interception safeguards |
| `cert_in_directions_2022.pdf` | rules | 6-hour cyber-incident reporting, log retention |
| `rbi_limiting_liability_unauthorised_transactions_2017.pdf` | guidelines | Zero/limited customer liability for payment fraud — previously **ungroundable** |
| `it_intermediary_amendment_rules_2023.pdf` | amendment_rules | 2023 amendment to the 2021 Intermediary Rules |
| `npci_upi_procedural_guidelines.pdf` | procedural_user_guide | UPI dispute-redressal / chargeback mechanics |
| `cybercrime_portal_citizen_manual_latest.pdf` | procedural_user_guide | Financial-fraud / SIM-swap / ransomware reporting + 1930 helpline |
| `sanchar_saathi_ceir_user_manual.pdf` | procedural_user_guide | Block a lost/stolen phone (CEIR), SIM verification (TAFCOP), fraud reporting (Chakshu) |

**Staged but NOT ingested** — `backend/documents/cyber/case_law/` (6 judgment PDFs, `case1`–`case6`:
Shreya Singhal, K.S. Puttaswamy, Anuradha Bhasin, Mrs X (NCII), Subhranshu Rout (RTBF), Sharat Babu
Digumarti). Tracked under `pending_case_law` in the manifest. Excluded from `ingest.py` because
judgments need a dedicated parser (headnote / holding / ratio) + good-law metadata.

**Removed from active retrieval** — `bharatiya_nagarik_suraksha_sanhita_2023.pdf` (BNSS) moved to
`backend/documents/archive/` and to `archived_documents` in the manifest. It was ~1,128 chunks of
criminal procedure that added retrieval noise without grounding cyber legal-information queries.
BNS (`bharatiya_nyaya_sanhita_2023.pdf`) is kept as supporting material, flagged for a future
curated cyber-sections extract.

**`corpus_manifest.json`:** +10 cyber `documents` entries (full metadata); BNSS → `archived_documents`;
new `pending_case_law` array + `pending_case_law_note`; `missing_expected_documents` refreshed
(DPDP Act and CERT-In Directions removed — now present; IT Intermediary Amendment Rules 2022 added).

**Re-parse + re-embed** (`python ingest.py --parse-only` then `python ingest.py`):

| | Before | After |
|---|---:|---:|
| Documents parsed | 25 | 34 |
| Total chunks | 4,388 | 3,695 |
| Cyber chunks | 2,089 (≈1,793 BNS+BNSS) | 1,396 (665 BNS + 731 substantive across 14 docs, up from ~296) |
| Structure-aware | 98.86% | 98.38% |
| Ingestion audit | PASS, MEDIUM=143 | PASS, MEDIUM=84 |

`backend/parsed/legal_chunks.jsonl`, `parse_summary.json`, `ingestion_audit.{json,md}` regenerated.
`backend/vectorstore/` is git-ignored — rebuild locally with `cd backend && python ingest.py --parse-only && python ingest.py`.

**Known issues (pre-existing, not blockers):**

1. IT Act ss. 43–47 and 65–66A: text is in the index but merged under the chunks tagged
   `section 42` and `section 65` — section-boundary detection in `ingest.py`'s statute parser
   misses those clusters. Semantic/lexical retrieval still finds them; provision-level metadata
   match on "s.66" does not.
2. Fallback-heavy new docs: `sanchar_saathi_ceir_user_manual` (6/6), `cert_in_directions_2022`
   (5/10) — acceptable for short prose; noted in the audit.
3. `requirements.txt` pins (`faiss-cpu==1.8.0.post1`, `numpy==1.26.4`) have no wheels for
   Python 3.13. Ran with `faiss-cpu 1.15`, `numpy 2.3`, `torch 2.14`, `sentence-transformers 6.0`,
   `google-genai 2.22`. `ingest.py` is unaffected; the API server (`rag.py`, `domain_router.py`,
   etc.) should be checked against `google-genai` 2.x before running the full app.

**`datasetcybernconsumer/`** — the staging/source-tracking area for this work: the collected PDFs,
the acquisition checklists (`REQUIRED_SOURCES.md`, `required_sources.json`,
`cyber/SOURCES_TO_UPLOAD.md`), and a synthetic cyber Q&A dataset under `test/` (candidate eval
set, not ingested). See `datasetcybernconsumer/README.md`.

---

### Frontend — move Vite app into `frontend/` (commit `5986070`)

**Where it reflects:** repo root → `frontend/`.

The root-level Vite app (`index.html`, `src/`, `public/`, `vite.config.js`, `package*.json`) moved
into `frontend/` so the repo has clean `frontend/` and `backend/` siblings. README "Run Frontend"
updated to `cd frontend && npm install && npm run dev`. No source or build-config changes; the
`/api` dev proxy is unchanged.

---

### Frontend — home page redesign (commit `25f425c`)

**Where it reflects:** `frontend/src/App.jsx`, `frontend/src/styles.css`, `frontend/CHANGELOG.md`.

Cleaner, flatter home page: rebuilt hero / search box / topic pills / feature cards; new
below-the-fold sections (Documents, Summarize, My Cases, Know Your Rights, Schemes) with jump-chip
nav, "How it works", privacy/help cards, topic marquee and footer; About Us and Schemes pages
filled in; a motion pass (masked hero reveal, scroll reveals, parallax, magnetic CTAs, custom
home-page cursor) all gated behind `prefers-reduced-motion` / pointer type. Full breakdown in
[`frontend/CHANGELOG.md`](frontend/CHANGELOG.md).
