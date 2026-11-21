import importlib.util
from pathlib import Path
from unittest import mock, skipUnless

from django.test import SimpleTestCase

from apps.cases.pdf_text import Page, read_pdf_pages

CASE_DIR = Path(__file__).resolve().parents[3] / "fixtures" / "cases" / "case_01"
HAS_OCR = importlib.util.find_spec("rapidocr") is not None


class PageQualityTests(SimpleTestCase):
    def test_low_quality_flag(self):
        self.assertTrue(Page(1, "matn " * 10, source="ocr", ocr_confidence=0.6).low_quality)
        self.assertFalse(Page(1, "matn " * 10, source="ocr", ocr_confidence=0.97).low_quality)
        self.assertFalse(Page(1, "matn " * 10).low_quality)

    def test_text_pdf_does_not_run_ocr(self):
        with mock.patch("apps.cases.ocr.ocr_image_smart") as ocr_smart, mock.patch("apps.cases.ocr.ocr_image") as ocr_image:
            pages = read_pdf_pages(CASE_DIR / "case_01.pdf")
        ocr_smart.assert_not_called()
        ocr_image.assert_not_called()
        self.assertEqual({p.source for p in pages}, {"text"})


class VisionOcrTests(SimpleTestCase):
    def test_vision_ocr_extracts_handwriting_and_stamps(self):
        import numpy as np
        from apps.cases.ocr import ocr_image_vision

        sample_img = np.full((100, 100, 3), 255, dtype=np.uint8)
        mock_text = (
            "BAYONNOMA\n"
            "[QOʻLYOZMA: Men oʻz aybimga iqror emasman va koʻrsatuv berishdan bosh tortaman.]\n"
            "[MUHR: Toshkent shahar Chilonzor tumani IIO FMB]"
        )

        with mock.patch("apps.cases.ocr.get_llm") as mock_get_llm:
            mock_llm = mock.MagicMock()
            mock_llm.transcribe_image.return_value = (mock_text, 0.00025)
            mock_get_llm.return_value = mock_llm

            result = ocr_image_vision(sample_img)

        self.assertEqual(result.engine, "gemini_vision")
        self.assertTrue(result.has_handwriting)
        self.assertEqual(result.stamps, ["Toshkent shahar Chilonzor tumani IIO FMB"])
        self.assertEqual(result.cost_usd, 0.00025)
        self.assertIn("koʻrsatuv", result.text)

    def test_smart_ocr_fallback_on_vision_error(self):
        import numpy as np
        from apps.cases.ocr import ocr_image_smart, OcrResult

        sample_img = np.full((50, 50, 3), 255, dtype=np.uint8)

        with mock.patch("apps.cases.ocr.get_llm") as mock_get_llm, \
             mock.patch("apps.cases.ocr.ocr_image") as mock_rapid:
            mock_llm = mock.MagicMock()
            mock_llm.transcribe_image.side_effect = RuntimeError("API unavailable")
            mock_get_llm.return_value = mock_llm

            mock_rapid.return_value = OcrResult(text="Lokal matn", confidence=0.96, script="latin")

            res = ocr_image_smart(sample_img, force_vision=True)

        self.assertEqual(res.text, "Lokal matn")
        mock_rapid.assert_called_once()


@skipUnless(HAS_OCR, "rapidocr o'rnatilmagan")
class ScannedPageOcrTests(SimpleTestCase):
    """Haqiqiy OCR (CPU, ~2-8 s): case_01_scan.pdf — tools/make_scanned_copy.py bilan yasalgan skaner nusxa."""

    def test_full_width_lines_are_not_lost(self):
        from apps.cases.ocr import ocr_image, render_page

        result = ocr_image(render_page(str(CASE_DIR / "case_01_scan.pdf"), 3))  # 4-varaq
        self.assertEqual(result.script, "latin")
        self.assertGreater(result.confidence, 0.95)
        # cls modeli yoqilganda yo'qolgan to'liq kenglikdagi qatorlar
        self.assertIn("Toshkent shahar Sergeli", result.text)
        self.assertIn("miqdorida mulkiy", result.text)
        self.assertIn("Qodirova Malika Anvarovna", result.text)  # oʻ/ʼ normallashtirilgan

    def test_uzbek_cyrillic_page_is_flagged(self):
        from apps.cases.ocr import ocr_image, render_page

        result = ocr_image(render_page(str(CASE_DIR / "case_01_scan.pdf"), 11))  # 12-varaq, o'zbek kirill
        self.assertEqual(result.script, "cyrillic")
        self.assertIn("ГУВО", result.text)
        self.assertIn("ў қ ғ ҳ", result.warning)
