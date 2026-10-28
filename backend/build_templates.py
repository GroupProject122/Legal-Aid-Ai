"""One-time authoring script that generates the fixed docxtpl base templates under
backend/templates/. This is not a rendering path -- it is run manually (or via
`python build_templates.py`) whenever a base template needs to be created or revised, and its
output (a .docx file with Jinja2 merge tags) is what complaint_drafter.py fills in at request
time via docxtpl. Keeping this separate from complaint_drafter.py keeps the request-time module
free of python-docx paragraph/style plumbing.
"""
from __future__ import annotations

import logging

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

from config import BASE_DIR

logger = logging.getLogger("legal_aid_ai.build_templates")

TEMPLATES_DIR = BASE_DIR / "templates"
TENANCY_EVICTION_TEMPLATE_PATH = TEMPLATES_DIR / "tenancy_eviction_base.docx"
CONSUMER_GOODS_TEMPLATE_PATH = TEMPLATES_DIR / "consumer_defective_goods_base.docx"
CONSUMER_ADS_TEMPLATE_PATH = TEMPLATES_DIR / "consumer_misleading_ads_base.docx"
RTI_APPLICATION_TEMPLATE_PATH = TEMPLATES_DIR / "rti_application_base.docx"
RTI_FIRST_APPEAL_TEMPLATE_PATH = TEMPLATES_DIR / "rti_first_appeal_base.docx"
SENIOR_CITIZEN_MAINTENANCE_TEMPLATE_PATH = TEMPLATES_DIR / "senior_citizen_maintenance_base.docx"
TENANT_ESSENTIAL_SUPPLY_TEMPLATE_PATH = TEMPLATES_DIR / "tenant_essential_supply_base.docx"
BANK_FRAUD_COMPLAINT_TEMPLATE_PATH = TEMPLATES_DIR / "bank_fraud_complaint_base.docx"
CASE_FILE_TEMPLATE_PATH = TEMPLATES_DIR / "case_file_base.docx"


def build_tenancy_eviction_base_template() -> None:
    """Fixed section order: heading/forum -> parties -> property & tenancy particulars ->
    grounds (selected clause inserted here) -> relief sought -> verification/signature block."""
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    def heading(text: str, *, bold: bool = True, center: bool = True, size: int = 12) -> None:
        paragraph = document.add_paragraph()
        if center:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(text)
        run.bold = bold
        run.font.size = Pt(size)

    def body(text: str) -> None:
        document.add_paragraph(text)

    # 1. Heading / forum
    heading("{{ forum_name }}")
    heading("{{ petition_title }}")
    document.add_paragraph()

    # 2. Parties
    heading("PARTIES", center=False)
    body("{{ landlord_name }}, residing at {{ landlord_address }}")
    body("... Petitioner/Landlord")
    heading("Versus", bold=False)
    body("{{ tenant_name }}, residing at {{ tenant_address }}")
    body("... Respondent/Tenant")
    document.add_paragraph()

    # 3. Property & tenancy particulars
    heading("PROPERTY AND TENANCY PARTICULARS", center=False)
    body("1. The tenanted premises are situated at: {{ property_address }}.")
    body("2. The agreed monthly rent of the tenanted premises is: {{ monthly_rent_display }}.")
    body("3. The tenancy commenced on: {{ tenancy_start_date_display }}.")
    document.add_paragraph()

    # 4. Grounds (selected clause(s) inserted here). Single-ground path (grounds_for_eviction has
    # exactly one entry) is byte-for-byte identical to the original single-ground-only template --
    # same three lines, same variable names -- so a single-ground draft is unchanged by this
    # feature. Multi-ground path (2+) adds a fixed framing line and numbers each ground
    # "Ground N" in fixed statutory order (see complaint_drafter.GROUND_STATUTORY_ORDER /
    # ordered_grounds()), never in the order the user selected them in. complaint_drafter.py's
    # _build_render_context() puts EITHER grounds_label/grounds_clause/citation_line (single)
    # OR grounds/multi_ground_framing_line (multi) in the render context, never both -- "is not
    # defined" (a safe Jinja test even under StrictUndefined) is how this branch tells them apart.
    heading("GROUNDS FOR EVICTION", center=False)
    body("{%p if grounds is not defined %}")
    body("Ground relied upon: {{ grounds_label }}")
    body("{{ grounds_clause }}")
    body("{{ citation_line }}")
    body("{%p else %}")
    body("{{ multi_ground_framing_line }}")
    body("{%p for ground in grounds %}")
    body("Ground {{ loop.index }}: {{ ground.label }}")
    body("{{ ground.clause_text }}")
    body("{{ ground.citation_line }}")
    body("{%p endfor %}")
    body("{%p endif %}")
    document.add_paragraph()

    # 5. Relief sought
    heading("RELIEF SOUGHT", center=False)
    body("The Petitioner/Landlord respectfully prays that this Hon'ble Court be pleased to grant:")
    # docxtpl loops over whole paragraphs using {%p %} tags: one paragraph opens the loop, one
    # (or more) paragraphs are the repeated body, and one paragraph closes it. A plain
    # {% for %}...{% endfor %} inline in a single paragraph would not duplicate paragraphs.
    body("{%p for line in relief_sought_lines %}")
    body("{{ loop.index }}. {{ line }}")
    body("{%p endfor %}")
    document.add_paragraph()

    # 6. Verification / signature block
    heading("VERIFICATION", center=False)
    body(
        "I, {{ landlord_name }}, the Petitioner/Landlord above named, do hereby verify that the "
        "contents of the foregoing petition are true and correct to the best of my knowledge and "
        "belief, and that nothing material has been concealed therefrom."
    )
    body("Verified at ____________________ on {{ generated_date_display }}.")
    document.add_paragraph()
    document.add_paragraph()
    body("________________________________")
    body("{{ landlord_name }}")
    body("Petitioner/Landlord")

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    document.save(str(TENANCY_EVICTION_TEMPLATE_PATH))
    logger.info("Saved base template to %s", TENANCY_EVICTION_TEMPLATE_PATH)


