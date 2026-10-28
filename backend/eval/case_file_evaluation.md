# Case File Export Evaluation

## Overall Results
- Cases: 5 (5 passed)
- Checks: 119/119 passed
- LLM calls made: 0 (the case file is assembled, not generated)

## Per Case
- `consumer_receipt_document` -> PASS; sections=['cover', 'situation', 'facts', 'timeline', 'laws', 'where_to_go', 'evidence', 'lawyer_questions', 'free_legal_help', 'appendix']; laws=2; sources resolved 2/2
  - Consumer case with a confirmed receipt document (facts from it must name the document), a dated purchase, and one unverified source that must be excluded.
- `cyber_correction` -> PASS; sections=['cover', 'situation', 'facts', 'laws', 'where_to_go', 'evidence', 'lawyer_questions', 'free_legal_help', 'appendix']; laws=2; sources resolved 2/2
  - Cyber case where the user corrects a count: 'actually it was 3 transactions, not 2'. The old fact must be replaced, not shown alongside.
- `tenancy_no_dates` -> PASS; sections=['cover', 'situation', 'facts', 'laws', 'where_to_go', 'lawyer_questions', 'free_legal_help', 'appendix']; laws=1; sources resolved 1/1
  - Tenancy case with no full dates anywhere ('last week' only): Timeline must be omitted; no evidence items or documents, so Evidence is omitted too. Two chunks of the same provision must de-duplicate to one law entry.
- `consumer_case_law_and_summary` -> PASS; sections=['cover', 'situation', 'facts', 'timeline', 'laws', 'where_to_go', 'evidence', 'lawyer_questions', 'free_legal_help', 'appendix']; laws=3; sources resolved 3/3
  - Sources include case law, a compiled summary and official guidance -- each must carry its own label. A second answer has no verification record (saved before it was persisted) and its source must be left out with a note.
- `cyber_otp_redaction` -> PASS; sections=['cover', 'situation', 'facts', 'timeline', 'laws', 'where_to_go', 'evidence', 'lawyer_questions', 'free_legal_help', 'appendix']; laws=1; sources resolved 1/1
  - The user typed an OTP, a spaced Aadhaar-like number, a password and a card number into messages. None may reach the file. Also carries Hinglish, special characters (& < >) and a long unbroken URL for the rendering check.
