"""Build the Set 3 (Right law) report PDF from the test set itself.

    python make_set3_report.py

Reads ../externaltestset/set3/right_law.json and writes
../externaltestset/set3/Set3_Right_Law_Test_Set.pdf. Re-run after changing the test set so the
tables stay in step with it. Uses the same look as the Set 1 report (needs reportlab).
"""
from __future__ import annotations

import json
from collections import Counter, OrderedDict
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.units import mm
from reportlab.platypus import LongTable, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from make_set1_report import HEAD_BG, MUTED, RULE, S, P, grid, link

HERE = Path(__file__).resolve().parent
SET_DIR = HERE.parent / "externaltestset" / "set3"
DATA = SET_DIR / "right_law.json"
OUT = SET_DIR / "Set3_Right_Law_Test_Set.pdf"

AREA = OrderedDict([
    ("consumer", "Consumer"),
    ("cyber", "Cyber"),
    ("tenancy", "Tenancy (Delhi)"),
    ("constitutional_public_authority", "Constitutional / public authority (RTI)"),
])
FORUMS = {
    "consumer": "State Consumer Commissions (Delhi, Haryana, Punjab), National Consumer Commission (NCDRC)",
    "cyber": "State Consumer Commissions, Delhi High Court, Andhra Pradesh High Court, IT Act adjudication appeal",
    "tenancy": "Delhi High Court, Rent Control Tribunal Delhi, Delhi District Courts / Rent Controller",
    "constitutional_public_authority": "Central Information Commission (CIC)",
}


def domain_label(domains: list[str]) -> str:
    main = AREA.get(domains[0], domains[0])
    others = [AREA.get(d, d).split(" (")[0] for d in domains[1:]]
    return main + (f" (also {', '.join(others)})" if others else "")


def on_page(canvas, doc):
    canvas.saveState()
    width, _height = landscape(A4)
    canvas.setFont("Body", 7.5)
    canvas.setFillColor(MUTED)
    canvas.drawString(doc.leftMargin, 12 * mm, "Legal Aid AI — Set 3: Right law (retrieval) test set")
    canvas.drawRightString(width - doc.rightMargin, 12 * mm, f"Page {doc.page}")
    canvas.setStrokeColor(RULE)
    canvas.line(doc.leftMargin, 15 * mm, width - doc.rightMargin, 15 * mm)
    canvas.restoreState()


