# Document Summarization Evaluation

## Overall Results

- Total cases: 10
- Evaluated cases: 8
- Not evaluated: 2
- Structured-output success: 100.0%
- Status accuracy: 87.5%
- Factual preservation: 87.5%
- Hallucinated-detail / legal-interpretation leakage: 0.0%
- Sensitive-data leakage: 0.0%
- Gemini calls: 7
- Average latency: 1113.1 ms

## Case Results

### summary_rent_agreement
- Expected status: success
- Actual status: success
- Keyword hits: rent, Rs. 25,000, security deposit, 11 months, two months
- Forbidden hits: None
- Message: N/A

### summary_invoice
- Expected status: success
- Actual status: success
- Keyword hits: INV-1042, Metro Gadgets, Rs. 20,000, 5 August 2026, UPI
- Forbidden hits: None
- Message: N/A

### summary_legal_notice
- Expected status: success
- Actual status: success
- Keyword hits: Legal Notice, 10 June 2026, ABC Traders, Rs. 45,000, seven days
- Forbidden hits: None
- Message: N/A

### summary_consumer_complaint
- Expected status: success
- Actual status: success
- Keyword hits: online order, laptop, 2 August 2026, replacement, refund
- Forbidden hits: None
- Message: N/A

### summary_rti_reply
- Expected status: success
- Actual status: success
- Keyword hits: RTI, 4 May 2026, Public Information Officer, records are not available
- Forbidden hits: None
- Message: N/A

### summary_transaction_record
- Expected status: success
- Actual status: success
- Keyword hits: transaction receipt, Rs. 15,000, UPI, 31 August 2026, phone purchase
- Forbidden hits: None
- Message: N/A

### summary_short_agreement
- Expected status: success
- Actual status: success
- Keyword hits: 20 chairs, 15 September 2026, Rs. 12,000
- Forbidden hits: None
- Message: N/A

### summary_ambiguous_document
- Expected status: success
- Actual status: summary_unavailable
- Keyword hits: None
- Forbidden hits: None
- Message: The document summary could not be generated right now.

### summary_sensitive_credentials
- Expected status: success
- Actual status: not_evaluated
- Keyword hits: None
- Forbidden hits: None
- Message: Live summarization became unavailable; remaining cases were not evaluated to avoid repeated calls.

### summary_empty_scan_like
- Expected status: ocr_required
- Actual status: not_evaluated
- Keyword hits: None
- Forbidden hits: None
- Message: Live summarization became unavailable; remaining cases were not evaluated to avoid repeated calls.

## Limitations

- This evaluator checks factual preservation and leakage patterns, not legal correctness.
- It does not add uploaded documents to the legal corpus, FAISS, or embeddings.