"""Convert the flat DA-31 PDF into PNG backgrounds using pypdfium2.

No system dependencies — works without poppler.
"""

from pathlib import Path
import pypdfium2 as pdfium

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "corpus" / "forms" / "DA-31.pdf"
OUT_DIR = ROOT / "corpus" / "forms"


def main():
    if not SRC.exists():
        print(f"❌ Source PDF not found at {SRC}")
        return

    pdf = pdfium.PdfDocument(str(SRC))
    for i, page in enumerate(pdf, start=1):
        # scale=2.78 ≈ 200 DPI for letter-sized pages
        bitmap = page.render(scale=2.78)
        image = bitmap.to_pil()
        out = OUT_DIR / f"da31_page{i}.png"
        image.save(out, "PNG")
        print(f"✓ Saved {out.name} ({image.width}x{image.height})")


if __name__ == "__main__":
    main()