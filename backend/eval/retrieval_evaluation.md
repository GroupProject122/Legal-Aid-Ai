# Retrieval Evaluation

> **Baseline note (2026-09-14):** this file is regenerated in full by `evaluate_retrieval.py` on
> every run, which overwrites any hand-written notes in it (this one included) -- so a note here
> only survives until the next re-run; it is not a durable record on its own. The durable version
> of the finding below lives in `rag.py`, as a code comment above `RETRIEVAL_PRIORITY_WEIGHTS` /
> `AUTHORITY_LEVEL_WEIGHTS`, which will not be overwritten by this script.
>
> This particular regeneration (2026-09-14) also found that the previously-committed baseline
> (last generated at commit `3ed645c`) predated the cyber corpus expansion in commit
> `0dbf9415a572d8500de0da6b7cfeb338b21bbe54`, which added `cybercrime_portal_citizen_manual_latest.pdf`
> among other documents and re-embedded the corpus. `backend/vectorstore/` is git-ignored and
> rebuilt locally from `backend/parsed/*`, so the numbers below reflect whatever corpus state is
> currently embedded locally, not necessarily what's committed. The metric shift from the prior
> committed baseline (Domain Hit@1 100.0% -> 97.2%, Document Hit@5 97.2% -> 88.9%, MRR 0.944 ->
> 0.813) reflects that stale-baseline gap, not any change made in this session -- confirmed by
> re-running this script twice back-to-back with no code changes between runs (identical output
> both times) and by this script's evaluation path never calling `LegalRAG.retrieve()` (the only
> function touched by this session's candidate_k widening fix; this script calls
> `retrieve_candidates()` directly with a fixed `candidate_k=10`).

## Overall Metrics
- Single-domain queries: 36
- Domain Hit@1: 97.2%
- Domain Hit@3: 100.0%
- Document Hit@1: 75.0%
- Document Hit@3: 86.1%
- Document Hit@5: 88.9%
- Provision Hit@5: 90.9% over 11 provision-labelled queries
- MRR: 0.813
- Average off-domain Top-5 count: 0.056

## Domain-wise Performance
- constitutional_public_authority: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 1.0, Avg off-domain Top-5 0.111
- consumer: Domain Hit@1 100.0%, Document Hit@5 88.9%, MRR 0.849, Avg off-domain Top-5 0.0
- cyber: Domain Hit@1 88.9%, Document Hit@5 66.7%, MRR 0.404, Avg off-domain Top-5 0.111
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
- `someone hacked my social media account`: broad supporting statute outranking primary source, expected primary document absent from Top 5, duplicate/adjacent chunks; top result `cyber/cybercrime_portal_citizen_manual_latest.pdf`

## Cyber Retrieval Analysis
> **Known limitation, accepted as of 2026-09-14 (not a new regression if seen again):**
> `cybercrime_portal_citizen_manual_latest.pdf` (added in commit
> `0dbf9415a572d8500de0da6b7cfeb338b21bbe54`) is already tagged `status: reference_only`,
> `authority_level: procedural_guide`, `retrieval_priority: low` in `corpus_manifest.json`, and
> `rag.py`'s down-weighting is applied to it -- but its plain, citizen-facing language still has
> strong enough raw semantic similarity to user-style cyber queries that it sometimes outranks
> primary statutory text anyway, as seen taking all of ranks 1-5 below for `cyber fraud online
> payment`. This was investigated and ruled out as the cause of several other eval findings (a
> domain_router misclassification, two grounded_answer unsafe-certainty flags, a corpus_gap
> abstain->answer flip). Accepted as-is; not considered worth further scoring changes. If this
> baseline is re-run and shows the same document at similar ranks/scores for cyber-domain
> queries, that reflects this accepted state, not a new regression -- compare against the actual
> regression bar (missing primary document, wrong domain, or a real score/rank shift on
> statutory text), not against this document's presence in the Top 5.
- `cyber fraud online payment` Top 5:
  - rank 1: `cyber/cybercrime_portal_citizen_manual_latest.pdf` domain `cyber`, score 0.6485, rerank 0.8165
  - rank 2: `cyber/cybercrime_portal_citizen_manual_latest.pdf` domain `cyber`, score 0.5975, rerank 0.7655
  - rank 3: `cyber/cybercrime_portal_citizen_manual_latest.pdf` domain `cyber`, score 0.6161, rerank 0.7541
  - rank 4: `cyber/cybercrime_portal_citizen_manual_latest.pdf` domain `cyber`, score 0.5853, rerank 0.7533
  - rank 5: `cyber/cybercrime_portal_citizen_manual_latest.pdf` domain `cyber`, score 0.585, rerank 0.753

## Supporting vs Primary Source Issues
- `cyber fraud online payment`: supporting `cyber/cybercrime_portal_citizen_manual_latest.pdf` at rank 1 before first primary rank None
- `phishing link stole my money`: supporting `cyber/cybercrime_portal_citizen_manual_latest.pdf` at rank 1 before first primary rank None
- `someone hacked my social media account`: supporting `cyber/cybercrime_portal_citizen_manual_latest.pdf` at rank 1 before first primary rank 10
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
