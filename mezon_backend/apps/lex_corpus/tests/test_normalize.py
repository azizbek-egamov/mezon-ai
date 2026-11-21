from django.test import SimpleTestCase

from apps.lex_corpus import normalize as N
from apps.lex_corpus.models import CorpusTier, DocType, Status


class NormalizeTests(SimpleTestCase):
    def test_detect_script(self):
        self.assertEqual(N.detect_script("Oʻzbekiston Respublikasining Qonuni"), "lat")
        self.assertEqual(N.detect_script("Ўзбекистон Республикасининг Қонуни"), "cyr")

    def test_is_russian(self):
        self.assertTrue(N.is_russian("О внесении изменений в Налоговый кодекс"))
        self.assertFalse(N.is_russian("Ўзбекистон Республикасининг Қонуни"))

    def test_apostrophes(self):
        self.assertEqual(N.normalize_apostrophes("o'zgartirish ma'lumot g`oya"), "oʻzgartirish maʼlumot gʻoya")

    def test_homoglyphs(self):
        # "pаrlаmеnt" ichida kirill а, е
        self.assertEqual(N.fix_homoglyphs("pаrlаmеnt nazorati"), "parlament nazorati")
        self.assertEqual(N.fix_homoglyphs("Ўзбекистон"), "Ўзбекистон")

    def test_clean_text(self):
        self.assertEqual(N.clean_text("a‎ —‎  b\xa0cd"), "a — b c d")

    def test_classify(self):
        c = N.classify_doc_type
        self.assertEqual(c(6445145, "", "Oʻzbekiston Respublikasi Konstitutsiyasi", ""), DocType.CONSTITUTION)
        self.assertEqual(c(111453, "Oʻzbekiston Respublikasining Jinoyat kodeksi", "", ""), DocType.CODE)
        self.assertEqual(c(1, "Oʻzbekiston Respublikasining Qonuni", "", "OʻRQ-547-son"), DocType.LAW)
        self.assertEqual(c(1, "Oʻzbekiston Respublikasi Prezidentining Farmoni", "", "PF-1-son"), DocType.PRES_DECREE)
        self.assertEqual(c(1, "Oʻzbekiston Respublikasi Prezidentining qarori", "", "PQ-1-son"), DocType.PRES_RESOLUTION)
        self.assertEqual(c(1, "Oʻzbekiston Respublikasi Oliy sudi Plenumining qarori", "", ""), DocType.PLENUM)
        self.assertEqual(c(1, "Oʻzbekiston Respublikasi Konstitutsiyaviy sudining qarori", "", ""), DocType.COURT)
        self.assertEqual(c(1, "Toshkent shahar hokimining qarori", "", ""), DocType.LOCAL)
        self.assertEqual(c(1, "Qoraqalpogʻiston Respublikasining Qonuni", "", ""), DocType.LOCAL)
        self.assertEqual(c(1, "Постановление Законодательной палаты Олий Мажлиса", "", ""), DocType.PARLIAMENT)
        self.assertEqual(c(1, "Huquqni muhofaza qilish Axloq kodeksi", "", ""), DocType.OTHER)
        # act_type axlat bo'lsa — raqam formati bo'yicha
        self.assertEqual(c(1, "1", "", "PF-5000-son"), DocType.PRES_DECREE)

    def test_amending_and_tier(self):
        self.assertTrue(N.is_amending("Ayrim qonun hujjatlariga oʻzgartish va qoʻshimchalar kiritish toʻgʻrisida"))
        self.assertFalse(N.is_amending("Advokatura toʻgʻrisida"))
        self.assertEqual(N.corpus_tier(DocType.LAW, Status.ACTIVE), CorpusTier.CORE)
        self.assertEqual(N.corpus_tier(DocType.LAW, Status.REPEALED), CorpusTier.ON_DEMAND)
        self.assertEqual(N.corpus_tier(DocType.VMQ, Status.ACTIVE), CorpusTier.EXTENDED)