def build_consumer_defective_goods_base_template() -> None:
    """Fixed section order: heading/forum -> parties -> transaction/claim particulars ->
    grounds (selected clause inserted here) -> relief sought -> verification/signature block."""
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    def heading(text: str, *, bold: bool = True, center: bool = True, size: int = 12) -> None:
        paragraph = document.add_paragraph()
        if center:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(text)
        run.bold = bold
        run.font.size = Pt(size)

    def body(text: str) -> None:
        document.add_paragraph(text)

    # 1. Heading / forum
    heading("{{ forum_name }}")
    heading("{{ complaint_title }}")
    document.add_paragraph()

    # 2. Parties
    heading("PARTIES", center=False)
    body("{{ complainant_name }}, residing at {{ complainant_address }}")
    body("... Complainant")
    heading("Versus", bold=False)
    body("{{ opposite_party_name }}, having its address/place of business at {{ opposite_party_address }}")
    body("... Opposite Party")
    document.add_paragraph()

    # 3. Transaction / claim particulars
    heading("TRANSACTION PARTICULARS", center=False)
    body("1. Goods or service in question: {{ goods_or_service_description }}.")
    body("2. Date of transaction: {{ transaction_date_display }}.")
    body("3. Amount paid as consideration: {{ amount_paid_display }}.")
    body("{%p if prior_complaint_made %}")
    body("4. The Complainant previously raised this complaint with the Opposite Party, who responded as follows: {{ prior_complaint_response }}.")
    body("{%p endif %}")
    document.add_paragraph()

    # 4. Grounds (selected clause inserted here)
    heading("GROUNDS OF COMPLAINT", center=False)
    body("Ground relied upon: {{ defect_type_label }}")
    body("{{ grounds_clause }}")
    body("{{ citation_line }}")
    body("{{ forum_citation_line }}")
    document.add_paragraph()

    # 5. Relief sought
    heading("RELIEF SOUGHT", center=False)
    body("The Complainant respectfully prays that this Hon'ble Commission be pleased to direct the Opposite Party to:")
    body("{%p for line in relief_sought_lines %}")
    body("{{ loop.index }}. {{ line }}")
    body("{%p endfor %}")
    document.add_paragraph()

    # 6. Verification / signature block
    heading("VERIFICATION", center=False)
    body(
        "I, {{ complainant_name }}, the Complainant above named, do hereby verify that the contents "
        "of the foregoing complaint are true and correct to the best of my knowledge and belief, and "
        "that nothing material has been concealed therefrom."
    )
    body("Verified at ____________________ on {{ generated_date_display }}.")
    document.add_paragraph()
    document.add_paragraph()
    body("________________________________")
    body("{{ complainant_name }}")
    body("Complainant")

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    document.save(str(CONSUMER_GOODS_TEMPLATE_PATH))
    logger.info("Saved base template to %s", CONSUMER_GOODS_TEMPLATE_PATH)


