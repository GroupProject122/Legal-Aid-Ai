"""Generate the sample documents in this folder (fictional person, fictional companies).

    python sample-documents/generate_sample_documents.py

Every name, number and address here is made up for testing Legal Aid AI's document features;
the Aadhaar number is masked like a real e-Aadhaar printout. Uses fpdf (PDF) and python-docx
(Word), both already installed with the backend requirements.
"""
from __future__ import annotations

from pathlib import Path

from docx import Document
from fpdf import FPDF

OUT = Path(__file__).resolve().parent

PERSON = "Priya Sharma"
ADDRESS = "Flat 12B, Green Park Extension, New Delhi 110016"


def pdf(filename: str, title: str, lines: list[str]) -> None:
    doc = FPDF()
    doc.add_page()
    doc.set_font("Helvetica", "B", 15)
    doc.multi_cell(0, 9, title, new_x="LMARGIN", new_y="NEXT")
    doc.ln(3)
    doc.set_font("Helvetica", size=11)
    for line in lines:
        if line == "":
            doc.ln(4)
        else:
            doc.multi_cell(0, 6.5, line, new_x="LMARGIN", new_y="NEXT")
    doc.output(str(OUT / filename))


def docx(filename: str, title: str, paragraphs: list[str]) -> None:
    doc = Document()
    doc.add_heading(title, level=1)
    for paragraph in paragraphs:
        doc.add_paragraph(paragraph)
    doc.save(OUT / filename)


