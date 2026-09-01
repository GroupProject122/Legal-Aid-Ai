# Retrieval Evaluation

## Overall Metrics
- Single-domain queries: 36
- Domain Hit@1: 100.0%
- Domain Hit@3: 100.0%
- Document Hit@1: 80.6%
- Document Hit@3: 88.9%
- Document Hit@5: 88.9%
- Provision Hit@5: 90.9% over 11 provision-labelled queries
- MRR: 0.84
- Average off-domain Top-5 count: 0.083

## Domain-wise Performance
- constitutional_public_authority: Domain Hit@1 100.0%, Document Hit@5 77.8%, MRR 0.778, Avg off-domain Top-5 0.333
- consumer: Domain Hit@1 100.0%, Document Hit@5 88.9%, MRR 0.826, Avg off-domain Top-5 0.0
- cyber: Domain Hit@1 100.0%, Document Hit@5 88.9%, MRR 0.831, Avg off-domain Top-5 0.0
- tenancy: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 0.926, Avg off-domain Top-5 0.0

## Strong Examples
- `online seller refusing refund` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `defective product and seller not replacing it` -> `consumer/consumer_protection_act_2019.pdf` (section 83)
- `misleading advertisement caused me loss` -> `consumer/misleading_ads_guidelines_2022.pdf` (guideline 4)
- `dark pattern forced me to subscribe` -> `consumer/dark_patterns_guidelines_2023.pdf` (guideline 5)
- `where can I file consumer complaint` -> `consumer/consumer_protection_act_2019.pdf` (section 17)
- `limitation period for consumer complaint` -> `consumer/consumer_protection_act_2019.pdf` (section 69)
- `can consumer commission order repair or replacement` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `cyber fraud online payment` -> `cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf` (fallback )
- `someone hacked my social media account` -> `cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf` (fallback )

## Failure Examples
- `direct selling company refusing refund`: expected primary document absent from Top 5; top result `consumer/consumer_protection_act_2019.pdf`
- `intermediary failed to remove unlawful content`: broad supporting statute outranking primary source, expected primary document absent from Top 5; top result `cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf`
- `government authority treated me unfairly`: expected primary document absent from Top 5; top result `constitutional_public_authority/right_to_information_act_2005.pdf`
- `RTI application issue`: generic/common wording; top result `constitutional_public_authority/constitution_of_india.pdf`

## Cyber Retrieval Analysis
- `cyber fraud online payment` Top 5:
  - rank 1: `cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf` domain `cyber`, score 0.4705, rerank 0.6705
  - rank 2: `cyber/information_technology_act_2000.pdf` domain `cyber`, score 0.4397, rerank 0.6127
  - rank 3: `cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf` domain `cyber`, score 0.4741, rerank 0.6111
  - rank 4: `cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf` domain `cyber`, score 0.4392, rerank 0.5942
  - rank 5: `cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf` domain `cyber`, score 0.4467, rerank 0.5567

## Supporting vs Primary Source Issues
- `phishing link stole my money`: supporting `cyber/bharatiya_nagarik_suraksha_sanhita_2023.pdf` at rank 1 before first primary rank 3
- `intermediary failed to remove unlawful content`: supporting `cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf` at rank 1 before first primary rank 7
- `dispute over rent agreement`: supporting `tenancy/transfer_of_property_act_1882.pdf` at rank 1 before first primary rank 3
- `government authority treated me unfairly`: supporting `cyber/bharatiya_nagarik_suraksha_sanhita_2023.pdf` at rank 8 before first primary rank None
- `RTI application issue`: supporting `cyber/bharatiya_nagarik_suraksha_sanhita_2023.pdf` at rank 8 before first primary rank None

## Cross-Domain Queries
- `Instagram seller took payment and blocked me`: expected ['consumer', 'cyber']; Top5 ['consumer', 'cyber']; Top10 ['consumer', 'cyber']
- `online marketplace account hacked and money lost`: expected ['consumer', 'cyber']; Top5 ['cyber']; Top10 ['consumer', 'cyber']
- `public authority leaked my personal information`: expected ['constitutional_public_authority', 'cyber']; Top5 ['constitutional_public_authority']; Top10 ['constitutional_public_authority', 'cyber']
- `government website did not respond to my RTI and exposed my data`: expected ['constitutional_public_authority', 'cyber']; Top5 ['constitutional_public_authority', 'cyber']; Top10 ['constitutional_public_authority', 'cyber']
- `landlord used online threats to force me to leave`: expected ['cyber', 'tenancy']; Top5 ['cyber', 'tenancy']; Top10 ['cyber', 'tenancy']

## Non-Legal Queries
- `weather tomorrow` -> top result `constitutional_public_authority/constitution_of_india.pdf` domain `constitutional_public_authority`
- `best pizza recipe` -> top result `constitutional_public_authority/constitution_of_india.pdf` domain `constitutional_public_authority`
- `how to learn Python` -> top result `tenancy/transfer_of_property_act_1882.pdf` domain `tenancy`

## Recommended Next Improvements
- Best-performing domain by Document Hit@5: `tenancy`.
- Weakest-performing domain by Document Hit@5: `constitutional_public_authority`.
- Consider using `retrieval_priority` and `authority_level` in reranking after this baseline is accepted.
- Review remaining document-level misses before adding heavier retrieval methods.