def build_misleading_advertisement_base_template() -> None:
    """Fixed section order: heading/forum -> parties -> transaction/claim particulars ->
    grounds (selected clause inserted here) -> relief sought -> verification/signature block."""
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    def heading(text: str, *, bold: bool = True, center: bool = True, size: int = 12) -> None:
        paragraph = document.add_paragraph()
        if center:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(text)
        run.bold = bold
        run.font.size = Pt(size)

    def body(text: str) -> None:
        document.add_paragraph(text)

    # 1. Heading / forum
    heading("{{ forum_name }}")
    heading("{{ complaint_title }}")
    document.add_paragraph()

    # 2. Parties
    heading("PARTIES", center=False)
    body("{{ complainant_name }}, residing at {{ complainant_address }}")
    body("... Complainant")
    heading("Versus", bold=False)
    body("{{ opposite_party_name }}, having its address/place of business at {{ opposite_party_address }}")
    body("... Opposite Party")
    document.add_paragraph()

    # 3. Transaction / claim particulars
    heading("ADVERTISEMENT/PRACTICE PARTICULARS", center=False)
    body("1. Advertisement or practice complained of: {{ advertisement_or_practice_description }}.")
    body("2. Platform or medium: {{ platform_label }}.")
    body("3. Date encountered: {{ date_encountered_display }}.")
    # amount_paid is optional in this scenario (not every claim -- e.g. a dark pattern
    # encountered without completing a purchase -- involves a completed transaction), so this
    # line is only shown when it was actually supplied. Items 1-3 above are always present, so
    # hardcoding "4." here (rather than a loop index) is safe -- there's no gap to renumber around.
    body("{%p if amount_paid_display %}")
    body("4. Amount paid: {{ amount_paid_display }}.")
    body("{%p endif %}")
    document.add_paragraph()

    # 4. Grounds (selected clause inserted here)
    heading("GROUNDS OF COMPLAINT", center=False)
    body("Ground relied upon: {{ claim_type_label }}")
    body("{{ grounds_clause }}")
    body("{{ citation_line }}")
    document.add_paragraph()

    # 5. Relief sought
    heading("RELIEF SOUGHT", center=False)
    body("The Complainant respectfully prays that this Hon'ble Commission be pleased to direct the Opposite Party to:")
    body("{%p for line in relief_sought_lines %}")
    body("{{ loop.index }}. {{ line }}")
    body("{%p endfor %}")
    document.add_paragraph()

    # 6. Verification / signature block
    heading("VERIFICATION", center=False)
    body(
        "I, {{ complainant_name }}, the Complainant above named, do hereby verify that the contents "
        "of the foregoing complaint are true and correct to the best of my knowledge and belief, and "
        "that nothing material has been concealed therefrom."
    )
    body("Verified at ____________________ on {{ generated_date_display }}.")
    document.add_paragraph()
    document.add_paragraph()
    body("________________________________")
    body("{{ complainant_name }}")
    body("Complainant")

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    document.save(str(CONSUMER_ADS_TEMPLATE_PATH))
    logger.info("Saved base template to %s", CONSUMER_ADS_TEMPLATE_PATH)


