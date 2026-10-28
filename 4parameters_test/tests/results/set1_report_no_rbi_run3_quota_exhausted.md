# Set 1 (official Q&A): results

42 questions scored. BERTScore: `roberta-large`, rescaled with baseline (unrelated text scores near 0; identical meaning near 1). Scores compare the app's **full answer** with the official answer unless marked *short* (the "In short" paragraph only).

**Run:** 42 of 42 questions scored · 6.8 min asking the app · median 9.7s per question.

## What the app did

| Outcome | Questions | BERTScore F1 | ROUGE-L | *short* BERTScore |
|---|---|---|---|---|
| Answered from the law (with sources) | 37 | 0.067 | 0.095 | 0.121 |
| Said the material was insufficient | 2 | -0.17 | 0.097 | -0.139 |
| Still asking for clarification | 3 | -0.073 | 0.048 | -0.073 |

## Scores

| | ROUGE-1 | ROUGE-2 | ROUGE-L | BERTScore F1 | *short* ROUGE-L | *short* BERTScore | Right law retrieved | Needed clarification |
|---|---|---|---|---|---|---|---|---|
| **Overall** (n=42) | 0.13 | 0.05 | 0.092 | 0.046 | 0.109 | 0.094 | 76% | 31% |
| consumer law (n=14) | 0.257 | 0.12 | 0.191 | 0.084 | 0.23 | 0.175 | 64% | 57% |
| cybercrime reporting (n=9) | 0.184 | 0.048 | 0.108 | 0.049 | 0.128 | 0.136 | 78% | 56% |
| right to information (n=8) | 0.004 | 0.0 | 0.004 | 0.014 | 0.004 | 0.014 | 88% | 0% |
| free legal aid (n=11) | 0.016 | 0.0 | 0.016 | 0.017 | 0.016 | 0.017 | 82% | 0% |

## Per question

| ID | ROUGE-L | BERTScore | Right law | Clarified | Question |
|---|---|---|---|---|---|
| `consumer_01` | 0.248 | 0.155 | yes | yes | Who is a consumer? |
| `consumer_02` | 0.049 | -0.019 | no | yes | Who is a not a consumer? |
| `consumer_03` | 0.124 | -0.163 | no | yes | Who can make complaint? |
| `consumer_04` | 0.168 | -0.136 | yes | yes | Where the complaint can be filed? |
| `consumer_05` | 0.581 | 0.465 | yes | no | What is meant by ‘deficiency’ under the Act? |
| `consumer_06` | 0.066 | -0.106 | no | yes | What is an unfair contract? |
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
| `cyber_08` | 0.000 | -0.009 | yes | yes | Can I withdraw my complaint from the portal? |
| `cyber_09` | 0.000 | 0.188 | yes | no | Can I file a complaint if I am an Indian citizen but have been victimized online/ in cyberspace by a foreign national or company? |
| `rti_01` | 0.000 | 0.187 | yes | no | Is it required to give any reason for seeking information? |
| `rti_02` | 0.000 | -0.028 | yes | no | What is the Time Period for Supply of Information? |
| `rti_03` | 0.000 | -0.031 | yes | no | What is the Method of Seeking Information? |
| `rti_04` | 0.000 | 0.043 | yes | no | What is the Fee for the BPL applicant for Seeking Information? |
| `rti_05` | 0.033 | 0.040 | no | no | Is there any specific Format of Application? |
| `rti_06` | 0.000 | -0.081 | yes | no | Is there any provision of Appeal under the RTI Act? |
| `rti_07` | 0.000 | -0.022 | yes | no | Is there any scope for second appeal under the RTI Act? |
| `rti_08` | 0.000 | 0.006 | yes | no | Is there any organization(s) exempt from providing information under RTI Act? |
| `legalaid_01` | 0.069 | 0.093 | yes | no | Whether one needs to pay for legal services provided by Legal Services Institutions constituted under the Legal Services Authorities Act, 1987? |
| `legalaid_02` | 0.105 | 0.225 | yes | no | Does one have to pay any charge/fee for acquiring or submitting an application form for free legal aid? |
| `legalaid_03` | 0.000 | 0.051 | yes | no | Are there any Helpline Services provided by NALSA for urgent legal assistance? |
| `legalaid_04` | 0.000 | -0.178 | yes | no | How can one approach NALSA/ SLSA/ DLSA/ TLSC/ HCLSC/ SCLSC? Where can an application for legal aid be made? |
| `legalaid_05` | 0.000 | -0.044 | no | no | Can one choose a lawyer of his choice while availing free legal aid? |
| `legalaid_06` | 0.000 | 0.155 | no | no | Can one get free legal consultation only, even if one does not want to pursue a proper case in the courts? |
| `legalaid_07` | 0.005 | -0.206 | yes | no | Who is eligible to seek legal aid from the Legal Services Institutions under the Legal Services Authorities Act, 1987? What kind of cases can one apply free legal aid for? |
| `legalaid_08` | 0.000 | 0.051 | yes | no | Whether a financially independent woman is eligible for free legal aid? |
| `legalaid_09` | 0.000 | -0.039 | yes | no | Till what age is a child eligible for free legal aid? |
| `legalaid_10` | 0.000 | 0.021 | yes | no | Are Senior Citizens eligible for free legal aid? |
| `legalaid_11` | 0.000 | 0.060 | yes | no | Can persons called for questioning at the Police Station or persons arrested by the Police avail free legal aid? |
