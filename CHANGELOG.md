# Changelog

Notable changes to Legal Aid AI. Newest first. Frontend-only detail also lives in
[`frontend/CHANGELOG.md`](frontend/CHANGELOG.md).

> **Known corpus caveat (consumer)** — two CCPA instruments have no official machine-readable
> source (only scanned-image PDFs exist and no OCR was run), so they are in the corpus as
> **compiled summaries**, not verbatim law:
> - `consumer/greenwashing_guidelines_2024_summary.pdf` — Guidelines for Prevention and Regulation
>   of Greenwashing or Misleading Environmental Claims, 2024
> - `consumer/coaching_sector_ads_guidelines_2024_summary.pdf` — Guidelines for Prevention of
>   Misleading Advertisement in Coaching Sector, 2024
>
> Each is compiled from the CCPA's official notification announcement + PIB press releases, with
> a `COMPILED SUMMARY — NOT THE OFFICIAL VERBATIM TEXT` disclaimer as the first line of the
> document itself, and `authority_level: "secondary_summary"` / `status:
> "compiled_summary_pending_official_text"` in the manifest so retrieval and citation code can
> tell them apart from primary sources. Replace with the official Gazette text (or an OCR'd scan)
> if either becomes available.
>
> **Skipped, deliberately:** e-Jagriti filing user manual. Unlike the two guidelines above, a
> "how to file" walkthrough is step-by-step UI instruction on a portal that only launched
> 1 Jan 2025 and is still actively changing — a compiled secondary-source summary risks being
> wrong about live steps, which actively misleads a user filing a real case. Left out rather than
> risk that.

## Unreleased — corpus completion round (Stamp Act, 2022 IT amendment, CCPA summaries)

Closes the remaining gaps identified after the teammate pull (`91dba0d`/`19ca62d`) that added
constitutional/public-authority and tenancy statutes.

**Added:**

| File | Domain | Type | Why |
|---|---|---|---:|
| `tenancy/indian_stamp_act_1899.pdf` | tenancy | statute | Schedule I Article 35 (Lease) — stamp duty on rent/lease agreements. Delhi has no separate Stamp Act; the central Act applies. Distinct from the archived Uttarakhand-specific copy. 178 chunks, 99% structure-aware. |
| `cyber/it_intermediary_amendment_rules_2022.pdf` | cyber | amendment_rules | G.S.R. 794(E), 28 Oct 2022 — Grievance Appellate Committees, updated terms-of-use/privacy-policy duties. Fills the gap between the 2021 base rules and the 2023 amendment already in the corpus. 6 chunks. |
| `consumer/greenwashing_guidelines_2024_summary.pdf` | consumer | guidelines (compiled summary — see caveat above) | 9 chunks |
| `consumer/coaching_sector_ads_guidelines_2024_summary.pdf` | consumer | guidelines (compiled summary — see caveat above) | 10 chunks |

`missing_expected_documents`: the 2022 Intermediary Amendment entry removed (resolved). Model
Tenancy Act, 2021 stays flagged — not operative in Delhi, so treated as optional context rather
than a real gap.

**Re-parse + re-embed + audit:**

| | Before this round | After |
|---|---:|---:|
| Documents | 56 (post teammate pull) | 58 |
| Total chunks | 4,694 | 4,989 |
| Audit | PASS, HIGH=0 | PASS, HIGH=0, MEDIUM=92, LOW=3 |

Retrieval-tested: Stamp Act's Lease article ranks top-3 for on-topic stamp-duty queries; the 2022
amendment ranks #2 for a Grievance Appellate Committee query; both CCPA summaries rank #1 for
on-topic queries (greenwashing claim, coaching-institute refund/rank dispute).

## Unreleased — consumer case law staged

Adds 4 Supreme Court judgments to `backend/documents/consumer/case_law/`, tracked in the
manifest's `pending_case_law` array (now 10 entries: 6 cyber + 4 consumer). **Not in the active
retrieval index** — same reason as the 6 cyber judgments: `ingest.py` has no judgment parser
(`case_law` is not a supported `document_type`), and `pending_case_law` entries are never read by
`ingest.py`'s document discovery (confirmed: it only iterates the `documents` array). No
re-parse/re-embed needed for this change.

| File | Case | Citation | Holds |
|---|---|---|---|
| `case1_indian_medical_association_v_vp_shantha_1995.pdf` | Indian Medical Association v. V.P. Shantha | (1995) 6 SCC 651 | Medical services for consideration are "service" under the Act — negligence complaints are maintainable before consumer fora |
| `case2_lucknow_development_authority_v_mk_gupta_1994.pdf` | Lucknow Development Authority v. M.K. Gupta | (1994) 1 SCC 243 | Statutory/development authorities are service providers; possession delay attracts compensation for harassment, not just refund |
| `case3_experion_developers_v_sushma_ashok_shiroor_2022.pdf` | Experion Developers Pvt. Ltd. v. Sushma Ashok Shiroor | Civil Appeal No. 6044 of 2019 (7 Apr 2022) | CPA and RERA remedies are concurrent; builder must refund with interest for delayed possession |
| `case4_rohit_chaudhary_v_vipul_ltd_2023.pdf` | Rohit Chaudhary v. M/S Vipul Ltd. | 2023 INSC 807 | Clarifies the "commercial purpose" exclusion (s.2(7)) — self-employment/livelihood purchases aren't automatically excluded; fact-specific test |

All 4 verified against Indian Kanoon before download (case name, court, date, citation match).
Staging copies in `datasetcybernconsumer/consumer/` kept as-is.

**Deliberately not collected:** curated NCDRC orders (e-commerce non-delivery, airline
cancellation, banking deficiency). Reasoning: NCDRC orders are fact-specific applications, not
precedent-setting like the SC cases above; no canonical shortlist exists so any selection would be
arbitrary; and citing a specific lower-forum order risks a user reading it as "my case must match
this one" rather than the general rule. The 4 SC cases already cover the load-bearing principles.

**Next step for case law (all domains):** none of the 10 staged judgments (6 cyber + 4 consumer)
are retrievable yet — needs the judgment parser built and validated first. Tenancy and
constitutional/public-authority have no case-law PDFs collected at all yet.

## Unreleased — consumer corpus expansion

Uncommitted working-tree change on `main`. Staging/source area:
[`datasetcybernconsumer/consumer/`](datasetcybernconsumer/consumer/) (kept as-is, mirrors the cyber round).

**Where it reflects:** `backend/documents/consumer/`, `backend/documents/corpus_manifest.json`,
`backend/parsed/*`. `backend/vectorstore/` is git-ignored — rebuild locally with
`cd backend && python ingest.py --parse-only && python ingest.py`.

**Added to `backend/documents/consumer/` (now in the active retrieval index):**

| File | Type | Why | Chunks |
|---|---|---|---:|
| `legal_metrology_act_2009.pdf` | statute | MRP as a ceiling, net-quantity/declaration duties, instrument verification, offences — basis for overcharging-above-MRP and short-weight complaints | 67 |
| `legal_metrology_packaged_commodities_rules_2011.pdf` | rules | Pre-packaged goods: mandatory label declarations, dual-MRP ban, permissible error, penalties | 126 |
| `sale_of_goods_act_1930.pdf` | statute (supporting) | Implied conditions/warranties, merchantable quality, passing of property/risk, buyer/seller remedies — contract-law backing for defective-goods reasoning | 67 |
| `bureau_of_indian_standards_act_2016.pdf` | statute | ISI / Standard Mark, compulsory certification for notified goods, hallmarking, product recall, penalties | 53 |
| `insurance_ombudsman_rules_2017.pdf` | rules | Remedy route for claim repudiation / delay / mis-selling; Ombudsman jurisdiction, procedure, award, limits (consolidated to the 18 May 2021 amendments) | 29 |
| `rbi_integrated_ombudsman_scheme_2021.pdf` | guidelines | Cost-free remedy for deficiency in banking / NBFC / digital-payment services; grounds unauthorised-transaction complaints. `cross_domain_relevance: ["cyber"]`. `document_type` is `guidelines` because `ingest.py` has no scheme parser (text unaffected) | 37 |

**Not added (already covered — kept in staging only):**

- `consumer_protection_act_2019.pdf` — already in the corpus.
- `consumer_protection_general_rules_2020.pdf` (G.S.R. 449(E)) — its full text is already inside
  `cdrc_general_rules_2020.pdf` (verified: "public utility service", "games of chance",
  "customer care number or e-mail" all present). Adding it would duplicate indexed content.
  A standalone PDF was still produced from the source `.txt` and left in the staging folder.

**`corpus_manifest.json`:** +6 consumer `documents` entries (full metadata), inserted after the
existing consumer block. `documents` total 35 → 41.

**Re-parse + re-embed:**

| | Before (cyber round) | After |
|---|---:|---:|
| Documents parsed | 34 | 40 |
| Total chunks | 3,695 | 4,074 |
| Consumer chunks | 297 | 676 |
| Structure-aware | 98.38% | 98.38% |
| Ingestion audit | PASS, HIGH=0, MEDIUM=84 | PASS, HIGH=0, MEDIUM=88, LOW=3 |

All 6 new docs parsed 96.5–99.2% structure-aware (1 fallback chunk each). The +4 MEDIUM are
benign `sequence_anomalies` in the Packaged Commodities Rules (rule numbering restarts per
chapter/schedule). Retrieval smoke test: MRP-overcharge → Packaged Commodities Rules 6/8/23;
missing net-quantity → Rules 6/12/21; rejected mediclaim → Insurance Ombudsman Rules 14/15/9.

---

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
