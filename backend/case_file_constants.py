"""Fixed text for the Case File export (case_file.py). Everything here is the same for every
case -- nothing in this module is generated per case, and nothing in the case file is written by
an LLM (see case_file.py's module docstring)."""
from __future__ import annotations

CASE_FILE_HEADING = "Case File — prepared with Legal Aid AI"

NOT_LEGAL_ADVICE_NOTICE = (
    "This is legal information to help you explain your situation. It is not legal advice and "
    "has not been reviewed by a lawyer."
)

HOW_THIS_FILE_WAS_MADE = (
    "Everything in this file was assembled from your saved conversation with Legal Aid AI: what "
    "you told us, facts you confirmed from documents you uploaded, and the legal sources the app "
    "retrieved and checked while answering you. Nothing new was written for this file. Facts are "
    "recorded as you stated them; they have not been checked or proven."
)

DOMAIN_LABELS = {
    "consumer": "Consumer",
    "cyber": "Cyber",
    "tenancy": "Tenancy",
    "constitutional_public_authority": "Public authority / constitutional rights",
}

# Generic on purpose: the same list for every case, never tailored by an LLM.
LAWYER_QUESTIONS = (
    "Is my complaint still within time? Is there a deadline I should know about?",
    "Which forum, court or authority should I file in?",
    "What documents or evidence do I still need?",
    "What will it cost (fees, lawyer's charges), and do I qualify for free legal aid?",
    "What outcome can I realistically expect, and how long might it take?",
    "Should I send a notice or try to settle before filing?",
    "Is anything in this file wrong or missing that could affect my case?",
)

# Mirrors the NALSA entry in frontend/src/helplines/helplinesData.js (the Helplines page) --
# keep the two in step if either changes.
FREE_LEGAL_HELP = (
    {
        "name": "NALSA Free Legal Services Helpline",
        "contact": "Call 15100",
        "detail": "Free legal aid and advice from the National Legal Services Authority. Website: nalsa.gov.in",
    },
    {
        "name": "District Legal Services Authority (DLSA)",
        "contact": "Usually at your district court complex",
        "detail": (
            "Every district has a DLSA. You can visit or call to ask whether you qualify for free "
            "legal aid, and take this file with you."
        ),
    },
)

# Authority labels for the "Laws that may apply" section. "Statute" and "Official guidance" are
# the exact labels the Complaint Drafter's citation chips already use
# (frontend/src/complaints/DraftPreview.jsx); case law and compiled summaries had no label
# anywhere in the UI before this, so they get explicit ones here.
CASE_LAW_LABEL = "Case law (court judgment)"
COMPILED_SUMMARY_LABEL = "Compiled summary — not the official text of the law"
OFFICIAL_GUIDANCE_LABEL = "Official guidance"
PROCEDURAL_GUIDE_LABEL = "Procedural guide (how-to manual, not law)"
SUPPORTING_LAW_LABEL = "Supporting law"
PRIMARY_LABELS_BY_DOCUMENT_TYPE = {
    "rules": "Rules",
    "amendment_rules": "Rules",
    "regulations": "Regulations",
    "constitution": "Constitution",
}
DEFAULT_PRIMARY_LABEL = "Statute"
GOOD_LAW_WARNINGS = {
    False: "This judgment is no longer good law.",
    "partial": "Part of this judgment has since been overruled or superseded.",
}
