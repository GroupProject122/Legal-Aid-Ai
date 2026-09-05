# Required Legal Sources — Consumer & Cyber

Acquisition checklist for completing the `consumer` and `cyber` retrieval corpus
in `backend/documents/`. Derived from the gap analysis of the current corpus,
`backend/parsed/legal_chunks.jsonl`, and the eval reports in `backend/eval/`.

## What this is / is not

- **Is:** a to-download list. Each row names an authentic government document,
  where to get it, the filename/path it must be saved as, and its
  `corpus_manifest.json` metadata (see `required_sources.json` for paste-ready blocks).
- **Is not:** the documents themselves, and not a dataset to train on. These are
  primary legal texts that must be downloaded from official portals unchanged.

## Workflow per document

1. Download the PDF from the official source below.
2. Save it to the exact `target_path` (under `backend/documents/<domain>/`).
3. Add its block from `required_sources.json` into `backend/documents/corpus_manifest.json`
   (`documents` array; drop the `acquisition` sub-object).
4. After a batch: `cd backend && python ingest.py`, then
   `python audit_ingestion.py`, then re-run the eval suite.
5. Add matching cases to `backend/eval/retrieval_queries.json` and
   `backend/eval/final_end_to_end_cases.json` before trusting the numbers.

Official portals referenced (locate by document title; deep links change):

- **India Code** — https://www.indiacode.nic.in (central Acts + subordinate legislation)
- **MeitY** — https://www.meity.gov.in (IT Act rules)
- **CERT-In** — https://www.cert-in.org.in (s.70B directions)
- **RBI** — https://www.rbi.org.in → Notifications
- **NPCI** — https://www.npci.org.in → UPI → Circulars
- **Dept. of Consumer Affairs** — https://consumeraffairs.nic.in (CCPA guidelines, Legal Metrology)
- **BIS** — https://www.bis.gov.in
- **e-Daakhil** — https://edaakhil.nic.in
- **National Cyber Crime Reporting Portal** — https://cybercrime.gov.in → Resources
- **e-Gazette** — https://egazette.gov.in
- **Supreme Court judgments** — https://main.sci.gov.in/judgments

---

## P0 — Critical fix (re-source an existing file)

| Document | Why | Source | Target path |
|---|---|---|---|
| **Information Technology Act, 2000** (consolidated, as amended — must contain Chapter IX ss. 43–47 and Chapter XI ss. 65–74) | The current `cyber/information_technology_act_2000.pdf` is missing **s.43** (damage to computer / unauthorised access — civil liability) and **s.66** (computer-related offences). Parsed chunks jump from s.42 past s.43–45 and s.66/66A. Provision eval `unauthorized access to computer account` (expected 43, 66) fails: not in top-10 candidates. | India Code — "The Information Technology Act, 2000" (updated version with amendments) | `backend/documents/cyber/information_technology_act_2000.pdf` (replace) |

After replacing, verify: `grep -c '"section_number": "43"' backend/parsed/legal_chunks.jsonl` etc. for 43, 43A, 66, 66C, 66D, 66E after re-ingest.

---

## Consumer — documents to add

