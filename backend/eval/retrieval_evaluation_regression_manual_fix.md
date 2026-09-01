# Retrieval Evaluation

## Overall Metrics
- Single-domain queries: 36
- Domain Hit@1: 100.0%
- Domain Hit@3: 100.0%
- Document Hit@1: 91.7%
- Document Hit@3: 97.2%
- Document Hit@5: 97.2%
- Provision Hit@5: 90.9% over 11 provision-labelled queries
- MRR: 0.943
- Average off-domain Top-5 count: 0.028

## Domain-wise Performance
- constitutional_public_authority: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 1.0, Avg off-domain Top-5 0.111
- consumer: Domain Hit@1 100.0%, Document Hit@5 88.9%, MRR 0.827, Avg off-domain Top-5 0.0
- cyber: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 0.944, Avg off-domain Top-5 0.0
- tenancy: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 1.0, Avg off-domain Top-5 0.0

## Strong Examples
- `online seller refusing refund` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `defective product and seller not replacing it` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `misleading advertisement caused me loss` -> `consumer/consumer_protection_act_2019.pdf` (section 89)
- `dark pattern forced me to subscribe` -> `consumer/dark_patterns_guidelines_2023.pdf` (guideline 5)
- `where can I file consumer complaint` -> `consumer/consumer_protection_act_2019.pdf` (section 17)
- `limitation period for consumer complaint` -> `consumer/consumer_protection_act_2019.pdf` (section 69)
- `can consumer commission order repair or replacement` -> `consumer/consumer_protection_act_2019.pdf` (section 39)
- `cyber fraud online payment` -> `cyber/information_technology_act_2000.pdf` (section 66C)
- `phishing link stole my money` -> `cyber/information_technology_act_2000.pdf` (section 66C)

## Failure Examples
- `direct selling company refusing refund`: expected primary document absent from Top 5; top result `consumer/consumer_protection_act_2019.pdf`

## Cyber Retrieval Analysis
- `cyber fraud online payment` Top 5:
  - rank 1: `cyber/information_technology_act_2000.pdf` domain `cyber`, score 0.4397, rerank 0.6927
  - rank 2: `cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf` domain `cyber`, score 0.4705, rerank 0.6085
  - rank 3: `cyber/it_intermediary_guidelines_digital_media_ethics_code_rules_2021.pdf` domain `cyber`, score 0.4659, rerank 0.5789
  - rank 4: `cyber/it_intermediary_guidelines_digital_media_ethics_code_rules_2021.pdf` domain `cyber`, score 0.4548, rerank 0.5498
  - rank 5: `cyber/national_cybercrime_reporting_portal_user_manual_2019.pdf` domain `cyber`, score 0.4741, rerank 0.5491

## Supporting vs Primary Source Issues
- No supporting-only source outranked expected primary documents under this test set.

## Cross-Domain Queries
- `Instagram seller took payment and blocked me`: expected ['consumer', 'cyber']; Top5 ['consumer', 'cyber']; Top10 ['consumer', 'cyber']
- `online marketplace account hacked and money lost`: expected ['consumer', 'cyber']; Top5 ['cyber']; Top10 ['consumer', 'cyber']
- `public authority leaked my personal information`: expected ['constitutional_public_authority', 'cyber']; Top5 ['constitutional_public_authority']; Top10 ['constitutional_public_authority', 'cyber']
- `government website did not respond to my RTI and exposed my data`: expected ['constitutional_public_authority', 'cyber']; Top5 ['constitutional_public_authority']; Top10 ['constitutional_public_authority', 'cyber']
- `landlord used online threats to force me to leave`: expected ['cyber', 'tenancy']; Top5 ['cyber', 'tenancy']; Top10 ['cyber', 'tenancy']

## Non-Legal Queries
- `weather tomorrow` -> top result `constitutional_public_authority/constitution_of_india.pdf` domain `constitutional_public_authority`
- `best pizza recipe` -> top result `constitutional_public_authority/constitution_of_india.pdf` domain `constitutional_public_authority`
- `how to learn Python` -> top result `constitutional_public_authority/constitution_of_india.pdf` domain `constitutional_public_authority`

## Recommended Next Improvements
- Best-performing domain by Document Hit@5: `constitutional_public_authority`.
- Weakest-performing domain by Document Hit@5: `consumer`.
- Review remaining document-level misses before adding heavier retrieval methods.
- Consider targeted query-intent handling or domain routing only after comparing this report with earlier baselines.
