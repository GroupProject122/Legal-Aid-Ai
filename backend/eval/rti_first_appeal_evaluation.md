# Complaint Drafter Evaluation (RTI First Appeal, Section 19(1))

## Overall Results
- Total cases: 7
- PIO response types covered: incomplete_information_provided, no_response_received, request_rejected
- Overall accuracy: 100.0%
- Pass-case accuracy: 100.0% (3 cases)
- Citation accuracy: 100.0%
- Citation corpus-resolution rate: 100.0%
- Fail-case (hard validator) accuracy: 100.0% (4 cases)
- Hard-fail message match rate: 100.0%

## Group Breakdown
- `hard_validators`: overall accuracy 100.0% (4 cases)
- `valid_cases`: overall accuracy 100.0% (3 cases)

## Failures
- No failures under the current case labels.

## Scope
- Models only the standard 30-day Section 7(1) response period -- the 48-hour life-or-liberty period and Section 11 third-party-information periods are not modeled.

## Recommendation
- Re-run this eval whenever a clause file, citation mapping, or hard validator changes; treat any drop below 100% pass/fail accuracy as a regression.
