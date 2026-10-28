# Retrieval Evaluation

## Overall Metrics
- Single-domain queries: 47
- Domain Hit@1: 97.9%
- Domain Hit@3: 100.0%
- Document Hit@1: 83.0%
- Document Hit@3: 95.7%
- Document Hit@5: 97.9%
- Provision Hit@5: 85.7% over 14 provision-labelled queries
- MRR: 0.884
- Average off-domain Top-5 count: 0.064

## Domain-wise Performance
- constitutional_public_authority: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 1.0, Avg off-domain Top-5 0.091
- consumer: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 0.889, Avg off-domain Top-5 0.0
- cyber: Domain Hit@1 92.3%, Document Hit@5 92.3%, MRR 0.682, Avg off-domain Top-5 0.154
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
- Weakest-performing domain by Document Hit@5: `cyber`.
- Review remaining document-level misses before adding heavier retrieval methods.
- Consider targeted query-intent handling or domain routing only after comparing this report with earlier baselines.
