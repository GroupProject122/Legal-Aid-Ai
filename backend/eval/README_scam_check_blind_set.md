# Scam checker blind test set

A test set the scam checker's rules and Gemini prompt were **not** tuned on, so it gives an honest
idea of how the checker does on messages it has never seen. Two parts:

| Part | File | Status |
|---|---|---|
| Scam messages, published by official sources | `scam_check_cases_blind.json` | **2 of ~20** -- needs collecting by hand |
| Genuine messages, from the team's own phones | `scam_check_genuine_submissions_template.json` | **0 of ~15** -- needs adding |

**Rule for everyone:** do not change the checker's rules or prompt because of a case in this set.
If the checker misses something, write the miss and a suggested fix in the PR or an issue. Once a
case has been used to change the checker, it is no longer blind -- move it to
`scam_check_cases.json` instead.

## Adding scam messages (scam part)

Only messages an official source **shows word for word** -- never write one yourself, and never
"improve" one. Good places (see `to_collect` in the JSON for which scam types are still missing):

- **PIB Fact Check** posts (pib.gov.in fact check pages, @PIBFactCheck): screenshots of real
  fake messages, mostly government-scheme and KYC scams.
- **I4C / @Cyberdost** posts and advisories (digital arrest, courier, job/task scams).
- **RBI** cautions and the BE(A)WARE booklet; **CERT-In** advisories; **TRAI** and **DoT /
  Sanchar Saathi** releases; your bank's fraud-awareness pages.

Why by hand: on 2026-10-29 PIB's site refused automated downloads, and most other official
pages describe scams instead of quoting them. Open the page in a normal browser and copy the text.

For each message add an entry like the existing two, with:

- `message`: the text exactly as published, with real phone numbers, account numbers and the
  identifying part of links masked (keep the link's domain and shape, e.g.
  `http://xxxxxxxxxxxx.ngrok.io/xxxbank`), and a `masking_note` saying what you changed;
- `expected_type`: one of the checker's types (`bank_kyc_fraud`, `electricity_bill_scam`,
  `courier_or_parcel_scam`, `digital_arrest_or_authority_threat`, `job_or_task_scam`,
  `prize_or_refund_scam`, `loan_app_or_extortion`, `malicious_app_link`, `remote_access_scam`,
  `otp_or_credential_theft`, `phishing_link`, `upi_collect_scam`, `unknown`);
- `source_category` (the source's own words), `source_name`, `source_url`, `source_date`,
  `retrieved`, `language` (`en`, `hinglish`, `hi`).

Pick messages to cover the types in `to_collect` -- about two per type -- not ones you expect the
checker to catch or miss.

## Adding genuine messages (genuine part)

Real messages you received that are **not** scams: bank alerts, OTP messages you asked for,
delivery updates, electricity/phone bills, government messages, a message from a friend.
Replace personal details as listed in the template's `replace_before_adding` (names, numbers,
OTPs, addresses, identifying parts of links). Keep sender IDs such as `AD-HDFCBK` -- the checker
may use them. Add each as a case with `"label": "genuine"`.

Merge the genuine cases into `scam_check_cases_blind.json` (same `cases` list) once checked by a
second person for leftover personal details.

## Running it

Rules only (no Gemini, free, run as often as you like):

```bash
cd backend
python evaluate_scam_checker.py --cases eval/scam_check_cases_blind.json --tag blind
```

With Gemini (one request per message -- check the team's daily quota first; the app shares the key):

```bash
python evaluate_scam_checker.py --cases eval/scam_check_cases_blind.json --with-gemini --delay 2 --tag blind
```

Reports are written to `eval/scam_check_evaluation_<mode>_blind.{json,md}`.
The reports give recall per scam type (scam part) and false alarms (genuine part).
