# Set 1 (official Q&A): results

50 questions scored. BERTScore: `roberta-large`, rescaled with baseline (unrelated text scores near 0; identical meaning near 1). Scores compare the app's **full answer** with the official answer unless marked *short* (the "In short" paragraph only).

**Run:** 50 of 50 questions scored · 11.8 min asking the app · median 11.8s per question.

## What the app did

| Outcome | Questions | BERTScore F1 | ROUGE-L | *short* BERTScore |
|---|---|---|---|---|
| Answered from the law (with sources) | 43 | 0.154 | 0.217 | 0.254 |
| Said the material was insufficient | 7 | -0.021 | 0.094 | 0.024 |

## Scores

| | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore F1 | *short* ROUGE-L | *short* BERTScore | Right law retrieved | Needed clarification |
|---|---|---|---|---|---|---|---|---|
| **Overall** (n=50) | 0.291 | 0.115 | 0.199 | 0.129 | 0.226 | 0.222 | 72% | 26% |
| consumer law (n=14) | 0.35 | 0.164 | 0.26 | 0.175 | 0.247 | 0.215 | 86% | 43% |
| cybercrime reporting (n=9) | 0.276 | 0.101 | 0.166 | 0.097 | 0.246 | 0.257 | 100% | 33% |
| banking ombudsman (RBI) (n=8) | 0.239 | 0.061 | 0.166 | 0.055 | 0.149 | 0.126 | 38% | 38% |
| right to information (n=8) | 0.279 | 0.104 | 0.191 | 0.139 | 0.268 | 0.272 | 75% | 12% |
| free legal aid (n=11) | 0.275 | 0.113 | 0.18 | 0.144 | 0.206 | 0.234 | 55% | 0% |

## Per question

