# Retrieval Evaluation

> **Baseline note (2026-09-14):** this file is regenerated in full by `evaluate_retrieval.py` on
> every run, overwriting any hand-written notes (this one included) -- the durable copy of the
> finding below lives in `rag.py` as a comment above `authority_level_boost()` /
> `PROCEDURAL_GUIDE_SUBSTANTIVE_PENALTY`.
>
> A down-weighting fix was added this session for retrieval_priority=low + authority_level=
> procedural_guide documents (currently `cybercrime_portal_citizen_manual_latest.pdf`,
> `national_cybercrime_reporting_portal_user_manual_2019.pdf`,
> `sanchar_saathi_ceir_user_manual.pdf`) on substantive (non-procedural-intent) queries. **This
> file's own Overall Metrics do not reflect it**, and that's expected, not a sign the fix didn't
> work: `evaluate_retrieval.py` calls `retrieve_candidates()` with its own hardcoded
> `RAW_CANDIDATE_K=10`, a narrower window than `LegalRAG.retrieve()` actually uses in production
> (40 for single-domain queries as of this session). At candidate_k=10, statutory sources like the
> IT Act/DPDP Act often aren't fetched as candidates at all for cyber queries where these manuals
> dominate raw semantic similarity, so no amount of down-weighting inside this evaluator's own
> 10-candidate window can surface them -- verified directly against the production `retrieve()`
> path instead (candidate_k=40): e.g. for `cyber fraud online payment`, IT Act s.66C now appears
> at rank 3 of 4 alongside the manual, correctly, where it was absent before. See the git history /
> conversation record for full before/after numbers across both substantive and procedural test
> queries; this evaluator is not a reliable proxy for that particular before/after because of the
> candidate_k mismatch just described (a pre-existing property of this script, not something
> changed this session).
>
> One side effect specific to this evaluator's narrow window: `average_off_domain_top5_count`
> moved slightly (0.056 -> 0.083 overall; cyber 0.111 -> 0.222). Traced to one query
> (`intermediary failed to remove unlawful content`): with the manual correctly down-weighted, this
> evaluator's 10-candidate pool had no other strong same-domain candidate to fill the vacated
> slot and fell back to an off-domain RTI Act chunk. Confirmed this does not happen against the
> real `LegalRAG.retrieve()` path (candidate_k=40), which fills that slot with another cyber
> document (an Intermediary Guidelines Rules chunk) instead -- an artifact of this evaluator's
> RAW_CANDIDATE_K=10 being narrower than production, not a real production regression.

## Overall Metrics
- Single-domain queries: 36
- Domain Hit@1: 97.2%
- Domain Hit@3: 100.0%
- Document Hit@1: 75.0%
- Document Hit@3: 86.1%
- Document Hit@5: 88.9%
- Provision Hit@5: 90.9% over 11 provision-labelled queries
- MRR: 0.813
- Average off-domain Top-5 count: 0.083

## Domain-wise Performance
- constitutional_public_authority: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 1.0, Avg off-domain Top-5 0.111
- consumer: Domain Hit@1 100.0%, Document Hit@5 88.9%, MRR 0.849, Avg off-domain Top-5 0.0
- cyber: Domain Hit@1 88.9%, Document Hit@5 66.7%, MRR 0.404, Avg off-domain Top-5 0.222
- tenancy: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 1.0, Avg off-domain Top-5 0.0

## Strong Examples
- `online seller refusing refund` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `defective product and seller not replacing it` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `misleading advertisement caused me loss` -> `consumer/consumer_protection_act_2019.pdf` (section 89)
- `dark pattern forced me to subscribe` -> `consumer/dark_patterns_guidelines_2023.pdf` (guideline 5)
- `where can I file consumer complaint` -> `consumer/consumer_protection_act_2019.pdf` (section 17)
- `limitation period for consumer complaint` -> `consumer/consumer_protection_act_2019.pdf` (section 69)
- `can consumer commission order repair or replacement` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `identity theft using my personal details` -> `cyber/information_technology_act_2000.pdf` (section 66C)
- `unauthorized access to computer account` -> `cyber/information_technology_act_2000.pdf` (section 29)