def build_rti_application_base_template() -> None:
    """Fixed section order: heading -> addressee (PIO) block -> applicant block -> subject line
    -> request body (clause inserted here) -> closing/signature block. A formal letter to a
    Public Information Officer, not a court/commission pleading -- so no "PARTIES"/"Versus"
    structure like the other three scenarios; this is the one scenario in this file that isn't a
    petition or complaint."""
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    def heading(text: str, *, bold: bool = True, center: bool = True, size: int = 12) -> None:
        paragraph = document.add_paragraph()
        if center:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(text)
        run.bold = bold
        run.font.size = Pt(size)

    def body(text: str) -> None:
        document.add_paragraph(text)

    # 1. Heading
    heading("{{ application_title }}")
    document.add_paragraph()

    # 2. Addressee (Public Information Officer)
    body("To,")
    body("The Public Information Officer,")
    body("{{ public_authority_name }},")
    body("{{ public_authority_address }}.")
    document.add_paragraph()

    # 3. Applicant details
    body("From,")
    body("{{ applicant_name }},")
    body("{{ applicant_address }}.")
    document.add_paragraph()

    # 4. Subject line
    body("Subject: Request for information under the Right to Information Act, 2005.")
    document.add_paragraph()

    body("Sir/Madam,")
    document.add_paragraph()

    # 5. Request body (clause inserted here)
    heading("REQUEST FOR INFORMATION", center=False)
    body("{{ request_clause }}")
    body("{{ citation_line }}")
    document.add_paragraph()

    # 6. Closing / signature block
    body("Yours faithfully,")
    document.add_paragraph()
    document.add_paragraph()
    body("________________________________")
    body("{{ applicant_name }}")
    body("Applicant")
    body("Dated: {{ generated_date_display }}")

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    document.save(str(RTI_APPLICATION_TEMPLATE_PATH))
    logger.info("Saved base template to %s", RTI_APPLICATION_TEMPLATE_PATH)


def build_rti_first_appeal_base_template() -> None:
    """Fixed section order: heading -> addressee (Appellate Authority) block -> appellant block ->
    subject line -> appeal body (clause inserted here) -> closing/signature block. Same formal-
    letter shape as build_rti_application_base_template() above -- this is the appeal that follows
    when the original request goes unanswered or is refused."""
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    def heading(text: str, *, bold: bool = True, center: bool = True, size: int = 12) -> None:
        paragraph = document.add_paragraph()
        if center:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(text)
        run.bold = bold
        run.font.size = Pt(size)

    def body(text: str) -> None:
        document.add_paragraph(text)

    heading("{{ application_title }}")
    document.add_paragraph()

    body("To,")
    body("The First Appellate Authority,")
    body("{{ public_authority_name }},")
    body("{{ public_authority_address }}.")
    document.add_paragraph()

    body("From,")
    body("{{ appellant_name }},")
    body("{{ appellant_address }}.")
    document.add_paragraph()

    body("Subject: First appeal under Section 19(1) of the Right to Information Act, 2005.")
    document.add_paragraph()

    body("Sir/Madam,")
    document.add_paragraph()

    heading("GROUNDS OF APPEAL", center=False)
    body("{{ appeal_clause }}")
    body("{{ citation_line }}")
    document.add_paragraph()

    body("Yours faithfully,")
    document.add_paragraph()
    document.add_paragraph()
    body("________________________________")
    body("{{ appellant_name }}")
    body("Appellant")
    body("Dated: {{ generated_date_display }}")

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    document.save(str(RTI_FIRST_APPEAL_TEMPLATE_PATH))
    logger.info("Saved base template to %s", RTI_FIRST_APPEAL_TEMPLATE_PATH)


