"""Ko'p formatli yuklash (PDF, DOCX, JPG/PNG), qiyshiq skanerni to'g'rilash va o'zbek kirill tuzatishi (9-bosqich)."""
import importlib.util
import io
from pathlib import Path
from unittest import skipUnless

import numpy as np
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings
from pypdf import PdfReader

from apps.cases import cyr_fix, intake
from apps.cases.intake import IntakeError, build_case_pdf
from apps.cases.models import CaseRun
from apps.cases.tests.test_views import CASE_PDF, CaseTestBase

CASE_DIR = CASE_PDF.parent
HAS_OCR = importlib.util.find_spec("rapidocr") is not None
HAS_TNR = (Path(settings.EXPORT_FONT_DIR) / "times.ttf").exists()


def png(width=300, height=200, fmt="PNG", exif_orientation=None) -> bytes:
    from PIL import Image

    img = Image.new("RGB", (width, height), (255, 255, 255))
    out = io.BytesIO()
    if exif_orientation:
        exif = Image.Exif()
        exif[0x0112] = exif_orientation
        img.save(out, fmt, exif=exif)
    else:
        img.save(out, fmt)
    return out.getvalue()


def docx(paragraphs=("Birinchi abzats.", "Ikkinchi abzats."), table=(("Ism", "Summa"), ("Karimov", "1 500 000"))) -> bytes:
    from docx import Document

    doc = Document()
    for text in paragraphs:
        doc.add_paragraph(text)
    if table:
        t = doc.add_table(rows=len(table), cols=len(table[0]))
        for r, row in enumerate(table):
            for c, text in enumerate(row):
                t.cell(r, c).text = text
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


@skipUnless(HAS_TNR, "Times New Roman shrifti yo'q")
class IntakeTests(SimpleTestCase):
    def test_merges_pdf_image_docx_with_continuous_pages(self):
        pdf = CASE_PDF.read_bytes()
        n = len(PdfReader(io.BytesIO(pdf)).pages)
        result = build_case_pdf([("ish.pdf", pdf), ("foto.JPG", png(fmt="JPEG")), ("izoh.docx", docx())])
        self.assertEqual(result.pages, n + 2)
        self.assertEqual([(s.name, s.kind, s.first_page, s.last_page) for s in result.sources],
                         [("ish.pdf", "pdf", 1, n), ("foto.JPG", "image", n + 1, n + 1),
                          ("izoh.docx", "docx", n + 2, n + 2)])
        pages = PdfReader(io.BytesIO(result.pdf)).pages
        self.assertEqual(len(pages), result.pages)
        self.assertEqual((pages[n].extract_text() or "").strip(), "")  # rasm: matn qatlami yo'q — OCR qiladi
        text = pages[n + 1].extract_text()
        self.assertIn("Birinchi abzats.", text)
        self.assertIn("Karimov", text)  # jadval ham o'qiladi
        self.assertIn("1 500 000", text)

    def test_image_exif_orientation_applied(self):
        # 300x200 rasm, EXIF "90° aylantirilgan" -> sahifa 200x300 (portret)
        result = build_case_pdf([("telefon.jpg", png(fmt="JPEG", exif_orientation=6))])
        box = PdfReader(io.BytesIO(result.pdf)).pages[0].mediabox
        self.assertLess(float(box.width), float(box.height))

    def test_rejects_bad_input(self):
        for name, data, text in [
            ("a.txt", b"x", "faqat PDF"), ("a.pdf", b"bu pdf emas", "PDF faylni"), ("a.jpg", b"bu rasm emas", "rasmni"),
            ("a.docx", b"bu docx emas", "DOCX faylni"), ("bosh.docx", docx(paragraphs=(), table=()), "matn topilmadi"),
        ]:
            with self.assertRaisesRegex(IntakeError, text):
                build_case_pdf([(name, data)])
        with self.assertRaises(IntakeError):
            build_case_pdf([])

    def test_docx_images_warning(self):
        from docx import Document
        from docx.shared import Cm

        doc = Document()
        doc.add_paragraph("Matn bor.")
        doc.add_picture(io.BytesIO(png()), width=Cm(3))
        out = io.BytesIO()
        doc.save(out)
        result = build_case_pdf([("rasmli.docx", out.getvalue())])
        self.assertEqual(len(result.warnings), 1)
        self.assertIn("rasm", result.warnings[0])
        # Ichki rasm alohida varaq sifatida qo'shildi
        self.assertEqual(result.pages, 2)
        self.assertEqual(len(result.sources), 2)
        self.assertEqual(result.sources[0].kind, "docx")
        self.assertEqual(result.sources[1].kind, "image")

    def test_oversized_image_rejected(self):
        old, intake.MAX_IMAGE_PIXELS = intake.MAX_IMAGE_PIXELS, 1000
        try:
            with self.assertRaisesRegex(IntakeError, "juda katta"):
                build_case_pdf([("katta.png", png(100, 100))])
        finally:
            intake.MAX_IMAGE_PIXELS = old


