"""Fill every field with its own name as a marker.

After running, open the output PDF — each field will contain its own
name (e.g., the field "Text_1" will literally show 'Text_1' in the form).
That tells us which generic name corresponds to which form block.
"""

from pathlib import Path
from pdfrw import PdfReader, PdfWriter, PdfDict, PdfName

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "corpus" / "forms" / "DA31_fillable.pdf"
OUT = ROOT / "output" / "DA31_field_map.pdf"


def field_name(annot):
    if annot.T:
        return annot.T.to_unicode() if hasattr(annot.T, "to_unicode") else str(annot.T).strip("()")
    if annot.Parent and annot.Parent.T:
        parent = annot.Parent.T
        return parent.to_unicode() if hasattr(parent, "to_unicode") else str(parent).strip("()")
    return None


def main():
    pdf = PdfReader(str(SRC))
    pdf.Root.AcroForm.update(PdfDict(NeedAppearances=PdfName("true")))

    for page in pdf.pages:
        if not page.Annots:
            continue
        for annot in page.Annots:
            if annot.Subtype != "/Widget":
                continue
            name = field_name(annot)
            if not name:
                continue
            ftype = str(annot.FT) if annot.FT else ""
            if ftype == "/Tx":
                # Text field — write the name as the value
                annot.update(PdfDict(V=name, AP=None))
            elif ftype == "/Btn":
                # Checkbox — toggle on so we can see which is which
                annot.update(PdfDict(V=PdfName("Yes"), AS=PdfName("Yes")))

    OUT.parent.mkdir(parents=True, exist_ok=True)
    PdfWriter().write(str(OUT), pdf)
    print(f"✓ Wrote {OUT}")
    print("Open it and note which block label corresponds to which Text_N / Date_N / Checkbox_N")


if __name__ == "__main__":
    main()