def build_senior_citizen_maintenance_base_template() -> None:
    """Fixed section order: heading/forum -> parties -> applicant particulars -> grounds (clause
    inserted here) -> verification/signature block. An application to the Maintenance Tribunal,
    not a court petition, but structured the same PARTIES/Versus way as the eviction scenario
    since it is still an adversarial two-party proceeding."""
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    def heading(text: str, *, bold: bool = True, center: bool = True, size: int = 12) -> None:
        paragraph = document.add_paragraph()
        if center:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(text)
        run.bold = bold
        run.font.size = Pt(size)

    def body(text: str) -> None:
        document.add_paragraph(text)

    heading("{{ forum_name }}")
    heading("{{ application_title }}")
    document.add_paragraph()

    heading("PARTIES", center=False)
    body("{{ applicant_name }}, aged {{ applicant_age }} years, residing at {{ applicant_address }}")
    body("... Applicant")
    heading("Versus", bold=False)
    body("{{ respondent_name }}, residing at {{ respondent_address }}")
    body("... Respondent")
    document.add_paragraph()

    heading("GROUNDS OF APPLICATION", center=False)
    body("{{ maintenance_clause }}")
    body("{{ citation_line }}")
    document.add_paragraph()

    heading("VERIFICATION", center=False)
    body(
        "I, {{ applicant_name }}, the Applicant above named, do hereby verify that the contents "
        "of the foregoing application are true and correct to the best of my knowledge and "
        "belief, and that nothing material has been concealed therefrom."
    )
    body("Verified at ____________________ on {{ generated_date_display }}.")
    document.add_paragraph()
    document.add_paragraph()
    body("________________________________")
    body("{{ applicant_name }}")
    body("Applicant")

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    document.save(str(SENIOR_CITIZEN_MAINTENANCE_TEMPLATE_PATH))
    logger.info("Saved base template to %s", SENIOR_CITIZEN_MAINTENANCE_TEMPLATE_PATH)


def build_tenant_essential_supply_base_template() -> None:
    """Fixed section order: heading/forum -> parties (tenant as Applicant, landlord as
    Respondent -- reversed from the eviction scenario) -> property particulars -> grounds (clause
    inserted here) -> verification/signature block."""
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    def heading(text: str, *, bold: bool = True, center: bool = True, size: int = 12) -> None:
        paragraph = document.add_paragraph()
        if center:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(text)
        run.bold = bold
        run.font.size = Pt(size)

    def body(text: str) -> None:
        document.add_paragraph(text)

    heading("{{ forum_name }}")
    heading("{{ application_title }}")
    document.add_paragraph()

    heading("PARTIES", center=False)
    body("{{ tenant_name }}, residing at {{ tenant_address }}")
    body("... Applicant/Tenant")
    heading("Versus", bold=False)
    body("{{ landlord_name }}, residing at {{ landlord_address }}")
    body("... Respondent/Landlord")
    document.add_paragraph()

    heading("PROPERTY PARTICULARS", center=False)
    body("The tenanted premises are situated at: {{ property_address }}.")
    document.add_paragraph()

    heading("GROUNDS OF APPLICATION", center=False)
    body("{{ essential_supply_clause }}")
    body("{{ citation_line }}")
    document.add_paragraph()

    heading("VERIFICATION", center=False)
    body(
        "I, {{ tenant_name }}, the Applicant/Tenant above named, do hereby verify that the "
        "contents of the foregoing application are true and correct to the best of my knowledge "
        "and belief, and that nothing material has been concealed therefrom."
    )
    body("Verified at ____________________ on {{ generated_date_display }}.")
    document.add_paragraph()
    document.add_paragraph()
    body("________________________________")
    body("{{ tenant_name }}")
    body("Applicant/Tenant")

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    document.save(str(TENANT_ESSENTIAL_SUPPLY_TEMPLATE_PATH))
    logger.info("Saved base template to %s", TENANT_ESSENTIAL_SUPPLY_TEMPLATE_PATH)


def build_bank_fraud_complaint_base_template() -> None:
    """Fixed section order: heading -> addressee (bank) block -> complainant block -> subject
    line -> complaint body (clause inserted here) -> closing/signature block. A formal letter to
    a bank's grievance channel, same shape as the RTI scenarios -- not a court/commission
    pleading."""
    document = Document()
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)

    def heading(text: str, *, bold: bool = True, center: bool = True, size: int = 12) -> None:
        paragraph = document.add_paragraph()
        if center:
            paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = paragraph.add_run(text)
        run.bold = bold
        run.font.size = Pt(size)

    def body(text: str) -> None:
        document.add_paragraph(text)

    heading("{{ complaint_title }}")
    document.add_paragraph()

    body("To,")
    body("The Nodal Officer / Grievance Redressal Officer,")
    body("{{ bank_name }},")
    body("{{ bank_branch_address }}.")
    document.add_paragraph()

    body("From,")
    body("{{ complainant_name }},")
    body("{{ complainant_address }}.")
    document.add_paragraph()

    body("Subject: Complaint regarding an unauthorized electronic banking transaction.")
    document.add_paragraph()

    body("Sir/Madam,")
    document.add_paragraph()

    heading("COMPLAINT", center=False)
    body("{{ complaint_clause }}")
    document.add_paragraph()

    body("Yours faithfully,")
    document.add_paragraph()
    document.add_paragraph()
    body("________________________________")
    body("{{ complainant_name }}")
    body("Complainant")
    body("Dated: {{ generated_date_display }}")

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    document.save(str(BANK_FRAUD_COMPLAINT_TEMPLATE_PATH))
    logger.info("Saved base template to %s", BANK_FRAUD_COMPLAINT_TEMPLATE_PATH)


