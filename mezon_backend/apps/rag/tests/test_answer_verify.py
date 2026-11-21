from django.test import SimpleTestCase

from apps.rag.answer import build_prompt, build_sources, verify_answer
from apps.rag.search import SearchHit

TEXT_168 = ("Firibgarlik, yaʼni aldash yoki ishonchni suiisteʼmol qilish yoʻli bilan oʻzganing mulkini yoki "
            "oʻzganing mulkiga boʻlgan huquqni qoʻlga kiritish —\nbazaviy hisoblash miqdorining ellik baravaridan "
            "yuz baravarigacha miqdorda jarima yoki ikki yilgacha axloq tuzatish ishlari bilan jazolanadi.")


def hit(article_id: int, number: str, text: str) -> SearchHit:
    return SearchHit(article_id=article_id, document_id=111453, doc_title="Oʻzbekiston Respublikasining Jinoyat kodeksi",
                     label=f"{number}-modda", text=text, lex_url=f"https://lex.uz/uz/docs/-111453#-{article_id}",
                     score=0.9, payload={"article_number": number, "unit_type": "ARTICLE", "edition": "15.10.2026"})


class VerifyAnswerTests(SimpleTestCase):
    def setUp(self):
        self.sources = build_sources([hit(1, "168", TEXT_168), hit(2, "169", "Oʻgʻrilik, yaʼni oʻzganing mulkini yashirin ravishda talon-toroj qilish —")])

    def test_good_answer(self):
        answer = ("Firibgarlik uchun JK 168-modda qo'llanadi [M1]: «aldash yoki ishonchni suiiste'mol qilish yo'li bilan "
                  "o'zganing mulkini ... qo'lga kiritish» [M1]. O'g'rilik esa alohida jinoyat [M2].")
        report = verify_answer(answer, self.sources)
        self.assertTrue(report.ok, report.issues)
        self.assertEqual(report.citations, ["M1", "M2"])
        self.assertEqual(report.quotes_checked, 1)

    def test_unknown_source_and_altered_quote(self):
        answer = "Jazo: «ellik baravaridan ikki yuz baravarigacha jarima» [M1][M7]."
        kinds = sorted(i.kind for i in verify_answer(answer, self.sources).issues)
        self.assertEqual(kinds, ["iqtibos_mos_emas", "manba_yoq"])

    def test_plain_quotation_marks_are_not_law_quotes(self):
        answer = "# Ответственность «за решение вопроса»\nДеньги «для передачи должностному лицу» — мошенничество [M1]."
        report = verify_answer(answer, self.sources)
        self.assertTrue(report.ok, report.issues)
        self.assertEqual(report.quotes_checked, 0)

    def test_straight_double_quotes_before_citation_are_checked(self):
        good = verify_answer('Qonunda: "aldash yoki ishonchni suiisteʼmol qilish ... qoʻlga kiritish" [M1].', self.sources)
        self.assertTrue(good.ok, good.issues)
        self.assertEqual(good.quotes_checked, 1)
        bad = verify_answer("Qonunda: “ellik baravaridan ikki yuz baravarigacha” [M1].", self.sources)
        self.assertEqual([i.kind for i in bad.issues], ["iqtibos_mos_emas"])

    def test_quote_must_come_from_the_cited_source(self):
        """168-moddadan olingan gap [M2] (169-modda) deb ko'rsatilsa — noto'g'ri havola xatosi."""
        wrong = verify_answer("Jazo: «ikki yilgacha axloq tuzatish ishlari bilan jazolanadi» [M2].", self.sources)
        self.assertEqual([i.kind for i in wrong.issues], ["iqtibos_boshqa_manbada"])
        right = verify_answer("Jazo: «ikki yilgacha axloq tuzatish ishlari bilan jazolanadi» [M2][M1].", self.sources)
        self.assertTrue(right.ok, right.issues)   # ikki manbadan biri to'g'ri bo'lsa yetarli

    def test_article_mention_not_found_inside_longer_number(self):
        sources = build_sources([hit(1, "168", "Qoida 16-modda bilan belgilanadi.")])
        report = verify_answer("JK 6-modda qo'llanadi [M1].", sources)
        self.assertEqual([i.kind for i in report.issues], ["notanish_modda"])

    def test_invented_article_and_missing_citations(self):
        report = verify_answer("Bunday holatda 170-modda qo'llanadi.", self.sources)
        self.assertFalse(report.ok)
        self.assertEqual(sorted(i.kind for i in report.issues), ["iqtibossiz", "notanish_modda"])

    def test_prompt_contains_sources_and_language(self):
        system, user = build_prompt("firibgarlik uchun jazo", self.sources, lang="ru")
        self.assertIn("rus tilida", system)
        self.assertIn('<manba id="M1"', user)
        self.assertIn("https://lex.uz/uz/docs/-111453#-1", user)
