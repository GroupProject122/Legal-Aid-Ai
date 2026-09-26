# Backend structure map

Navigation aid only — no files were renamed or moved to produce this. It groups what's
already there and marks what was added in the recent corpus-expansion work (cyber →
consumer → tenancy/cyber follow-ups → consumer case law), so it's clear what's new vs.
what was already in the repo. See [`CHANGELOG.md`](../CHANGELOG.md) at the repo root for
the full chronological account of *why* each addition happened.

## 1. Code — grouped by what it does

```
backend/
├── main.py                          FastAPI app entrypoint — wires all routes
├── config.py                        env / provider config (LLM_PROVIDER, embedding model, etc.)
│
├── RAG pipeline (a question's path from input to answer)
│   ├── domain_router.py             classifies a query into consumer/cyber/tenancy/constitutional
│   ├── clarification.py             asks a follow-up when the query is ambiguous
│   ├── fact_sufficiency.py          checks whether enough facts were given to answer
│   ├── rag.py                       retrieval — embeds the query, searches vectorstore/
│   ├── grounded_answer.py           generates the answer strictly from retrieved chunks
│   ├── claim_verifier.py            checks generated claims are actually supported by context
│   ├── corpus_gap.py                detects when the corpus has no authority for the topic
│   │                                 (keyword-based; this is where "judgment in" / "held in" /
│   │                                 "precedent" are flagged as case-law questions — see §4)
│   ├── conversation_state.py        multi-turn conversation/session state; sorts each follow-up
│   │                                 (question / fact / correction / new issue / thanks) --
│   │                                 keyword rules give a hint, Gemini decides
│   └── turn_memory.py               correction memory: records rules-vs-Gemini disagreements
│                                     (redacted, pending review), reuses them as examples and,
│                                     once approved, as a no-Gemini shortcut. Own table in
│                                     legal_aid.db -- never in the legal vectorstore
│                                     Review with: python review_turn_corrections.py
│
├── Document tools (user-uploaded documents, separate from the legal corpus)
│   ├── document_extractor.py        extracts text from an uploaded .pdf/.docx/.txt
│   ├── document_store.py            persists uploaded documents
│   ├── document_facts.py            pulls structured facts out of an uploaded document
│   ├── document_summarizer.py       summarizes an uploaded document
│   └── case_store.py                stores a user's case/session record
│
├── Legal education
│   ├── legal_education.py
│   └── legal_education_config.py
│
├── Corpus ingestion (turns documents/*.pdf into the searchable index)
│   ├── ingest.py                    THE pipeline: parse PDFs → legal_chunks.jsonl → embed → vectorstore/
│   │                                 (--parse-only re-parses; no flag re-embeds the frozen chunks)
│   ├── audit_ingestion.py           quality-checks parsed/legal_chunks.jsonl, writes parsed/ingestion_audit.*
│   └── diagnose_provision_regression.py   debugging aid for provision-level retrieval regressions
│
├── Evaluation harness (15 evaluate_*.py files, one per pipeline stage)
│   ├── evaluate_retrieval.py, evaluate_domain_router.py, evaluate_clarification.py,
│   │   evaluate_fact_sufficiency.py, evaluate_grounded_answer.py, evaluate_claim_verification.py,
│   │   evaluate_corpus_gap.py, evaluate_conversation_state.py, evaluate_document_extraction.py,
│   │   evaluate_document_facts.py, evaluate_document_fact_integration.py,
│   │   evaluate_document_summarization.py, evaluate_manual_regression.py,
│   │   evaluate_final_end_to_end.py
│   └── eval/                        82 files — input cases + recorded results per evaluator above
│
├── tests/                           23 pytest files, one per module above (test_ingest.py, etc.)
│
├── requirements.txt, .env.example   dependency pins (stale for Python 3.13 — see CHANGELOG) / env template
│
└── Data (see §2, §3 below)
    ├── documents/                   the legal corpus — source PDFs + corpus_manifest.json
    ├── parsed/                      generated: legal_chunks.jsonl, parse_summary.json, ingestion_audit.*
    ├── vectorstore/                 generated, git-ignored: index.faiss, metadata.json — rebuild with ingest.py
    └── user_uploads/                runtime storage for user-uploaded documents (document_store.py)
```