| ID | ROUGE-L | BERTScore | Right law | Clarified | Question |
|---|---|---|---|---|---|
| `consumer_01` | 0.294 | 0.099 | yes | no | Who is a consumer? |
| `consumer_02` | 0.400 | 0.268 | yes | no | Who is a not a consumer? |
| `consumer_03` | 0.219 | -0.006 | no | yes | Who can make complaint? |
| `consumer_04` | 0.164 | -0.122 | yes | yes | Where the complaint can be filed? |
| `consumer_05` | 0.599 | 0.484 | yes | yes | What is meant by ‘deficiency’ under the Act? |
| `consumer_06` | 0.378 | 0.322 | yes | no | What is an unfair contract? |
| `consumer_07` | 0.479 | 0.401 | yes | no | What is a misleading advertisement? |
| `consumer_08` | 0.095 | 0.167 | yes | no | Can I claim compensation if the product itself is damaged? |
| `consumer_09` | 0.123 | 0.033 | yes | no | Can a consumer complaint be resolved through mediation? |
| `consumer_10` | 0.129 | 0.269 | yes | yes | Is there any fee to be paid for Mediation? |
| `consumer_11` | 0.073 | 0.103 | yes | yes | Can appeal be filed after settlement through mediation? |
| `consumer_12` | 0.184 | 0.117 | no | no | Does consumer need an advocate to represent his case in the Commission? |
| `consumer_13` | 0.312 | 0.251 | yes | yes | What is the time limit for filing the complaint? |
| `consumer_14` | 0.190 | 0.063 | yes | no | What reliefs are provided by Consumer Commissions? |
| `cyber_01` | 0.211 | 0.140 | yes | no | What is the purpose of National Cyber Crime Reporting Portal? |
| `cyber_02` | 0.141 | -0.003 | yes | no | Apart from this portal, are there any alternative ways to remove objectionable content from social media websites? |
| `cyber_03` | 0.210 | 0.208 | yes | no | Which type of cybercrimes I can report on the portal? |
| `cyber_04` | 0.234 | 0.192 | yes | no | How can I file the complaints about other cybercrimes? |
| `cyber_05` | 0.119 | -0.107 | yes | no | What type of information would be considered as evidence while filing my complaint related to cybercrime? |
| `cyber_06` | 0.189 | 0.205 | yes | yes | What happens once I report a complaint? |
| `cyber_07` | 0.169 | 0.080 | yes | yes | Can I check the status of my complaint? |
| `cyber_08` | 0.073 | -0.053 | yes | yes | Can I withdraw my complaint from the portal? |
| `cyber_09` | 0.150 | 0.217 | yes | no | Can I file a complaint if I am an Indian citizen but have been victimized online/ in cyberspace by a foreign national or company? |
| `banking_01` | 0.258 | 0.139 | yes | no | What is the procedure for filing a complaint before the RBI Ombudsman? |
| `banking_02` | 0.112 | 0.024 | no | no | Can the complainant track the status of a complaint lodged under RB-IOS, 2026? |
| `banking_03` | 0.111 | -0.013 | no | no | Can a complaint be filed before the RBI Ombudsman through a representative? |
| `banking_04` | 0.103 | 0.012 | no | no | Is there any charge or fee for filing a complaint with the RBI Ombudsman? |
| `banking_05` | 0.233 | 0.165 | yes | yes | What happens if the complaint is not settled by agreement? |
| `banking_06` | 0.305 | 0.189 | yes | yes | Is there any time limit for filing an appeal? |
| `banking_07` | 0.095 | -0.028 | no | yes | Can I withdraw my complaint at any stage? |
| `banking_08` | 0.106 | -0.043 | no | no | In what languages can a complaint be filed under RB-IOS, 2026? |
| `rti_01` | 0.208 | 0.360 | yes | no | Is it required to give any reason for seeking information? |
| `rti_02` | 0.093 | -0.092 | no | no | What is the Time Period for Supply of Information? |
| `rti_03` | 0.205 | 0.173 | yes | no | What is the Method of Seeking Information? |
| `rti_04` | 0.224 | 0.253 | yes | no | What is the Fee for the BPL applicant for Seeking Information? |
| `rti_05` | 0.138 | 0.004 | yes | yes | Is there any specific Format of Application? |
| `rti_06` | 0.243 | 0.103 | yes | no | Is there any provision of Appeal under the RTI Act? |
| `rti_07` | 0.174 | 0.111 | yes | no | Is there any scope for second appeal under the RTI Act? |
| `rti_08` | 0.246 | 0.201 | no | no | Is there any organization(s) exempt from providing information under RTI Act? |
| `legalaid_01` | 0.209 | 0.183 | yes | no | Whether one needs to pay for legal services provided by Legal Services Institutions constituted under the Legal Services Authorities Act, 1987? |
| `legalaid_02` | 0.250 | 0.445 | no | no | Does one have to pay any charge/fee for acquiring or submitting an application form for free legal aid? |
| `legalaid_03` | 0.034 | -0.003 | no | no | Are there any Helpline Services provided by NALSA for urgent legal assistance? |
| `legalaid_04` | 0.192 | 0.006 | no | no | How can one approach NALSA/ SLSA/ DLSA/ TLSC/ HCLSC/ SCLSC? Where can an application for legal aid be made? |
| `legalaid_05` | 0.230 | 0.195 | no | no | Can one choose a lawyer of his choice while availing free legal aid? |
| `legalaid_06` | 0.070 | 0.046 | no | no | Can one get free legal consultation only, even if one does not want to pursue a proper case in the courts? |
| `legalaid_07` | 0.183 | -0.097 | yes | no | Who is eligible to seek legal aid from the Legal Services Institutions under the Legal Services Authorities Act, 1987? What kind of cases can one apply free legal aid for? |
| `legalaid_08` | 0.248 | 0.397 | yes | no | Whether a financially independent woman is eligible for free legal aid? |
| `legalaid_09` | 0.332 | 0.255 | yes | no | Till what age is a child eligible for free legal aid? |
| `legalaid_10` | 0.176 | 0.122 | yes | no | Are Senior Citizens eligible for free legal aid? |
| `legalaid_11` | 0.058 | 0.037 | yes | no | Can persons called for questioning at the Police Station or persons arrested by the Police avail free legal aid? |
