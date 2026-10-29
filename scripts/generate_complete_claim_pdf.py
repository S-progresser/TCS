import os
import pymupdf

def build_pdf(filepath: str):
    doc = pymupdf.open()

    # ---------------- PAGE 1: HOSPITAL DISCHARGE SUMMARY ----------------
    page1 = doc.new_page(width=595, height=842) # A4 size

    # Header banner
    page1.draw_rect(pymupdf.Rect(40, 35, 555, 95), color=(0.1, 0.45, 0.45), fill=(0.94, 0.98, 0.98), width=1)
    page1.insert_text((55, 60), "APOLLO CITY HOSPITAL & RESEARCH INSTITUTE", fontsize=15, fontname="helv", fontfile=None, color=(0.05, 0.3, 0.3))
    page1.insert_text((55, 75), "154 Bannerghatta Main Road, Bengaluru, Karnataka 560076 | Phone: +91 80 2630 4000", fontsize=8, color=(0.3, 0.3, 0.3))
    page1.insert_text((55, 87), "Accreditation: NABH / NABL Accredited Multi-Specialty Tertiary Care Center", fontsize=8, color=(0.3, 0.3, 0.3))

    # Document Title
    page1.draw_rect(pymupdf.Rect(40, 105, 555, 130), color=(0.15, 0.35, 0.35), fill=(0.15, 0.35, 0.35))
    page1.insert_text((185, 122), "HOSPITAL DISCHARGE SUMMARY", fontsize=13, color=(1, 1, 1))

    # Patient & Admission Meta Box
    page1.draw_rect(pymupdf.Rect(40, 140, 555, 255), color=(0.8, 0.8, 0.8), fill=(0.98, 0.98, 0.98), width=0.8)
    
    col1 = 55
    col2 = 310
    y = 158
    page1.insert_text((col1, y), "Patient Name:", fontsize=9.5, color=(0.1, 0.1, 0.1))
    page1.insert_text((col1 + 80, y), "Asha Reddy", fontsize=10, color=(0, 0, 0))
    page1.insert_text((col2, y), "Claim Reference:", fontsize=9.5, color=(0.1, 0.1, 0.1))
    page1.insert_text((col2 + 95, y), "CLM-3021", fontsize=10, color=(0, 0, 0))

    y += 18
    page1.insert_text((col1, y), "Patient ID / UHID:", fontsize=9, color=(0.3, 0.3, 0.3))
    page1.insert_text((col1 + 95, y), "ACH-BLR-2026-90412", fontsize=9, color=(0.1, 0.1, 0.1))
    page1.insert_text((col2, y), "Policy Number:", fontsize=9, color=(0.3, 0.3, 0.3))
    page1.insert_text((col2 + 95, y), "TCS-HL-77891", fontsize=9.5, color=(0, 0, 0))

    y += 18
    page1.insert_text((col1, y), "Age / Gender:", fontsize=9, color=(0.3, 0.3, 0.3))
    page1.insert_text((col1 + 95, y), "42 Years / Female", fontsize=9, color=(0.1, 0.1, 0.1))
    page1.insert_text((col2, y), "Insurance Provider:", fontsize=9, color=(0.3, 0.3, 0.3))
    page1.insert_text((col2 + 95, y), "ClaimSense Protect", fontsize=9, color=(0.1, 0.1, 0.1))

    y += 18
    page1.insert_text((col1, y), "Date of Admission:", fontsize=9, color=(0.3, 0.3, 0.3))
    page1.insert_text((col1 + 95, y), "2026-10-25 (09:30 AM)", fontsize=9, color=(0.1, 0.1, 0.1))
    page1.insert_text((col2, y), "Treatment Date:", fontsize=9, color=(0.3, 0.3, 0.3))
    page1.insert_text((col2 + 95, y), "2026-10-28", fontsize=9.5, color=(0, 0, 0))

    y += 18
    page1.insert_text((col1, y), "Date of Discharge:", fontsize=9, color=(0.3, 0.3, 0.3))
    page1.insert_text((col1 + 95, y), "2026-10-28 (04:30 PM)", fontsize=9, color=(0.1, 0.1, 0.1))
    page1.insert_text((col2, y), "Attending Consultant:", fontsize=9, color=(0.3, 0.3, 0.3))
    page1.insert_text((col2 + 95, y), "Dr. Ramesh Kumar, MS, DNB", fontsize=9, color=(0.1, 0.1, 0.1))

    y += 18
    page1.insert_text((col1, y), "Department:", fontsize=9, color=(0.3, 0.3, 0.3))
    page1.insert_text((col1 + 95, y), "Gynecology & Laparoscopic Surgery", fontsize=9, color=(0.1, 0.1, 0.1))
    page1.insert_text((col2, y), "Ward / Room No:", fontsize=9, color=(0.3, 0.3, 0.3))
    page1.insert_text((col2 + 95, y), "Deluxe Private Ward 304", fontsize=9, color=(0.1, 0.1, 0.1))

    # Clinical Summary Section
    y = 275
    page1.draw_line(pymupdf.Point(40, y), pymupdf.Point(555, y), color=(0.2, 0.4, 0.4), width=1)
    page1.insert_text((40, y + 16), "CLINICAL DIAGNOSIS & REASON FOR ADMISSION", fontsize=10.5, color=(0.1, 0.35, 0.35))
    y += 32
    page1.insert_text((40, y), "Primary Diagnosis: Symptomatic Multiple Intramural & Subserosal Uterine Leiomyoma (Fibroids) with Menorrhagia.", fontsize=9, color=(0.15, 0.15, 0.15))
    y += 15
    page1.insert_text((40, y), "Secondary Findings: Microcytic hypochromic anaemia secondary to chronic heavy menstrual blood loss.", fontsize=9, color=(0.2, 0.2, 0.2))

    y += 26
    page1.draw_line(pymupdf.Point(40, y), pymupdf.Point(555, y), color=(0.2, 0.4, 0.4), width=1)
    page1.insert_text((40, y + 16), "SURGICAL PROCEDURE & OPERATIVE FINDINGS", fontsize=10.5, color=(0.1, 0.35, 0.35))
    y += 32
    page1.insert_text((40, y), "Procedure Performed: Total Laparoscopic Hysterectomy (TLH) with Bilateral Salpingectomy.", fontsize=9, color=(0.15, 0.15, 0.15))
    y += 15
    page1.insert_text((40, y), "Anaesthesia Type: General Endotracheal Anaesthesia | Procedure Date: 2026-10-26 | Duration: 2 hours 15 mins", fontsize=9, color=(0.2, 0.2, 0.2))
    y += 15
    page1.insert_text((40, y), "Operative Details: Successful laparoscopic excision of uterus. Specimen removed via vaginal vault. Good hemostasis.", fontsize=9, color=(0.2, 0.2, 0.2))

    y += 26
    page1.draw_line(pymupdf.Point(40, y), pymupdf.Point(555, y), color=(0.2, 0.4, 0.4), width=1)
    page1.insert_text((40, y + 16), "HOSPITAL COURSE & CONDITION AT DISCHARGE", fontsize=10.5, color=(0.1, 0.35, 0.35))
    y += 32
    page1.insert_text((40, y), "Patient had an uneventful post-operative recovery. Foley catheter removed on post-op day 1. Tolerating soft diet.", fontsize=9, color=(0.2, 0.2, 0.2))
    y += 15
    page1.insert_text((40, y), "Condition at discharge: Stable, fully ambulatory, afebrile, surgical ports clean, dry, and healthy. Pain well-managed.", fontsize=9, color=(0.2, 0.2, 0.2))

    y += 26
    page1.draw_line(pymupdf.Point(40, y), pymupdf.Point(555, y), color=(0.2, 0.4, 0.4), width=1)
    page1.insert_text((40, y + 16), "DISCHARGE MEDICATION & FOLLOW-UP ADVICE", fontsize=10.5, color=(0.1, 0.35, 0.35))
    y += 32
    page1.insert_text((40, y), "1. Tab. Cefixime 200mg BD x 5 days | 2. Tab. Paracetamol 650mg TDS PRN | 3. Tab. Pantoprazole 40mg OD x 7 days", fontsize=8.5, color=(0.2, 0.2, 0.2))
    y += 15
    page1.insert_text((40, y), "Follow-up: Visit Gynaecology OPD after 7 days for suture inspection and histopathology review.", fontsize=8.5, color=(0.2, 0.2, 0.2))

    # Doctor Signature and Stamp
    y = 705
    page1.draw_rect(pymupdf.Rect(40, y, 555, 790), color=(0.7, 0.7, 0.7), fill=(0.97, 0.99, 0.99), width=0.8)
    page1.insert_text((55, y + 20), "Hospital Verification Stamp:", fontsize=8.5, color=(0.3, 0.3, 0.3))
    page1.draw_rect(pymupdf.Rect(55, y + 28, 220, y + 72), color=(0.2, 0.5, 0.7), fill=(0.94, 0.97, 1.0), width=1)
    page1.insert_text((65, y + 45), "[OFFICIAL HOSPITAL SEAL]", fontsize=9, color=(0.1, 0.3, 0.6))
    page1.insert_text((65, y + 60), "Apollo City Hospital - Bengaluru Stamped", fontsize=8, color=(0.2, 0.35, 0.6))

    page1.insert_text((320, y + 20), "Authorized Medical Signature:", fontsize=8.5, color=(0.3, 0.3, 0.3))
    page1.insert_text((320, y + 42), "Signature: Signed by Dr. Ramesh Kumar, MS, DNB", fontsize=9.5, color=(0.05, 0.2, 0.4))
    page1.insert_text((320, y + 57), "Senior Consultant Gynecological Surgeon (KMC Reg. 44912)", fontsize=8, color=(0.3, 0.3, 0.3))
    page1.insert_text((320, y + 70), "Date of Certification: 2026-10-28", fontsize=8, color=(0.3, 0.3, 0.3))


    # ---------------- PAGE 2: FINAL HOSPITAL INVOICE & ITEMIZED BILL ----------------
    page2 = doc.new_page(width=595, height=842)

    # Header banner
    page2.draw_rect(pymupdf.Rect(40, 35, 555, 95), color=(0.1, 0.45, 0.45), fill=(0.94, 0.98, 0.98), width=1)
    page2.insert_text((55, 60), "APOLLO CITY HOSPITAL - BILLING & REVENUE DEPARTMENT", fontsize=14, color=(0.05, 0.3, 0.3))
    page2.insert_text((55, 75), "GSTIN: 29AAAAA0000A1Z5 | PAN: AAACR9081K | CIN: U85110KA2001PLC029810", fontsize=8, color=(0.3, 0.3, 0.3))
    page2.insert_text((55, 87), "154 Bannerghatta Main Road, Bengaluru, Karnataka 560076 | Central Billing Desk: +91 80 2630 4050", fontsize=8, color=(0.3, 0.3, 0.3))

    # Invoice Title Box
    page2.draw_rect(pymupdf.Rect(40, 105, 555, 130), color=(0.12, 0.32, 0.4), fill=(0.12, 0.32, 0.4))
    page2.insert_text((160, 122), "FINAL HOSPITAL INVOICE & ITEMIZED BILL", fontsize=13, color=(1, 1, 1))

    # Invoice Metadata Table
    page2.draw_rect(pymupdf.Rect(40, 140, 555, 235), color=(0.8, 0.8, 0.8), fill=(0.98, 0.98, 0.98), width=0.8)
    
    y = 158
    page2.insert_text((col1, y), "Invoice / Bill Number:", fontsize=9, color=(0.3, 0.3, 0.3))
    page2.insert_text((col1 + 105, y), "INV-BLR-2026-9941", fontsize=9.5, color=(0, 0, 0))
    page2.insert_text((col2, y), "Invoice Date:", fontsize=9, color=(0.3, 0.3, 0.3))
    page2.insert_text((col2 + 85, y), "2026-10-28", fontsize=9.5, color=(0, 0, 0))

    y += 18
    page2.insert_text((col1, y), "Patient / Claimant:", fontsize=9, color=(0.3, 0.3, 0.3))
    page2.insert_text((col1 + 105, y), "Asha Reddy", fontsize=10, color=(0, 0, 0))
    page2.insert_text((col2, y), "Treatment Date:", fontsize=9, color=(0.3, 0.3, 0.3))
    page2.insert_text((col2 + 85, y), "2026-10-28", fontsize=9.5, color=(0, 0, 0))

    y += 18
    page2.insert_text((col1, y), "Policy Number:", fontsize=9, color=(0.3, 0.3, 0.3))
    page2.insert_text((col1 + 105, y), "TCS-HL-77891", fontsize=9.5, color=(0, 0, 0))
    page2.insert_text((col2, y), "Claim Reference:", fontsize=9, color=(0.3, 0.3, 0.3))
    page2.insert_text((col2 + 85, y), "CLM-3021", fontsize=9.5, color=(0, 0, 0))

    y += 18
    page2.insert_text((col1, y), "Hospital Admission:", fontsize=9, color=(0.3, 0.3, 0.3))
    page2.insert_text((col1 + 105, y), "2026-10-25", fontsize=9, color=(0.1, 0.1, 0.1))
    page2.insert_text((col2, y), "Discharge Date:", fontsize=9, color=(0.3, 0.3, 0.3))
    page2.insert_text((col2 + 85, y), "2026-10-28", fontsize=9, color=(0.1, 0.1, 0.1))

    y += 18
    page2.insert_text((col1, y), "Insurance Payer:", fontsize=9, color=(0.3, 0.3, 0.3))
    page2.insert_text((col1 + 105, y), "ClaimSense Protect", fontsize=9, color=(0.1, 0.1, 0.1))
    page2.insert_text((col2, y), "Payment Mode:", fontsize=9, color=(0.3, 0.3, 0.3))
    page2.insert_text((col2 + 85, y), "Original Bill / Paid in Full", fontsize=9, color=(0.05, 0.45, 0.15))

    # Itemized Charges Table
    y = 255
    page2.draw_rect(pymupdf.Rect(40, y, 555, y + 22), color=(0.2, 0.35, 0.4), fill=(0.9, 0.94, 0.96))
    page2.insert_text((48, y + 15), "Sl", fontsize=8.5, color=(0.1, 0.2, 0.3))
    page2.insert_text((70, y + 15), "Service Description / Billing Category", fontsize=9, color=(0.1, 0.2, 0.3))
    page2.insert_text((345, y + 15), "SAC / Code", fontsize=8.5, color=(0.1, 0.2, 0.3))
    page2.insert_text((420, y + 15), "Qty / Days", fontsize=8.5, color=(0.1, 0.2, 0.3))
    page2.insert_text((490, y + 15), "Amount (INR)", fontsize=9, color=(0.1, 0.2, 0.3))

    items = [
        ("1", "Room charges (Deluxe Private AC Ward - 3 Days)", "999312", "3 Days", "Rs. 45000"),
        ("2", "Operation Theatre (OT) & High-Tech Laparoscopy charges", "999313", "1 Proc", "Rs. 40000"),
        ("3", "Surgery charges (Senior Consultant Operating Surgeon Fees)", "999314", "1 Team", "Rs. 35000"),
        ("4", "Anaesthesia charges & Pre-operative Monitoring", "999315", "1 Case", "Rs. 15000"),
        ("5", "Medicine, Pharmacy consumables, IV Fluids & Trocar sets", "999316", "1 Kit", "Rs. 25000"),
        ("6", "Investigation charges (Pre-op Blood, ECG, Ultrasound & Histopathology)", "999317", "1 Panel", "Rs. 15000"),
        ("7", "Post-operative Consultation charges & Specialty Nursing care", "999318", "3 Days", "Rs. 10000"),
    ]

    table_y = y + 22
    for sl, desc, code, qty, amt in items:
        page2.draw_rect(pymupdf.Rect(40, table_y, 555, table_y + 24), color=(0.85, 0.85, 0.85), width=0.5)
        page2.insert_text((48, table_y + 16), sl, fontsize=8.5, color=(0.2, 0.2, 0.2))
        page2.insert_text((70, table_y + 16), desc, fontsize=8.5, color=(0.1, 0.1, 0.1))
        page2.insert_text((345, table_y + 16), code, fontsize=8, color=(0.3, 0.3, 0.3))
        page2.insert_text((425, table_y + 16), qty, fontsize=8, color=(0.3, 0.3, 0.3))
        page2.insert_text((490, table_y + 16), amt, fontsize=8.5, color=(0.1, 0.1, 0.1))
        table_y += 24

    # Financial Total Summary Box
    summary_y = table_y + 10
    page2.draw_rect(pymupdf.Rect(300, summary_y, 555, summary_y + 115), color=(0.1, 0.4, 0.4), fill=(0.96, 0.98, 0.98), width=1)
    
    sy = summary_y + 20
    page2.insert_text((315, sy), "Sub-Total Gross Charges:", fontsize=9, color=(0.3, 0.3, 0.3))
    page2.insert_text((475, sy), "Rs. 185,000.00", fontsize=9, color=(0.1, 0.1, 0.1))

    sy += 18
    page2.insert_text((315, sy), "Hospital Discount / Concession:", fontsize=9, color=(0.3, 0.3, 0.3))
    page2.insert_text((475, sy), "Rs. 0.00", fontsize=9, color=(0.1, 0.1, 0.1))

    sy += 18
    page2.insert_text((315, sy), "Taxable Service Value:", fontsize=9, color=(0.3, 0.3, 0.3))
    page2.insert_text((475, sy), "Rs. 185,000.00", fontsize=9, color=(0.1, 0.1, 0.1))

    sy += 22
    page2.draw_line(pymupdf.Point(305, sy - 5), pymupdf.Point(550, sy - 5), color=(0.2, 0.4, 0.4), width=1)
    page2.insert_text((315, sy + 10), "Total Amount:", fontsize=11, color=(0.05, 0.25, 0.25))
    page2.insert_text((465, sy + 10), "Rs. 185000", fontsize=12, color=(0.05, 0.25, 0.25))

    sy += 24
    page2.insert_text((315, sy + 6), "Bill Amount:", fontsize=9.5, color=(0.2, 0.2, 0.2))
    page2.insert_text((465, sy + 6), "Rs. 185000", fontsize=10, color=(0.2, 0.2, 0.2))

    # Payment Status Text
    page2.draw_rect(pymupdf.Rect(40, summary_y, 285, summary_y + 115), color=(0.8, 0.8, 0.8), fill=(0.98, 0.98, 0.98), width=0.8)
    page2.insert_text((50, summary_y + 20), "Payment & Clearance Confirmation", fontsize=9.5, color=(0.1, 0.35, 0.35))
    page2.insert_text((50, summary_y + 40), "Amount Received: Rs. 185,000 (Paid in Full)", fontsize=8.5, color=(0.05, 0.5, 0.15))
    page2.insert_text((50, summary_y + 55), "Balance Outstanding: Rs. 0 (Nil)", fontsize=8.5, color=(0.1, 0.1, 0.1))
    page2.insert_text((50, summary_y + 70), "Receipt Voucher: RCPT-BLR-2026-90412", fontsize=8, color=(0.3, 0.3, 0.3))
    page2.insert_text((50, summary_y + 85), "Mode: Electronic Bank Transfer / IMPS", fontsize=8, color=(0.3, 0.3, 0.3))
    page2.insert_text((50, summary_y + 100), "Status: Verified Final Hospital Bill", fontsize=8.5, color=(0.1, 0.35, 0.35))

    # Signatures & Stamps
    y = 690
    page2.draw_rect(pymupdf.Rect(40, y, 555, 785), color=(0.7, 0.7, 0.7), fill=(0.97, 0.99, 0.99), width=0.8)
    
    page2.insert_text((55, y + 20), "Hospital Accounts & Cashier Stamp:", fontsize=8.5, color=(0.3, 0.3, 0.3))
    page2.draw_rect(pymupdf.Rect(55, y + 28, 230, y + 78), color=(0.15, 0.45, 0.3), fill=(0.93, 0.98, 0.94), width=1)
    page2.insert_text((65, y + 46), "[OFFICIAL PAID & CANCELLED STAMP]", fontsize=8.5, color=(0.1, 0.45, 0.2))
    page2.insert_text((65, y + 60), "Apollo City Hospital - Central Accounts Dept", fontsize=7.5, color=(0.2, 0.35, 0.2))
    page2.insert_text((65, y + 71), "Stamp: Stamped & Verified on 2026-10-28", fontsize=7.5, color=(0.2, 0.35, 0.2))

    page2.insert_text((315, y + 20), "Authorized Finance Officer Signature:", fontsize=8.5, color=(0.3, 0.3, 0.3))
    page2.insert_text((315, y + 44), "Signature: Signed by K. S. Sundaram", fontsize=9.5, color=(0.05, 0.2, 0.4))
    page2.insert_text((315, y + 59), "Chief Finance Officer & Hospital Controller", fontsize=8, color=(0.3, 0.3, 0.3))
    page2.insert_text((315, y + 72), "Authorized Hospital Signatory (Bengaluru)", fontsize=8, color=(0.3, 0.3, 0.3))


    # ---------------- PAGE 3: TREATING DOCTOR'S CERTIFICATE & CLAIM DECLARATION ----------------
    page3 = doc.new_page(width=595, height=842)

    # Header banner
    page3.draw_rect(pymupdf.Rect(40, 35, 555, 95), color=(0.1, 0.45, 0.45), fill=(0.94, 0.98, 0.98), width=1)
    page3.insert_text((55, 60), "APOLLO CITY HOSPITAL - DEPARTMENT OF GYNAECOLOGY", fontsize=14, color=(0.05, 0.3, 0.3))
    page3.insert_text((55, 75), "Medical Certificate & Certificate of Treatment for Mediclaim / Insurance", fontsize=8.5, color=(0.3, 0.3, 0.3))
    page3.insert_text((55, 87), "Reference Claim ID: CLM-3021 | Policy Number: TCS-HL-77891", fontsize=8.5, color=(0.3, 0.3, 0.3))

    page3.draw_rect(pymupdf.Rect(40, 105, 555, 130), color=(0.15, 0.35, 0.35), fill=(0.15, 0.35, 0.35))
    page3.insert_text((155, 122), "ATTENDING PHYSICIAN'S CERTIFICATE OF TREATMENT", fontsize=12, color=(1, 1, 1))

    y = 150
    page3.insert_text((40, y), "TO WHOMSOEVER IT MAY CONCERN / INSURER TPA CLAIM SETTLEMENT CELL", fontsize=9.5, color=(0.1, 0.1, 0.1))
    y += 20
    cert_text = (
        "This is to certify that Smt. Asha Reddy, aged 42 years, female, residing in Bengaluru, was admitted under my care at "
        "Apollo City Hospital on 2026-10-25 and was discharged on 2026-10-28 after receiving necessary medical and surgical treatment."
    )
    page3.insert_textbox(pymupdf.Rect(40, y, 555, y + 40), cert_text, fontsize=9, color=(0.2, 0.2, 0.2))
    
    y += 45
    page3.insert_text((40, y), "1. Diagnosis on Admission: Multiple intramural and subserosal uterine leiomyoma with persistent menorrhagia.", fontsize=9, color=(0.2, 0.2, 0.2))
    y += 18
    page3.insert_text((40, y), "2. Medical Necessity: Surgical intervention was medically necessary due to failure of medical management and anemia.", fontsize=9, color=(0.2, 0.2, 0.2))
    y += 18
    page3.insert_text((40, y), "3. Procedure Performed: Total Laparoscopic Hysterectomy with bilateral salpingectomy under GA on 2026-10-26.", fontsize=9, color=(0.2, 0.2, 0.2))
    y += 18
    page3.insert_text((40, y), "4. Treatment Date & Active Inpatient Duration: Active treatment date 2026-10-28 (Hospitalization: 3 Days).", fontsize=9, color=(0.2, 0.2, 0.2))
    y += 18
    page3.insert_text((40, y), "5. History of Previous Ailment: Nil relevant. Condition is not due to any pre-existing excluded illness.", fontsize=9, color=(0.2, 0.2, 0.2))

    # Doctor Certification Box
    y += 35
    page3.draw_rect(pymupdf.Rect(40, y, 555, y + 100), color=(0.8, 0.8, 0.8), fill=(0.98, 0.98, 0.98), width=0.8)
    page3.insert_text((50, y + 20), "Doctor Certification & Verification:", fontsize=9, color=(0.3, 0.3, 0.3))
    page3.insert_text((50, y + 42), "Signature: Signed by Dr. Ramesh Kumar, MS (OBG), DNB", fontsize=10, color=(0.05, 0.25, 0.4))
    page3.insert_text((50, y + 58), "Designation: Senior Consultant & HOD, Gynecological Surgery | KMC Reg: 44912", fontsize=8.5, color=(0.3, 0.3, 0.3))
    page3.insert_text((50, y + 72), "Hospital: Apollo City Hospital, Bengaluru | Date: 2026-10-28", fontsize=8.5, color=(0.3, 0.3, 0.3))
    page3.insert_text((50, y + 86), "Stamp: Official Medical Seal & Hospital Signature Attached", fontsize=8.5, color=(0.1, 0.4, 0.2))

    # Claimant Self-Declaration Box
    y += 125
    page3.draw_rect(pymupdf.Rect(40, y, 555, y + 155), color=(0.1, 0.35, 0.35), fill=(0.95, 0.98, 0.98), width=1)
    page3.insert_text((50, y + 22), "CLAIMANT'S SIGNED CLAIM DECLARATION & KYC VERIFICATION", fontsize=10.5, color=(0.05, 0.3, 0.3))
    decl_text = (
        "I, Asha Reddy, hereby declare that the medical and hospital billing information furnished in this claim is true, "
        "accurate, and complete in all respects. The total bill amount of Rs. 185000 corresponds to actual medical expenses "
        "incurred during my hospitalization at Apollo City Hospital from 2026-10-25 to 2026-10-28. I authorize ClaimSense Protect "
        "to verify these hospital records and process settlement as per policy terms."
    )
    page3.insert_textbox(pymupdf.Rect(50, y + 32, 545, y + 85), decl_text, fontsize=8.5, color=(0.2, 0.2, 0.2))
    
    page3.insert_text((50, y + 102), "Insured Customer Name: Asha Reddy", fontsize=9, color=(0, 0, 0))
    page3.insert_text((50, y + 118), "Policy Number: TCS-HL-77891 | Claim ID: CLM-3021", fontsize=9, color=(0, 0, 0))
    page3.insert_text((50, y + 134), "KYC Status: KYC verification complete (Aadhaar / PAN Verified)", fontsize=9, color=(0.05, 0.45, 0.15))

    page3.insert_text((340, y + 105), "Signature of Claimant:", fontsize=8.5, color=(0.3, 0.3, 0.3))
    page3.insert_text((340, y + 125), "Signed by Asha Reddy", fontsize=10.5, color=(0.05, 0.25, 0.4))
    page3.insert_text((340, y + 140), "Date: 2026-10-28 (Bengaluru)", fontsize=8.5, color=(0.3, 0.3, 0.3))

    # Save to file
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    doc.save(filepath)
    doc.close()
    print(f"Successfully generated complete claim PDF: {filepath}")

if __name__ == "__main__":
    out_dir = os.path.join(os.path.dirname(__file__), "..", "sample_documents")
    target = os.path.join(out_dir, "Asha_Reddy_CLM-3021_Complete_Claim_Documents.pdf")
    build_pdf(target)
