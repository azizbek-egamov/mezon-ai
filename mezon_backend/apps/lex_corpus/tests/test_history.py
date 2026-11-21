from datetime import date
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase

from apps.lex_corpus.history import as_of, build_history, unit_keys
from apps.lex_corpus.models import LegalActArticle, LegalActDocument, LegalActEdition
from apps.lex_corpus.parser import Article
from apps.rag.answer import Source, verify_answer
from apps.rag.search import SearchHit, apply_date


def art(number, text, elem="-1"):
    return Article(number=number, heading=f"{number}-modda", elem_id=elem, position=int(number), section_path=[],
                   parts=[{"n": 1, "paragraphs": [{"elem_id": elem}], "text": text}])


OLD_1 = "eng kam oylik ish haqining yuz baravarigacha jarima"
NEW_1 = "bazaviy hisoblash miqdorining ellik baravaridan yuz baravarigacha jarima"
FUTURE_1 = "bazaviy hisoblash miqdorining yuz baravarigacha jarima"
# Tahrir yorlig'i -> o'sha tahrirdagi moddalar
EDITIONS = {
    "01.01.2018": [art("1", OLD_1), art("2", "ikkinchi modda")],
    "01.06.2020": [art("1", NEW_1), art("2", "ikkinchi modda"), art("3", "yangi modda")],
    "01.06.2020 01": [art("1", NEW_1 + " (oraliq)"), art("2", "ikkinchi modda"), art("3", "yangi modda")],
    "01.03.2024": [art("1", NEW_1 + " (oraliq)"), art("3", "yangi modda")],    # joriy; 2-modda chiqarilgan
    "01.01.2099": [art("1", FUTURE_1), art("3", "yangi modda")],               # kelajak sanali
}
CURRENT = "01.03.2024"


class FakeClient:
    def get_document_html(self, lex_id, label=None):
        return label or CURRENT


def fake_parse(html):
    return SimpleNamespace(articles=EDITIONS[html])


class HistoryTests(TestCase):
    def setUp(self):
        self.doc = LegalActDocument.objects.create(abs_id=111453, lex_id_lat="-111453", doc_type="CODE",
                                                   hierarchy_weight=0.95, status="ACTIVE", corpus_tier="CORE",
                                                   title_uz_lat="Jinoyat kodeksi")
        self.eds = {}
        for label in EDITIONS:
            d, m, y = label[:10].split(".")
            self.eds[label] = LegalActEdition.objects.create(
                document=self.doc, edition_label=label, edition_date=date(int(y), int(m), int(d)),
                is_current=label == CURRENT, source_url="x")
        current_arts = EDITIONS[CURRENT]
        for key, a in zip(unit_keys(current_arts), current_arts):
            LegalActArticle.objects.create(document=self.doc, edition=self.eds[CURRENT], position=a.position,
                                           article_number=a.number, heading=a.heading, content_uz_lat=a.text,
                                           lex_elem_id=a.elem_id)
        with mock.patch("apps.lex_corpus.history.parse_document", side_effect=fake_parse):
            self.stats = build_history(self.doc, FakeClient(), since=date(2016, 1, 1))

    def row(self, number, on_current=True):
        qs = LegalActArticle.objects.filter(document=self.doc, article_number=number)
        return qs.get(edition__is_current=True) if on_current else qs

    def test_versions_and_validity(self):
        self.assertEqual(self.stats.editions, 5)
        self.assertEqual(self.stats.history_from, date(2018, 1, 1))
        cur1 = self.row("1")
        # Joriy matn 2020-06-01 01 tahririda paydo bo'lgan; kelajak tahririgacha amal qiladi
        self.assertEqual((cur1.valid_from, cur1.valid_until), (date(2020, 6, 1), date(2098, 12, 31)))
        texts = {(r.valid_from, r.valid_until): r.content_uz_lat for r in self.row("1", on_current=False)}
        self.assertEqual(texts[(date(2018, 1, 1), date(2020, 5, 31))], OLD_1)
        self.assertEqual(texts[(date(2099, 1, 1), None)], FUTURE_1)
        self.assertNotIn(NEW_1, texts.values())  # bir kunlik oraliq tahrir hech qachon alohida kuchda bo'lmagan
        removed = LegalActArticle.objects.get(document=self.doc, article_number="2")
        self.assertEqual((removed.valid_from, removed.valid_until), (date(2018, 1, 1), date(2024, 2, 29)))
        self.assertFalse(removed.edition.is_current)
        self.assertEqual(self.row("3").valid_from, date(2020, 6, 1))

    def test_as_of_states(self):
        cur1, cur3 = self.row("1"), self.row("3")
        changed = as_of(cur1, date(2019, 5, 1))
        self.assertEqual(changed.state, "changed")
        self.assertEqual(changed.version.content_uz_lat, OLD_1)
        self.assertIn("ONDATE=01.01.2018", changed.version.direct_lex_url)
        self.assertEqual(as_of(cur1, date(2023, 1, 1)).state, "same")
        self.assertEqual(as_of(cur3, date(2019, 5, 1)).state, "not_yet")
        self.assertEqual(as_of(cur1, date(2015, 1, 1)).state, "unknown")  # tarix 2018 dan
        self.assertNotIn("ONDATE", cur1.direct_lex_url)

    def test_rebuild_is_idempotent(self):
        before = LegalActArticle.objects.filter(document=self.doc).count()
        with mock.patch("apps.lex_corpus.history.parse_document", side_effect=fake_parse):
            build_history(self.doc, FakeClient(), since=date(2016, 1, 1))
        self.assertEqual(LegalActArticle.objects.filter(document=self.doc).count(), before)

    def test_search_hits_follow_event_date(self):
        cur1, cur3 = self.row("1"), self.row("3")
        hits = [SearchHit(article_id=a.pk, document_id=self.doc.abs_id, doc_title="JK", label=f"{a.article_number}-modda",
                          text=a.content_uz_lat, lex_url=a.direct_lex_url, score=1.0) for a in (cur1, cur3)]
        out = apply_date(hits, date(2019, 5, 1))
        self.assertEqual(len(out), 1)  # 3-modda 2019 da yo'q edi
        h = out[0]
        self.assertEqual((h.as_of["state"], h.text), ("changed", OLD_1))
        self.assertEqual(h.current_text, NEW_1 + " (oraliq)")
        rendered = Source("M1", h).render()
        self.assertIn('voqea_sanasi="2019-05-01"', rendered)
        self.assertIn("[Hozirgi tahrir]", rendered)
        # Iqtibos sanadagi ham, hozirgi tahrirdan ham olinishi mumkin
        for quote in ("eng kam oylik ish haqining yuz baravarigacha", "ellik baravaridan yuz baravarigacha"):
            self.assertTrue(verify_answer(f"Qonunda: «{quote}» [M1].", [Source("M1", h)]).ok, quote)
        self.assertEqual(apply_date(hits, None), hits)
