"""Render DA-31 by writing into the OCT 2023 fillable PDF's actual form fields.

Uses pdfrw to set field values directly. No coordinates, no image overlay,
no alignment problems — the PDF tells us where each value goes.
"""

from __future__ import annotations

from pathlib import Path

from pdfrw import PdfReader, PdfWriter, PdfDict, PdfName

ROOT = Path(__file__).resolve().parents[2]
TEMPLATE = ROOT / "corpus" / "forms" / "DA31_fillable.pdf"

# Maps our schema's to_form_dict() keys to the actual PDF field names.
# Drawn from running scripts/map_fields.py and reading the labeled PDF.
FIELD_MAP = {
    "control_number":  "Number_1",
    "name":            "Text_1",
    "ssn":             "Text_2",   # DOD ID (treated as identity field)
    "rank":            "Text_3",
    "date":            "Date_1",
    "leave_address":   "Text_4",
    "org_station":     "Text_5",
    "date_from":       "Date_2",
    "days_requested":  "Text_6",
    "date_to":         "Date_3",
    "days_accrued":    "Text_7",
}

# Checkboxes for type of absence.
CHECKBOX_MAP = {
    "type_chargeable": "Checkbox_1",   # always check this for ordinary/emergency
    "type_ordinary":   "Checkbox_4",   # Annual (Ordinary) Leave
    "type_emergency":  "Checkbox_7",   # Emergency Leave
}


def _field_name(annot) -> str | None:
    if annot.T:
        return annot.T.to_unicode() if hasattr(annot.T, "to_unicode") else str(annot.T).strip("()")
    if annot.Parent and annot.Parent.T:
        parent = annot.Parent.T
        return parent.to_unicode() if hasattr(parent, "to_unicode") else str(parent).strip("()")
    return None


def _format_date(value: str) -> str:
    """Convert '03 JUN 26' or '2026-06-03' to YYYYMMDD."""
    if not value:
        return ""
    # Already YYYYMMDD
    if len(value) == 8 and value.isdigit():
        return value
    # ISO date 2026-06-03
    if "-" in value and len(value) == 10:
        return value.replace("-", "")
    # "03 JUN 26" — fallback: just return as-is, PDF will accept text
    return value


def render_fillable(data: dict, output_path: Path) -> Path:
    """Fill the DA-31 fillable PDF with values from the schema dict."""
    pdf = PdfReader(str(TEMPLATE))

    # Tell viewers to regenerate field appearances so values show up
    if pdf.Root.AcroForm:
        pdf.Root.AcroForm.update(PdfDict(NeedAppearances=PdfName("true")))

    # Build reverse lookup: PDF field name → value to write
    text_values: dict[str, str] = {}
    for our_key, pdf_field in FIELD_MAP.items():
        if our_key in data and data[our_key]:
            value = str(data[our_key])
            # Normalize date fields
            if pdf_field.startswith("Date_"):
                value = _format_date(value)
            text_values[pdf_field] = value

    # Determine which checkboxes to tick
    checked: set[str] = set()
    leave_type = data.get("leave_type") or (
        "ORDINARY" if data.get("type_ordinary") == "X"
        else "EMERGENCY" if data.get("type_emergency") == "X"
        else "ORDINARY"
    )
    if leave_type in ("ORDINARY", "EMERGENCY"):
        checked.add(CHECKBOX_MAP["type_chargeable"])
    if leave_type == "ORDINARY":
        checked.add(CHECKBOX_MAP["type_ordinary"])
    elif leave_type == "EMERGENCY":
        checked.add(CHECKBOX_MAP["type_emergency"])

    # Walk the form, write values
    for page in pdf.pages:
        if not page.Annots:
            continue
        for annot in page.Annots:
            if annot.Subtype != "/Widget":
                continue
            name = _field_name(annot)
            if not name:
                continue
            if name in text_values:
                annot.update(PdfDict(V=text_values[name], AP=None))
            elif name in checked:
                annot.update(PdfDict(V=PdfName("Yes"), AS=PdfName("Yes")))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    PdfWriter().write(str(output_path), pdf)
    return output_path