# Complaint Drafter Evaluation (Bank Fraud Complaint, RBI Limiting Liability Directions 2017 + IT Act Section 66D)

## Overall Results
- Total cases: 8
- Account categories covered: bsbd_account, high_value_account, standard_account
- Liability tiers covered: bank_policy, limited, zero
- Overall accuracy: 100.0%
- Pass-case accuracy: 100.0% (4 cases)
- Liability-tier computation accuracy: 100.0%
- Citation accuracy: 100.0%
- Additional-citation (cap + IT Act) accuracy: 100.0%
- Citation corpus-resolution rate: 100.0%
- Fail-case (hard validator) accuracy: 100.0% (4 cases)
- Hard-fail message match rate: 100.0%

## Group Breakdown
- `hard_validators`: overall accuracy 100.0% (4 cases)
- `valid_cases`: overall accuracy 100.0% (4 cases)

## Failures
- No failures under the current case labels.

## Scope And Known Limitations
- elapsed_days_to_report is calculated on a calendar-day basis, approximating the RBI circular's 'working days' standard -- a bank holiday inside the window would shift the true tier boundary by one or more days. The rendered clause text says so explicitly.
- Does not draft a separate FIR / National Cybercrime Reporting Portal complaint; Section 66D of the IT Act is cited as an always-present additional citation pointing the complainant to that separate channel, not drafted as its own document.

## Recommendation
- Re-run this eval whenever a clause file, citation mapping, or hard validator changes; treat any drop below 100% pass/fail accuracy as a regression.
