# Scam Message Checker Evaluation (rules_only)

- Cases: 2 scam, 0 genuine
- Gemini model: not used
- Gemini calls unavailable: 0

## Headline metrics

| Metric | Value |
|---|---|
| Scam recall (high_risk or warning_signs) | 100.0% |
| Scams flagged high_risk | 50.0% |
| Scam type accuracy | 100.0% |
| False-alarm rate (genuine flagged high_risk) | 0.0% |
| Genuine messages with any warning | 0.0% |

## Per scam type

| Expected type | Cases | Flagged | High risk | Type correct |
|---|---|---|---|---|
| bank_kyc_fraud | 1 | 1 | 0 | 1 |
| upi_collect_scam | 1 | 1 | 1 | 1 |

## Per language

| Language | Scam recall | False alarms (high_risk) | Genuine with any warning |
|---|---|---|---|
| en | 100.0% | 0.0% | 0.0% |

## Misses and false warnings

- None.
