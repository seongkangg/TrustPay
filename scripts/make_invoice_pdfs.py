"""Render the demo fixtures in data/invoices/*.json as labelled one-page PDFs.

    python scripts/make_invoice_pdfs.py          # writes data/invoices/pdf/<scenario>.pdf

Email one of them to the watched Gmail account as `invoice.pdf` and the inbox poller picks it
up. The labels match backend/inbox/pdf_parser.py exactly, so parse(render(fixture)) == fixture.
"""

import json
import sys
from pathlib import Path

from fpdf import FPDF

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from backend.inbox.pdf_parser import LABELS  # noqa: E402

FIXTURES = {
    "low_risk": "low_risk_invoice.json",
    "policy_violation": "policy_violation_invoice.json",
    "suspicious": "suspicious_invoice.json",
    "duplicate": "duplicate_invoice.json",
}


def render_invoice_pdf(upload: dict, title: str = "INVOICE") -> bytes:
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 18)
    pdf.cell(0, 12, title, new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", size=12)
    pdf.ln(4)
    for field, labels in LABELS:
        value = upload.get(field)
        if value in (None, ""):
            continue
        if field == "amount":
            value = f"{float(value):.2f}"
        pdf.cell(0, 8, f"{labels[0]}: {value}", new_x="LMARGIN", new_y="NEXT")
    if upload.get("raw_text"):
        pdf.ln(6)
        pdf.set_font("Helvetica", "I", 11)
        pdf.multi_cell(0, 7, upload["raw_text"])
    return bytes(pdf.output())


def main() -> None:
    out_dir = ROOT / "data" / "invoices" / "pdf"
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, fixture in FIXTURES.items():
        upload = json.loads((ROOT / "data" / "invoices" / fixture).read_text(encoding="utf-8"))[
            "upload"
        ]
        path = out_dir / f"{name}.pdf"
        path.write_bytes(render_invoice_pdf(upload))
        print(f"wrote {path.relative_to(ROOT)} ({path.stat().st_size} bytes)")


if __name__ == "__main__":
    main()