| P | Document | Type | Authority | Official source | Target path | Notes |
|---|---|---|---|---|---|---|
| P1 | **Consumer Protection (General) Rules, 2020** | rules | primary | India Code / consumeraffairs.nic.in | `backend/documents/consumer/consumer_protection_general_rules_2020.pdf` | 0 chunks reference "General Rules, 2020"; may be partly bundled in `cdrc_general_rules_2020.pdf` — verify before adding to avoid duplication. |
| P1 | **Legal Metrology Act, 2009** | statute | primary | India Code | `backend/documents/consumer/legal_metrology_act_2009.pdf` | MRP, net-quantity, mandatory declarations; only 2 incidental chunks today. |
| P1 | **Legal Metrology (Packaged Commodities) Rules, 2011** | rules | primary | consumeraffairs.nic.in (Legal Metrology division) / India Code | `backend/documents/consumer/legal_metrology_packaged_commodities_rules_2011.pdf` | Pre-packaged goods labelling, declarations, penalties. |
| P1 | **Sale of Goods Act, 1930** | supporting_contract_law | primary | India Code | `backend/documents/consumer/sale_of_goods_act_1930.pdf` | Implied conditions/warranties, title, delivery, caveat emptor exceptions. Mark `status: supporting_only`. |
| P2 | **Bureau of Indian Standards Act, 2016** | statute | primary | India Code / bis.gov.in | `backend/documents/consumer/bureau_of_indian_standards_act_2016.pdf` | Compulsory certification, product recall, standard marks. |
| P2 | **Guidelines for Prevention and Regulation of Greenwashing, 2024** (CCPA) | guidelines | official_guidance | consumeraffairs.nic.in | `backend/documents/consumer/greenwashing_guidelines_2024.pdf` | Newer CCPA unfair-practice instrument. |
| P2 | **Guidelines for Prevention of Misleading Advertisements in Coaching Sector, 2024** (CCPA) | guidelines | official_guidance | consumeraffairs.nic.in | `backend/documents/consumer/coaching_sector_ads_guidelines_2024.pdf` | Common complaint pattern (refund, false claims). |
| P2 | **IS 19000:2022 — Online Consumer Reviews** (BIS) | guidelines | official_guidance | bis.gov.in | `backend/documents/consumer/is_19000_2022_online_reviews.pdf` | Fake/paid reviews framework. Standard doc — access may require BIS login. |
| P2 | **Reserve Bank – Integrated Ombudsman Scheme, 2021** | scheme | official_guidance | rbi.org.in | `backend/documents/consumer/rbi_integrated_ombudsman_scheme_2021.pdf` | Deficiency in banking/payment services remedy route. |
| P2 | **Insurance Ombudsman Rules, 2017** | rules | primary | irdai.gov.in / e-Gazette / cioins.co.in | `backend/documents/consumer/insurance_ombudsman_rules_2017.pdf` | Insurance claim-repudiation disputes. |
| P2 | **e-Daakhil user manual / consumer-commission filing guide** | procedural_user_guide | procedural_guide | edaakhil.nic.in | `backend/documents/consumer/edaakhil_user_manual.pdf` | 0 chunks say "e-Daakhil" or "pecuniary jurisdiction"; "how/where to file" is currently ungroundable. |

Note: pecuniary jurisdiction post-2021 is in `jurisdiction_rules_2021.pdf` (already present) — confirm it parsed (see `audit_ingestion.md`: fallback-heavy consumer procedure docs).

---

## Cyber — documents to add

| P | Document | Type | Authority | Official source | Target path | Notes |
|---|---|---|---|---|---|---|
| P1 | **Digital Personal Data Protection Act, 2023** | statute | primary | India Code | `backend/documents/cyber/digital_personal_data_protection_act_2023.pdf` | You hold only the **2025 Rules**; the Act appears as 3 incidental mentions. Listed in manifest `missing_expected_documents`. |
| P1 | **IT (Reasonable Security Practices and Procedures and Sensitive Personal Data or Information) Rules, 2011** | rules | primary | MeitY | `backend/documents/cyber/it_spdi_rules_2011.pdf` | s.43A body-corporate data-security duties; still operative. |
| P1 | **IT (Procedure and Safeguards for Blocking for Access of Information by Public) Rules, 2009** | rules | primary | MeitY | `backend/documents/cyber/it_blocking_rules_2009.pdf` | Lawful takedown/blocking process. |
| P1 | **IT (Procedure and Safeguards for Interception, Monitoring and Decryption) Rules, 2009** | rules | primary | MeitY | `backend/documents/cyber/it_interception_rules_2009.pdf` | Lawful interception safeguards. `retrieval_priority: low`. |
| P1 | **IT (The Indian Computer Emergency Response Team and Manner of Performing Functions and Duties) Rules, 2013** | rules | primary | MeitY / cert-in.org.in | `backend/documents/cyber/cert_in_rules_2013.pdf` | CERT-In statutory functions. |
| P1 | **CERT-In Directions under s.70B(6), dated 28 April 2022** | directions | primary | cert-in.org.in | `backend/documents/cyber/cert_in_directions_2022.pdf` | 6-hour incident reporting, log retention. 0 chunks say "CERT-In". Listed in manifest `missing_expected_documents`. |
| P1 | **RBI – Customer Protection: Limiting Liability of Customers in Unauthorised Electronic Banking Transactions (2017)** | circular | official_guidance | rbi.org.in (Notification DBR.No.Leg.BC.78/09.07.005/2017-18, 06-Jul-2017) | `backend/documents/cyber/rbi_limiting_liability_unauthorised_transactions_2017.pdf` | Zero / limited liability windows for online payment fraud. Currently **nothing** on this — the #1 cyber query type. |
| P1 | **RBI – Master Direction on Digital Payment Security Controls (2021)** | master_direction | official_guidance | rbi.org.in (18-Feb-2021) | `backend/documents/cyber/rbi_digital_payment_security_controls_2021.pdf` | Bank obligations, fraud monitoring. |
| P2 | **NPCI – UPI Procedural Guidelines / dispute redressal & chargeback rules** | procedural_guide | procedural_guide | npci.org.in → UPI → Circulars | `backend/documents/cyber/npci_upi_procedural_guidelines.pdf` | 0 chunks say "chargeback". Dispute-raising path for UPI fraud. |
| P2 | **National Cyber Crime Reporting Portal — citizen SOP / category guide (latest)** | procedural_user_guide | procedural_guide | cybercrime.gov.in → Resources | `backend/documents/cyber/cybercrime_portal_citizen_manual_latest.pdf` | Updates the 2019 women/children manual already present; covers financial-fraud + 1930 flow. |
| P2 | **IT (Intermediary Guidelines and Digital Media Ethics Code) Amendment Rules, 2022 & 2023** | amendment_rules | primary | MeitY | `backend/documents/cyber/it_intermediary_amendment_rules_2022_2023.pdf` | Base 2021 rules present; amendments (grievance appellate committees, due-diligence changes) are not. |
| P2 | **Bharatiya Nyaya Sanhita, 2023 — cyber-relevant extract** | supporting_criminal_law | primary | derive from existing `cyber/bharatiya_nyaya_sanhita_2023.pdf` | `backend/documents/cyber/bns_2023_cyber_extract.pdf` | Curate ~ss. 77 (voyeurism), 78 (stalking), 294/296 (obscene), 318 (cheating), 319 (personation), 336–340 (forgery), 351 (criminal intimidation), 356 (defamation). Replace the 665-chunk full dump to cut retrieval noise. |

