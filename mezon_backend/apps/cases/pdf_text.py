"""PDF dan sahifa matnlarini olish: matn qatlami bo'lsa — undan, bo'lmasa (skaner) — OCR (apps/cases/ocr.py).

Sahifa raqami = PDF dagi tartib raqami (1 dan). Ish hujjatlarida bu "varaq" raqamiga mos keladi.
"""
import re
from dataclasses import dataclass, field
from pathlib import Path

from pypdf import PdfReader

LOW_OCR_CONFIDENCE = 0.85  # bundan past — advokatga "yomon o'qilgan sahifa" deb ko'rsatiladi


@dataclass
class Page:
    number: int
    text: str
    source: str = "text"                  # "text" (PDF matn qatlami) | "rapidocr" | "gemini_vision"
    ocr_confidence: float | None = None
    ocr_warning: str = ""
    has_handwriting: bool = False
    stamps: list[str] = field(default_factory=list)
    ocr_cost_usd: float = 0.0

    @property
    def is_empty(self) -> bool:
        return len(self.text.strip()) < 20  # matn yo'q (OCR ham o'qiy olmagan bo'lsa ham)

    @property
    def low_quality(self) -> bool:
        return self.source in ("ocr", "rapidocr") and (self.ocr_confidence or 0) < LOW_OCR_CONFIDENCE


def clean_page_text(text: str) -> str:
    text = text.replace("\xa0", " ").replace("\u200e", "")
    text = re.sub(r"[ \t]+", " ", text)            # PDF kengaytirilgan bo'shliqlari ("Toshkent  shahar")
    text = re.sub(r" *\n *", "\n", text)
    return text.strip()


def read_pdf_pages(path: str | Path, ocr: bool = True, on_progress=None) -> list[Page]:
    """ocr=True: matn qatlami yo'q sahifalar OCR qilinadi. on_progress(tayyor, jami) — OCR sahifalari bo'yicha."""
    reader = PdfReader(str(path))
    pages = [Page(number=i, text=clean_page_text(p.extract_text() or "")) for i, p in enumerate(reader.pages, 1)]
    scanned = [p for p in pages if p.is_empty]
    if ocr and scanned:
        from .ocr import ocr_image_smart, render_page  # og'ir importlar — faqat skaner bo'lsa

        for k, page in enumerate(scanned, 1):
            result = ocr_image_smart(render_page(str(path), page.number - 1))
            page.text = clean_page_text(result.text)
            page.source = getattr(result, "engine", "ocr") or "ocr"
            page.ocr_confidence = round(result.confidence, 3)
            page.ocr_warning = result.warning
            page.has_handwriting = getattr(result, "has_handwriting", False)
            page.stamps = getattr(result, "stamps", [])
            page.ocr_cost_usd = getattr(result, "cost_usd", 0.0)
            if on_progress:
                on_progress(k, len(scanned))
    return pages
