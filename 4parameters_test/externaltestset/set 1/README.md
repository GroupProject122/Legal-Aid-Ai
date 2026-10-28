# Set 1 — Official Q&A

`official_qa.json`: **50 questions with official answers**, copied word for word from Indian
government FAQs. Used to score the app's answers with **ROUGE** and **BERTScore** (the official
answer is the reference). Collected 29 September 2026.

**Every item was checked to be current:** against the law in the dataset (e.g. the Consumer
Protection Act, 2019) and against current rules. FAQs that are outdated, or that contradict the
law itself, were excluded and are listed below.

## Used (50)

| Topic | Items | ids | Source | Official question numbers used |
|---|---|---|---|---|
| Consumer law | 14 | `consumer_01`–`14` | [National Consumer Helpline — Consumer Protection Act 2019](https://consumerhelpline.gov.in/public/knowledgebasedetails/Consumer%20Protection%20Act%202019) | 3, 4, 7, 11, 12, 13, 14, 29, 36, 37, 38, 39, 41, 43 |
| Cybercrime reporting | 9 | `cyber_01`–`09` | [National Cybercrime Reporting Portal FAQ](https://cybercrime.gov.in/webform/FAQ.aspx) (Ministry of Home Affairs) | purpose; other ways to remove content; crimes covered; filing other cybercrimes; evidence; what happens next; status; withdrawal; foreign offender |
| Banking ombudsman | 8 | `banking_01`–`08` | [RBI — Integrated Ombudsman Scheme 2026 FAQs](https://www.rbi.org.in/commonman/Upload/English/FAQs/PDFs/RBIOS01072026.pdf) | 9, 19, 20, 21, 28, 32, 34, 37 |
| Right to Information | 8 | `rti_01`–`08` | [Delhi Government RTI FAQs](https://dsci.delhi.gov.in/sites/default/files/dsci/rti/faq-rti_0_1.pdf) | 3, 5, 7, 15, 16, 20, 21, 29 |
| Free legal aid | 11 | `legalaid_01`–`11` | [NALSA FAQs](https://nalsa.gov.in/faqs/) | 9, 10, 11, 12, 13, 14, 16, 17, 18, 21, 27 |

**Banking:** the dataset contains the 2021 RBI scheme, which RBI replaced with the 2026 scheme
on 1 July 2026. Only 2026 questions whose rules are **unchanged from 2021** were used — how to
file, tracking, filing through a representative, no fee, what happens without a settlement,
appeal time limits, withdrawal, languages — so the answers are current *and* answerable from the
dataset.

## Excluded because outdated or wrong

| Source | Question | Problem | Current position |
|---|---|---|---|
| National Consumer Helpline Q10 | Which Commission hears which claim value? | Gives the original 2019 limits: up to ₹1 cr / ₹1–10 cr / above ₹10 cr | Changed by the Consumer Protection (Jurisdiction…) Rules, 2021 to **₹50 lakh / ₹50 lakh–2 cr / above ₹2 cr** (in the dataset) |
| National Consumer Helpline Q35 | Procedure for filing a complaint | Directs users to the **e-Daakhil** portal | e-Daakhil was merged into **e-Jagriti** on 1 January 2025 |
| National Consumer Helpline Q44 | Appeal against a Commission's order | Says District→State **30 days** and National→Supreme Court **45 days** | **Contradicts the Act**: s.41 gives **45 days** (District→State) and s.67 **30 days** (National→Supreme Court) |
| Cybercrime portal FAQ | Action on a false complaint | Cites the **Indian Penal Code** | Replaced by the Bharatiya Nyaya Sanhita, 2023 from 1 July 2024 |
| RBI 2021 scheme FAQs (all 8 used earlier) | Filing, compensation, time limits, etc. | Based on the **2021 scheme** | Replaced by the **2026 scheme** on 1 July 2026 |
| RBI 2026 FAQ Q17, 22, 23 | When to file; compensation limits | Rules **changed** in 2026 (90-day window; ₹30 lakh / ₹3 lakh) | The dataset still has the 2021 scheme (1 year; ₹20 lakh / ₹1 lakh), so it can't answer these correctly yet |
| RBI 2026 FAQ Q5, 15, 26 | Deficiency in service; grounds; rejection | Definitions and grounds **changed** in 2026 | As above |

## Excluded for other reasons

| Source | Question | Why |
|---|---|---|
| National Consumer Helpline Q45 | Filing fees | The answer is a table that doesn't survive as plain text |
| National Consumer Helpline Q8 | Can a business buyer complain? | The whole official answer is "No": too short to score |
| National Consumer Helpline Q15 | Who is liable for a misleading ad? | Oversimplifies the Act (publisher liability is qualified) |
| Cybercrime portal FAQ | CSEAM definition; hash value | Technical or definitional, not what users ask |
| Delhi RTI FAQ Q22 | Complaints under the Act | Words were lost in PDF extraction; not guessed |
| — | Tenancy | No official Delhi tenancy FAQ exists; tenancy is tested in sets 2 and 3 |

## Fields

| Field | Meaning |
|---|---|
| `question` | The official question, word for word |
| `reference_answer` | The official answer, word for word — the reference for ROUGE and BERTScore |
| `expected_sources` | Dataset documents we expect the app to retrieve (**team-assigned**, not from the source) |
| `source_title`, `source_url` | Where the item came from |
| `notes` | Original question number, and any caveat |

`domain` uses the app's own names: banking questions are `consumer` (where the RBI scheme sits in
the dataset); RTI and legal aid are `constitutional_public_authority`.

## How the text was handled

Downloaded from the official pages and extracted locally, so answers are **verbatim**. The only
edits repair PDF extraction artefacts: words split by a stray space (`t o`, `In formation`,
`rec eived`, `complaint s`, `e- mail`, `RB -IOS`, `third -party`), stray section headings at the
end of an answer (`Second Appeal`, `RTI AUTHORITIES`), RBI's standard disclaimer paragraph
appended to its last answer, and `rti_07` trimmed to its first part (the second-appeal rule) because the
list that followed was jumbled by the PDF's two-column layout.
