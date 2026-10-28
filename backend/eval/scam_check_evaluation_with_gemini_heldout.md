# Scam Message Checker Evaluation (with_gemini)

- Cases: 8 scam, 4 genuine
- Gemini model: gemini-flash-lite-latest
- Gemini calls unavailable: 0

## Headline metrics

| Metric | Value |
|---|---|
| Scam recall (high_risk or warning_signs) | 100.0% |
| Scams flagged high_risk | 25.0% |
| Scam type accuracy | 75.0% |
| False-alarm rate (genuine flagged high_risk) | 0.0% |
| Genuine messages with any warning | 0.0% |

## Per scam type

| Expected type | Cases | Flagged | High risk | Type correct |
|---|---|---|---|---|
| bank_kyc_fraud | 1 | 1 | 0 | 1 |
| digital_arrest_or_authority_threat | 1 | 1 | 1 | 1 |
| electricity_bill_scam | 1 | 1 | 0 | 1 |
| job_or_task_scam | 1 | 1 | 0 | 1 |
| otp_or_credential_theft | 1 | 1 | 0 | 1 |
| prize_or_refund_scam | 1 | 1 | 0 | 0 |
| remote_access_scam | 1 | 1 | 1 | 1 |
| unknown | 1 | 1 | 0 | 0 |

## Per language

| Language | Scam recall | False alarms (high_risk) | Genuine with any warning |
|---|---|---|---|
| en | 100.0% | 0.0% | 0.0% |
| hinglish | 100.0% | 0.0% | 0.0% |

## Misses and false warnings

- `ho_scam_prize_hinglish`: expected prize_or_refund_scam, got `warning_signs` / `job_or_task_scam` signs=['unexpected_prize_or_refund', 'job_or_task_offer', 'ai_urgency_or_pressure']
- `ho_scam_wrong_transfer`: expected unknown, got `warning_signs` / `upi_collect_scam` signs=['urgency_or_threat', 'ai_emotional_manipulation']