@skipUnless(HAS_TNR, "Times New Roman shrifti yo'q")
class UploadViewTests(CaseTestBase):
    def post(self, files, **extra):
        return self.client.post("/cases/upload", {"files": [SimpleUploadedFile(n, c) for n, c in files], **extra})

    def test_multi_file_upload_creates_one_run(self):
        resp = self.post([("ish.pdf", CASE_PDF.read_bytes()), ("foto.png", png()), ("izoh.docx", docx())],
                         title="Aralash ish")
        self.assertEqual(resp.status_code, 302)
        run = CaseRun.objects.get()
        self.assertEqual((run.title, run.pages), ("Aralash ish", 32))
        self.assertEqual([s["name"] for s in run.sources], ["ish.pdf", "foto.png", "izoh.docx"])
        self.assertEqual(run.sources[1]["first_page"], 31)
        self.enqueue.assert_called_once_with(run.id)
        self.assertIn("ish.pdf", self.client.get(f"/cases/{run.id}/").content.decode())  # fayllar ro'yxati

    def test_single_pdf_is_stored_unchanged(self):
        data = CASE_PDF.read_bytes()
        result = build_case_pdf([("ish.pdf", data)])
        self.assertEqual((result.pdf, result.pages, result.sources[0].last_page), (data, 30, 30))

    def test_default_title_names_files(self):
        self.post([("a.png", png()), ("b.png", png())])
        self.assertEqual(CaseRun.objects.get().title, "a.png + 1 fayl")

    def test_limits(self):
        with override_settings(CASE_MAX_FILES=1):
            self.assertIn("error=", self.post([("a.png", png()), ("b.png", png())])["Location"])
        with override_settings(CASE_MAX_PAGES=1):
            self.assertIn("error=", self.post([("a.png", png()), ("b.png", png())])["Location"])
        self.assertIn("error=", self.post([("a.png", b"rasm emas")])["Location"])
        self.assertEqual(CaseRun.objects.count(), 0)

    def test_upload_page_offers_all_formats(self):
        html = self.client.get("/cases/").content.decode()
        self.assertIn('name="files"', html)
        self.assertIn(".docx", html)


VOCAB = {"гувоҳ": 40, "сўроқ": 80, "қилиш": 100, "тариқасида": 12, "ўқув": 9, "ўқ": 30, "ука": 25, "ва": 500,
         "учун": 300, "билан": 400, "шаҳар": 60, "бўлими": 30, "туғилган": 20, "жойи": 40, "ҳолат": 50}