## 2. `documents/` — the legal corpus, by domain

`✚ new` = added in the recent corpus-expansion work. Everything else pre-dates it (either
original corpus or added by a teammate in the same period — see `CHANGELOG.md` for which).
Filenames are exactly as they are in the repo; nothing here was renamed.

```
documents/
├── corpus_manifest.json             the index: every document's metadata, extract configs, void_provisions
│
├── consumer/                        18 active + case_law/ (4 judgments, indexed) = 22 files
│   ├── consumer_protection_act_2019.pdf
│   ├── cdrc_general_rules_2020.pdf
│   ├── consumer_commission_procedure_regulations_2020.pdf
│   ├── ecommerce_rules_2020.pdf
│   ├── ecommerce_amendment_rules_2021.pdf
│   ├── jurisdiction_rules_2021.pdf
│   ├── mediation_rules_2020.pdf
│   ├── direct_selling_rules_2021.pdf
│   ├── misleading_ads_guidelines_2022.pdf
│   ├── dark_patterns_guidelines_2023.pdf
│   ├── legal_metrology_act_2009.pdf                        ✚ new
│   ├── legal_metrology_packaged_commodities_rules_2011.pdf ✚ new
│   ├── sale_of_goods_act_1930.pdf                          ✚ new
│   ├── bureau_of_indian_standards_act_2016.pdf              ✚ new
│   ├── insurance_ombudsman_rules_2017.pdf                   ✚ new
│   ├── rbi_integrated_ombudsman_scheme_2021.pdf             ✚ new
│   ├── greenwashing_guidelines_2024_summary.pdf             ✚ new — compiled summary, not verbatim text (see manifest notes)
│   ├── coaching_sector_ads_guidelines_2024_summary.pdf      ✚ new — compiled summary, not verbatim text (see manifest notes)
│   └── case_law/                                            ✚ indexed — see §3
│       ├── case1_indian_medical_association_v_vp_shantha_1995.pdf
│       ├── case2_lucknow_development_authority_v_mk_gupta_1994.pdf
│       ├── case3_experion_developers_v_sushma_ashok_shiroor_2022.pdf
│       └── case4_rohit_chaudhary_v_vipul_ltd_2023.pdf
│
├── cyber/                           16 active + case_law/ (6 judgments, indexed) = 22 files
│   ├── information_technology_act_2000.pdf
│   ├── it_intermediary_guidelines_digital_media_ethics_code_rules_2021.pdf
│   ├── digital_personal_data_protection_rules_2025.pdf
│   ├── national_cybercrime_reporting_portal_user_manual_2019.pdf
│   ├── bharatiya_nyaya_sanhita_2023.pdf                     (supporting only — ingested as a 30-section curated extract, see §3)
│   ├── digital_personal_data_protection_act_2023.pdf        ✚ new
│   ├── it_spdi_rules_2011.pdf                               ✚ new
│   ├── it_blocking_rules_2009.pdf                           ✚ new
│   ├── it_interception_rules_2009.pdf                       ✚ new
│   ├── cert_in_directions_2022.pdf                          ✚ new
│   ├── rbi_limiting_liability_unauthorised_transactions_2017.pdf ✚ new
│   ├── it_intermediary_amendment_rules_2023.pdf             ✚ new
│   ├── it_intermediary_amendment_rules_2022.pdf             ✚ new
│   ├── npci_upi_procedural_guidelines.pdf                   ✚ new
│   ├── cybercrime_portal_citizen_manual_latest.pdf          ✚ new
│   ├── sanchar_saathi_ceir_user_manual.pdf                  ✚ new
│   └── case_law/                                            ✚ indexed — see §3
│       ├── case1_shreya_singhal_v_union_of_india_2015.pdf
│       ├── case2_ks_puttaswamy_v_union_of_india_2017.pdf
│       ├── case3_anuradha_bhasin_v_union_of_india_2020.pdf
│       ├── case4_mrs_x_v_union_of_india_2023_ncii.pdf
│       ├── case5_subhranshu_rout_v_state_of_odisha_2020_rtbf.pdf
│       └── case6_sharat_babu_digumarti_v_nct_delhi_2016.pdf
│
├── tenancy/                         9 files (Delhi-scoped) + case_law/ (5 judgments, indexed)
│   ├── delhi_rent_control_act_1958.pdf
│   ├── delhi_rent_control_rules_1959.pdf
│   ├── delhi_rent_act_1995.pdf               (never brought into force — status: manual_verification_required, excluded from ingest)
│   ├── transfer_of_property_act_1882.pdf
│   ├── registration_act_1908.pdf
│   ├── indian_easements_act_1882.pdf         (teammate-added)
│   ├── slum_areas_improvement_and_clearance_act_1956.pdf  (teammate-added)
│   ├── specific_relief_act_1963.pdf          (teammate-added)
│   └── indian_stamp_act_1899.pdf             ✚ new — stamp duty on rent/lease agreements
│
├── constitutional_public_authority/  16 files + case_law/ (8 judgments, indexed)
│   ├── constitution_of_india.pdf
│   ├── right_to_information_act_2005.pdf
│   ├── legal_services_authorities_act_1987.pdf
│   ├── protection_of_human_rights_act_1993.pdf
│   ├── contempt_of_courts_act_1971.pdf
│   └── (11 more — all teammate-added: administrative_tribunals_act_1985, prevention_of_corruption_act_1988,
│       lokpal_and_lokayuktas_act_2013, right_to_education_act_2009, rights_of_persons_with_disabilities_act_2016,
│       maintenance_and_welfare_of_parents_and_senior_citizens_act_2007,
│       commissions_for_protection_of_child_rights_act_2005, rti_rules_2012,
│       nalsa_free_and_competent_legal_services_regulations_2010, nalsa_legal_services_clinics_regulations_2011,
│       nalsa_lok_adalats_regulations_2009)
│
└── archive/                          2 files — excluded from ingest.py (source_file starts "archive/")
    ├── bharatiya_nagarik_suraksha_sanhita_2023.pdf   (BNSS — moved here, was pure retrieval noise)
    └── indian_stamp_act_1899_uttarakhand.pdf         (state-specific, superseded by tenancy/indian_stamp_act_1899.pdf)
```

