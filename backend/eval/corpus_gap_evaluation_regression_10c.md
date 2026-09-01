# Corpus Gap Evaluation

## Overall Results
- Cases: 30
- Overall classification accuracy: 100.0%
- Reason-aware accuracy: 100.0%
- Sufficient precision: 100.0%
- Sufficient recall: 100.0%
- Limited detection accuracy: 100.0%
- Insufficient detection accuracy: 100.0%
- Unsafe-answer rate: 0.0%
- Unnecessary-abstention rate: 0.0%
- Jurisdiction-gap detection rate: 100.0%
- Missing-primary-source detection rate: 100.0%

## Confusion Matrix
```json
{
  "sufficient": {
    "sufficient": 12,
    "limited": 0,
    "insufficient": 0
  },
  "limited": {
    "sufficient": 0,
    "limited": 9,
    "insufficient": 0
  },
  "insufficient": {
    "sufficient": 0,
    "limited": 0,
    "insufficient": 9
  }
}
```

## Sufficient Cases
- `sufficient_delhi_electricity` -> sufficient
- `sufficient_equality` -> sufficient
- `sufficient_rti` -> sufficient
- `sufficient_identity_theft` -> sufficient
- `sufficient_defective_refund` -> sufficient
- `sufficient_legal_aid` -> sufficient
- `sufficient_human_rights` -> sufficient
- `sufficient_dark_pattern` -> sufficient
- `sufficient_intermediary` -> sufficient
- `sufficient_misleading_ad` -> sufficient
- `sufficient_direct_selling` -> sufficient
- `sufficient_contempt` -> sufficient

## Limited Cases
- `limited_cert_in` -> limited (missing_current_law, domain_not_fully_covered)
- `limited_dpdp_act` -> limited (missing_current_law, domain_not_fully_covered)
- `limited_cyber_manual_only` -> limited (supporting_sources_only, missing_primary_authority)
- `limited_weak_consumer` -> limited (weak_retrieval)
- `limited_constitution_complex` -> limited (weak_retrieval)
- `limited_supporting_property` -> limited (supporting_sources_only, missing_primary_authority)
- `limited_bns_cyber_support` -> limited (supporting_sources_only, missing_primary_authority)
- `limited_procedural_rti` -> limited (weak_retrieval)
- `limited_bnss_procedure` -> limited (supporting_sources_only, missing_primary_authority)

## Insufficient Cases
- `insufficient_mumbai_tenancy` -> insufficient (jurisdiction_not_covered)
- `insufficient_haryana_tenancy` -> insufficient (jurisdiction_not_covered)
- `insufficient_specific_case` -> insufficient (case_law_not_in_corpus)
- `insufficient_no_chunks` -> insufficient (no_relevant_source)
- `insufficient_off_domain_chunks` -> insufficient (fact_law_mismatch)
- `insufficient_weak_supporting` -> insufficient (weak_retrieval, missing_primary_authority)
- `limited_case_law_general` -> insufficient (case_law_not_in_corpus)
- `insufficient_up_tenancy` -> insufficient (jurisdiction_not_covered)
- `insufficient_tax_public` -> insufficient (domain_not_fully_covered, missing_primary_authority)

## Failure Examples
- No failures under the current deterministic corpus-gap checks.

## Recommendation
- Use the current layer to prevent obvious corpus gaps, then review any failure examples before broadening coverage.
