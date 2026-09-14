# Complaint Drafter Evaluation (Misleading Advertisement / Dark Patterns, Consumer Protection Act, 2019)

## Overall Results
- Total cases: 10
- Claim types covered: dark_pattern_deceptive_design, false_claim_about_goods, false_guarantee_or_warranty, misleading_price_representation, surrogate_advertisement
- Overall accuracy: 100.0%
- Pass-case accuracy: 100.0% (6 cases)
- Clause-selection accuracy: 100.0%
- Citation accuracy: 100.0%
- Citation review-flag accuracy: 100.0%
- Citation corpus-resolution rate: 100.0%
- Fail-case (hard validator) accuracy: 100.0% (4 cases)
- Hard-fail message match rate: 100.0%

## Valid Drafts Per Claim Type
- `valid_false_claim_about_goods` -> clause `ads_false_claim_ground.txt`, citation `Section 2(28)(i)` (authority_level=primary), review_required=False, resolved_against_corpus=True
- `valid_misleading_price_representation` -> clause `ads_misleading_price_ground.txt`, citation `Section 2(47)(i)(i)` (authority_level=primary), review_required=False, resolved_against_corpus=True
- `valid_false_guarantee_or_warranty` -> clause `ads_false_guarantee_ground.txt`, citation `Section 2(28)(ii)` (authority_level=primary), review_required=False, resolved_against_corpus=True
- `valid_surrogate_advertisement` -> clause `ads_surrogate_advertisement_ground.txt`, citation `Guideline 6(1), read with the definition in Guideline 2(h)` (authority_level=official_guidance), review_required=False, resolved_against_corpus=True
- `valid_dark_pattern_deceptive_design` -> clause `ads_dark_pattern_ground.txt`, citation `Guideline 4, read with the definition in Guideline 2(e)` (authority_level=official_guidance), review_required=True, resolved_against_corpus=True
- `valid_dark_pattern_without_purchase` -> clause `ads_dark_pattern_ground.txt`, citation `Guideline 4, read with the definition in Guideline 2(e)` (authority_level=official_guidance), review_required=True, resolved_against_corpus=True

## Dark-Pattern Citation Flag
- dark_pattern_deceptive_design cites Guideline 4 (prohibition) + Guideline 2(e) (definition) of the Dark Patterns Guidelines, 2023 -- both exist in the corpus and the citation resolves -- but Guideline 2(e) itself defines a dark pattern as amounting to misleading advertisement OR unfair trade practice OR violation of consumer rights, an explicit either/or rather than one fixed Act provision. That is flagged citation_review_required=true (same mechanism, same reasoning, as tenancy's dropped unauthorized_construction ground), not silently asserted.

## Hard Validator Cases
- `hard_fail_loss_description_too_short` expected `fail` -> got `fail`; message matched=True
- `hard_fail_loss_description_empty` expected `fail` -> got `fail`; message matched=True
- `hard_fail_future_date_encountered` expected `fail` -> got `fail`; message matched=True
- `hard_fail_compensation_relief_missing_amount` expected `fail` -> got `fail`; message matched=True

## Group Breakdown
- `hard_validators`: overall accuracy 100.0% (4 cases)
- `no_transaction_case`: overall accuracy 100.0% (1 cases)
- `valid_per_ground`: overall accuracy 100.0% (5 cases)

## Failures
- No failures under the current case labels.

## Cost And Latency
- Cases run: 10
- LLM calls: 0 (no LLM is part of the drafting path)
- Average latency: 23.3 ms
- Max latency: 101 ms

## Remaining Limitations
- Citation resolution checks source_file + section_number/guideline_number presence in the corpus rag.py loads, not clause-letter-level textual entailment (same limitation as the other two scenarios; see complaint_drafter.py's ADS_CLAUSE_CITATIONS comments).
- surrogate_advertisement and dark_pattern_deceptive_design cite CCPA guidelines (document_type=guidelines, authority_level=official_guidance), not the Act itself (document_type=statute, authority_level=primary) -- reflected in each citation's authority_level field and in the clause text, not asserted with statute-level confidence.

## Recommendation
- Re-run this eval whenever a clause file, citation mapping, or hard validator changes; treat any drop below 100% pass/fail accuracy as a regression, since every case here encodes a specific, manually verified legal fact rather than a fuzzy quality judgment.
