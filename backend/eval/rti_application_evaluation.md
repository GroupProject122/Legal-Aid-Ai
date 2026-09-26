# Complaint Drafter Evaluation (RTI Application, Right to Information Act, 2005)

## Overall Results
- Total cases: 6
- Preferred modes covered: certified_copies, electronic_format, inspection_of_records
- Overall accuracy: 100.0%
- Pass-case accuracy: 100.0% (3 cases)
- Citation accuracy: 100.0%
- Additional-citation (BPL fee exemption) accuracy: 100.0%
- Citation review-flag accuracy: 100.0%
- Citation corpus-resolution rate: 100.0%
- Fail-case (hard validator) accuracy: 100.0% (3 cases)
- Hard-fail message match rate: 100.0%

## Valid Drafts
- `valid_certified_copies_non_bpl` -> citation `Section 6(1)`, additional_citations=[], review_required=False, resolved_against_corpus=True
- `valid_inspection_bpl_applicant` -> citation `Section 6(1)`, additional_citations=['Section 7(5), proviso'], review_required=False, resolved_against_corpus=True
- `valid_electronic_format` -> citation `Section 6(1)`, additional_citations=[], review_required=False, resolved_against_corpus=True

## Hard Validator Cases
- `hard_fail_short_information_sought` expected `fail` -> got `fail`; message matched=True
- `hard_fail_empty_information_sought` expected `fail` -> got `fail`; message matched=True
- `hard_fail_missing_public_authority_name` expected `fail` -> got `fail`; message matched=True

## Group Breakdown
- `hard_validators`: overall accuracy 100.0% (3 cases)
- `valid_cases`: overall accuracy 100.0% (3 cases)

## Failures
- No failures under the current case labels.

## Cost And Latency
- Cases run: 6
- LLM calls: 0 (no LLM is part of the drafting path)
- Average latency: 24.17 ms
- Max latency: 97 ms

## Remaining Limitations
- Citation resolution checks source_file + section_number presence in the corpus rag.py loads, not sub-clause-level textual entailment (same limitation as the other three scenarios; see complaint_drafter.py's RTI_REQUEST_CITATION / RTI_BPL_FEE_EXEMPTION_CITATION comments).
- This scenario has no 'grounds' selection -- there is exactly one kind of request this drafts, addressed to the Public Information Officer of a named public authority. It does not draft a first appeal (Section 19) or second appeal (to the Information Commission) if a request is refused or ignored -- only the initial Section 6(1) request.

## Recommendation
- Re-run this eval whenever a clause file, citation mapping, or hard validator changes; treat any drop below 100% pass/fail accuracy as a regression, since every case here encodes a specific, manually verified legal fact rather than a fuzzy quality judgment.
