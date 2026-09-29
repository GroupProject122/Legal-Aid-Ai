"""Build the Set 1 (Official Q&A) report PDF from the test set itself.

    python make_set1_report.py

Reads ../externaltestset/set 1/official_qa.json and writes
../externaltestset/set 1/Set1_Official_QA_Test_Set.pdf. Re-run after changing the test set so
the tables stay in step with it. Needs reportlab (installed in this folder's .venv).
"""
from __future__ import annotations

import json
from collections import Counter, OrderedDict
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    KeepTogether,
    LongTable,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

HERE = Path(__file__).resolve().parent
SET_DIR = HERE.parent / "externaltestset" / "set 1"
DATA = SET_DIR / "official_qa.json"
OUT = SET_DIR / "Set1_Official_QA_Test_Set.pdf"

# Arial has the rupee sign and the curly quotes used in the official text.
pdfmetrics.registerFont(TTFont("Body", "C:/Windows/Fonts/arial.ttf"))
pdfmetrics.registerFont(TTFont("Body-Bold", "C:/Windows/Fonts/arialbd.ttf"))
pdfmetrics.registerFont(TTFont("Body-Italic", "C:/Windows/Fonts/ariali.ttf"))
pdfmetrics.registerFontFamily("Body", normal="Body", bold="Body-Bold", italic="Body-Italic", boldItalic="Body-Bold")

INK = colors.HexColor("#2b1d12")
MUTED = colors.HexColor("#6b5a4a")
ACCENT = colors.HexColor("#6f3b16")
RULE = colors.HexColor("#d9c7ae")
HEAD_BG = colors.HexColor("#efe3d0")
ZEBRA = colors.HexColor("#fbf7f0")
WARN_BG = colors.HexColor("#fbeee6")
WARN_EDGE = colors.HexColor("#b5532f")

S = {
    "title": ParagraphStyle("title", fontName="Body-Bold", fontSize=22, leading=27, textColor=INK, spaceAfter=4),
    "subtitle": ParagraphStyle("subtitle", fontName="Body", fontSize=11, leading=15, textColor=MUTED, spaceAfter=14),
    "h1": ParagraphStyle("h1", fontName="Body-Bold", fontSize=14, leading=18, textColor=ACCENT, spaceBefore=12, spaceAfter=6),
    "h2": ParagraphStyle("h2", fontName="Body-Bold", fontSize=11, leading=14, textColor=INK, spaceBefore=8, spaceAfter=4),
    "body": ParagraphStyle("body", fontName="Body", fontSize=9.5, leading=13.5, textColor=INK, spaceAfter=5),
    "bullet": ParagraphStyle("bullet", fontName="Body", fontSize=9.5, leading=13.5, textColor=INK, leftIndent=12, bulletIndent=2, spaceAfter=2),
    "cell": ParagraphStyle("cell", fontName="Body", fontSize=8.5, leading=11, textColor=INK, alignment=TA_LEFT),
    "cellb": ParagraphStyle("cellb", fontName="Body-Bold", fontSize=8.5, leading=11, textColor=INK),
    "head": ParagraphStyle("head", fontName="Body-Bold", fontSize=8.5, leading=11, textColor=INK),
    "small": ParagraphStyle("small", fontName="Body", fontSize=7.4, leading=9.6, textColor=INK),
    "smallb": ParagraphStyle("smallb", fontName="Body-Bold", fontSize=7.4, leading=9.6, textColor=INK),
    "note": ParagraphStyle("note", fontName="Body-Italic", fontSize=8.5, leading=11.5, textColor=MUTED, spaceAfter=4),
}

