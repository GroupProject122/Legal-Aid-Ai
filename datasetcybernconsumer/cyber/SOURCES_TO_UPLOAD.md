# Cyber corpus — FINAL

Status: **acquired and wired into `backend/documents/cyber/` + `corpus_manifest.json`.**
This folder (`datasetcybernconsumer/cyber/`) is the staging copy and is kept as-is.

## Active retrieval sources — in `backend/documents/cyber/` and in manifest `documents`

| File | document_type | authority | priority | notes |
|---|---|---|---|---|
| `information_technology_act_2000.pdf` | statute | primary | high | already in corpus, unchanged (byte-identical to the downloaded copy) |
| `it_intermediary_guidelines_digital_media_ethics_code_rules_2021.pdf` | rules | primary | high | already in corpus |
| `digital_personal_data_protection_rules_2025.pdf` | rules | primary | medium | already in corpus |
| `digital_personal_data_protection_act_2023.pdf` | statute | primary | high | **new** |
| `it_spdi_rules_2011.pdf` | rules | primary | medium | **new** — s.43A data-security duties |
| `it_blocking_rules_2009.pdf` | rules | primary | medium | **new** — s.69A takedown process |
| `it_interception_rules_2009.pdf` | rules | primary | low | **new** — s.69 safeguards |
| `cert_in_directions_2022.pdf` | rules | primary | medium | **new** — 6-hr incident reporting |
| `rbi_limiting_liability_unauthorised_transactions_2017.pdf` | guidelines | official_guidance | high | **new** — zero/limited liability for payment fraud |
| `it_intermediary_amendment_rules_2023.pdf` | amendment_rules | primary | medium | **new** — 2022 amendment still missing |
| `npci_upi_procedural_guidelines.pdf` | procedural_user_guide | procedural_guide | medium | **new** — mirror copy, verify version/date |
| `cybercrime_portal_citizen_manual_latest.pdf` | procedural_user_guide | procedural_guide | low | **new** — supplements the 2019 manual |
| `sanchar_saathi_ceir_user_manual.pdf` | procedural_user_guide | procedural_guide | low | **new** — lost phone / SIM-swap / fraud reporting |
| `national_cybercrime_reporting_portal_user_manual_2019.pdf` | procedural_user_guide | procedural_guide | low | already in corpus |
| `bharatiya_nyaya_sanhita_2023.pdf` | supporting_criminal_law | primary | low | kept as supporting; candidate for a curated cyber-sections extract |

## Archived (removed from active retrieval)

| File | Reason |
|---|---|
| `archive/bharatiya_nagarik_suraksha_sanhita_2023.pdf` | ~1,128 noise chunks of criminal procedure; no grounding value for cyber legal-information queries. Manifest entry moved to `archived_documents`. |

## Case law — staged, NOT ingested

In `backend/documents/cyber/case_law/`, tracked in manifest `pending_case_law`. Excluded from `ingest.py`
because judgments need a dedicated parser (headnote / holding / ratio) + good-law metadata.

| File | Case | Citation | Court |
|---|---|---|---|
| `case1_shreya_singhal_v_union_of_india_2015.pdf` | Shreya Singhal v. Union of India | (2015) 5 SCC 1 | SC |
| `case2_ks_puttaswamy_v_union_of_india_2017.pdf` | Justice K.S. Puttaswamy (Retd) v. Union of India | (2017) 10 SCC 1 | SC (9-judge) |
| `case3_anuradha_bhasin_v_union_of_india_2020.pdf` | Anuradha Bhasin v. Union of India | (2020) 3 SCC 637 | SC |
| `case4_mrs_x_v_union_of_india_2023_ncii.pdf` | Mrs X v. Union of India | 2023:DHC:2806 | Delhi HC |
| `case5_subhranshu_rout_v_state_of_odisha_2020_rtbf.pdf` | Subhranshu Rout @ Gugul v. State of Odisha | 2020 SCC OnLine Ori 878 | Orissa HC |
| `case6_sharat_babu_digumarti_v_nct_delhi_2016.pdf` | Sharat Babu Digumarti v. Govt (NCT of Delhi) | (2017) 2 SCC 18 | SC |

## Not added (deliberate)

| Item | Reason |
|---|---|
| RBI Master Direction on Digital Payment Security Controls, 2021 | Bank/PSO compliance direction, not consumer rights; status murky. |
| CERT-In Rules, 2013 | The 2022 Directions carry the operative incident-reporting content. |
| IT Intermediary Amendment Rules, 2022 | The 2023 amendment is the significant one; 2022 tracked in `missing_expected_documents`. |
| `12_04_2021_Jorawer_Singh_Mundy_..._on_12_October_2022.PDF` (still in this folder) | Wrong document — a 12 Oct 2022 case-management order with no holding. Not copied to backend. |

## Optional future additions

- Jorawer Singh Mundy v. Union of India — the actual **12.04.2021** de-indexing order (casemine / SFLC), if the RTBF angle needs strengthening.
- The Promotion and Regulation of Online Gaming Act, 2025 — if betting/gambling-app queries are in scope.
- The Bharatiya Sakshya Adhiniyam, 2023 — s.63 electronic-evidence certificate (supporting).
- IT Intermediary Amendment Rules, 2022.

## Pending pipeline work (not a file task)

1. `bns_2023_cyber_extract.pdf` — curated section extract to replace the full BNS.
2. Judgment parser family in `ingest.py` → then move `pending_case_law` into `documents`.
3. IT Act parsing fix — ss. 43–47 and 65–66A currently merge into adjacent chunks (section-boundary
   detection issue in `ingest.py`); the PDF text is complete.
4. Re-run `python ingest.py` + `python audit_ingestion.py` after the above.