## Failure Examples
- `direct selling company refusing refund`: expected primary document absent from Top 5; top result `consumer/consumer_protection_act_2019.pdf`
- `cyber fraud online payment`: broad supporting statute outranking primary source, generic/common wording, duplicate/adjacent chunks; top result `cyber/cybercrime_portal_citizen_manual_latest.pdf`
- `phishing link stole my money`: broad supporting statute outranking primary source, expected primary document absent from Top 5, duplicate/adjacent chunks; top result `cyber/cybercrime_portal_citizen_manual_latest.pdf`
- `someone hacked my social media account`: broad supporting statute outranking primary source, expected primary document absent from Top 5, duplicate/adjacent chunks; top result `cyber/it_blocking_rules_2009.pdf`

## Cyber Retrieval Analysis
- `cyber fraud online payment` Top 5:
  - rank 1: `cyber/cybercrime_portal_citizen_manual_latest.pdf` domain `cyber`, score 0.6485, rerank 0.6165
  - rank 2: `cyber/cybercrime_portal_citizen_manual_latest.pdf` domain `cyber`, score 0.5975, rerank 0.5655
  - rank 3: `cyber/cybercrime_portal_citizen_manual_latest.pdf` domain `cyber`, score 0.6161, rerank 0.5541
  - rank 4: `cyber/cybercrime_portal_citizen_manual_latest.pdf` domain `cyber`, score 0.5853, rerank 0.5533
  - rank 5: `cyber/cybercrime_portal_citizen_manual_latest.pdf` domain `cyber`, score 0.585, rerank 0.553

## Supporting vs Primary Source Issues
- `cyber fraud online payment`: supporting `cyber/cybercrime_portal_citizen_manual_latest.pdf` at rank 1 before first primary rank None
- `phishing link stole my money`: supporting `cyber/cybercrime_portal_citizen_manual_latest.pdf` at rank 1 before first primary rank None
- `someone hacked my social media account`: supporting `cyber/cybercrime_portal_citizen_manual_latest.pdf` at rank 2 before first primary rank 10
- `how to report online cybercrime`: supporting `cyber/cybercrime_portal_citizen_manual_latest.pdf` at rank 1 before first primary rank 5

## Cross-Domain Queries
- `Instagram seller took payment and blocked me`: expected ['consumer', 'cyber']; Top5 ['cyber']; Top10 ['cyber']
- `online marketplace account hacked and money lost`: expected ['consumer', 'cyber']; Top5 ['cyber']; Top10 ['cyber']
- `public authority leaked my personal information`: expected ['constitutional_public_authority', 'cyber']; Top5 ['constitutional_public_authority', 'cyber']; Top10 ['constitutional_public_authority', 'cyber']
- `government website did not respond to my RTI and exposed my data`: expected ['constitutional_public_authority', 'cyber']; Top5 ['constitutional_public_authority']; Top10 ['constitutional_public_authority', 'cyber']
- `landlord used online threats to force me to leave`: expected ['cyber', 'tenancy']; Top5 ['cyber', 'tenancy']; Top10 ['cyber', 'tenancy']

## Non-Legal Queries
- `weather tomorrow` -> top result `constitutional_public_authority/constitution_of_india.pdf` domain `constitutional_public_authority`
- `best pizza recipe` -> top result `constitutional_public_authority/constitution_of_india.pdf` domain `constitutional_public_authority`
- `how to learn Python` -> top result `constitutional_public_authority/right_to_education_act_2009.pdf` domain `constitutional_public_authority`

## Recommended Next Improvements
- Best-performing domain by Document Hit@5: `constitutional_public_authority`.
- Weakest-performing domain by Document Hit@5: `cyber`.
- Review remaining document-level misses before adding heavier retrieval methods.
- Consider targeted query-intent handling or domain routing only after comparing this report with earlier baselines.