def txt(filename: str, lines: list[str]) -> None:
    (OUT / filename).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    # --- Identity and address proof (useful in any case) ---
    pdf("aadhaar_card_masked.pdf", "Government of India - Aadhaar (e-Aadhaar, masked)", [
        "Unique Identification Authority of India (UIDAI)",
        "",
        f"Name: {PERSON}",
        "Date of Birth: 14/03/1996",
        "Gender: Female",
        f"Address: {ADDRESS}",
        "",
        "Aadhaar No.: XXXX XXXX 4821",
        "",
        "Aadhaar is proof of identity, not of citizenship or date of birth.",
    ])
    pdf("electricity_bill_aug_2026.pdf", "Delhi Power Distribution Ltd - Electricity Bill", [
        "Bill Month: August 2026        Bill Date: 05/09/2026        Due Date: 20/09/2026",
        "",
        f"Consumer Name: {PERSON}",
        f"Supply Address: {ADDRESS}",
        "CA Number: 1520 3344 87",
        "",
        "Units consumed: 312 kWh",
        "Energy charges: Rs. 1,874.00",
        "Fixed charges: Rs. 250.00",
        "Total amount payable: Rs. 2,124.00",
        "",
        "This bill may be used as proof of address.",
    ])

    # --- Tenancy: security deposit not returned ---
    pdf("rent_agreement_green_park.pdf", "Rent Agreement", [
        "This Rent Agreement is made at New Delhi on 1 July 2025",
        "",
        "BETWEEN Mr. Rakesh Malhotra, resident of C-44 Hauz Khas, New Delhi 110016",
        "(hereinafter the LESSOR / LANDLORD)",
        "",
        f"AND Ms. {PERSON}, (hereinafter the LESSEE / TENANT).",
        "",
        f"1. Premises: {ADDRESS}, a two-room furnished flat.",
        "2. Term: 11 months from 1 July 2025, renewable by mutual consent.",
        "3. Monthly rent: Rs. 25,000, payable on or before the 5th of each month.",
        "4. Security deposit: Rs. 50,000 paid by the Tenant, refundable within 30 days of the Tenant",
        "   vacating the premises, after deducting only unpaid rent or the cost of damage beyond normal",
        "   wear and tear.",
        "5. Either party may end this agreement with one month's written notice.",
        "6. Electricity and water charges are payable by the Tenant as per actual meter readings.",
        "",
        "Signed: Rakesh Malhotra (Landlord)        Signed: Priya Sharma (Tenant)",
        "Witness: Anil Gupta",
    ])
    pdf("rent_receipts_jan_jun_2026.pdf", "Rent Receipts - January to June 2026", [
        f"Received from {PERSON} the monthly rent for {ADDRESS}.",
        "",
        "Month            Amount          Date paid     Mode",
        "January 2026     Rs. 25,000      03/01/2026    UPI",
        "February 2026    Rs. 25,000      04/02/2026    UPI",
        "March 2026       Rs. 25,000      02/03/2026    UPI",
        "April 2026       Rs. 25,000      05/04/2026    UPI",
        "May 2026         Rs. 25,000      03/05/2026    UPI",
        "June 2026        Rs. 25,000      04/06/2026    UPI",
        "",
        "Security deposit of Rs. 50,000 received on 1 July 2025 (held by landlord).",
        "No rent is outstanding as of 30 June 2026.",
        "",
        "Received by: Rakesh Malhotra (Landlord)",
    ])
    docx("legal_notice_to_landlord.docx", "Legal Notice for Refund of Security Deposit", [
        "Date: 20 July 2026",
        "To: Mr. Rakesh Malhotra, C-44 Hauz Khas, New Delhi 110016",
        f"From: {PERSON}, presently residing at 7 Saket Enclave, New Delhi 110017",
        "Subject: Refund of security deposit of Rs. 50,000 under the Rent Agreement dated 1 July 2025",
        "Sir, I was your tenant at Flat 12B, Green Park Extension, New Delhi under the Rent Agreement dated "
        "1 July 2025. I gave one month's written notice on 30 May 2026 and vacated the premises on 30 June 2026, "
        "handing over the keys in your presence. All rent up to June 2026 has been paid and the flat was left in good condition.",
        "Under clause 4 of the agreement, the security deposit of Rs. 50,000 was to be refunded within 30 days of my vacating, "
        "i.e. by 30 July 2026. You have not refunded it despite repeated requests by phone and WhatsApp.",
        "You are hereby called upon to refund Rs. 50,000 within 15 days of receiving this notice, failing which I will be "
        "constrained to take appropriate legal action at your cost.",
        f"Yours faithfully, {PERSON}",
    ])

    # --- Consumer: refrigerator stopped working under warranty ---
    pdf("refrigerator_tax_invoice.pdf", "HomeKart Electronics - Tax Invoice", [
        "HomeKart Electronics Pvt. Ltd., 18 Central Market, Lajpat Nagar, New Delhi 110024",
        "GSTIN: 07ABCDE1234F1Z5",
        "",
        "Invoice No: HK/2026/05/0192        Invoice Date: 02/05/2026",
        f"Bill to: {PERSON}, {ADDRESS}",
        "",
        "Item: CoolBreeze 260L Frost-Free Double Door Refrigerator, Model CB-260DD",
        "Serial No: CB26D5X88213",
        "Qty: 1        Rate: Rs. 27,542.37        GST 18%: Rs. 4,957.63",
        "Total: Rs. 32,500.00",
        "Payment: Debit card ending 4410",
        "",
        "Warranty: 1 year comprehensive on product, 10 years on compressor (see warranty card).",
    ])
    pdf("refrigerator_warranty_card.pdf", "CoolBreeze Appliances - Warranty Card", [
        "Model: CB-260DD        Serial No: CB26D5X88213",
        "Date of purchase: 02/05/2026        Dealer: HomeKart Electronics, Lajpat Nagar",
        "",
        "Warranty terms:",
        "1. 12 months comprehensive warranty from the date of purchase covering all parts and labour.",
        "2. 10 years warranty on the compressor.",
        "3. Warranty does not cover damage from misuse, voltage fluctuation without a stabiliser, or",
        "   physical damage.",
        "4. Service requests: CoolBreeze Service Centre, toll-free 1800-000-0000.",
    ])
    txt("service_centre_job_sheet.txt", [
        "CoolBreeze Authorised Service Centre - Job Sheet",
        "Job No: CBS-DL-77120        Date: 21/08/2026",
        f"Customer: {PERSON}, {ADDRESS}",
        "Product: CoolBreeze 260L Refrigerator, Model CB-260DD, Serial CB26D5X88213",
        "Complaint: Not cooling since 18/08/2026",
        "Technician finding: Compressor not working. Gas leakage from condenser coil.",
        "Remarks: Damage attributed to voltage fluctuation. Not covered under warranty.",
        "Estimate for repair: Rs. 9,000 (compressor + gas refill), payable by customer.",
        "Customer remarks: Customer disagrees. Stabiliser was in use since installation.",
    ])
    pdf("phone_purchase_invoice_2025.pdf", "QuickMobiles - Tax Invoice", [
        "QuickMobiles, 4 Nehru Place, New Delhi 110019",
        "Invoice No: QM-25-11873        Invoice Date: 14/11/2025",
        f"Bill to: {PERSON}",
        "Item: Nova X5 smartphone, 128 GB        IMEI: 35 882 110 457 219 0",
        "Total: Rs. 18,999.00        Payment: UPI",
        "Warranty: 1 year manufacturer warranty.",
    ])

    # --- Cyber: UPI fraud ---
    pdf("bank_statement_sept_2026.pdf", "Bharat Union Bank - Account Statement", [
        f"Account holder: {PERSON}        Account No: XXXXXX7732        Branch: Green Park, New Delhi",
        "Statement period: 01/09/2026 to 15/09/2026",
        "",
        "Date         Description                                   Debit        Credit       Balance",
        "01/09/2026   Opening balance                                                         Rs. 61,240",
        "03/09/2026   UPI/Salary credit/ACME Tech                                Rs. 85,000   Rs. 1,46,240",
        "05/09/2026   UPI/Rent/7 Saket Enclave                     Rs. 22,000                 Rs. 1,24,240",
        "08/09/2026   UPI/UTR 624811093301/merchant-pay@xyz        Rs. 25,000                 Rs. 99,240",
        "08/09/2026   UPI/UTR 624811093518/merchant-pay@xyz        Rs. 20,000                 Rs. 79,240",
        "10/09/2026   ATM withdrawal                               Rs. 5,000                  Rs. 74,240",
        "",
        "Customer disputes the two transactions of 08/09/2026 (Rs. 45,000 total) as unauthorised.",
    ])
    pdf("cybercrime_complaint_acknowledgement.pdf", "National Cyber Crime Reporting Portal - Acknowledgement", [
        "cybercrime.gov.in",
        "",
        "Acknowledgement Number: 31509260045172",
        "Date of complaint: 08/09/2026, 18:42",
        f"Complainant: {PERSON}, {ADDRESS}",
        "Category: Online Financial Fraud - UPI related fraud",
        "Amount lost: Rs. 45,000 (two UPI transactions, UTR 624811093301 and 624811093518)",
        "Suspect details: Caller claimed to be from bank KYC team, mobile 90000 12345, link sent by SMS.",
        "",
        "Your complaint has been registered and forwarded to the concerned police station.",
        "Also call helpline 1930 for financial fraud.",
    ])

    # --- Public authority: RTI not answered ---
    docx("rti_application_municipal_corporation.docx", "Application under the Right to Information Act, 2005", [
        "To: The Public Information Officer, South Delhi Municipal Corporation, Engineering Department, Green Park Zone, New Delhi",
        f"From: {PERSON}, {ADDRESS}",
        "Date: 1 August 2026",
        "Subject: Information on road repair work in Green Park Extension",
        "Please provide the following information for the period 1 January 2025 to 31 July 2026:",
        "1. Copies of the work orders issued for repair of the main road in Green Park Extension.",
        "2. The sanctioned budget and the amount actually spent.",
        "3. The name of the contractor and the scheduled completion date.",
        "4. Copies of any inspection reports on the quality of the work.",
        "The application fee of Rs. 10 has been paid by Indian Postal Order No. 45F 667812.",
        "I am a citizen of India.",
        f"Signature: {PERSON}",
    ])
    print(f"Wrote sample documents to {OUT}")


if __name__ == "__main__":
    main()
