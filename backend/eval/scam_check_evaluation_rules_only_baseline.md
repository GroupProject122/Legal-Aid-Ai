# Scam Message Checker Evaluation (rules_only) -- BASELINE, before rule fixes

- Cases: 26 scam, 15 genuine
- Gemini model: not used
- Gemini calls unavailable: 0

## Headline metrics

| Metric | Value |
|---|---|
| Scam recall (high_risk or warning_signs) | 88.5% |
| Scams flagged high_risk | 34.6% |
| Scam type accuracy | 80.8% |
| False-alarm rate (genuine flagged high_risk) | 0.0% |
| Genuine messages with any warning | 6.7% |

## Per scam type

| Expected type | Cases | Flagged | High risk | Type correct |
|---|---|---|---|---|
| bank_kyc_fraud | 2 | 2 | 0 | 2 |
| courier_or_parcel_scam | 2 | 2 | 0 | 2 |
| digital_arrest_or_authority_threat | 3 | 3 | 2 | 2 |
| electricity_bill_scam | 2 | 2 | 0 | 2 |
| job_or_task_scam | 3 | 3 | 0 | 3 |
| loan_app_or_extortion | 2 | 1 | 1 | 1 |
| malicious_app_link | 1 | 1 | 1 | 0 |
| otp_or_credential_theft | 3 | 2 | 2 | 2 |
| prize_or_refund_scam | 3 | 3 | 0 | 3 |
| remote_access_scam | 2 | 2 | 2 | 2 |
| unknown | 1 | 1 | 0 | 1 |
| upi_collect_scam | 2 | 1 | 1 | 1 |

## Per language

| Language | Scam recall | False alarms (high_risk) | Genuine with any warning |
|---|---|---|---|
| en | 88.2% | 0.0% | 8.3% |
| hinglish | 88.9% | 0.0% | 0.0% |

## Misses and false warnings

- `scam_otp_03_en_cvv`: expected otp_or_credential_theft, got `no_common_signs` / `unknown` signs=[]
- `scam_electricity_03_apk`: expected malicious_app_link, got `high_risk` / `electricity_bill_scam` signs=['impersonates_bank_or_authority', 'link_apk_file']
- `scam_upi_02_hinglish`: expected upi_collect_scam, got `no_common_signs` / `unknown` signs=[]
- `scam_loan_01_en`: expected loan_app_or_extortion, got `no_common_signs` / `unknown` signs=[]
- `scam_trai_01_en`: expected digital_arrest_or_authority_threat, got `warning_signs` / `unknown` signs=['urgency_or_threat', 'impersonates_bank_or_authority']
- `genuine_kyc_branch`: expected genuine, got `warning_signs` / `bank_kyc_fraud` signs=['kyc_pan_aadhaar_update']