SOURCES = OrderedDict(
    [
        ("consumerhelpline", ("National Consumer Helpline — Knowledge Base: Consumer Protection Act 2019", "Consumer",
                              "https://consumerhelpline.gov.in/public/knowledgebasedetails/Consumer%20Protection%20Act%202019")),
        ("cybercrime", ("National Cybercrime Reporting Portal — FAQ (Ministry of Home Affairs)", "Cyber",
                        "https://cybercrime.gov.in/webform/FAQ.aspx")),
        ("rbi.org.in", ("Reserve Bank of India — Integrated Ombudsman Scheme 2026 FAQs", "Consumer (banking)",
                        "https://www.rbi.org.in/commonman/Upload/English/FAQs/PDFs/RBIOS01072026.pdf")),
        ("dsci.delhi", ("Delhi Government — RTI Frequently Asked Questions", "Constitutional / public authority (RTI)",
                        "https://dsci.delhi.gov.in/sites/default/files/dsci/rti/faq-rti_0_1.pdf")),
        ("nalsa", ("National Legal Services Authority (NALSA) — FAQs", "Constitutional / public authority (legal aid)",
                   "https://nalsa.gov.in/faqs/")),
    ]
)
SHORT = {"consumerhelpline": "National Consumer Helpline", "cybercrime": "Cybercrime Reporting Portal (MHA)",
         "rbi.org.in": "RBI — RB-IOS 2026 FAQs", "dsci.delhi": "Delhi Govt RTI FAQs", "nalsa": "NALSA FAQs"}
DOMAIN = {"consumer": "Consumer", "cyber": "Cyber", "constitutional_public_authority": "Constitutional / public authority"}

EXCLUDED_OUTDATED = [
    ("National Consumer Helpline, Q10", "Consumer", "Which Commission hears which claim value",
     "<b>Outdated.</b> Gives the original 2019 limits (up to ₹1 crore / ₹1–10 crore / above ₹10 crore). The Consumer "
     "Protection (Jurisdiction…) Rules, 2021 changed them to ₹50 lakh / ₹50 lakh–2 crore / above ₹2 crore, and the "
     "dataset has the 2021 Rules.", SOURCES["consumerhelpline"][2]),
    ("National Consumer Helpline, Q35", "Consumer", "Procedure for filing a complaint",
     "<b>Outdated.</b> Directs users to the e-Daakhil portal, which was merged into e-Jagriti on 1 January 2025.",
     SOURCES["consumerhelpline"][2]),
    ("National Consumer Helpline, Q44", "Consumer", "Appeals against a Commission's order",
     "<b>Contradicts the Act.</b> Says 30 days (District→State) and 45 days (National→Supreme Court). The Consumer "
     "Protection Act, 2019 says 45 days (s.41) and 30 days (s.67).", SOURCES["consumerhelpline"][2]),
    ("Cybercrime Reporting Portal FAQ", "Cyber", "Action on a false complaint",
     "<b>Outdated.</b> Cites the Indian Penal Code, replaced by the Bharatiya Nyaya Sanhita, 2023 from 1 July 2024.",
     SOURCES["cybercrime"][2]),
    ("RBI Integrated Ombudsman Scheme 2021 FAQs (SBM Bank copy)", "Consumer (banking)", "All 8 used in the first draft",
     "<b>Outdated.</b> The 2021 scheme was replaced by the Integrated Ombudsman Scheme, 2026 on 1 July 2026.",
     "https://www.sbm.bank.in/pdf/notice-board/FAQs-on-Banking-Ombudsman-scheme-2021.pdf"),
    ("RBI Integrated Ombudsman Scheme 2026 FAQs, Q17, Q22, Q23", "Consumer (banking)", "When to file; compensation limits",
     "<b>Rules changed in 2026</b> (90-day filing window; ₹30 lakh / ₹3 lakh). The dataset still has the 2021 scheme "
     "(one year; ₹20 lakh / ₹1 lakh), so it cannot answer these correctly yet.", SOURCES["rbi.org.in"][2]),
    ("RBI Integrated Ombudsman Scheme 2026 FAQs, Q5, Q15, Q26", "Consumer (banking)",
     "Deficiency in service; grounds; rejection", "<b>Definitions and grounds changed in 2026</b>, as above.",
     SOURCES["rbi.org.in"][2]),
]
EXCLUDED_OTHER = [
    ("National Consumer Helpline, Q45", "Consumer", "Filing fees", "The answer is a table that does not survive as plain text.",
     SOURCES["consumerhelpline"][2]),
    ("National Consumer Helpline, Q8", "Consumer", "Can a business buyer complain?",
     "The whole official answer is “No” — too short to score.", SOURCES["consumerhelpline"][2]),
    ("National Consumer Helpline, Q15", "Consumer", "Who is liable for a misleading advertisement?",
     "Oversimplifies the Act (publisher liability is qualified).", SOURCES["consumerhelpline"][2]),
    ("Department of Consumer Affairs — FAQs on the CPA 2019 (PDF)", "Consumer", "Whole source",
     "The site did not respond when downloading; the National Consumer Helpline covers the same law.",
     "https://consumeraffairs.nic.in/sites/default/files/file-uploads/latestnews/FAQ.pdf"),
    ("Cybercrime Reporting Portal FAQ", "Cyber", "CSEAM definition; hash value",
     "Technical or definitional; not what users ask.", SOURCES["cybercrime"][2]),
    ("DoPT — FAQs on RTI (PDF)", "Constitutional / public authority (RTI)", "Whole source",
     "Same questions as the Delhi FAQs with worse PDF text; the Delhi version fits the Delhi focus of the dataset.",
     "https://dopt.gov.in/sites/default/files/FAQ_RTI_2012%20(1).pdf"),
    ("Delhi Government RTI FAQs, Q22", "Constitutional / public authority (RTI)", "Complaints under the Act",
     "Words were lost in PDF extraction; not guessed.", SOURCES["dsci.delhi"][2]),
    ("—", "Tenancy", "—",
     "No official Delhi tenancy FAQ exists; tenancy is tested in sets 2 and 3.", ""),
]