def build_case_file_base_template() -> None:
    """Case File export (case_file.py), not a complaint -- an information pack the user takes to a
    lawyer or DLSA. Same Times New Roman 12 body as the complaint templates. Fixed section order:
    cover (with the not-legal-advice notice) -> situation in brief -> facts as stated by you ->
    timeline -> laws that may apply -> where to go -> evidence checklist -> questions for the
    lawyer -> free legal help -> about this file -> appendix (conversation record).

    Optional sections sit entirely inside a {%p if ... %} block, heading included, so an
    omitted section leaves no empty heading behind. There is deliberately no Deadlines or
    forum-finder section: those features don't exist in the app yet. Section headings use the
    built-in "Heading 1" style (restyled) so LibreOffice exports them as PDF bookmarks."""
    document = Document()
    for section in document.sections:
        section.left_margin = section.right_margin = Cm(2.2)
        section.top_margin = section.bottom_margin = Cm(2.0)
    style = document.styles["Normal"]
    style.font.name = "Times New Roman"
    style.font.size = Pt(12)
    style.paragraph_format.space_after = Pt(4)
    for name, size in (("Heading 1", 15), ("Heading 2", 12.5)):
        heading_style = document.styles[name]
        heading_style.font.name = "Times New Roman"
        heading_style.font.size = Pt(size)
        heading_style.font.bold = True
        heading_style.font.color.rgb = RGBColor(0x3F, 0x28, 0x18)
        heading_style.paragraph_format.space_before = Pt(16 if name == "Heading 1" else 10)
        heading_style.paragraph_format.space_after = Pt(6)
        heading_style.paragraph_format.keep_with_next = True
        # python-docx's default theme sets an East-Asian/ascii theme font on headings; pin it.
        fonts = heading_style.element.get_or_add_rPr().get_or_add_rFonts()
        for attribute in ("w:asciiTheme", "w:hAnsiTheme", "w:eastAsiaTheme", "w:cstheme"):
            fonts.attrib.pop(qn(attribute), None)
        for attribute in ("w:ascii", "w:hAnsi", "w:cs"):
            fonts.set(qn(attribute), "Times New Roman")

    def paragraph(*runs: tuple[str, dict], center: bool = False, indent_cm: float = 0, size: float | None = None, keep_with_next: bool = False):
        para = document.add_paragraph()
        if center:
            para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if indent_cm:
            para.paragraph_format.left_indent = Cm(indent_cm)
        if keep_with_next:
            para.paragraph_format.keep_with_next = True
        for text, fmt in runs:
            run = para.add_run(text)
            run.bold = fmt.get("bold")
            run.italic = fmt.get("italic")
            if size or fmt.get("size"):
                run.font.size = Pt(fmt.get("size") or size)
            if fmt.get("muted"):
                run.font.color.rgb = RGBColor(0x5A, 0x37, 0x1D)
        return para

    def tag(text: str) -> None:
        # docxtpl {%p ... %} control paragraphs: removed entirely at render time.
        document.add_paragraph(text)

    def heading(text: str) -> None:
        document.add_heading(text, level=1)

    def subheading(text: str) -> None:
        document.add_heading(text, level=2)

    def page_break() -> None:
        document.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def shade(cell, fill: str) -> None:
        properties = cell._tc.get_or_add_tcPr()
        shading = OxmlElement("w:shd")
        shading.set(qn("w:val"), "clear")
        shading.set(qn("w:color"), "auto")
        shading.set(qn("w:fill"), fill)
        properties.append(shading)

    # Footer on every page: the notice in short + page number.
    document.styles["Footer"].font.size = Pt(9)  # the PAGE field run takes the style size
    footer = document.sections[0].footer.paragraphs[0]
    footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
    footer_run = footer.add_run("Legal information, not legal advice. Not reviewed by a lawyer.  ·  Page ")
    footer_run.font.size = Pt(9)
    page_field = OxmlElement("w:fldSimple")
    page_field.set(qn("w:instr"), "PAGE")
    field_run = OxmlElement("w:r")
    field_properties = OxmlElement("w:rPr")
    field_size = OxmlElement("w:sz")
    field_size.set(qn("w:val"), "18")
    field_properties.append(field_size)
    field_run.append(field_properties)
    field_text = OxmlElement("w:t")
    field_text.text = "1"
    field_run.append(field_text)
    page_field.append(field_run)
    footer._p.append(page_field)

    # 1. Cover
    for _ in range(3):
        document.add_paragraph()
    paragraph(("{{ heading }}", {"bold": True}), center=True, size=20)
    document.add_paragraph()
    paragraph(("{{ title }}", {"bold": True}), center=True, size=16)
    document.add_paragraph()
    paragraph(("Legal area(s): ", {"bold": True}), ("{{ legal_areas }}", {}), center=True)
    paragraph(("{%if case_created_display %}Case started: {{ case_created_display }}   ·   {% endif %}File generated: {{ generated_on_display }}", {}), center=True)
    document.add_paragraph()
    notice_table = document.add_table(rows=1, cols=1)
    notice_table.style = "Table Grid"
    notice_cell = notice_table.rows[0].cells[0]
    shade(notice_cell, "FFF4D6")
    notice_title = notice_cell.paragraphs[0]
    notice_title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    notice_title_run = notice_title.add_run("IMPORTANT — PLEASE READ")
    notice_title_run.bold = True
    notice_body = notice_cell.add_paragraph()
    notice_body.alignment = WD_ALIGN_PARAGRAPH.CENTER
    notice_body_run = notice_body.add_run("{{ notice }}")
    notice_body_run.bold = True
    notice_body_run.font.size = Pt(13)
    document.add_paragraph()
    paragraph(("{{ how_made }}", {"italic": True, "muted": True}), size=10.5)
    page_break()

    # 2. Situation in brief
    heading("Your situation in brief")
    paragraph(("{{ situation.label }}:", {"italic": True, "muted": True}), size=10.5)
    paragraph(("{{ situation.text }}", {}))

    # 3. Facts as stated by you
    heading("Facts as stated by you")
    paragraph(("These are recorded exactly as you gave them. They have not been checked or proven.", {"italic": True, "muted": True}), size=10.5)
    tag("{%p for fact in facts %}")
    paragraph(("{{ loop.index }}. {{ fact.text }}", {}), keep_with_next=True)
    paragraph(("{{ fact.label }}{% if fact.stated_on %}, {{ fact.stated_on }}{% endif %}", {"italic": True, "muted": True}), indent_cm=0.6, size=10)
    tag("{%p endfor %}")

    # 4. Timeline (only dated facts)
    tag("{%p if timeline %}")
    heading("Timeline")
    paragraph(("Only dates that you or a document you confirmed actually gave, oldest first. No date has been estimated.", {"italic": True, "muted": True}), size=10.5)
    tag("{%p for event in timeline %}")
    paragraph(("{{ event.date_display }}", {"bold": True}), ("  —  {{ event.text }}", {}))
    paragraph(("{{ event.label }}", {"italic": True, "muted": True}), indent_cm=0.6, size=10)
    tag("{%p endfor %}")
    tag("{%p endif %}")

    # 5. Laws that may apply
    tag("{%p if laws %}")
    heading("Laws that may apply")
    paragraph(
        (
            "Sources Legal Aid AI retrieved from its legal library and checked against its answers to you. "
            "Whether they actually apply to your case is a question for a lawyer.",
            {"italic": True, "muted": True},
        ),
        size=10.5,
    )
    tag("{%p for law in laws %}")
    paragraph(("{{ law.title }}{% if law.provision %} — {{ law.provision }}{% endif %}", {"bold": True}), keep_with_next=True)
    paragraph(("{{ law.authority }}{% if law.pages %} · {{ law.pages }}{% endif %}{% if law.warning %} · {{ law.warning }}{% endif %}", {"italic": True, "muted": True}), size=10, keep_with_next=True)
    paragraph(("“{{ law.excerpt }}”", {}), indent_cm=0.6, size=10.5)
    tag("{%p endfor %}")
    tag("{%p endif %}")

    # 6. Where to go
    tag("{%p if where_to_go %}")
    heading("Where to go")
    paragraph(("Places Legal Aid AI's answers to you mentioned for raising this issue.", {"italic": True, "muted": True}), size=10.5)
    tag("{%p for place in where_to_go %}")
    paragraph(("•  {{ place }}", {}), indent_cm=0.3)
    tag("{%p endfor %}")
    tag("{%p endif %}")

    # 7. Evidence checklist
    tag("{%p if evidence_items or uploaded_documents %}")
    heading("Evidence checklist")
    tag("{%p if evidence_items %}")
    paragraph(("Tick each item once you have it safely kept (originals and copies).", {"italic": True, "muted": True}), size=10.5)
    tag("{%p for item in evidence_items %}")
    paragraph(("☐  {{ item }}", {}), indent_cm=0.3)
    tag("{%p endfor %}")
    tag("{%p endif %}")
    tag("{%p if uploaded_documents %}")
    subheading("Documents already uploaded")
    tag("{%p for doc in uploaded_documents %}")
    paragraph(("☑  {{ doc.name }}{% if doc.date %} (uploaded {{ doc.date }}){% endif %}", {}), indent_cm=0.3)
    tag("{%p endfor %}")
    tag("{%p endif %}")
    tag("{%p endif %}")

    # 8. Questions for the lawyer (fixed list)
    heading("Questions you may want to ask the lawyer")
    tag("{%p for question in lawyer_questions %}")
    paragraph(("{{ loop.index }}. {{ question }}", {}))
    tag("{%p endfor %}")

    # 9. Free legal help
    heading("Free legal help")
    tag("{%p for help in free_help %}")
    paragraph(("{{ help.name }}", {"bold": True}), ("  —  {{ help.contact }}", {}), keep_with_next=True)
    paragraph(("{{ help.detail }}", {}), indent_cm=0.6, size=10.5)
    tag("{%p endfor %}")

    # 10. About this file
    tag("{%p if notes %}")
    heading("About this file")
    tag("{%p for note in notes %}")
    paragraph(("•  {{ note }}", {}), indent_cm=0.3, size=10.5)
    tag("{%p endfor %}")
    tag("{%p endif %}")

    # 11. Appendix -- conversation record. No forced page break: when "About this file" spills
    # onto a new page, a break here left that page almost empty.
    heading("Appendix — conversation record")
    paragraph(("Each message you sent and the app's short reply. The full answers are in the app under My Cases.", {"italic": True, "muted": True}), size=10.5)
    tag("{%p for entry in appendix %}")
    paragraph(("{% if entry.date %}{{ entry.date }} — {% endif %}You asked:", {"bold": True}), keep_with_next=True, size=10.5)
    paragraph(("{{ entry.question }}", {}), indent_cm=0.6, keep_with_next=True)
    paragraph(("{{ entry.answer_label }}: ", {"bold": True}), ("{{ entry.short_answer }}", {}), indent_cm=0.6, size=10.5)
    tag("{%p endfor %}")

    TEMPLATES_DIR.mkdir(parents=True, exist_ok=True)
    document.save(str(CASE_FILE_TEMPLATE_PATH))
    logger.info("Saved base template to %s", CASE_FILE_TEMPLATE_PATH)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    build_tenancy_eviction_base_template()
    build_consumer_defective_goods_base_template()
    build_misleading_advertisement_base_template()
    build_rti_application_base_template()
    build_rti_first_appeal_base_template()
    build_senior_citizen_maintenance_base_template()
    build_tenant_essential_supply_base_template()
    build_bank_fraud_complaint_base_template()
    build_case_file_base_template()


if __name__ == "__main__":
    main()
