# Retrieval Evaluation

## Overall Metrics
- Single-domain queries: 24
- Domain Hit@1: 95.8%
- Domain Hit@3: 100.0%
- Document Hit@1: 87.5%
- Document Hit@3: 100.0%
- Document Hit@5: 100.0%
- Provision Hit@5: 54.2% over 24 provision-labelled queries
- MRR: 0.931
- Average off-domain Top-5 count: 0.125

## Domain-wise Performance
- constitutional_public_authority: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 1.0, Avg off-domain Top-5 0.0
- consumer: Domain Hit@1 83.3%, Document Hit@5 100.0%, MRR 0.806, Avg off-domain Top-5 0.5
- cyber: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 0.917, Avg off-domain Top-5 0.0
- tenancy: Domain Hit@1 100.0%, Document Hit@5 100.0%, MRR 1.0, Avg off-domain Top-5 0.0

## Strong Examples
- `I was admitted to hospital for eight days with typhoid and a urine infection and paid 68,000 rupees. My health insurer rejected the claim saying hospitalisation was not needed. Where can I complain?` -> `consumer/insurance_ombudsman_rules_2017.pdf` (rule 17)
- `We paid a builder about 13 lakh rupees for a flat but never got possession. The builder's man took the refund cheques and never paid us back. Can we get a refund with interest?` -> `consumer/case_law/case3_experion_developers_v_sushma_ashok_shiroor_2022.pdf` (judgment_paragraph 15)
- `I ordered a new HP laptop on Amazon for 27,190 rupees and received an old damaged one. I uploaded photos and asked for a return but nobody replied and the return window closed. What are my rights?` -> `consumer/consumer_protection_act_2019.pdf` (section 83)
- `I ordered a foldable laptop desk online and got a dirty rice bowl instead. The platform refused to replace it saying the return window was over and that it is only an intermediary, not the seller. Is the platform responsible?` -> `consumer/ecommerce_rules_2020.pdf` (rule 6)
- `I left my ATM card in the machine by mistake. Three days later five withdrawals of 39,000 rupees were made from my account. I told the bank within two days but it refunded only 14,000. Is the bank liable for the rest?` -> `cyber/rbi_limiting_liability_unauthorised_transactions_2017.pdf` (guideline 14)
- `I got a call saying my SMS service would be blocked and an SMS link to click. After I clicked it, 2.6 lakh rupees were taken from my account by net banking. I told the bank at once, but the ombudsman gave back only 33,000. What can I do?` -> `consumer/rbi_integrated_ombudsman_scheme_2021.pdf` (guideline 8)
- `I am a seafarer. While I was on the ship, 98 online card transactions worth about 12.8 lakh rupees were made from my account. I never shared my PIN and never got any SMS or email alerts. The bank refunded only part. Can I claim compensation?` -> `cyber/rbi_limiting_liability_unauthorised_transactions_2017.pdf` (guideline 10)
- `Someone in my family is posting vulgar messages and my photos with my phone number on WhatsApp and social media, calling me a prostitute. A court already told him to stop. What law covers this and how do I get the posts removed?` -> `cyber/cybercrime_portal_citizen_manual_latest.pdf` (manual_section 5.1.1.1)
- `I took a small loan from a mobile loan app and have already repaid more than I borrowed. Their agents keep threatening to send morphed nude photos of me to everyone in my contacts. What can I do?` -> `cyber/cybercrime_portal_citizen_manual_latest.pdf` (manual_section 5.5.1.1)

## Failure Examples
- No clear failures under the current labels.

## Cyber Retrieval Analysis

## Supporting vs Primary Source Issues
- No supporting-only source outranked expected primary documents under this test set.

## Cross-Domain Queries

## Non-Legal Queries

## Recommended Next Improvements
- Best-performing domain by Document Hit@5: `constitutional_public_authority`.
- Weakest-performing domain by Document Hit@5: `constitutional_public_authority`.
- Review remaining document-level misses before adding heavier retrieval methods.
- Consider targeted query-intent handling or domain routing only after comparing this report with earlier baselines.
