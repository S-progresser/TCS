from __future__ import annotations

import json
from pathlib import Path

import pymupdf


ROOT = Path(__file__).resolve().parents[1]
CLAIMS_FILE = ROOT / "backend" / "data" / "claims.json"
OUTPUT_FILE = ROOT / "sample_documents" / "CLM-3021_mock_mediclaim.pdf"
WATERMARK = "FICTIONAL DEMO DATA — NOT FOR REAL INSURANCE CLAIM SUBMISSION."
PAGE_WIDTH, PAGE_HEIGHT = 595, 842
MARGIN = 48
INK = (0.12, 0.18, 0.25)
MUTED = (0.37, 0.43, 0.5)
TEAL = (0.05, 0.39, 0.4)
PALE = (0.92, 0.96, 0.96)
LINE = (0.83, 0.87, 0.89)


def add_text(page, point, text, *, size=10, color=INK, font="body"):
    page.insert_text(
        point,
        str(text),
        fontname=font,
        fontsize=size,
        color=color,
        overlay=True,
    )


def add_wrapped(page, rect, text, *, size=10, color=INK, font="body", lineheight=1.35):
    page.insert_textbox(
        rect,
        str(text),
        fontname=font,
        fontsize=size,
        color=color,
        lineheight=lineheight,
        overlay=True,
    )


def add_page_frame(page, number, regular_font, bold_font):
    page.insert_font(fontname="body", fontfile=str(regular_font))
    page.insert_font(fontname="bold", fontfile=str(bold_font))
    page.draw_rect(
        pymupdf.Rect(0, 0, PAGE_WIDTH, 56),
        color=None,
        fill=(1.0, 0.96, 0.84),
        overlay=True,
    )
    add_text(page, (MARGIN, 25), WATERMARK, size=10, color=(0.45, 0.2, 0.12), font="bold")
    add_text(page, (MARGIN, 43), "SAMPLE PACKET • FICTIONAL • NOT AN OFFICIAL HOSPITAL OR INSURER DOCUMENT", size=7, color=MUTED)
    page.draw_line((MARGIN, PAGE_HEIGHT - 42), (PAGE_WIDTH - MARGIN, PAGE_HEIGHT - 42), color=LINE, width=0.7)
    add_text(page, (MARGIN, PAGE_HEIGHT - 25), "ClaimSense demo document • No real claim or clinical use", size=8, color=MUTED)
    add_text(page, (PAGE_WIDTH - MARGIN - 46, PAGE_HEIGHT - 25), f"Page {number}", size=8, color=MUTED)

    # A low-opacity diagonal watermark is repeated on each page without obscuring body text.
    page.insert_text(
        (92, 490),
        WATERMARK,
        fontname="bold",
        fontsize=16,
        color=(0.82, 0.84, 0.85),
        rotate=0,
        overlay=True,
    )


def add_section(page, y, title):
    page.draw_rect(pymupdf.Rect(MARGIN, y, PAGE_WIDTH - MARGIN, y + 24), color=None, fill=PALE)
    add_text(page, (MARGIN + 9, y + 16), title, size=11, color=TEAL, font="bold")
    return y + 37


