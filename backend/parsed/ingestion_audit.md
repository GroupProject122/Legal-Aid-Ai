# Ingestion Audit Summary

## Overall Results
- Status: PASS WITH WARNINGS
- Total chunks checked: 6697
- Unique chunk IDs: 6697
- HIGH findings: 0
- MEDIUM findings: 96
- LOW findings: 3

## High-Priority Issues
- None found.

## Medium-Priority Issues
- 96 medium-priority finding(s), mainly review-scale quality signals.
- Large chunks over 8,000 characters: 0
- Exact duplicate text groups: 1
- Near-duplicate text groups: 14

## Low-Priority / Informational Findings
- Very short chunks under 40 characters: 10
- Review-candidate chunks from 40 to 100 characters: 268
- Suspicious recurring header/footer patterns: 14

## Documents Requiring Attention
- `cyber/sanchar_saathi_ceir_user_manual.pdf`: 6 fallback chunks (100.0%)
- `consumer/ecommerce_amendment_rules_2021.pdf`: 1 fallback chunks (50.0%)
- `cyber/cert_in_directions_2022.pdf`: 5 fallback chunks (50.0%)
- `consumer/consumer_commission_procedure_regulations_2020.pdf`: 13 fallback chunks (33.33%)

## Fallback Analysis
- Total fallback chunks: 95
- `cyber/sanchar_saathi_ceir_user_manual.pdf`: 6/6 fallback (100.0%)
- `consumer/ecommerce_amendment_rules_2021.pdf`: 1/2 fallback (50.0%)
- `cyber/cert_in_directions_2022.pdf`: 5/10 fallback (50.0%)
- `consumer/consumer_commission_procedure_regulations_2020.pdf`: 13/39 fallback (33.33%)
- `consumer/jurisdiction_rules_2021.pdf`: 1/6 fallback (16.67%)
- `cyber/it_intermediary_amendment_rules_2022.pdf`: 1/6 fallback (16.67%)
- `consumer/mediation_rules_2020.pdf`: 1/8 fallback (12.5%)
- `consumer/greenwashing_guidelines_2024_summary.pdf`: 1/9 fallback (11.11%)

## Largest Chunks
- `constitutional_public_authority_constitution_of_india__chunk_0270` in `constitutional_public_authority/constitution_of_india.pdf`: 2495 chars, article 4
- `constitutional_public_authority_constitution_of_india__chunk_0282` in `constitutional_public_authority/constitution_of_india.pdf`: 2474 chars, article 226
- `constitutional_public_authority_constitution_of_india__chunk_0153` in `constitutional_public_authority/constitution_of_india.pdf`: 2429 chars, article 124A
- `tenancy_delhi_rent_control_act_1958__chunk_0023` in `tenancy/delhi_rent_control_act_1958.pdf`: 2404 chars, section 14
- `constitutional_public_authority_constitution_of_india__chunk_0150` in `constitutional_public_authority/constitution_of_india.pdf`: 2385 chars, article 124
- `constitutional_public_authority_constitution_of_india__chunk_0152` in `constitutional_public_authority/constitution_of_india.pdf`: 2383 chars, article 4
- `constitutional_public_authority_constitution_of_india__chunk_0159` in `constitutional_public_authority/constitution_of_india.pdf`: 2335 chars, article 128
- `constitutional_public_authority_case_law_case6_sp_gupta_v_union_of_india_1981__chunk_0104` in `constitutional_public_authority/case_law/case6_sp_gupta_v_union_of_india_1981.pdf`: 2257 chars, judgment_segment 
- `constitutional_public_authority_case_law_case6_sp_gupta_v_union_of_india_1981__chunk_0107` in `constitutional_public_authority/case_law/case6_sp_gupta_v_union_of_india_1981.pdf`: 2253 chars, judgment_segment 
- `constitutional_public_authority_case_law_case6_sp_gupta_v_union_of_india_1981__chunk_0145` in `constitutional_public_authority/case_law/case6_sp_gupta_v_union_of_india_1981.pdf`: 2251 chars, judgment_segment 

## Duplicate / Noise Findings
- Exact duplicate groups: 1
- Near-duplicate groups: 14
- Recurring noise examples:
  - `MINISTRY OF CONSUMER AFFAIRS, FOOD AND PUBLIC DISTRIBUTION` (6 occurrences)
  - `(2) They shall come into force on the date of their publication in the Official Gazette.` (5 occurrences)
  - `(1)The Central Government may, by notification in the Official Gazette, make rules to carry out the` (3 occurrences)
  - `by order, published in the Official Gazette, make such provisions not inconsistent with the` (3 occurrences)
  - `4 Inserted vide notification dated 22/10/2018, published in the Gazette of India on 25/10/2018.` (3 occurrences)
  - `MINISTRY OF HOME AFFAIRS` (3 occurrences)
  - `publication in the Official Gazette.` (3 occurrences)
  - `by order published in the Official Gazette, make such provisions, not inconsistent with the` (2 occurrences)

## Recommended Next Actions
- Review the warnings in `ingestion_audit.json`; proceed to Part 5B only for findings worth fixing.
