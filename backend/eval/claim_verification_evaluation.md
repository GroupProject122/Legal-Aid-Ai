# Claim Verification Evaluation

## Overall Results
- Cases: 27
- Verified cases: 27
- Verifier structured-output success rate: 100.0%
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
- Verifier-call failure rate: 0.0%

## Confusion Matrix
```json
{
  "supported": {
    "supported": 12,
    "partially_supported": 0,
    "unsupported": 0
  },
  "partially_supported": {
    "supported": 0,
    "partially_supported": 6,
    "unsupported": 0
  },
  "unsupported": {
    "supported": 0,
    "partially_supported": 0,
    "unsupported": 9
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
- `supported_dark_pattern_guideline` -> supported
- `supported_misleading_ad` -> supported
- `supported_direct_selling_obligation` -> supported

## Partial-Support Cases
- `partial_extra_deadline` -> partially_supported
- `partial_essential_supply_plus_compensation` -> partially_supported
- `partial_consumer_replacement_plus_immediate` -> partially_supported
- `partial_identity_theft_plus_arrest` -> partially_supported
- `partial_rti_request_plus_no_fee` -> partially_supported
- `partial_legal_aid_plus_all_cases` -> partially_supported

## Unsupported Claims
- `unsupported_30_day_deadline` -> unsupported; leaked=False
- `unsupported_wrong_forum` -> unsupported; leaked=False
- `unsupported_guaranteed_refund` -> unsupported; leaked=False
- `unsupported_wrong_section_meaning` -> unsupported; leaked=False
- `unsupported_weather_claim` -> unsupported; leaked=False
- `unsupported_fake_portal` -> unsupported; leaked=False
- `unsupported_fake_penalty` -> unsupported; leaked=False
- `unsupported_wrong_article` -> unsupported; leaked=False
- `unsupported_password_request` -> unsupported; leaked=False

## High-Risk Claim Checks
- High-risk evaluated cases: 12
- Safe handling rate: 100.0%

## Wrong-Source / Wrong-Section Cases
- `unsupported_wrong_forum`: expected unsupported, predicted unsupported
- `unsupported_wrong_section_meaning`: expected unsupported, predicted unsupported
- `unsupported_fake_portal`: expected unsupported, predicted unsupported
- `unsupported_fake_penalty`: expected unsupported, predicted unsupported
- `unsupported_wrong_article`: expected unsupported, predicted unsupported

## Gemini Failure / Quota Handling
- Successful verifier calls: 27
- Average latency: 1511.6 ms
- Failure count: 0

## Remaining Limitations
- This is a lightweight Gemini verifier, not formal entailment/citation proof.
- Quota failures are handled safely and reported separately from verifier quality.

## Recommendation
- Use this verifier as a guardrail, then add deeper claim-to-citation review in a later phase if needed.
