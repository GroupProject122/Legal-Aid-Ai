# Final End-to-End Evaluation

## 1. Evaluation Objective
This evaluation measures the complete user-facing pipeline from user input through routing, clarification, fact sufficiency, retrieval, corpus-gap checks, grounded generation, claim verification, and document-fact integration.

## 2. Dataset Composition
- Total curated cases: 54
- Cases evaluated in live run: 54
- Categories: {"constitutional_public_authority": 7, "consumer": 9, "corpus_gap": 8, "cyber": 8, "document_assisted": 10, "multi_domain": 6, "tenancy": 6}
- Document-assisted cases: 9
- Expected clarification cases: 6
- Corpus-gap/abstention cases: 10
- Hinglish cases: 8

## 3. Overall System Results
| Metric | Result |
|---|---:|
| End-to-End Success Rate | 77.8% |
| Domain Routing Accuracy | 98.1% |
| Clarification Accuracy | 96.3% |
| Fact Sufficiency Accuracy | 96.3% |
| Expected Legal Source Hit | 84.1% |
| Expected Provision Hit | 100.0% |
| Corpus-Gap Accuracy | 88.9% |
| Grounded Output Success | 100.0% |
| Unsupported Claim Leakage | 0.0% |
| Safe Abstention Accuracy | 66.7% |
| Document Fact Integration Accuracy | 90.0% |
| Unconfirmed Fact Leakage | 0.0% |
| Document/Legal Source Separation | 100.0% |
| Avg End-to-End Latency | 24686.3 ms |

## 4. Routing
- Final route/domain accuracy: 98.1%
- Primary-domain accuracy: 90.7%
- Multi-domain recall: 83.3%
- Hinglish routing accuracy: 87.5%

## 5. Clarification
- Clarification trigger accuracy: 96.3%
- Necessary clarification rate: 100.0%
- Unnecessary clarification rate: 13.2%
- Repeated-question rate: N/A in this run; no repeated-question loop was observed in evaluated cases.

## 6. Fact Sufficiency
- Fact-sufficiency flow accuracy: 96.3%
- Unnecessary factual-question rate: 13.2%
- Missing factual-question rate: N/A; scored through end-to-end status matching.

## 7. Retrieval
- Expected primary legal source hit rate: 84.1%
- Expected provision hit rate: 100.0%
- Frozen retrieval component benchmark remains separately recorded in the component metrics section.

## 8. Corpus-Gap Detection
- Corpus-gap accuracy: 88.9%
- Unsafe answer rate on abstention cases: 33.3%
- Unnecessary abstention rate: 0.0%
- Corpus-gap bypass rate: 25.0%

## 9. Grounded Answer Generation
- Structured grounded-output success: 100.0%
- Source-ID validity: 100.0%
- Disclaimer presence: 98.1%

## 10. Claim Verification
- Unsupported legal-claim leakage: 0.0%
- Gemini verification calls observed: 36
- High-risk unsupported-claim benchmark from Part 9B.1 remains 27/27 classified with 0% leakage.

## 11. Document Integration
- Document fact integration accuracy: 90.0%
- Unconfirmed-fact leakage: 0.0%
- Document-as-legal-source leakage: 0.0%
- Confirmed-fact mutation rate: 0.0%

## 12. Safe Abstention
- Safe Abstention Accuracy: 66.7%
- Abstention cases include unsupported domains, out-of-scope prompts, corpus gaps, unconfirmed document context, and factual conflicts.

## 13. Latency
- Average: 24686.3 ms
- Median: 22954.5 ms
- Min: 8 ms
- Max: 75269 ms
- Gemini generation calls observed: 39
- Gemini quota/API failures: 0

## 14. Manual Quality Review
- Reviewed subset: 20 cases
- Mean score: 9.05 / 10
- Rubric note: Heuristic manual-style rubric: 0-2 each for grounding, usefulness, cautiousness, clarity, and source transparency. This is not expert legal validation.

## 15. Failure Analysis
- `consumer_006_complaint_forum`: expected answered, got clarification; causes: clarification, retrieval
- `cyber_001_payment_fraud`: expected answered, got clarification; causes: clarification, retrieval
- `cyber_006_intermediary`: expected answered, got answered; causes: retrieval
- `cyber_008_data_breach_limited`: expected answered, got answered; causes: corpus gap, retrieval
- `cyber_010_receipt_document_blocked`: expected answered, got answered; causes: retrieval
- `public_004_free_legal_aid`: expected answered, got answered; causes: retrieval
- `public_008_specific_case_gap`: expected abstained, got answered; causes: corpus gap
- `multi_004_public_data_leak`: expected answered, got answered; causes: corpus gap
- `multi_005_delivery_app_refund_data`: expected answered, got answered; causes: corpus gap
- `multi_006_vague_fraud_clarify`: expected answered, got answered; causes: retrieval, routing
- `gap_002_out_of_scope_python`: expected abstained, got answered; causes: corpus gap
- `gap_004_weather_out_scope`: expected abstained, got answered; causes: corpus gap

## 16. Limitations
- The tenancy legal corpus is Delhi-focused.
- The corpus is not a comprehensive Supreme Court or High Court case-law database.
- Some current-law sources may be absent from the active corpus.
- Scanned or image-only documents are detected, but OCR is not implemented.
- Document confirmation state is in-memory and not persistent case storage.
- The system depends on Gemini availability and quota for routing, fact checks, generation, and verification.
- Several evaluation cases and document contexts are curated or synthetic.
- The system provides general legal information, not a substitute for qualified legal advice.

## 17. Final Conclusion
The curated end-to-end benchmark found targeted issues that should be reviewed before demo freeze.

## BTP Methodology Summary
The final evaluation used a curated domain-balanced benchmark with clear, vague, Hinglish, multi-domain, corpus-gap, and document-assisted scenarios. Objective checks measured routing, clarification, source retrieval, corpus-gap behavior, source-ID control, claim leakage, safe abstention, and document/legal-source separation. A manual-style quality rubric was applied to a representative subset for grounding, usefulness, cautiousness, clarity, and source transparency. These results describe benchmark performance, not expert-certified legal accuracy.

## Component Benchmarks
Previously validated component metrics are kept separate from the end-to-end success rate.
- retrieval: domain_hit_at_1=100.0%, document_hit_at_5=97.2%, provision_hit_at_5=90.9%, mrr=94.3%, query_count=36
- router: overall_accuracy=94.0%
- clarification: overall_accuracy=95.8%
- fact_sufficiency: overall_accuracy=100.0%
- corpus_gap: overall_classification_accuracy=100.0%, case_count=30
- grounded_answer: metrics recorded
- claim_verification: overall_classification_accuracy=100.0%, final_unsupported_claim_leakage_rate=0.0%, overall_verified_accuracy=100.0%, case_count=27
- document_integration: overall_accuracy=100.0%, case_count=21
