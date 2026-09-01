# Ingestion Audit Summary

## Overall Results
- Status: PASS WITH WARNINGS
- Total chunks checked: 4388
- Unique chunk IDs: 4388
- HIGH findings: 0
- MEDIUM findings: 143
- LOW findings: 3

## High-Priority Issues
- None found.

## Medium-Priority Issues
- 143 medium-priority finding(s), mainly review-scale quality signals.
- Large chunks over 8,000 characters: 0
- Exact duplicate text groups: 0
- Near-duplicate text groups: 3

## Low-Priority / Informational Findings
- Very short chunks under 40 characters: 9
- Review-candidate chunks from 40 to 100 characters: 367
- Suspicious recurring header/footer patterns: 4

## Documents Requiring Attention
- `cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf`: 14 fallback chunks (70.0%)
- `consumer/ecommerce_amendment_rules_2021.pdf`: 1 fallback chunks (50.0%)
- `consumer/consumer_commission_procedure_regulations_2020.pdf`: 13 fallback chunks (33.33%)

## Fallback Analysis
- Total fallback chunks: 50
- `cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf`: 14/20 fallback (70.0%)
- `consumer/ecommerce_amendment_rules_2021.pdf`: 1/2 fallback (50.0%)
- `consumer/consumer_commission_procedure_regulations_2020.pdf`: 13/39 fallback (33.33%)
- `consumer/jurisdiction_rules_2021.pdf`: 1/6 fallback (16.67%)
- `consumer/mediation_rules_2020.pdf`: 1/8 fallback (12.5%)
- `consumer/dark_patterns_guidelines_2023.pdf`: 1/15 fallback (6.67%)
- `consumer/ecommerce_rules_2020.pdf`: 1/15 fallback (6.67%)
- `consumer/misleading_ads_guidelines_2022.pdf`: 1/18 fallback (5.56%)

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
- Exact duplicate groups: 0
- Near-duplicate groups: 3
- Recurring noise examples:
  - `MINISTRY OF CONSUMER AFFAIRS, FOOD AND PUBLIC DISTRIBUTION` (6 occurrences)
  - `(2) They shall come into force on the date of their publication in the Official Gazette.` (5 occurrences)
  - `(2) It shall come into force on the date of its publication in the Official Gazette.` (2 occurrences)
  - `Gazette, appoint.` (2 occurrences)

## Recommended Next Actions
- Review the warnings in `ingestion_audit.json`; proceed to Part 5B only for findings worth fixing.
