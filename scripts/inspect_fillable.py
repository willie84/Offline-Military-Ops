"""Dump every fillable field name in the DA-31 fillable PDF.

Run once. Output goes to stdout — paste into the chat.
"""

from pathlib import Path
from pdfrw import PdfReader

FORM_PATH = Path(__file__).resolve().parent.parent / "corpus" / "forms" / "DA31_fillable.pdf"


def field_name(annot):
    if annot.T:
        return annot.T.to_unicode() if hasattr(annot.T, "to_unicode") else str(annot.T).strip("()")
    if annot.Parent and annot.Parent.T:
        parent = annot.Parent.T
        return parent.to_unicode() if hasattr(parent, "to_unicode") else str(parent).strip("()")
    return None


def main():
    if not FORM_PATH.exists():
        print(f"❌ Form not found at {FORM_PATH}")
        return

    pdf = PdfReader(str(FORM_PATH))
    seen = set()
    print(f"Inspecting {FORM_PATH.name}\n" + "=" * 70)

    for page_num, page in enumerate(pdf.pages, 1):
        if not page.Annots:
            continue
        for annot in page.Annots:
            if annot.Subtype == "/Widget":
                name = field_name(annot)
                if name and name not in seen:
                    seen.add(name)
                    field_type = str(annot.FT) if annot.FT else "?"
                    print(f"Page {page_num} | {field_type:6} | {name}")

    print("=" * 70)
    print(f"Total unique fields: {len(seen)}")


if __name__ == "__main__":
    main()