def build() -> None:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    cases = data["single_domain_queries"]
    page_w, _page_h = landscape(A4)
    margin = 14 * mm
    width = page_w - 2 * margin
    story = []
    by_area = Counter(case["expected_domain"][0] for case in cases)

    # --- Cover / overview ---------------------------------------------------------------
    story += [
        P("Set 3 — Right Law Test Set", "title"),
        P("Legal Aid AI · External evaluation set for retrieval (does the app find the right law?) · "
          "Collected 29 September 2026", "subtitle"),
    ]
    overview = [
        [P("<b>Questions</b>", "cell"), P(f"<b>{len(cases)}</b> real situations, each taken from a published Indian "
                                          "court, consumer commission or Information Commission decision", "cell")],
        [P("<b>Domains</b>", "cell"), P(" · ".join(f"{AREA[key]}: {by_area[key]}" for key in AREA), "cell")],
        [P("<b>Expected output</b>", "cell"), P("The law the decision actually applied: the Act, rules or case, and the "
                                                "section numbers. All of it is in the app's dataset.", "cell")],
        [P("<b>Used for</b>", "cell"), P("Retrieval metrics: <b>Document Hit@1 / Hit@5</b> (right document found), "
                                         "<b>Section Hit@5</b> (right section found) and <b>MRR</b> (how high it ranks). "
                                         "No Gemini calls, so no API quota is used.", "cell")],
        [P("<b>File</b>", "cell"), P("4parameters_test/externaltestset/set3/right_law.json "
                                     "(details in README.md in the same folder)", "cell")],
    ]
    table = Table(overview, colWidths=[34 * mm, width - 34 * mm])
    table.setStyle(TableStyle([
        ("LINEBELOW", (0, 0), (-1, -1), 0.25, RULE), ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BACKGROUND", (0, 0), (0, -1), HEAD_BG), ("TOPPADDING", (0, 0), (-1, -1), 4), ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story += [table, Spacer(1, 8)]

    story.append(P("Why this set exists", "h1"))
    story += [
        P("An answer can only be correct if the app first finds the right law. This set checks that step on its own. "
          "The questions are real situations that came before Indian courts and commissions, and the expected law is "
          "what the judge or commissioner actually applied — not what the team thinks should apply."),
        P("It is one of three external sets. <b>Set 1</b> tests whether answers are <i>correct</i> against official "
          "answers (ROUGE, BERTScore). <b>Set 2</b> tests messy real questions and whether answers are <i>grounded</i> "
          "(AlignScore, ParaScore). <b>Set 3</b> (this one) tests whether the app finds the <i>right law</i>."),
    ]

    story.append(P("How it was built", "h1"))
    for text in [
        "<b>Searched Indian Kanoon</b> for recent decisions in each area and read each one.",
        "<b>Rewrote the facts as a user would type them</b>, in plain first-person words, without naming any Act or "
        "section, so the app has to work out the law itself.",
        "<b>Recorded the law the decision applied</b>, and matched it to the exact document titles and file names in the "
        "app's dataset. Closely related documents that are also correct (for example a Supreme Court case on the same "
        "section) are accepted too.",
        "<b>Mapped old IPC sections to BNS</b> in the cyber cases, since the dataset has the Bharatiya Nyaya Sanhita.",
        "<b>Did not use any decision that is itself in the dataset</b>, so the app cannot find the answer by matching "
        "the case.",
    ]:
        story.append(Paragraph(text, S["bullet"], bulletText="•"))

    # --- Table A ------------------------------------------------------------------------
    story.append(PageBreak())
    story.append(P("Table A — Questions by domain", "h1"))
    rows = [[P("Domain (in the app)", "head"), P("Questions", "head"), P("Where the decisions come from", "head"),
             P("Main law expected", "head")]]
    main_law = {
        "consumer": "Consumer Protection Act, 2019; E-Commerce Rules, 2020; Insurance Ombudsman Rules, 2017",
        "cyber": "RBI 2017 limiting-liability circular; IT Act, 2000; BNS, 2023; SPDI Rules, 2011; IT Intermediary "
                 "Rules, 2021; Cybercrime Portal manuals",
        "tenancy": "Delhi Rent Control Act, 1958; Transfer of Property Act, 1882",
        "constitutional_public_authority": "Right to Information Act, 2005; RTI Rules, 2012",
    }
    for key, name in AREA.items():
        rows.append([P(escape(name), "cell"), P(str(by_area[key]), "cellb"), P(escape(FORUMS[key]), "cell"),
                     P(escape(main_law[key]), "cell")])
    rows.append([P("<b>Total</b>", "cell"), P(f"<b>{len(cases)}</b>", "cell"), P("", "cell"), P("", "cell")])
    story.append(grid(rows, [62 * mm, 20 * mm, 95 * mm, width - 177 * mm]))
    story.append(Spacer(1, 6))
    story.append(P("Three cyber questions are about bank fraud; for those the Consumer domain is also accepted, because "
                   "the complaint route (RBI Ombudsman, consumer commission) sits there.", "note"))

    # --- Table B ------------------------------------------------------------------------
    story.append(Spacer(1, 10))
    story.append(P("Table B — Every question with its expected law and source", "h1"))
    story.append(P("The question is written from the facts of the decision. The expected output is the law the decision "
                   "applied; the app passes if it retrieves these documents, and scores higher if it also reaches these "
                   "sections. Click a source to open the decision.", "note"))
    widths = [7 * mm, 21 * mm, 27 * mm, 80 * mm, width - 7 * mm - 21 * mm - 27 * mm - 80 * mm - 52 * mm, 52 * mm]
    rows = [[P("#", "smallb"), P("ID", "smallb"), P("Domain", "smallb"), P("Question", "smallb"),
             P("Expected output (law applied)", "smallb"), P("Source decision", "smallb")]]
    for number, case in enumerate(cases, 1):
        source = (link(case["source_url"], case["source_case"]) + "<br/>"
                  + f'<font color="#6b5a4a">{escape(case["source_url"])}</font>')
        rows.append([
            P(str(number), "small"),
            P(escape(case["id"]), "small"),
            P(escape(domain_label(case["expected_domain"])), "small"),
            P(escape(case["query"]), "small"),
            P(escape(case["expected_law"]), "small"),
            P(source, "small"),
        ])
    story.append(grid(rows, widths, table_cls=LongTable))

    # --- Format and limitations -----------------------------------------------------------
    story.append(PageBreak())
    story.append(P("File format", "h1"))
    story.append(P("Each item in <b>right_law.json</b> (under <b>single_domain_queries</b>) has these fields:"))
    fields = [
        [P("Field", "head"), P("Meaning", "head")],
        [P("id", "cellb"), P("Unique id, e.g. consumer_01, tenancy_04, rti_02", "cell")],
        [P("query", "cellb"), P("The question, written from the facts of the decision", "cell")],
        [P("expected_law", "cellb"), P("Readable summary of the law the decision applied, with sub-sections", "cell")],
        [P("expected_domain", "cellb"), P("The app's domain(s) that count as correct", "cell")],
        [P("expected_primary_documents / expected_primary_sources", "cellb"),
         P("Dataset document titles and file names that count as the right law", "cell")],
        [P("expected_provision_numbers", "cellb"),
         P("Section numbers as the dataset labels them (bare numbers, e.g. “14” for s.14(1)(e))", "cell")],
        [P("source_case / source_url", "cellb"), P("The decision the question came from, and its Indian Kanoon link", "cell")],
        [P("notes", "cellb"), P("What the decision relied on, and any caveat", "cell")],
    ]
    story.append(grid(fields, [80 * mm, width - 80 * mm]))

    story.append(P("Limitations", "h1"))
    for text in [
        "<b>24 questions is a small set.</b> It shows where retrieval is strong or weak, not a precise percentage.",
        "<b>Document Hit@5 is lenient</b> because related documents are accepted. <b>Section Hit@5 is the stricter "
        "number</b> and the better one to quote.",
        "<b>Section numbers are matched without sub-sections</b> (“14”, not “14(1)(e)”), because that is how the "
        "dataset is indexed.",
        "<b>The decision's outcome is not tested</b> — only which law applied. Some decisions went against the person "
        "asking; the law is still the right law for the question.",
        "<b>The expected law is a team reading of each decision</b>; the decision text is linked so it can be checked.",
    ]:
        story.append(Paragraph(text, S["bullet"], bulletText="•"))

    doc = SimpleDocTemplate(
        str(OUT), pagesize=landscape(A4), leftMargin=margin, rightMargin=margin, topMargin=13 * mm, bottomMargin=20 * mm,
        title="Set 3 — Right Law Test Set", author="Legal Aid AI team",
        subject="External evaluation set for Legal Aid AI (retrieval)",
    )
    doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
    print(f"Wrote {OUT}")


if __name__ == "__main__":
    build()