class CyrFixTests(SimpleTestCase):
    def test_restores_uzbek_letters(self):
        text = "Гувох сурок килиш тарикасида. Тугилган жойи"
        fixed, n = cyr_fix.fix_uzbek_cyrillic(text, VOCAB)
        self.assertEqual(fixed, "Гувоҳ сўроқ қилиш тариқасида. Туғилган жойи")
        self.assertEqual(n, 5)

    def test_preserves_case(self):
        fixed, _ = cyr_fix.fix_uzbek_cyrillic("ГУВОХ СУРОК учун билан ва Шахар", VOCAB)
        self.assertEqual(fixed, "ГУВОҲ СЎРОҚ учун билан ва Шаҳар")

    def test_known_word_is_not_changed_unless_variant_dominates(self):
        self.assertEqual(cyr_fix.fix_word("ука", VOCAB), "ука")   # lug'atda bor (25); "ўқа" yo'q
        self.assertEqual(cyr_fix.fix_uzbek_cyrillic("ук", VOCAB)[0], "ук")  # 3 harfdan qisqa so'z tegilmaydi
        self.assertEqual(cyr_fix.fix_word("ухо", {"ухо": 50, "ўҳо": 60}), "ухо")  # variant yetarli ustun emas
        self.assertEqual(cyr_fix.fix_word("ухо", {"ухо": 2, "ўҳо": 60}), "ўҳо")

    def test_russian_text_is_untouched(self):
        text = "Гражданин Иванов хотел купить хороший курс и кто-то уходил из города"
        self.assertEqual(cyr_fix.fix_uzbek_cyrillic(text, VOCAB), (text, 0))

    def test_empty_vocab_does_nothing(self):
        self.assertEqual(cyr_fix.fix_uzbek_cyrillic("Гувох", {}), ("Гувох", 0))


def synthetic_page(angle: float = 0.0) -> np.ndarray:
    """Matn qatorlari bor oq sahifa (TNR), ixtiyoriy burchakka aylantirilgan."""
    import cv2
    from PIL import Image, ImageDraw, ImageFont

    img = Image.new("RGB", (1240, 1754), "white")
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(str(Path(settings.EXPORT_FONT_DIR) / "times.ttf"), 30)
    for i in range(30):
        draw.text((120, 150 + i * 48), "Tergov bolimi katta terghovchisi guvohni soroq qildi " * 2, fill="black",
                  font=font)
    arr = np.asarray(img)
    if not angle:
        return arr
    h, w = arr.shape[:2]
    return cv2.warpAffine(arr, cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0), (w, h),
                          borderValue=(255, 255, 255))


@skipUnless(HAS_TNR, "Times New Roman shrifti yo'q")
class DeskewTests(SimpleTestCase):
    def test_estimates_and_removes_skew(self):
        from apps.cases.ocr import deskew, estimate_skew

        self.assertAlmostEqual(estimate_skew(synthetic_page()), 0.0, delta=0.05)
        for angle in (-7.0, 2.5, 8.0):
            skewed = synthetic_page(angle)
            self.assertAlmostEqual(abs(estimate_skew(skewed)), abs(angle), delta=0.3)
            self.assertLess(abs(estimate_skew(deskew(skewed))), 0.3)

    def test_straight_page_is_returned_as_is(self):
        from apps.cases.ocr import deskew

        page = synthetic_page()
        self.assertIs(deskew(page), page)

    def test_blank_page(self):
        from apps.cases.ocr import estimate_skew

        self.assertEqual(estimate_skew(np.full((500, 400, 3), 255, dtype=np.uint8)), 0.0)


@skipUnless(HAS_OCR, "rapidocr o'rnatilmagan")
class UzbekCyrillicOcrTests(SimpleTestCase):
    """Haqiqiy OCR (CPU): case_01_scan.pdf 12-varaq — o'zbek kirill. Lug'at korpusdan olinadi (dev bazasi)."""

    def test_uzbek_letters_restored(self):
        from apps.cases.ocr import ocr_image, render_page

        if not cyr_fix.vocab_path().exists():
            self.skipTest("Lugʻat yoʻq: manage.py build_cyr_vocab")
        result = ocr_image(render_page(str(CASE_DIR / "case_01_scan.pdf"), 11))
        self.assertIn("ГУВОҲНИ СЎРОҚ ҚИЛИШ", result.text)
        self.assertIn("ў қ ғ ҳ", result.warning)

    def test_rotated_scan_reads_the_same(self):
        import cv2

        from apps.cases.ocr import ocr_image, render_page

        page = render_page(str(CASE_DIR / "case_01_scan.pdf"), 3)
        h, w = page.shape[:2]
        tilted = cv2.warpAffine(page, cv2.getRotationMatrix2D((w / 2, h / 2), 7.0, 1.0), (w, h),
                                borderValue=(255, 255, 255))
        result = ocr_image(tilted)
        self.assertGreater(result.confidence, 0.93)
        self.assertIn("Toshkent shahar Sergeli", result.text)

