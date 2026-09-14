# Complaint Drafter Evaluation (Consumer Defective Goods / Deficient Service, Consumer Protection Act, 2019)

## Overall Results
- Total cases: 13
- Grounds covered: defective_goods, deficient_service, short_delivery, spurious_goods, unfair_trade_practice_in_sale
- Overall accuracy: 100.0%
- Pass-case accuracy: 100.0% (9 cases)
- Clause-selection accuracy: 100.0%
- Citation accuracy: 100.0%
- Forum-tier accuracy: 100.0%
- Citation corpus-resolution rate: 100.0%
- Fail-case (hard validator) accuracy: 100.0% (4 cases)
- Hard-fail message match rate: 100.0%

## Valid Drafts Per Ground
- `valid_defective_goods` -> clause `consumer_defective_goods_ground.txt`, citation `Section 2(10)`, forum_tier `district`, all_citations_resolved=True
- `valid_deficient_service` -> clause `consumer_deficient_service_ground.txt`, citation `Section 2(11)`, forum_tier `district`, all_citations_resolved=True
- `valid_short_delivery` -> clause `consumer_short_delivery_ground.txt`, citation `Section 2(10) (the 'quantity' prong)`, forum_tier `district`, all_citations_resolved=True
- `valid_spurious_goods` -> clause `consumer_spurious_goods_ground.txt`, citation `Section 2(43)`, forum_tier `district`, all_citations_resolved=True
- `valid_unfair_trade_practice` -> clause `consumer_unfair_trade_practice_ground.txt`, citation `Section 2(47)`, forum_tier `district`, all_citations_resolved=True

## Forum-Tier Boundary (Sections 34/47/58, read with the 2021 Jurisdiction Rules)
- District Commission jurisdiction 'does not exceed' Rs. 50 lakh (Rule 3); State 'exceeds fifty lakh but does not exceed two crore' (Rule 4); National 'exceeds two crore' (Rule 5). Based on amount_paid alone (the Act's own phrase is 'value of goods or services paid as consideration' -- it does not mention compensation claimed).
- `forum_tier_district_boundary_at_cap` expected tier `district` -> got `district`
- `forum_tier_state_just_above_district_cap` expected tier `state` -> got `state`
- `forum_tier_state_boundary_at_cap` expected tier `state` -> got `state`
- `forum_tier_national_just_above_state_cap` expected tier `national` -> got `national`

## Hard Validator Cases
- `hard_fail_negative_amount_paid` expected `fail` -> got `fail`; message matched=True
- `hard_fail_future_transaction_date` expected `fail` -> got `fail`; message matched=True
- `hard_fail_prior_complaint_missing_response` expected `fail` -> got `fail`; message matched=True
- `hard_fail_compensation_relief_missing_amount` expected `fail` -> got `fail`; message matched=True

## Group Breakdown
- `forum_tier_boundary`: overall accuracy 100.0% (4 cases)
- `hard_validators`: overall accuracy 100.0% (4 cases)
- `valid_per_ground`: overall accuracy 100.0% (5 cases)

## Failures
- No failures under the current case labels.

## Cost And Latency
- Cases run: 13
- LLM calls: 0 (no LLM is part of the drafting path)
- Average latency: 24.38 ms
- Max latency: 103 ms

## Remaining Limitations
- Citation resolution checks source_file + section_number/rule_number presence in the corpus rag.py loads, not clause-letter-level textual entailment -- it confirms Section 2 (or the relevant Rule) exists in the corpus, not that the specific sub-clause (10)/(11)/(43)/(47) appears verbatim (verified manually at authoring time; see complaint_drafter.py's GOODS_CLAUSE_CITATIONS comments).
- short_delivery cites the same Section 2(10) as defective_goods (a different prong of the same defined term -- 'quantity' vs 'quality/potency/purity/standard'); the corpus-resolution check cannot distinguish prongs within one section, only that the section exists.

## Recommendation
- Re-run this eval whenever a clause file, citation mapping, forum-tier threshold, or hard validator changes; treat any drop below 100% pass/fail accuracy as a regression, since every case here encodes a specific, manually verified legal fact rather than a fuzzy quality judgment.