## 3. Case law — live in the retrieval index

**23 judgments, 2,186 chunks** (cyber 6, consumer 4, tenancy 5, constitutional 8), parsed by
`parse_case_law_document()` and part of the active index. `pending_case_law` is now an empty
staging slot for any future judgment collected before it is ready to ingest.

Full detail — parser design, accuracy, parameters, limitations, next steps — is in
[`docs/CASE_LAW_AND_CORPUS_CURRENCY.md`](docs/CASE_LAW_AND_CORPUS_CURRENCY.md).

## 4. Where case law shows up in the running code

- `ingest.py` — `parse_case_law_document()`, two-mode segmentation (paragraph / page-level prose),
  plus `select_extract_units()` for curated extracts of the very long judgments.
- `rag.py` — `CASE_LAW_SUBSTANTIVE_PENALTY` keeps judgments alongside rather than ahead of the
  provision they interpret, skipped when the question is itself about case law.
- `grounded_answer.py` — `currency_warning()` emits a `CURRENCY_WARNING` line for material that is
  not current law, with a matching system-prompt rule.
- `corpus_gap.py` — the case-law abstain gate now fires only when retrieval surfaced no case-law
  source, rather than refusing every case-law-shaped question as it did before ingestion.

## 5. Staging area (outside `backend/`)

`datasetcybernconsumer/` at the repo root holds the source/staging copies of everything added to
`backend/documents/` above (kept intentionally, per-file provenance), plus the acquisition
checklists (`REQUIRED_SOURCES.md`, `required_sources.json`, `cyber/SOURCES_TO_UPLOAD.md`) and a
synthetic cyber Q&A eval-candidate set under `test/`. See its own `README.md`.
