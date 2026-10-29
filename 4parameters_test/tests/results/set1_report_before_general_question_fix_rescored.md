# Set 1 (official Q&A): results

49 questions scored. BERTScore: `roberta-large`, rescaled with baseline (unrelated text scores near 0; identical meaning near 1). Scores compare the app's **full answer** with the official answer unless marked *short* (the "In short" paragraph only).

**Run:** 49 of 50 questions scored · 11.7 min asking the app · median 13.6s per question.

## What the app did

| Outcome | Questions | BERTScore F1 | ROUGE-L | *short* BERTScore |
|---|---|---|---|---|
| Answered from the law (with sources) | 37 | 0.148 | 0.208 | 0.255 |
| Said the material was insufficient | 8 | -0.092 | 0.097 | -0.045 |
| Still asking for clarification | 4 | -0.05 | 0.077 | -0.05 |

## Scores

| | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore F1 | *short* ROUGE-L | *short* BERTScore | Right law retrieved | Needed clarification |
|---|---|---|---|---|---|---|---|---|
| **Overall** (n=49) | 0.257 | 0.096 | 0.179 | 0.092 | 0.195 | 0.181 | 59% | 35% |
| consumer law (n=14) | 0.263 | 0.121 | 0.193 | 0.084 | 0.232 | 0.174 | 64% | 57% |
| cybercrime reporting (n=9) | 0.209 | 0.056 | 0.127 | 0.039 | 0.151 | 0.147 | 67% | 56% |
| banking ombudsman (RBI) (n=8) | 0.212 | 0.058 | 0.157 | 0.035 | 0.148 | 0.09 | 38% | 38% |
| right to information (n=7) | 0.29 | 0.092 | 0.196 | 0.128 | 0.224 | 0.225 | 71% | 14% |
| free legal aid (n=11) | 0.301 | 0.126 | 0.21 | 0.165 | 0.202 | 0.256 | 55% | 0% |

## Per question

