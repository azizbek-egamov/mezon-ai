from django.test import SimpleTestCase

from apps.cases.extract import Fact, verify_quote
from apps.cases.pdf_text import clean_page_text
from apps.cases.pii import PiiVault


class PiiTests(SimpleTestCase):
    def test_mask_and_unmask_consistently(self):
        v = PiiVault()
        text = ("JSHSHIR 41503881230051, tel. +998 90 123-45-67, pasport AD 2231475, karta 9860 **** **** 4417. "
                "Yana: 41503881230051")
        masked = v.mask(text)
        self.assertEqual(masked, "JSHSHIR <JSHSHIR_1>, tel. <TEL_1>, pasport <PASPORT_1>, karta <KARTA_1>. "
                                 "Yana: <JSHSHIR_1>")
        self.assertEqual(v.unmask(masked), "JSHSHIR 41503881230051, tel. +998901234567, pasport AD2231475, "
                                           "karta 9860********4417. Yana: 41503881230051")
        # model tokenni burchak qavssiz yozsa ham; noma'lum token o'zgarmaydi
        self.assertEqual(v.unmask("JSHSHIR_1 va TEL_1, lekin SHAXS_9"), "41503881230051 va +998901234567, lekin SHAXS_9")

    def test_amounts_and_dates_untouched(self):
        v = PiiVault()
        text = "85 000 000 soʻm, 2026-yil 3-mart, soat 14:00, № 2026/0457"
        self.assertEqual(v.mask(text), text)


class NameMaskingTests(SimpleTestCase):
    TEXTS = [
        "Fuqaro Qodirova Malika Anvarovna ariza berdi. Tergovchi N.Sh. Yusupov Sergeli tumani IIB da qabul qildi.",
        "Guvoh Hasanova Dilnoza Botirovnani soʻroq qildi. Dugonam Hasanova Dilnoza bilan bordim.",
        "Jasur ismli shaxs. Gumon qilinuvchi Rustamov Jasur Baxtiyorovich ushlab turildi.",
        "Выполнены ли текст и подпись Кодировой Маликой Анваровной? Подпись М.А. Кодировой.",
        "Тергов бўлими терговчиси Н.Ш. Юсупов гувоҳ Эргашев Шуҳрат Комиловични сўроқ қилди.",
    ]

    def setUp(self):
        self.v = PiiVault()
        self.v.learn_names(self.TEXTS)
        self.masked = [self.v.mask(t) for t in self.TEXTS]

    def test_names_masked_across_scripts_and_forms(self):
        joined = " ".join(self.masked)
        for name in ["Qodirova", "Malika", "Yusupov", "Hasanova", "Dilnoza", "Jasur", "Rustamov", "Кодировой",
                     "Маликой", "Юсупов", "Эргашев", "Шуҳрат"]:
            self.assertNotIn(name, joined, name)
        # lotin "Qodirova" va ruscha "Кодировой", "Yusupov" va "Юсупов" — bitta shaxs tokeni
        qodirova = self.masked[0].split()[1]
        self.assertTrue(qodirova.startswith("<SHAXS_"))
        self.assertIn(qodirova, self.masked[3])
        yusupov_token = self.masked[0].split("Tergovchi ")[1].split()[0]
        self.assertIn(yusupov_token, self.masked[4])

    def test_place_names_are_not_masked(self):
        self.assertIn("Sergeli tumani", self.masked[0])           # initsialdan keyingi so'z ism emas
        self.assertIn("<SHAXS_", self.masked[2].split("ismli")[0])  # "Jasur ismli" — Rustamov tokeni
        self.assertNotIn("<SHAXS_1> <SHAXS_1>", " ".join(self.masked))  # takrorlar qisqartirilgan


class SameSurnameTests(SimpleTestCase):
    """Bir familiyali turli shaxslar (er-xotin, ota-qiz) bitta tokenga qo'shilmasligi kerak."""
    TEXTS = [
        "Gumon qilinuvchi Karimov Jasur Anvarovich ushlandi. Guvoh Karimova Malika Anvarovna soʻroq qilindi.",
        "Jasur ayblanuvchi. Malika guvoh. Karimov Jasur bilan Karimova Malika qoʻshni.",
    ]

    def setUp(self):
        self.v = PiiVault()
        self.v.learn_names(self.TEXTS)
        self.masked = [self.v.mask(t) for t in self.TEXTS]

    def test_two_persons_get_two_tokens(self):
        self.assertEqual(len(self.v.persons), 2)
        t1, t2 = (p.token for p in self.v.persons)
        self.assertNotEqual(t1, t2)
        self.assertIn(f"Gumon qilinuvchi {t1} ushlandi. Guvoh {t2} soʻroq", self.masked[0])
        self.assertNotIn("Karimov", " ".join(self.masked))

    def test_unmask_restores_each_person_separately(self):
        restored = self.v.unmask(self.masked[0])
        self.assertIn("Gumon qilinuvchi Karimov Jasur Anvarovich ushlandi", restored)
        self.assertIn("Guvoh Karimova Malika Anvarovna", restored)

    def test_bare_surname_is_not_pinned_to_one_person(self):
        masked = self.v.mask("Karimov kelmadi.")
        t1, t2 = (p.token for p in self.v.persons)
        self.assertEqual(masked, f"{t1}/{t2} kelmadi.")


class QuoteTests(SimpleTestCase):
    def setUp(self):
        self.pages = {5: clean_page_text("Narx 85 000 000 soʻm deb kelishdik.  Jasur pulni naqd emas,\nkartaga "
                                         "oʻtkazishni soʻradi."),
                      6: "Bayonnoma oʻqib chiqildi."}

    def fact(self, quote, page=5):
        return Fact(id="F1", type="statement", page=page, date="", time="", source="", summary="", quote=quote)

    def test_exact_quote_across_line_break_and_apostrophes(self):
        f = self.fact("Jasur pulni naqd emas, kartaga o'tkazishni so'radi")
        verify_quote(f, self.pages)
        self.assertTrue(f.verified)
        self.assertEqual(f.verified_page, 5)

    def test_neighbour_page_and_altered_quote(self):
        f = self.fact("Bayonnoma oʻqib chiqildi", page=5)
        verify_quote(f, self.pages)
        self.assertEqual((f.verified, f.verified_page), (True, 6))
        g = self.fact("Narx 58 000 000 soʻm deb kelishdik")
        verify_quote(g, self.pages)
        self.assertFalse(g.verified)