def P(text: str, style: str = "body") -> Paragraph:
    return Paragraph(text, S[style])


def link(url: str, label: str) -> str:
    return f'<a href="{escape(url)}" color="#6f3b16"><u>{escape(label)}</u></a>'


def source_key(url: str) -> str:
    return next(key for key in SOURCES if key in url)


def grid(rows, widths, head_rows=1, zebra=True, repeat=True, table_cls=Table):
    table = table_cls(rows, colWidths=widths, repeatRows=head_rows if repeat else 0)
    style = [
        ("BACKGROUND", (0, 0), (-1, head_rows - 1), HEAD_BG),
        ("LINEBELOW", (0, head_rows - 1), (-1, head_rows - 1), 0.8, ACCENT),
        ("LINEBELOW", (0, head_rows), (-1, -1), 0.25, RULE),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    if zebra:
        for row in range(head_rows, len(rows)):
            if (row - head_rows) % 2 == 1:
                style.append(("BACKGROUND", (0, row), (-1, row), ZEBRA))
    table.setStyle(TableStyle(style))
    return table


def callout(paragraphs, width):
    box = Table([[paragraphs]], colWidths=[width])
    box.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), WARN_BG),
        ("LINEBEFORE", (0, 0), (0, -1), 3, WARN_EDGE),
        ("LEFTPADDING", (0, 0), (-1, -1), 10),
        ("RIGHTPADDING", (0, 0), (-1, -1), 10),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ]))
    return box