| ID | ROUGE-L | BERTScore | Right law | Clarified | Question |
|---|---|---|---|---|---|
| `consumer_01` | 0.248 | 0.155 | yes | yes | Who is a consumer? |
| `consumer_02` | 0.049 | -0.019 | no | yes | Who is a not a consumer? |
| `consumer_03` | 0.124 | -0.163 | no | yes | Who can make complaint? |
| `consumer_04` | 0.168 | -0.136 | yes | yes | Where the complaint can be filed? |
| `consumer_05` | 0.581 | 0.465 | yes | no | What is meant by ‘deficiency’ under the Act? |
| `consumer_06` | 0.095 | -0.111 | no | yes | What is an unfair contract? |
| `consumer_07` | 0.679 | 0.529 | yes | no | What is a misleading advertisement? |
| `consumer_08` | 0.102 | 0.172 | yes | no | Can I claim compensation if the product itself is damaged? |
| `consumer_09` | 0.150 | 0.069 | yes | no | Can a consumer complaint be resolved through mediation? |
| `consumer_10` | 0.032 | 0.066 | yes | yes | Is there any fee to be paid for Mediation? |
| `consumer_11` | 0.053 | 0.068 | yes | yes | Can appeal be filed after settlement through mediation? |
| `consumer_12` | 0.127 | 0.107 | no | no | Does consumer need an advocate to represent his case in the Commission? |
| `consumer_13` | 0.230 | 0.149 | yes | yes | What is the time limit for filing the complaint? |
| `consumer_14` | 0.070 | -0.176 | no | no | What reliefs are provided by Consumer Commissions? |
| `cyber_01` | 0.168 | 0.044 | yes | no | What is the purpose of National Cyber Crime Reporting Portal? |
| `cyber_02` | 0.124 | 0.040 | no | no | Apart from this portal, are there any alternative ways to remove objectionable content from social media websites? |
| `cyber_03` | 0.153 | -0.000 | yes | no | Which type of cybercrimes I can report on the portal? |
| `cyber_04` | 0.168 | 0.068 | yes | yes | How can I file the complaints about other cybercrimes? |
| `cyber_05` | 0.029 | -0.094 | no | yes | What type of information would be considered as evidence while filing my complaint related to cybercrime? |
| `cyber_06` | 0.121 | 0.071 | yes | yes | What happens once I report a complaint? |
| `cyber_07` | 0.206 | 0.138 | yes | yes | Can I check the status of my complaint? |
| `cyber_08` | 0.056 | -0.111 | no | yes | Can I withdraw my complaint from the portal? |
| `cyber_09` | 0.118 | 0.195 | yes | no | Can I file a complaint if I am an Indian citizen but have been victimized online/ in cyberspace by a foreign national or company? |
| `banking_01` | 0.289 | 0.168 | yes | no | What is the procedure for filing a complaint before the RBI Ombudsman? |
| `banking_02` | 0.166 | 0.052 | yes | no | Can the complainant track the status of a complaint lodged under RB-IOS, 2026? |
| `banking_03` | 0.111 | -0.013 | no | no | Can a complaint be filed before the RBI Ombudsman through a representative? |
| `banking_04` | 0.233 | 0.234 | yes | no | Is there any charge or fee for filing a complaint with the RBI Ombudsman? |
| `banking_05` | 0.092 | -0.041 | no | yes | What happens if the complaint is not settled by agreement? |
| `banking_06` | 0.122 | -0.100 | no | yes | Is there any time limit for filing an appeal? |
| `banking_07` | 0.133 | 0.024 | no | yes | Can I withdraw my complaint at any stage? |
| `banking_08` | 0.106 | -0.043 | no | no | In what languages can a complaint be filed under RB-IOS, 2026? |
| `rti_02` | 0.093 | -0.092 | no | no | What is the Time Period for Supply of Information? |
| `rti_03` | 0.177 | 0.097 | yes | no | What is the Method of Seeking Information? |
| `rti_04` | 0.267 | 0.278 | yes | no | What is the Fee for the BPL applicant for Seeking Information? |
| `rti_05` | 0.175 | 0.067 | yes | yes | Is there any specific Format of Application? |
| `rti_06` | 0.235 | 0.157 | yes | no | Is there any provision of Appeal under the RTI Act? |
| `rti_07` | 0.169 | 0.110 | yes | no | Is there any scope for second appeal under the RTI Act? |
| `rti_08` | 0.257 | 0.283 | no | no | Is there any organization(s) exempt from providing information under RTI Act? |
| `legalaid_01` | 0.183 | 0.143 | yes | no | Whether one needs to pay for legal services provided by Legal Services Institutions constituted under the Legal Services Authorities Act, 1987? |
| `legalaid_02` | 0.449 | 0.629 | no | no | Does one have to pay any charge/fee for acquiring or submitting an application form for free legal aid? |
| `legalaid_03` | 0.056 | -0.094 | no | no | Are there any Helpline Services provided by NALSA for urgent legal assistance? |
| `legalaid_04` | 0.187 | 0.029 | no | no | How can one approach NALSA/ SLSA/ DLSA/ TLSC/ HCLSC/ SCLSC? Where can an application for legal aid be made? |
| `legalaid_05` | 0.267 | 0.227 | no | no | Can one choose a lawyer of his choice while availing free legal aid? |
| `legalaid_06` | 0.113 | 0.134 | no | no | Can one get free legal consultation only, even if one does not want to pursue a proper case in the courts? |
| `legalaid_07` | 0.158 | -0.083 | yes | no | Who is eligible to seek legal aid from the Legal Services Institutions under the Legal Services Authorities Act, 1987? What kind of cases can one apply free legal aid for? |
| `legalaid_08` | 0.312 | 0.399 | yes | no | Whether a financially independent woman is eligible for free legal aid? |
| `legalaid_09` | 0.316 | 0.238 | yes | no | Till what age is a child eligible for free legal aid? |
| `legalaid_10` | 0.171 | 0.081 | yes | no | Are Senior Citizens eligible for free legal aid? |
| `legalaid_11` | 0.093 | 0.109 | yes | no | Can persons called for questioning at the Police Station or persons arrested by the Police avail free legal aid? |

Not scored (no answer): rti_01
