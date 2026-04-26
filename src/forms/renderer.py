"""Render DA-31 PDF by overlaying field data on the form image."""

from __future__ import annotations

from pathlib import Path

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter

ROOT = Path(__file__).resolve().parents[2]
BG_PAGE1 = ROOT / "corpus" / "forms" / "da31_page1.png"

FIELD_POSITIONS = {
    "control_number": (495, 712),
    "name":           (95,  672),
    "ssn":            (305, 672),
    "rank":           (430, 672),
    "date":           (525, 672),
    "leave_address":  (95,  632),
    "type_ordinary":  (290, 632),
    "type_emergency": (350, 632),
    "type_permissive":(290, 615),
    "type_other":     (350, 615),
    "org_station":    (490, 632),
    "days_accrued":   (95,  582),
    "days_requested": (170, 582),
    "date_from":      (435, 582),
    "date_to":        (530, 582),
    "signature_req":  (95,  542),
}


def render(data: dict, output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    c = canvas.Canvas(str(output_path), pagesize=letter)
    c.drawImage(str(BG_PAGE1), 0, 0, width=612, height=792)
    c.setFont("Helvetica", 9)
    for field, value in data.items():
        if field in FIELD_POSITIONS and value:
            x, y = FIELD_POSITIONS[field]
            c.drawString(x, y, str(value))
    c.save()
    return output_path