# Set 3 — Right law (retrieval)

**File:** `right_law.json` (24 questions)
**Table:** `Set3_Right_Law_Test_Set.pdf` — every question with its expected law, domain and a link to the source decision
(rebuild with `python make_set3_report.py` from `tests/`)
**Tests:** whether the app's search finds the law a real decision actually applied.
**Metrics:** Document Hit@1 / Hit@5, Section (provision) Hit@5, MRR.

## How it was made

Each question comes from a real, published Indian decision (Indian Kanoon links are in `source_url`).
The facts of the decision were rewritten in plain first-person words, the way a user would type them,
without naming any Act or section. The expected answer is the corpus document(s) holding the law
the decision applied, and the section numbers it relied on.

| Area | Questions | Sources |
|---|---|---|
| Consumer | 6 | State consumer commissions, NCDRC |
| Cyber / digital banking fraud | 6 | Consumer commissions, Delhi HC, AP HC, IT adjudication |
| Tenancy (Delhi) | 6 | Delhi HC, Rent Control Tribunal, Delhi district courts |
| RTI | 6 | Central Information Commission |

Rules followed:
- No decision that is itself in the app's corpus was used.
- Old IPC sections in cyber cases are mapped to the matching BNS sections, since the corpus has BNS.
- A decision's outcome does not matter here — only which law applied.
- "Expected documents" include the main document plus closely related corpus documents that are also correct
  (e.g. a Supreme Court case interpreting the same section). This makes Document Hit@5 lenient;
  **Section Hit@5 is the stricter number.**
- `expected_law` gives the law in readable form with sub-sections (e.g. s.14(1)(e)); it is for people, not scoring.
- Section numbers are bare numbers ("14", not "14(1)(e)") because that is how the index labels them.

## Run it

```
cd 4parameters_test/tests
python evaluate_retrieval_set3.py
```

No Gemini calls and no running server needed. Results go to `tests/results/set3_retrieval.json` and `.md`.
