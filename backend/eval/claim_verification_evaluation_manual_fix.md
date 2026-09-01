# Claim Verification Evaluation

## Overall Results
- Cases: 17
- Verified cases: 16
- Verifier structured-output success rate: 94.1%
- Overall classification accuracy: 100.0%
- Supported-claim precision: 100.0%
- Supported-claim recall: 100.0%
- Unsupported-claim detection rate: 100.0%
- Partially-supported detection rate: 100.0%
- False-acceptance rate: 0.0%
- False-rejection rate: 0.0%
- Final unsupported-claim leakage rate: 0.0%
- Sanitization-correct rate: 100.0%
- High-risk safe handling rate: 100.0%
- Verifier-call failure rate: 5.9%

## Confusion Matrix
```json
{
  "partially_supported": {
    "partially_supported": 3,
    "supported": 0,
    "unsupported": 0
  },
  "supported": {
    "partially_supported": 0,
    "supported": 9,
    "unsupported": 0
  },
  "unsupported": {
    "partially_supported": 0,
    "supported": 0,
    "unsupported": 4
  }
}
```

## Supported Claims
- `supported_article_14` -> supported
- `supported_essential_supply` -> supported
- `supported_identity_theft` -> supported
- `supported_rti_request` -> supported
- `supported_consumer_replacement` -> supported
- `supported_consumer_return_price` -> supported
- `supported_intermediary_grievance` -> supported
- `supported_legal_aid_authority` -> supported
- `supported_human_rights_commission` -> supported

## Partial-Support Cases
- `partial_extra_deadline` -> partially_supported
- `partial_essential_supply_plus_compensation` -> partially_supported
- `partial_consumer_replacement_plus_immediate` -> partially_supported
- `partial_identity_theft_plus_arrest` -> verification_unavailable

## Unsupported Claims
- `unsupported_30_day_deadline` -> unsupported; leaked=False
- `unsupported_wrong_forum` -> unsupported; leaked=False
- `unsupported_guaranteed_refund` -> unsupported; leaked=False
- `unsupported_wrong_section_meaning` -> unsupported; leaked=False

## High-Risk Claim Checks
- High-risk evaluated cases: 8
- Safe handling rate: 100.0%

## Wrong-Source / Wrong-Section Cases
- `unsupported_wrong_forum`: expected unsupported, predicted unsupported
- `unsupported_wrong_section_meaning`: expected unsupported, predicted unsupported

## Gemini Failure / Quota Handling
- Successful verifier calls: 16
- Average latency: 1510.7 ms
- Failure count: 1

## Remaining Limitations
- This is a lightweight Gemini verifier, not formal entailment/citation proof.
- Quota failures are handled safely and reported separately from verifier quality.

## Recommendation
- Use this verifier as a guardrail, then add deeper claim-to-citation review in a later phase if needed.