def add_key_values(page, y, pairs, col2=322):
    for label, value in pairs:
        value = str(value)
        line_count = max(1, (len(value) + 53) // 54)
        add_text(page, (MARGIN, y), label, size=9, color=MUTED, font="bold")
        add_wrapped(
            page,
            pymupdf.Rect(col2, y - 10, PAGE_WIDTH - MARGIN, y + line_count * 13),
            value,
            size=9,
        )
        y += max(27, line_count * 15)
    return y


def add_table(page, y, rows):
    x0, x1, x2 = MARGIN, PAGE_WIDTH - MARGIN - 95, PAGE_WIDTH - MARGIN
    add_text(page, (x0, y), "Description", size=9, color=TEAL, font="bold")
    add_text(page, (x1, y), "Estimate (INR)", size=9, color=TEAL, font="bold")
    y += 8
    page.draw_line((x0, y), (x2, y), color=LINE, width=0.8)
    y += 19
    for label, amount in rows:
        add_text(page, (x0, y), label, size=9)
        add_text(page, (x1, y), f"₹ {amount:,.2f}", size=9)
        y += 22
    page.draw_line((x0, y - 8), (x2, y - 8), color=LINE, width=0.8)
    add_text(page, (x0, y + 9), "TOTAL ESTIMATED CHARGES", size=9, color=TEAL, font="bold")
    add_text(page, (x1, y + 9), "₹ 1,85,000.00", size=10, color=TEAL, font="bold")
    return y + 39


def generate():
    claims = json.loads(CLAIMS_FILE.read_text(encoding="utf-8"))
    claim = next(item for item in claims if item["id"] == "CLM-3021")
    amount = int(claim["claim_amount"])
    patient = claim["customer_name"]
    assert amount == 185000

    regular_font = Path(r"C:\Windows\Fonts\arial.ttf")
    bold_font = Path(r"C:\Windows\Fonts\arialbd.ttf")
    if not regular_font.exists() or not bold_font.exists():
        raise FileNotFoundError("Arial fonts are required for readable INR symbols in this Windows PDF.")

    document = pymupdf.open()

    # Page 1: claim cover sheet and fictional claimant/policy information.
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    add_page_frame(page, 1, regular_font, bold_font)
    add_text(page, (MARGIN, 94), "MEDICLAIM DOCUMENT PACKET", size=20, color=INK, font="bold")
    add_text(page, (MARGIN, 116), "Fictional test sample for ClaimSense document review", size=10, color=MUTED)
    add_text(page, (MARGIN, 136), f"Patient: {patient}", size=9, color=TEAL, font="bold")
    y = 158
    y = add_section(page, y, "Claimant and policy details")
    y = add_key_values(page, y, [
        ("Claim ID", claim["id"]),
        ("Patient / claimant", patient),
        ("Product", claim["product"]),
        ("Claim type", claim["claim_type"].replace("-", " ").title()),
        ("Claim status", claim["status"]),
        ("Mock policy reference", f"{claim['policy_number']} (fictional demo value)"),
        ("Demo insurer label", f"{claim['insurer']} (fictional)"),
        ("Claim amount under review", f"₹ {amount:,.2f}"),
        ("Claim record location", claim["branch"]),
    ])
    y += 5
    y = add_section(page, y, "Hospital admission / planned procedure")
    y = add_key_values(page, y, [
        ("Treatment in claim record", "Planned hysterectomy"),
        ("Procedure status", "Planned; no completed admission recorded"),
        ("Hospital / facility", "Not specified in the selected demo claim"),
        ("Admission / treatment dates", "Not provided in the selected demo claim"),
        ("Packet preparation date", "28 October 2026 (demo document date only)"),
    ])
    add_wrapped(
        page,
        pymupdf.Rect(MARGIN, y + 2, PAGE_WIDTH - MARGIN, y + 55),
        "All person, policy, insurer, and claim references in this packet are fictional demo data. "
        "The selected claim record contains no scheduled procedure or treatment date; none is asserted here.",
        size=9,
        color=MUTED,
    )

    # Page 2: estimate (explicitly not a final invoice) and consistent item totals.
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    add_page_frame(page, 2, regular_font, bold_font)
    add_text(page, (MARGIN, 94), "SAMPLE HOSPITAL ESTIMATE", size=20, color=INK, font="bold")
    add_text(page, (MARGIN, 116), "FICTIONAL ESTIMATE • NOT A FINAL INVOICE • NOT PAID", size=10, color=(0.62, 0.22, 0.14), font="bold")
    y = 145
    y = add_section(page, y, "Estimate reference details")
    y = add_key_values(page, y, [
        ("Patient", patient),
        ("Claim ID", claim["id"]),
        ("Provider", "Sample Hospital (fictional placeholder; not a real facility)"),
        ("Proposed care", "Planned hysterectomy; no date specified in claim record"),
        ("Estimate date", "28 October 2026 (sample preparation date)"),
        ("Document status", "Provisional estimate only — no final billed or paid amount"),
        ("Estimated total amount", "Estimated total amount: ₹ 1,85,000.00 (not billed)"),
    ])
    y += 7
    y = add_section(page, y, "Illustrative estimated charges")
    rows = [
        ("Procedure and surgeon fees (estimated)", 78000),
        ("Operating theatre and anaesthesia (estimated)", 35000),
        ("Room and nursing (estimated)", 25000),
        ("Diagnostics and laboratory (estimated)", 12000),
        ("Medicines (estimated)", 18000),
        ("Consumables and supplies (estimated)", 12000),
        ("Pre-operative consultation (estimated)", 5000),
    ]
    assert sum(value for _, value in rows) == amount
    y = add_table(page, y, rows)
    add_wrapped(
        page,
        pymupdf.Rect(MARGIN, y, PAGE_WIDTH - MARGIN, y + 70),
        "The ₹1,85,000 total is an illustrative estimate matching the selected claim amount, not evidence "
        "of an incurred expense. A final itemized hospital invoice and payment proof are intentionally "
        "not included in this sample packet.",
        size=9,
        color=MUTED,
    )

    # Page 3: clearly fictional clinical context and checklist of submitted vs outstanding records.
    page = document.new_page(width=PAGE_WIDTH, height=PAGE_HEIGHT)
    add_page_frame(page, 3, regular_font, bold_font)
    add_text(page, (MARGIN, 94), "CLINICAL SUMMARY & DOCUMENT CHECKLIST", size=17, color=INK, font="bold")
    add_text(page, (MARGIN, 116), "Fictional illustrative text only — not a medical record or diagnosis", size=9, color=MUTED)
    y = 145
    y = add_section(page, y, "Sample clinical summary")
    y = add_key_values(page, y, [
        ("Patient", patient),
        ("Claim reference", claim["id"]),
        ("Planned procedure", "Hysterectomy (as stated in the demo claim summary)"),
        ("Clinical note", "Illustrative pre-operative planning summary; no completed procedure asserted."),
        ("Admission / discharge date", "Not available; treatment remains planned in the demo record."),
        ("Final diagnosis / outcome", "Not provided in the demo claim record."),
    ])
    add_wrapped(
        page,
        pymupdf.Rect(MARGIN, y + 3, PAGE_WIDTH - MARGIN, y + 52),
        "This fictional summary does not establish medical necessity, admission, treatment completion, "
        "or insurer approval. It is not signed and is not a discharge summary.",
        size=9,
        color=MUTED,
    )
    y += 68
    y = add_section(page, y, "Document checklist for this demo claim")
    checklist = [
        ("KYC verification", "Complete in selected demo claim"),
        ("Claim form", "Signed and notarized — complete in selected demo claim"),
        ("Hospital discharge summary", "Outstanding — intentionally not supplied"),
        ("Final hospital invoice", "Outstanding — intentionally not supplied"),
        ("Estimate", "Included on page 2; provisional, not a final invoice"),
        ("Treatment date / claim amount verification", "Outstanding; no treatment date recorded"),
    ]
    for item, status in checklist:
        page.draw_rect(pymupdf.Rect(MARGIN, y - 9, MARGIN + 8, y - 1), color=TEAL, width=0.8)
        add_text(page, (MARGIN + 16, y), item, size=9, font="bold")
        add_wrapped(page, pymupdf.Rect(MARGIN + 255, y - 11, PAGE_WIDTH - MARGIN, y + 17), status, size=8, color=MUTED)
        y += 31
    add_wrapped(
        page,
        pymupdf.Rect(MARGIN, y + 2, PAGE_WIDTH - MARGIN, y + 48),
        "No signature, hospital letterhead, real policy clause, final paid invoice, or signed discharge "
        "summary is represented by this packet. Created solely to test text extraction and missing-document detection.",
        size=8,
        color=(0.62, 0.22, 0.14),
    )

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    document.set_metadata({
        "title": "CLM-3021 Fictional Mediclaim Test Packet",
        "author": "ClaimSense Demo",
        "subject": "Fictional, machine-readable document-analysis test sample",
        "keywords": "fictional demo, test document, not for submission",
    })
    document.save(OUTPUT_FILE, garbage=4, deflate=True)
    document.close()
    print(OUTPUT_FILE)


if __name__ == "__main__":
    generate()
