# Document Fact Integration Evaluation

## Overall Results
- Cases: 21
- Overall accuracy: 100.0%
- Confirmed-context acceptance: 100.0%
- Unconfirmed-context rejection: 100.0%
- Fact preservation accuracy: 100.0%
- User-correction priority: 100.0%
- Conflict detection: 100.0%
- Document/legal-source separation: 100.0%
- Corpus-gap safety preservation: 100.0%
- Unconfirmed-fact leakage: 0.0%
- Document-as-legal-source leakage: 0.0%
- Confirmed-fact mutation: 0.0%
- Corpus-gap bypass: 0.0%
- Gemini calls: 0

## Case Results
- `rent_agreement_electricity` (confirmed_acceptance) -> pass
- `invoice_refund` (confirmed_acceptance) -> pass
- `receipt_instagram_blocked` (confirmed_acceptance) -> pass
- `legal_notice_response` (confirmed_acceptance) -> pass
- `vague_resolved_by_rent_agreement` (fact_sufficiency) -> pass
- `deposit_fact_sufficiency` (fact_sufficiency) -> pass
- `consumer_fact_sufficiency` (fact_sufficiency) -> pass
- `cyber_fact_sufficiency` (fact_sufficiency) -> pass
- `mumbai_tenancy_gap` (corpus_gap) -> pass
- `delhi_tenancy_no_gap` (corpus_gap) -> pass
- `amount_conflict` (conflict) -> pass
- `date_conflict` (conflict) -> pass
- `no_conflict_same_amount` (conflict) -> pass
- `corrected_amount_priority` (correction_priority) -> pass
- `unconfirmed_rejected` (unconfirmed_rejection) -> pass
- `document_evidence_separate` (separation) -> pass
- `no_document_normal` (no_document) -> pass
- `detached_context` (detach) -> pass
- `raw_extraction_not_context` (unconfirmed_rejection) -> pass
- `legal_notice_no_auto_answer` (confirmation_only) -> pass
- `user_correction_no_original_leak` (correction_priority) -> pass

## Failure Examples
- No failures under the current integration checks.

## Recommendation
- Confirmed document facts are ready for controlled use as user case context; keep them separate from legal citations.
