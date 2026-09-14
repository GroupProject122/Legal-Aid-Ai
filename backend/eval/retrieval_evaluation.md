# Retrieval Evaluation

> **Baseline note (2026-09-14):** this file is regenerated in full by `evaluate_retrieval.py` on
> every run, overwriting any hand-written notes (this one included) -- the durable copy of the
> full history lives in `rag.py` as a comment above `RETRIEVAL_PRIORITY_WEIGHTS`.
>
> This baseline reflects a three-step, same-day escalation on the
> `cybercrime_portal_citizen_manual_latest.pdf` retrieval drift, not a single clean fix: (1)
> accept as-is (an earlier baseline of this file), (2) strengthen scoring
> (`PROCEDURAL_GUIDE_SUBSTANTIVE_PENALTY`, extended to `retrieval_priority=medium` to also cover
> `npci_upi_procedural_guidelines.pdf`), (3) widen the cyber-domain candidate pool
> (`candidate_k=100`, via `production_candidate_k()`) after step 2 alone proved insufficient --
> several substantive cyber queries never fetched IT Act s.66C as a raw-FAISS candidate at all
> (rank 41-61) under the then-current candidate_k=40, so no scoring change could have surfaced it.
> `evaluate_retrieval.py` itself was also fixed this round: it previously hardcoded its own
> `candidate_k=10` (now `production_candidate_k()` per query, matching production), which is why
> this file's own Overall Metrics numbers only started reflecting the fix at step 3, not step 2 --
> at candidate_k=10 the statute was never a candidate here either, same underlying cause.
>
> **Net result (steps 2+3 combined), single-domain queries:** Document Hit@5 88.9% -> 94.4%,
> MRR 0.813 -> 0.857. Cyber-domain specifically: Document Hit@5 66.7% -> 88.9%, MRR 0.404 -> 0.615.
> `cyber fraud online payment`'s Top 5 no longer contains the manual at all (RBI, CERT-In, and IT
> Act s.66C now occupy the top 3); see the Cyber Retrieval Analysis section below for the current
> numbers.
>
> **Known, reported (not fixed) side effect of the wider candidate pool:** on
> `someone shared private data online`, `document_hit_at_5` flipped True->False (3 net
> query-level improvements elsewhere, 1 regression here; document_mrr 0.333->0.167 for this case).
> Cause: the wider pool let a single document (Digital Personal Data Protection Act, 2023) fill
> all 4 selected slots with its own chunks, pushing out The Information Technology Act, 2000 --
> one of this case's two expected primary documents -- which the narrower candidate_k=40 pool had
> included. Not corrected in this round; flagged for a future decision (e.g. a per-document cap
> on selected slots) rather than forced through silently.

## Overall Metrics
- Single-domain queries: 36
- Domain Hit@1: 97.2%
- Domain Hit@3: 100.0%
- Document Hit@1: 80.6%
- Document Hit@3: 91.7%
- Document Hit@5: 94.4%
- Provision Hit@5: 90.9% over 11 provision-labelled queries
- MRR: 0.857
- Average off-domain Top-5 count: 0.083

## Domain-wise Performance
- constitutional_public_authority: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 1.0, Avg off-domain Top-5 0.111
- consumer: Domain Hit@1 100.0%, Document Hit@5 88.9%, MRR 0.815, Avg off-domain Top-5 0.0
- cyber: Domain Hit@1 88.9%, Document Hit@5 88.9%, MRR 0.615, Avg off-domain Top-5 0.222
- tenancy: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 1.0, Avg off-domain Top-5 0.0

## Strong Examples
- `online seller refusing refund` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `defective product and seller not replacing it` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `misleading advertisement caused me loss` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `dark pattern forced me to subscribe` -> `consumer/dark_patterns_guidelines_2023.pdf` (guideline 5)
- `where can I file consumer complaint` -> `consumer/consumer_protection_act_2019.pdf` (section 17)
- `limitation period for consumer complaint` -> `consumer/consumer_protection_act_2019.pdf` (section 69)
- `can consumer commission order repair or replacement` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `phishing link stole my money` -> `cyber/information_technology_act_2000.pdf` (section 66C)
- `someone hacked my social media account` -> `cyber/information_technology_act_2000.pdf` (section 42)

## Failure Examples
- `direct selling company refusing refund`: expected primary document absent from Top 5; top result `consumer/consumer_protection_act_2019.pdf`
- `someone shared private data online`: expected primary document absent from Top 5; top result `cyber/digital_personal_data_protection_act_2023.pdf`

## Cyber Retrieval Analysis
- `cyber fraud online payment` Top 5:
  - rank 1: `cyber/rbi_limiting_liability_unauthorised_transactions_2017.pdf` domain `cyber`, score 0.5204, rerank 0.7384
  - rank 2: `cyber/cert_in_directions_2022.pdf` domain `cyber`, score 0.5074, rerank 0.6994
  - rank 3: `cyber/information_technology_act_2000.pdf` domain `cyber`, score 0.4397, rerank 0.6927
  - rank 4: `cyber/rbi_limiting_liability_unauthorised_transactions_2017.pdf` domain `cyber`, score 0.3898, rerank 0.6528
  - rank 5: `cyber/rbi_limiting_liability_unauthorised_transactions_2017.pdf` domain `cyber`, score 0.4813, rerank 0.6363

## Supporting vs Primary Source Issues
- `how to report online cybercrime`: supporting `cyber/cybercrime_portal_citizen_manual_latest.pdf` at rank 1 before first primary rank 5

## Cross-Domain Queries
- `Instagram seller took payment and blocked me`: expected ['consumer', 'cyber']; Top5 ['consumer', 'cyber']; Top10 ['consumer', 'cyber']
- `online marketplace account hacked and money lost`: expected ['consumer', 'cyber']; Top5 ['cyber']; Top10 ['cyber']
- `public authority leaked my personal information`: expected ['constitutional_public_authority', 'cyber']; Top5 ['constitutional_public_authority']; Top10 ['constitutional_public_authority']
- `government website did not respond to my RTI and exposed my data`: expected ['constitutional_public_authority', 'cyber']; Top5 ['constitutional_public_authority']; Top10 ['constitutional_public_authority']
- `landlord used online threats to force me to leave`: expected ['cyber', 'tenancy']; Top5 ['tenancy']; Top10 ['constitutional_public_authority', 'cyber', 'tenancy']

## Non-Legal Queries
- `weather tomorrow` -> top result `constitutional_public_authority/constitution_of_india.pdf` domain `constitutional_public_authority`
- `best pizza recipe` -> top result `constitutional_public_authority/constitution_of_india.pdf` domain `constitutional_public_authority`
- `how to learn Python` -> top result `constitutional_public_authority/right_to_education_act_2009.pdf` domain `constitutional_public_authority`

## Recommended Next Improvements
- Best-performing domain by Document Hit@5: `constitutional_public_authority`.
- Weakest-performing domain by Document Hit@5: `consumer`.
- Review remaining document-level misses before adding heavier retrieval methods.
- Consider targeted query-intent handling or domain routing only after comparing this report with earlier baselines.
