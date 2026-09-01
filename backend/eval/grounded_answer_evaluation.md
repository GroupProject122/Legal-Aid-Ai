# Grounded Answer Evaluation

## Overall Results
- Scenarios: 24
- Valid structured-output rate: 100.0%
- Source-ID validity rate: 100.0%
- Unsupported-source hallucination rate: 0.0%
- Unsafe certainty rate: 0.0%
- Insufficient-context handling rate: 100.0%
- Disclaimer presence rate: 100.0%
- Expected-document presence rate: 100.0%
- Expected-provision presence rate: 100.0%
- Overall heuristic pass rate: 75.0%

## Strong Examples
- `online seller refusing refund` -> 4 source(s)
- `seller refusing refund for defective product` -> 4 source(s)
- `product delivered to me was damaged` -> 4 source(s)
- `ecommerce company not responding to complaint` -> 3 source(s)
- `dark pattern forced me to subscribe` -> 2 source(s)
- `misleading advertisement caused me loss` -> 3 source(s)
- `cyber fraud online payment` -> 2 source(s)
- `my Instagram account was hacked` -> 2 source(s)

## Failure Examples
- `right to equality`: {'must_not_claim_hits': [], 'unsafe_certainty_hits': [], 'unsupported_source_claims': []}
- `I want free legal aid`: {'must_not_claim_hits': [], 'unsafe_certainty_hits': [], 'unsupported_source_claims': []}
- `human rights complaint against public authority`: {'must_not_claim_hits': [], 'unsafe_certainty_hits': [], 'unsupported_source_claims': []}
- `court order deliberately disobeyed hai`: {'must_not_claim_hits': [], 'unsafe_certainty_hits': [], 'unsupported_source_claims': []}
- `Instagram seller took payment and blocked me`: {'must_not_claim_hits': [], 'unsafe_certainty_hits': [], 'unsupported_source_claims': []}
- `landlord online threats de raha hai aur electricity cut kar di`: {'must_not_claim_hits': [], 'unsafe_certainty_hits': [], 'unsupported_source_claims': []}

## Manual Spot-Check Candidates
- `landlord cut electricity`
- `online seller refusing refund`
- `cyber fraud online payment`
- `right to equality`
- `RTI application ka reply nahi mila`
- `Instagram seller took payment and blocked me`

## Gemini Calls And Latency
- Generation calls: 15
- Average generation latency: 2588.6 ms

## Recommendation
- Part 9B should add claim-to-source citation verification on top of this backend-controlled source-ID approach.
