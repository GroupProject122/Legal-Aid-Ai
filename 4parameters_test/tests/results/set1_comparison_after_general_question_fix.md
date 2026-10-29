# Set 1 (official Q&A) -- after the general-question fix

Run completed 2026-10-29. Compared with the re-scored baseline
(`set1_scores_before_general_question_fix_rescored.json`, n=49: `rti_01` was an empty answer in
the baseline run, so it is left out of the comparison).

| | n | Needed clarification | clarification_unresolved | Right law retrieved | BERTScore F1 | ROUGE-L |
|---|---:|---:|---:|---:|---:|---:|
| **Overall (same 49)** | 49 | 35% -> 27% | 4 -> 0 | 59% -> 71% | 0.092 -> 0.125 | 0.179 -> 0.199 |
| Consumer | 14 | 57% -> 43% | 2 -> 0 | 64% -> 86% | 0.084 -> 0.175 | 0.193 -> 0.260 |
| Cybercrime reporting | 9 | 56% -> 33% | 1 -> 0 | 67% -> 100% | 0.039 -> 0.097 | 0.127 -> 0.166 |
| Banking ombudsman (RBI) | 8 | 38% -> 38% | 1 -> 0 | 38% -> 38% | 0.035 -> 0.055 | 0.157 -> 0.166 |
| RTI | 7 | 14% -> 14% | 0 -> 0 | 71% -> 71% | 0.128 -> 0.107 | 0.196 -> 0.189 |
| Free legal aid | 11 | 0% -> 0% | 0 -> 0 | 55% -> 55% | 0.165 -> 0.144 | 0.210 -> 0.180 |

All 50 after (including `rti_01`, now answered from the RTI Act): needed clarification 26%,
clarification_unresolved 0, right law retrieved 72%, BERTScore F1 0.129, ROUGE-L 0.199.

**Read the difference with care.**
- More changed between the two runs than the general-question fix: the router fallback, the
  `consumer_006` grounded-answer fix, two retrieval changes (manuals no longer fill the
  candidate pool; whole-word procedural detection), and the corpus and index changes from the
  earlier merges.
- This run itself mixes code versions. Questions 1-28 (`consumer_01` to `banking_05`) were
  answered at midday, before the later fixes. Questions 29-50 (`banking_06` onward) ran on the
  final code of the day.

## Questions that still fail (not fixed)

**No answer -- the app judged the retrieved material insufficient (7)**
- `banking_02`, `banking_03`, `banking_04`, `banking_07`, `banking_08`: mostly a corpus mismatch.
  The questions name "RB-IOS, 2026"; the corpus holds the 2021 scheme (with 2022 amendments),
  stored without its clause structure (see the README; `set1_report_no_rbi*` exists for this
  reason). `banking_02`-`04` were answered before the day's retrieval fixes.
- `rti_02` "What is the Time Period for Supply of Information?": a real miss. RTI Act s.7
  (30 days) is in the corpus.
- `legalaid_03` NALSA helpline for urgent help: a fair refusal. The 15100 helpline is not in any
  law in the corpus (it is on the Helplines page).

**Clarification still asked first -- then answered (13)**
`consumer_03`, `04`, `05`, `10`, `11`, `13`; `cyber_06`, `07`, `08`; `banking_05`, `06`, `07`; `rti_05`.
All are the router asking which legal area, for official FAQ questions that don't name one
("Can I check the status of my complaint?"). This is deliberate; each was answered after the
scripted one-line reply.

**Answered, but cited a different document than the expected one (7)**
- `consumer_03`, `consumer_12`: the Consumer Commission Procedure Regulations instead of the Act.
  A legitimate source and the answers are right -- a labelling difference.
- `legalaid_02`, `04`, `05`, `06`: the NALSA (Free and Competent Legal Services) Regulations
  instead of the Legal Services Authorities Act. The Regulations are the more specific source for
  these questions and the answers broadly match -- a labelling difference (same pattern as e2e
  `public_004`).
- `rti_08` exempt organisations: cites *CBSE v. Aditya Bandopadhyay* instead of the RTI Act. The
  content (s.24, Second Schedule) is right, but the statute should outrank the judgment -- minor,
  real retrieval issue.

## Gemini requests
71 for questions 29-50 (no 429s). Questions 1-28 were answered earlier the same day (101
requests; earlier attempts stopped by 429s used 37 more).
