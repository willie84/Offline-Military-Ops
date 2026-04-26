"""Smoke test: render a DA-31 with hardcoded data, no LLM yet.

Once this looks right, we replace the hardcoded dict with structured
output from the LLM in the form-fill pipeline.
"""

from pathlib import Path
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

ROOT = Path(__file__).resolve().parent.parent
BG_PAGE1 = ROOT / "corpus" / "forms" / "da31_page1.png"
OUT = ROOT / "output" / "test_da31.pdf"

# Coordinates are (x, y) from BOTTOM-LEFT in points (1 inch = 72 points).
# Letter page is 612 wide x 792 tall.
# Tuned for the SEP 93 DA-31 PNG at 200 DPI.
FIELD_POSITIONS = {
    "control_number": (495, 712),   # Block 1 (top right)
    "name":           (95,  672),   # Block 2
    "ssn":            (305, 672),   # Block 3
    "rank":           (430, 672),   # Block 4
    "date":           (525, 672),   # Block 5
    "leave_address":  (95,  632),   # Block 6
    "type_ordinary":  (290, 632),   # Block 7 - "X" mark
    "org_station":    (490, 632),   # Block 8
    "days_accrued":   (95,  582),   # Block 9a
    "days_requested": (170, 582),   # Block 9b
    "date_from":      (435, 582),   # Block 10a
    "date_to":        (530, 582),   # Block 10b
    "signature_req":  (95,  542),   # Block 11
}


def render(data: dict, output_path: Path):
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=letter)

    # Draw form image as full-page background
    c.drawImage(str(BG_PAGE1), 0, 0, width=612, height=792)

    # Overlay data
    c.setFont("Helvetica", 9)
    for field, value in data.items():
        if field in FIELD_POSITIONS and value:
            x, y = FIELD_POSITIONS[field]
            c.drawString(x, y, str(value))

    c.save()
    print(f"✓ Wrote {output_path}")


if __name__ == "__main__":
    test_data = {
        "control_number": "2026-0042",
        "name": "MACHARIA, WILLIE A.",
        "ssn": "XXX-XX-1234",
        "rank": "SPC",
        "date": "25 APR 26",
        "leave_address": "1234 University Ave, Berkeley CA 94704",
        "type_ordinary": "X",
        "org_station": "B Co, 1-1 IN, Fort Liberty",
        "days_accrued": "15.0",
        "days_requested": "10",
        "date_from": "03 JUN 26",
        "date_to": "12 JUN 26",
        "signature_req": "/s/ W. MACHARIA",
    }
    render(test_data, OUT)