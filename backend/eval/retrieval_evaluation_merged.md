# Retrieval Evaluation

## Overall Metrics
- Single-domain queries: 47
- Domain Hit@1: 97.9%
- Domain Hit@3: 100.0%
- Document Hit@1: 83.0%
- Document Hit@3: 93.6%
- Document Hit@5: 95.7%
- Provision Hit@5: 85.7% over 14 provision-labelled queries
- MRR: 0.892
- Average off-domain Top-5 count: 0.021

## Domain-wise Performance
- constitutional_public_authority: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 1.0, Avg off-domain Top-5 0.0
- consumer: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 0.917, Avg off-domain Top-5 0.0
- cyber: Domain Hit@1 92.3%, Document Hit@5 84.6%, MRR 0.686, Avg off-domain Top-5 0.077
- tenancy: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 1.0, Avg off-domain Top-5 0.0

## Strong Examples
- `online seller refusing refund` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `defective product and seller not replacing it` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `misleading advertisement caused me loss` -> `consumer/consumer_protection_act_2019.pdf` (section 2)
- `dark pattern forced me to subscribe` -> `consumer/dark_patterns_guidelines_2023.pdf` (guideline 5)
- `where can I file consumer complaint` -> `consumer/consumer_protection_act_2019.pdf` (section 17)
- `limitation period for consumer complaint` -> `consumer/consumer_protection_act_2019.pdf` (section 69)
- `can consumer commission order repair or replacement` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `cyber fraud online payment` -> `cyber/information_technology_act_2000.pdf` (section 66)
- `phishing link stole my money` -> `cyber/information_technology_act_2000.pdf` (section 66C)

## Failure Examples
- `intermediary failed to remove unlawful content`: expected primary document absent from Top 5; top result `cyber/information_technology_act_2000.pdf`
- `someone shared private data online`: expected primary document absent from Top 5; top result `cyber/digital_personal_data_protection_act_2023.pdf`

## Cyber Retrieval Analysis
- `cyber fraud online payment` Top 5:
  - rank 1: `cyber/information_technology_act_2000.pdf` domain `cyber`, score 0.505, rerank 0.74
  - rank 2: `cyber/rbi_limiting_liability_unauthorised_transactions_2017.pdf` domain `cyber`, score 0.5204, rerank 0.7384
  - rank 3: `cyber/cert_in_directions_2022.pdf` domain `cyber`, score 0.5074, rerank 0.6994
  - rank 4: `cyber/information_technology_act_2000.pdf` domain `cyber`, score 0.4397, rerank 0.6927
  - rank 5: `cyber/it_intermediary_guidelines_digital_media_ethics_code_rules_2021.pdf` domain `cyber`, score 0.4543, rerank 0.6623

## Supporting vs Primary Source Issues
- `someone hacked my social media account`: supporting `cyber/cybercrime_portal_citizen_manual_latest.pdf` at rank 1 before first primary rank 2
- `how to report online cybercrime`: supporting `cyber/cybercrime_portal_citizen_manual_latest.pdf` at rank 1 before first primary rank 3

## Cross-Domain Queries
- `Instagram seller took payment and blocked me`: expected ['consumer', 'cyber']; Top5 ['consumer', 'cyber']; Top10 ['consumer', 'cyber']
- `online marketplace account hacked and money lost`: expected ['consumer', 'cyber']; Top5 ['cyber']; Top10 ['cyber']
- `public authority leaked my personal information`: expected ['constitutional_public_authority', 'cyber']; Top5 ['constitutional_public_authority']; Top10 ['constitutional_public_authority', 'cyber']
- `government website did not respond to my RTI and exposed my data`: expected ['constitutional_public_authority', 'cyber']; Top5 ['constitutional_public_authority']; Top10 ['constitutional_public_authority']
- `landlord used online threats to force me to leave`: expected ['cyber', 'tenancy']; Top5 ['tenancy']; Top10 ['tenancy']

## Non-Legal Queries
- `weather tomorrow` -> top result `constitutional_public_authority/constitution_of_india.pdf` domain `constitutional_public_authority`
- `best pizza recipe` -> top result `constitutional_public_authority/constitution_of_india.pdf` domain `constitutional_public_authority`
- `how to learn Python` -> top result `constitutional_public_authority/right_to_education_act_2009.pdf` domain `constitutional_public_authority`

## Recommended Next Improvements
- Best-performing domain by Document Hit@5: `constitutional_public_authority`.
- Weakest-performing domain by Document Hit@5: `cyber`.
- Review remaining document-level misses before adding heavier retrieval methods.
- Consider targeted query-intent handling or domain routing only after comparing this report with earlier baselines.
