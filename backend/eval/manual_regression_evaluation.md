# Manual Regression Evaluation

## Overall Results
- Cases: 15
- Overall expected-behavior rate: 100.0%
- Consumer primary framing correctness: 100.0%
- Consumer no-harm product-liability suppression: 100.0%
- Cyber identity-misuse provision hit: 100.0%
- Multi-domain source coverage: 100.0%
- RTI no-response Section 19 priority: 100.0%
- Verifier fallback usefulness: 100.0%
- Empty-section guard rate: 100.0%
- Category sync correctness: 100.0%
- Debug-language leakage rate: 0.0%

## Case Results
- `manual_01_defective_refund`: PASS; top source=The Consumer Protection Act, 2019 39
- `manual_02_delhi_electricity`: PASS; top source=The Delhi Rent Control Act, 1958 45
- `manual_03_natural_credential_misuse`: PASS; top source=The Information Technology Act, 2000 66C
- `manual_04_explicit_identity_theft`: PASS; top source=The Information Technology Act, 2000 66C
- `manual_05_mumbai_tenancy_gap`: PASS; top source=The Delhi Rent Control Act, 1958 45
- `manual_06_rti_no_reply`: PASS; top source=The Right to Information Act, 2005 19
- `manual_07_article_14`: PASS; top source=The Constitution of India 14
- `manual_08_phone_refund`: PASS; top source=The Consumer Protection Act, 2019 39
- `manual_09_instagram_seller`: PASS; top source=The Consumer Protection Act, 2019 39
- `manual_10_free_legal_aid`: PASS; top source=The Legal Services Authorities Act, 1987 15
- `manual_11_vague_landlord_threat`: PASS; top source=The Delhi Rent Control Act, 1958 1
- `manual_12_divorce_unsupported`: PASS; top source=The Consumer Protection Act, 2019 52
- `manual_13_defective_laptop_no_harm`: PASS; top source=The Consumer Protection Act, 2019 39
- `manual_14_instagram_seller_true_multidomain`: PASS; top source=The Consumer Protection Act, 2019 39
- `manual_15_rti_no_response_appeal_priority`: PASS; top source=The Right to Information Act, 2005 19

## Remaining Failures
- None under the targeted regression checks.

## Recommendation
- Proceed to final manual retest of the 12 scenarios.