---

## P3 — Case law (needs the judgment parser + OCR; do after statutes)

Save under `backend/documents/<domain>/case_law/`. Each needs manifest fields
`document_type: case_law`, `court`, `citation`, `date`, `good_law: true`.

**Cyber**
- Shreya Singhal v. Union of India, (2015) 5 SCC 1 — s.66A void, s.69A upheld, safe-harbour reading.
- K.S. Puttaswamy v. Union of India, (2017) 10 SCC 1 — privacy a fundamental right.
- Anuradha Bhasin v. Union of India, (2020) 3 SCC 637 — internet-shutdown proportionality.
- Selected High Court NCII / "right to be forgotten" takedown orders (curate 3–5).

**Consumer**
- Indian Medical Association v. V.P. Shantha, (1995) 6 SCC 651 — services incl. medical.
- Lucknow Development Authority v. M.K. Gupta, (1994) 1 SCC 243 — deficiency, compensation.
- Experion Developers v. Sushma Ashok Shiroor, (2022) — builder-delay refund.
- Rohit Chaudhary v. Vipul Ltd, (2023) — "commercial purpose" test.
- Selected NCDRC orders on e-commerce non-delivery, airline cancellation, banking deficiency (curate 5–10).

Source: main.sci.gov.in/judgments; NCDRC at ncdrc.nic.in (confonet); indiankanoon.org as a locator only (cite the official report).

---

## Non-document work also required for real-world accuracy

These are code/pipeline fixes, not files — tracked here so the corpus work isn't
mistaken for "done". Detail is in the project discussion; summary:

- **Ingestion hygiene** (`backend/ingest.py`): strip recurring headers/footers
  ("MINISTRY OF CONSUMER AFFAIRS…", gazette boilerplate); merge sub-40-char
  fragments (367 tiny chunks today); add parser patterns for the fallback-heavy
  docs — cyber portal manual (70% fallback), consumer procedure regulations (33%),
  e-commerce amendment rules (50%).
- **OCR fallback** in `backend/document_extractor.py` + ingest path (currently
  detected-not-implemented) — several P1 items are scanned PDFs.
- **Judgment parser family** in `ingest.py` for the P3 case law.
- **Router cues** (`backend/domain_router.py`): add SIM swap, chargeback,
  unauthorised transaction, data-breach notification, loan-app harassment,
  sextortion, deepfake/morphed (cyber); MRP, net quantity, expired product,
  recall, e-Daakhil, coaching refund (consumer).
- **Retrieval relevance floor** (`backend/rag.py`): return empty when nothing
  clears a minimum score, so non-legal queries abstain cleanly instead of
  surfacing the Constitution as a source.
- **Grounded-answer prompt** (`backend/grounded_answer.py`): never cite IT Act
  s.66A (struck down); separate civil s.43/43A from criminal s.66/66C/66D; state
  RBI limited-liability framework only when that circular is retrieved.
- **Corpus-gap** (`backend/corpus_gap.py`): mark out-of-corpus cyber categories
  (betting apps, piracy, cyberterrorism, ransomware-specific, predatory loan
  apps) as `missing_primary_authority` → abstain rather than answer from thin
  retrieval.
- **Eval expansion** (`backend/eval/`): add cyber/consumer provision-labelled
  retrieval queries and end-to-end cases for every source added above.
