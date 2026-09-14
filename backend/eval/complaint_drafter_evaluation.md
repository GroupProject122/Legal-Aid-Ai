# Complaint Drafter Evaluation (Tenancy Eviction / Delhi Rent Control Act, 1958)

## Overall Results
- Total cases: 12
- Grounds covered: arrears, bona_fide_requirement, damage, subletting
- Overall accuracy: 100.0%
- Pass-case accuracy: 100.0% (5 cases)
- Clause-selection accuracy: 100.0%
- Citation accuracy: 100.0%
- Citation corpus-resolution rate: 100.0%
- Fail-case (hard validator) accuracy: 100.0% (7 cases)
- Hard-fail message match rate: 100.0%

## Valid Drafts Per Ground
- `valid_arrears` -> clause `tenancy_arrears_ground.txt`, citation `Section 14(1)(a)`, resolved_against_corpus=True
- `valid_subletting` -> clause `tenancy_subletting_ground.txt`, citation `Section 14(1)(b)`, resolved_against_corpus=True
- `valid_damage` -> clause `tenancy_damage_ground.txt`, citation `Section 14(1)(j)`, resolved_against_corpus=True
- `valid_bona_fide_requirement` -> clause `tenancy_bona_fide_ground.txt`, citation `Section 14(1)(e)`, resolved_against_corpus=True

## Rent-Cap Boundary (Section 3)
- Section 3 excludes premises 'whose monthly rent exceeds three thousand and five hundred rupees' -- 'exceeds' is strictly-greater-than, so the cap is EXCLUSIVE: exactly Rs. 3,500 is still covered by the Act.
- `boundary_rent_at_cap_is_covered` expected `pass` -> got `pass`
- `boundary_rent_just_above_cap_is_excluded` expected `fail` -> got `fail`

## Hard Validator Cases
- `rent_cap_exclusion` expected `fail` -> got `fail`; message matched=True
- `incomplete_arrears_missing_amount` expected `fail` -> got `fail`; message matched=True
- `incomplete_subletting_missing_details` expected `fail` -> got `fail`; message matched=True
- `incomplete_damage_missing_description` expected `fail` -> got `fail`; message matched=True
- `incomplete_bona_fide_missing_reason` expected `fail` -> got `fail`; message matched=True
- `future_tenancy_start_date` expected `fail` -> got `fail`; message matched=True

## Group Breakdown
- `hard_validators`: overall accuracy 100.0% (6 cases)
- `rent_cap_boundary`: overall accuracy 100.0% (2 cases)
- `valid_per_ground`: overall accuracy 100.0% (4 cases)

## Failures
- No failures under the current case labels.

## Cost And Latency
- Cases run: 12
- LLM calls: 0 (no LLM is part of the drafting path)
- Average latency: 17.33 ms
- Max latency: 101 ms

## Remaining Limitations
- This scenario covers 4 grounds only (arrears, subletting, damage, bona_fide_requirement); unauthorized_construction was dropped pending manual legal review of its citation.
- Citation resolution checks source_file + section_number presence in the corpus rag.py loads, not clause-letter-level textual entailment -- it confirms Section 14 exists in the corpus, not that clause (a)/(b)/(e)/(j) specifically appears verbatim (verified manually at authoring time; see complaint_drafter.py's CLAUSE_CITATIONS comments).

## Recommendation
- Re-run this eval whenever a clause file, citation mapping, or hard validator changes; treat any drop below 100% pass/fail accuracy as a regression, since every case here encodes a specific, manually verified legal fact rather than a fuzzy quality judgment.
