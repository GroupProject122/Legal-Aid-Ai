# Set 1 (official Q&A): results

42 questions scored. BERTScore: `roberta-large`, rescaled with baseline (unrelated text scores near 0; identical meaning near 1). Scores compare the app's **full answer** with the official answer unless marked *short* (the "In short" paragraph only).

**Run:** 42 of 42 questions scored · 15.8 min asking the app · median 21.0s per question.

## What the app did

| Outcome | Questions | BERTScore F1 | ROUGE-L | *short* BERTScore |
|---|---|---|---|---|
| Answered from the law (with sources) | 35 | 0.108 | 0.172 | 0.214 |
| Said the material was insufficient | 4 | -0.117 | 0.083 | -0.041 |
| Still asking for clarification | 3 | -0.097 | 0.07 | -0.097 |

## Scores

| | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore F1 | *short* ROUGE-L | *short* BERTScore | Right law retrieved | Needed clarification |
|---|---|---|---|---|---|---|---|---|
| **Overall** (n=42) | 0.236 | 0.074 | 0.156 | 0.072 | 0.171 | 0.167 | 62% | 36% |
| consumer law (n=14) | 0.217 | 0.072 | 0.164 | 0.038 | 0.145 | 0.099 | 50% | 64% |
| cybercrime reporting (n=9) | 0.233 | 0.056 | 0.14 | 0.062 | 0.181 | 0.183 | 78% | 56% |
| right to information (n=8) | 0.238 | 0.065 | 0.154 | 0.074 | 0.183 | 0.174 | 75% | 12% |
| free legal aid (n=11) | 0.262 | 0.1 | 0.161 | 0.121 | 0.185 | 0.237 | 55% | 0% |

## Per question

| ID | ROUGE-L | BERTScore | Right law | Clarified | Question |
|---|---|---|---|---|---|
| `consumer_01` | 0.094 | -0.037 | no | yes | Who is a consumer? |
| `consumer_02` | 0.086 | -0.139 | no | yes | Who is a not a consumer? |
| `consumer_03` | 0.174 | -0.134 | no | yes | Who can make complaint? |
| `consumer_04` | 0.217 | -0.063 | yes | yes | Where the complaint can be filed? |
| `consumer_05` | 0.616 | 0.498 | yes | yes | What is meant by ‘deficiency’ under the Act? |
| `consumer_06` | 0.066 | -0.141 | no | yes | What is an unfair contract? |
| `consumer_07` | 0.165 | -0.060 | no | no | What is a misleading advertisement? |
| `consumer_08` | 0.094 | 0.073 | yes | no | Can I claim compensation if the product itself is damaged? |
| `consumer_09` | 0.160 | 0.083 | yes | no | Can a consumer complaint be resolved through mediation? |
| `consumer_10` | 0.105 | 0.284 | yes | yes | Is there any fee to be paid for Mediation? |
| `consumer_11` | 0.078 | 0.078 | yes | yes | Can appeal be filed after settlement through mediation? |
| `consumer_12` | 0.149 | 0.123 | no | no | Does consumer need an advocate to represent his case in the Commission? |
| `consumer_13` | 0.220 | 0.137 | yes | yes | What is the time limit for filing the complaint? |
| `consumer_14` | 0.070 | -0.176 | no | no | What reliefs are provided by Consumer Commissions? |
| `cyber_01` | 0.170 | 0.040 | yes | no | What is the purpose of National Cyber Crime Reporting Portal? |
| `cyber_02` | 0.111 | -0.057 | no | no | Apart from this portal, are there any alternative ways to remove objectionable content from social media websites? |
| `cyber_03` | 0.169 | 0.057 | yes | no | Which type of cybercrimes I can report on the portal? |
| `cyber_04` | 0.195 | 0.099 | yes | yes | How can I file the complaints about other cybercrimes? |
| `cyber_05` | 0.049 | -0.113 | no | yes | What type of information would be considered as evidence while filing my complaint related to cybercrime? |
| `cyber_06` | 0.140 | 0.175 | yes | yes | What happens once I report a complaint? |
| `cyber_07` | 0.230 | 0.164 | yes | yes | Can I check the status of my complaint? |
| `cyber_08` | 0.055 | -0.009 | yes | yes | Can I withdraw my complaint from the portal? |
| `cyber_09` | 0.139 | 0.200 | yes | no | Can I file a complaint if I am an Indian citizen but have been victimized online/ in cyberspace by a foreign national or company? |
| `rti_01` | 0.108 | 0.154 | yes | no | Is it required to give any reason for seeking information? |
| `rti_02` | 0.093 | -0.092 | no | no | What is the Time Period for Supply of Information? |
| `rti_03` | 0.184 | 0.160 | yes | no | What is the Method of Seeking Information? |
| `rti_04` | 0.171 | 0.183 | yes | no | What is the Fee for the BPL applicant for Seeking Information? |
| `rti_05` | 0.180 | 0.032 | yes | yes | Is there any specific Format of Application? |
| `rti_06` | 0.194 | 0.127 | yes | no | Is there any provision of Appeal under the RTI Act? |
| `rti_07` | 0.214 | 0.088 | yes | no | Is there any scope for second appeal under the RTI Act? |
| `rti_08` | 0.085 | -0.061 | no | no | Is there any organization(s) exempt from providing information under RTI Act? |
| `legalaid_01` | 0.154 | 0.121 | yes | no | Whether one needs to pay for legal services provided by Legal Services Institutions constituted under the Legal Services Authorities Act, 1987? |
| `legalaid_02` | 0.121 | 0.215 | no | no | Does one have to pay any charge/fee for acquiring or submitting an application form for free legal aid? |
| `legalaid_03` | 0.062 | -0.044 | no | no | Are there any Helpline Services provided by NALSA for urgent legal assistance? |
| `legalaid_04` | 0.192 | -0.024 | no | no | How can one approach NALSA/ SLSA/ DLSA/ TLSC/ HCLSC/ SCLSC? Where can an application for legal aid be made? |
| `legalaid_05` | 0.281 | 0.273 | no | no | Can one choose a lawyer of his choice while availing free legal aid? |
| `legalaid_06` | 0.081 | 0.057 | no | no | Can one get free legal consultation only, even if one does not want to pursue a proper case in the courts? |
| `legalaid_07` | 0.134 | -0.046 | yes | no | Who is eligible to seek legal aid from the Legal Services Institutions under the Legal Services Authorities Act, 1987? What kind of cases can one apply free legal aid for? |
| `legalaid_08` | 0.234 | 0.359 | yes | no | Whether a financially independent woman is eligible for free legal aid? |
| `legalaid_09` | 0.260 | 0.239 | yes | no | Till what age is a child eligible for free legal aid? |
| `legalaid_10` | 0.176 | 0.117 | yes | no | Are Senior Citizens eligible for free legal aid? |
| `legalaid_11` | 0.073 | 0.068 | yes | no | Can persons called for questioning at the Police Station or persons arrested by the Police avail free legal aid? |
