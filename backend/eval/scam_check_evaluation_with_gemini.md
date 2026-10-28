# Scam Message Checker Evaluation (with_gemini)

- Cases: 26 scam, 15 genuine
- Gemini model: gemini-flash-lite-latest
- Gemini calls unavailable: 0

## Headline metrics

| Metric | Value |
|---|---|
| Scam recall (high_risk or warning_signs) | 100.0% |
| Scams flagged high_risk | 46.2% |
| Scam type accuracy | 100.0% |
| False-alarm rate (genuine flagged high_risk) | 0.0% |
| Genuine messages with any warning | 6.7% |

## Per scam type

| Expected type | Cases | Flagged | High risk | Type correct |
|---|---|---|---|---|
| bank_kyc_fraud | 2 | 2 | 0 | 2 |
| courier_or_parcel_scam | 2 | 2 | 0 | 2 |
| digital_arrest_or_authority_threat | 3 | 3 | 3 | 3 |
| electricity_bill_scam | 2 | 2 | 0 | 2 |
| job_or_task_scam | 3 | 3 | 0 | 3 |
| loan_app_or_extortion | 2 | 2 | 1 | 2 |
| malicious_app_link | 1 | 1 | 1 | 1 |
| otp_or_credential_theft | 3 | 3 | 3 | 3 |
| prize_or_refund_scam | 3 | 3 | 0 | 3 |
| remote_access_scam | 2 | 2 | 2 | 2 |
| unknown | 1 | 1 | 0 | 1 |
| upi_collect_scam | 2 | 2 | 2 | 2 |

## Per language

| Language | Scam recall | False alarms (high_risk) | Genuine with any warning |
|---|---|---|---|
| en | 100.0% | 0.0% | 8.3% |
| hinglish | 100.0% | 0.0% | 0.0% |

## Misses and false warnings

- `genuine_kyc_branch`: expected genuine, got `warning_signs` / `bank_kyc_fraud` signs=['kyc_pan_aadhaar_update']
