# Document Fact Extraction Evaluation

## Overall Results
- Cases: 15
- Structured-output success: 100.0%
- Document-type accuracy: 93.3%
- Key-fact precision: 100.0%
- Key-fact recall: 100.0%
- Hallucinated-fact rate: 0.0%
- Sensitive-data leakage rate: 0.0%
- Provenance-presence rate: 100.0%
- Uncertainty handling: 100.0%
- Gemini calls: 15
- Gemini failures: 0
- Average latency: 2638.2 ms

## Case Results
- `rent_agreement_basic` -> rent_agreement (pass)
- `invoice_phone` -> invoice_or_receipt (pass)
- `refund_receipt` -> invoice_or_receipt (pass)
- `legal_notice_consumer` -> legal_notice (pass)
- `complaint_copy` -> complaint (pass)
- `transaction_record` -> transaction_record (pass)
- `email_correspondence` -> correspondence (pass)
- `ambiguous_party_role` -> unknown (pass)
- `repeated_amount` -> rent_agreement (pass)
- `sensitive_credentials` -> transaction_record (pass)
- `legal_notice_tenancy` -> legal_notice (pass)
- `sparse_document` -> unknown (pass)
- `complaint_number_notice` -> complaint (pass)
- `other_identity_misuse` -> complaint (review)
- `unclear_signature` -> unknown (pass)

## Failure Examples
- `other_identity_misuse` missing=[] forbidden=[] expected_type=other actual_type=complaint

## Recommendation
- Use user-confirmed facts only in the next integration phase; do not auto-feed extracted facts into RAG yet.
