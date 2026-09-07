# Ingestion Audit Summary

## Overall Results
- Status: PASS WITH WARNINGS
- Total chunks checked: 4074
- Unique chunk IDs: 4074
- HIGH findings: 0
- MEDIUM findings: 88
- LOW findings: 3

## High-Priority Issues
- None found.

## Medium-Priority Issues
- 88 medium-priority finding(s), mainly review-scale quality signals.
- Large chunks over 8,000 characters: 0
- Exact duplicate text groups: 1
- Near-duplicate text groups: 12

## Low-Priority / Informational Findings
- Very short chunks under 40 characters: 12
- Review-candidate chunks from 40 to 100 characters: 291
- Suspicious recurring header/footer patterns: 7

## Documents Requiring Attention
- `cyber/sanchar_saathi_ceir_user_manual.pdf`: 6 fallback chunks (100.0%)
- `consumer/ecommerce_amendment_rules_2021.pdf`: 1 fallback chunks (50.0%)
- `cyber/cert_in_directions_2022.pdf`: 5 fallback chunks (50.0%)
- `consumer/consumer_commission_procedure_regulations_2020.pdf`: 13 fallback chunks (33.33%)

## Fallback Analysis
- Total fallback chunks: 66
- `cyber/sanchar_saathi_ceir_user_manual.pdf`: 6/6 fallback (100.0%)
- `consumer/ecommerce_amendment_rules_2021.pdf`: 1/2 fallback (50.0%)
- `cyber/cert_in_directions_2022.pdf`: 5/10 fallback (50.0%)
- `consumer/consumer_commission_procedure_regulations_2020.pdf`: 13/39 fallback (33.33%)
- `consumer/jurisdiction_rules_2021.pdf`: 1/6 fallback (16.67%)
- `consumer/mediation_rules_2020.pdf`: 1/8 fallback (12.5%)
- `cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf`: 3/32 fallback (9.38%)
- `cyber/it_spdi_rules_2011.pdf`: 1/11 fallback (9.09%)

## Largest Chunks
- `constitutional_public_authority_constitution_of_india__chunk_0603` in `constitutional_public_authority/constitution_of_india.pdf`: 2158 chars, article 9
- `constitutional_public_authority_constitution_of_india__chunk_0604` in `constitutional_public_authority/constitution_of_india.pdf`: 2158 chars, article 9
- `constitutional_public_authority_constitution_of_india__chunk_0617` in `constitutional_public_authority/constitution_of_india.pdf`: 2143 chars, article 3
- `constitutional_public_authority_constitution_of_india__chunk_0643` in `constitutional_public_authority/constitution_of_india.pdf`: 2132 chars, article 4
- `constitutional_public_authority_constitution_of_india__chunk_0528` in `constitutional_public_authority/constitution_of_india.pdf`: 2126 chars, article 3
- `constitutional_public_authority_constitution_of_india__chunk_0504` in `constitutional_public_authority/constitution_of_india.pdf`: 2116 chars, article 369
- `constitutional_public_authority_constitution_of_india__chunk_0508` in `constitutional_public_authority/constitution_of_india.pdf`: 2116 chars, article 369
- `constitutional_public_authority_constitution_of_india__chunk_0509` in `constitutional_public_authority/constitution_of_india.pdf`: 2116 chars, article 369
- `consumer_consumer_protection_act_2019__chunk_0037` in `consumer/consumer_protection_act_2019.pdf`: 2115 chars, section 21
- `cyber_bharatiya_nyaya_sanhita_2023__chunk_0469` in `cyber/bharatiya_nyaya_sanhita_2023.pdf`: 2113 chars, section 196

## Duplicate / Noise Findings
- Exact duplicate groups: 1
- Near-duplicate groups: 12
- Recurring noise examples:
  - `MINISTRY OF CONSUMER AFFAIRS, FOOD AND PUBLIC DISTRIBUTION` (6 occurrences)
  - `(2) They shall come into force on the date of their publication in the Official Gazette.` (5 occurrences)
  - `MINISTRY OF HOME AFFAIRS` (3 occurrences)
  - `(2) It shall come into force on the date of its publication in the Official Gazette.` (2 occurrences)
  - `Ministry of Home Affairs` (2 occurrences)
  - `Owner Ministry of Home Affairs, Government of India` (2 occurrences)
  - `publication in the Official Gazette.` (2 occurrences)

## Recommended Next Actions
- Review the warnings in `ingestion_audit.json`; proceed to Part 5B only for findings worth fixing.