def on_page(canvas, doc):
    canvas.saveState()
    width, height = landscape(A4)
    canvas.setFont("Body", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 12 * mm, "Legal Aid AI — Set 1: Official Q&A test set")
    canvas.drawRightString(width - doc.rightMargin, 12 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(RULE)
    canvas.line(doc.leftMargin, 15 * mm, width - doc.rightMargin, 15 * mm)
    canvas.restoreState()


def build() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    cases = data["cases"]
    page_w, _page_h = landscape(A4)
    margin = 14 * mm
    width = page_w - 2 * margin
    story = []

    by_source = Counter(source_key(case["source_url"]) for case in cases)
    by_domain = Counter(DOMAIN[case["domain"]] for case in cases)

    # --- Cover / overview ---------------------------------------------------------------
    story += [
        P("Set 1 — Official Q&amp;A Test Set", "title"),
        P("Legal Aid AI · External evaluation set for answer quality (ROUGE and BERTScore) · "
          "Collected 29 September 2026", "subtitle"),
    ]
    overview = [
        [P("<b>Questions</b>", "cell"), P(f"<b>{len(cases)}</b> official questions, each with its official answer", "cell")],
        [P("<b>Sources</b>", "cell"), P(f"{len(SOURCES)} Indian government sources (listed in Table A)", "cell")],
        [P("<b>Domains</b>", "cell"), P(" · ".join(f"{name}: {count}" for name, count in by_domain.items()), "cell")],
        [P("<b>Used for</b>", "cell"), P("Scoring the app's answers with <b>ROUGE</b> (word overlap) and <b>BERTScore</b> "
                                         "(meaning overlap). The official answer is the reference each app answer is "
                                         "compared against.", "cell")],
        [P("<b>File</b>", "cell"), P("4parameters_test/externaltestset/set 1/official_qa.json "
                                     "(details in README.md in the same folder)", "cell")],
    ]
    table = Table(overview, colWidths=[32 * mm, width - 32 * mm])
    table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), HEAD_BG), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [table, Spacer(1, 8)]

    story.append(P("Why this set exists", "h1"))
    story += [
        P("The app's own test sets were written by the team, so its scores on them are likely to be optimistic. This set "
          "is <b>external</b>: the questions and the correct answers both come from the government, not from us. It "
          "shows how the app performs on questions it was not tuned on, with answers nobody on the team wrote."),
        P("It is one of three external sets. <b>Set 1</b> (this one) tests whether answers are <i>correct</i>, using "
          "official answers as references. <b>Set 2</b> tests messy, real-world questions and whether answers are "
          "<i>grounded</i> in the retrieved law (AlignScore, ParaScore). <b>Set 3</b> tests whether the app finds the "
          "<i>right law</i>."),
    ]

    story.append(P("How it was built", "h1"))
    for text in [
        "<b>Downloaded</b> the official FAQ pages and PDFs directly from the government sites.",
        "<b>Extracted the text locally</b> and split it into question–answer pairs, so every answer is the official "
        "wording, copied exactly — not summarised or paraphrased.",
        "<b>Chose questions a real user would ask</b>, across consumer, cyber, banking, RTI and legal aid.",
        "<b>Checked every item was current</b>, against the law in the app's dataset (for example the Consumer "
        "Protection Act, 2019) and against current rules. Anything outdated or wrong was excluded (Table C).",
        "<b>Recorded</b> for each item its source, a link, the original question number, and the dataset documents the "
        "app is expected to retrieve.",
    ]:
        story.append(Paragraph(text, S["bullet"], bulletText="•"))

    story.append(KeepTogether([P("Key finding: some official FAQs are outdated or contradict the law", "h1"), callout([
        P("While checking the sources, <b>three official FAQs</b> from the National Consumer Helpline turned out to be "
          "outdated or wrong, and so did one on the Cybercrime Portal:", "body"),
        Paragraph("<b>Appeal deadlines contradict the Act.</b> The FAQ says 30 days (District→State) and 45 days "
                  "(National→Supreme Court); the Consumer Protection Act, 2019 says <b>45 days</b> (s.41) and "
                  "<b>30 days</b> (s.67).", S["bullet"], bulletText="•"),
        Paragraph("<b>Claim-value limits are out of date</b> (₹1 crore / ₹10 crore instead of ₹50 lakh / ₹2 crore "
                  "since the 2021 Rules).", S["bullet"], bulletText="•"),
        Paragraph("<b>The filing portal is out of date</b> (e-Daakhil instead of e-Jagriti since January 2025).",
                  S["bullet"], bulletText="•"),
        Paragraph("<b>The Cybercrime Portal FAQ still cites the Indian Penal Code</b>, replaced by the Bharatiya Nyaya "
                  "Sanhita in 2024.", S["bullet"], bulletText="•"),
        P("This is why Legal Aid AI answers from the <b>primary law</b> (Acts and Rules) rather than from FAQs, and why "
          "an evaluation set must be checked before it is used: scoring against these FAQs would have penalised the "
          "app for being correct.", "body"),
    ], width)]))
    story.append(Spacer(1, 6))
    story.append(P("Banking: RBI replaced its ombudsman scheme on 1 July 2026", "h2"))
    story.append(P(
        "The app's dataset contains the Reserve Bank – Integrated Ombudsman Scheme, <b>2021</b>. RBI replaced it with "
        "the <b>2026</b> scheme on 1 July 2026 (the 2021 scheme still governs complaints filed before that date). To stay "
        "both current and fair, only 2026 questions whose rules are <b>unchanged from 2021</b> were used: how to file, "
        "tracking, filing through a representative, no fee, what happens without a settlement, appeal time limits, "
        "withdrawal and languages. Questions whose rules changed (the filing window, now 90 days; compensation limits, "
        "now ₹30 lakh / ₹3 lakh; definitions and grounds) were excluded, and updating the dataset is listed as future "
        "work."))

    # --- Table A ------------------------------------------------------------------------
    story.append(PageBreak())
    story.append(P("Table A — Questions used, by source", "h1"))
    rows = [[P("Source", "head"), P("Domain (in the app)", "head"), P("Questions", "head"), P("Link", "head")]]
    for key, (name, domain, url) in SOURCES.items():
        rows.append([P(escape(name), "cell"), P(escape(domain), "cell"), P(str(by_source[key]), "cellb"),
                     P(link(url, url), "cell")])
    rows.append([P("<b>Total</b>", "cell"), P("", "cell"), P(f"<b>{len(cases)}</b>", "cell"), P("", "cell")])
    story.append(grid(rows, [85 * mm, 62 * mm, 20 * mm, width - 167 * mm]))
    story.append(Spacer(1, 6))
    story.append(P("By domain: " + " · ".join(f"<b>{name}</b> {count}" for name, count in by_domain.items())
                   + ". Banking questions are counted as Consumer, where the RBI scheme sits in the dataset; RTI and "
                     "legal aid are Constitutional / public authority.", "note"))

    # --- Table B ------------------------------------------------------------------------
    story.append(PageBreak())
    story.append(P("Table B — Every question with its official answer", "h1"))
    story.append(P("Question and answer are the official wording. The official answer is the reference that ROUGE and "
                   "BERTScore compare the app's answer against.", "note"))
    widths = [8 * mm, 21 * mm, 30 * mm, 58 * mm, width - 8 * mm - 21 * mm - 30 * mm - 58 * mm - 36 * mm, 36 * mm]
    rows = [[P("#", "smallb"), P("ID", "smallb"), P("Domain", "smallb"), P("Question", "smallb"),
             P("Official answer", "smallb"), P("Source", "smallb")]]
    for number, case in enumerate(cases, 1):
        key = source_key(case["source_url"])
        domain = DOMAIN[case["domain"]]
        if case["id"].startswith("banking"):
            domain += " (banking)"
        elif case["id"].startswith("rti"):
            domain += " (RTI)"
        elif case["id"].startswith("legalaid"):
            domain += " (legal aid)"
        rows.append([
            P(str(number), "small"),
            P(escape(case["id"]), "small"),
            P(escape(domain), "small"),
            P(escape(case["question"]), "small"),
            P(escape(case["reference_answer"]), "small"),
            P(link(case["source_url"], SHORT[key]), "small"),
        ])
    story.append(grid(rows, widths, table_cls=LongTable))

    # --- Table C ------------------------------------------------------------------------
    story.append(PageBreak())
    story.append(P("Table C — Sources and questions not used, and why", "h1"))
    head = [P("Source", "head"), P("Domain", "head"), P("Question(s) not used", "head"), P("Why", "head")]
    widths_c = [70 * mm, 45 * mm, 52 * mm, width - 167 * mm]

    def rows_for(items):
        rows = [head]
        for source, domain, question, why, url in items:
            source_cell = link(url, source) if url else escape(source)
            rows.append([P(source_cell, "cell"), P(escape(domain), "cell"), P(escape(question), "cell"), P(why, "cell")])
        return rows

    story.append(P("C1. Excluded because outdated or wrong", "h2"))
    story.append(grid(rows_for(EXCLUDED_OUTDATED), widths_c))
    story.append(P("C2. Excluded for other reasons", "h2"))
    story.append(grid(rows_for(EXCLUDED_OTHER), widths_c))

    # --- Edits, format, caveats -----------------------------------------------------------
    story.append(PageBreak())
    story.append(P("Changes made to the official text", "h1"))
    story.append(P("Answers are verbatim. The only edits repair problems introduced by extracting text from PDFs:"))
    for text in [
        "Words rejoined where a stray space split them: “t o” → “to”, “In formation” → “Information”, “rec eived” → "
        "“received”, “complaint s” → “complaints”, “e- mail” → “e-mail”, “RB -IOS” → “RB-IOS”, “third -party” → "
        "“third-party”.",
        "Stray section headings removed from the end of two answers (“Second Appeal”, “RTI AUTHORITIES”).",
        "RBI's standard disclaimer paragraph removed from the end of its last answer.",
        "<b>rti_07</b> trimmed to its first part (the second-appeal rule, with its section reference) because the list "
        "that followed was jumbled by the PDF's two-column layout.",
    ]:
        story.append(Paragraph(text, S["bullet"], bulletText="•"))

    story.append(P("File format", "h1"))
    story.append(P("Each item in <b>official_qa.json</b> has these fields:"))
    fields = [
        [P("Field", "head"), P("Meaning", "head")],
        [P("id", "cellb"), P("Unique id, e.g. consumer_01, banking_03", "cell")],
        [P("domain", "cellb"), P("The app's domain name: consumer, cyber, or constitutional_public_authority", "cell")],
        [P("topic", "cellb"), P("Finer topic, e.g. banking ombudsman (RBI), right to information, free legal aid", "cell")],
        [P("question", "cellb"), P("The official question, word for word", "cell")],
        [P("reference_answer", "cellb"), P("The official answer, word for word — the reference for ROUGE and BERTScore", "cell")],
        [P("expected_sources", "cellb"), P("Dataset documents the app is expected to retrieve (assigned by the team, "
                                           "not from the source); every name matches a document title in the dataset", "cell")],
        [P("source_title / source_url", "cellb"), P("Where the item came from", "cell")],
        [P("notes", "cellb"), P("Original question number in the source, and any caveat", "cell")],
    ]
    story.append(grid(fields, [45 * mm, width - 45 * mm]))

    story.append(P("Limitations", "h1"))
    for text in [
        "<b>No tenancy questions.</b> No official Delhi tenancy FAQ exists; tenancy is covered by sets 2 and 3.",
        "<b>FAQ answers are short and formal</b>, while the app's answers are longer and structured, so ROUGE in "
        "particular will score lower than the answers' real quality. BERTScore handles this better.",
        "<b>ROUGE and BERTScore reward similar wording</b>, and can score “you may not claim” highly against “you may "
        "claim”. They are reported alongside AlignScore and a small hand review, not on their own.",
        "<b>expected_sources is a team judgement</b> of which documents should be retrieved, not part of the official "
        "source.",
    ]:
        story.append(Paragraph(text, S["bullet"], bulletText="•"))

    story.append(KeepTogether([P("Next steps", "h1")] + [
        Paragraph(text, S["bullet"], bulletText="•") for text in [
            "Run the 50 questions through the app once and save its answers and retrieved sources.",
            "Score the saved answers with ROUGE and BERTScore, overall and by domain.",
            "Report the results next to the internal test-set results, and review a sample of answers by hand.",
        ]
    ]))

    doc = SimpleDocTemplate(
        str(OUT), pagesize=landscape(A4), leftMargin=margin, rightMargin=margin, topMargin=13 * mm, bottomMargin=20 * mm,
        title="Set 1 — Official Q&A Test Set", author="Legal Aid AI team",
        subject="External evaluation set for Legal Aid AI (ROUGE and BERTScore)",
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
