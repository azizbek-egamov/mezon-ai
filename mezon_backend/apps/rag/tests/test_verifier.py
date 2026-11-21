from datetime import date

from django.test import TestCase

from apps.lex_corpus.models import LegalActArticle, LegalActDocument, LegalActEdition
from apps.rag.answer import Source
from apps.rag.search import SearchHit
from apps.rag.verifier import verify_legal

ART_45 = ("Shaxsni muayyan huquqdan mahrum qilish sud tayinlagan muddat davomida taqiqlashdan iboratdir.\n"
          "Tadbirkorlik faoliyati bilan shugʻullanayotgan shaxslarga nisbatan bunday jazo tayinlanmaydi, "
          "bundan odam oʻlishiga yoki boshqa ogʻir oqibatlarga sabab boʻlgan hollar mustasno.")
ART_226 = ("Ushlab turish muddati koʻpi bilan qirq sakkiz soatni tashkil etadi.\n"
           "Sud ushlab turish muddatini qirq sakkiz soatga uzaytirishi mumkin.\n"
           "a) prokurorning iltimosnomasiga koʻra;")
ART_8 = "Kodeksda qoʻllanilgan atamalar.\nIzoh. Koʻp miqdor — bazaviy hisoblash miqdorining yuz baravari."


class VerifierTests(TestCase):
    def setUp(self):
        self.jk = self._doc(111453, "Jinoyat kodeksi")
        self.jpk = self._doc(111460, "Jinoyat-protsessual kodeksi")
        self.a45 = self._article(self.jk, "45", ART_45)
        self.a8 = self._article(self.jk, "8", ART_8)
        self.a226 = self._article(self.jpk, "226", ART_226, valid_from=date(2020, 1, 1))
        self.jpk.history_from = date(2016, 1, 1)
        self.jpk.save()

    def _doc(self, abs_id, title, status="ACTIVE"):
        doc = LegalActDocument.objects.create(abs_id=abs_id, lex_id_lat=f"-{abs_id}", doc_type="CODE", status=status,
                                              hierarchy_weight=0.95, corpus_tier="CORE", title_uz_lat=title,
                                              last_synced_at="2026-10-23T00:00:00Z")
        LegalActEdition.objects.create(document=doc, edition_label="15.10.2026", is_current=True, source_url="x")
        return doc

    def _article(self, doc, number, text, **kw):
        return LegalActArticle.objects.create(document=doc, edition=doc.editions.get(), position=int(number),
                                              article_number=number, heading="", content_uz_lat=text,
                                              lex_elem_id="-1", unit_key=f"ARTICLE:{number}#1", **kw)

    def source(self, key, article, **hit):
        return Source(key, SearchHit(article_id=article.pk, document_id=article.document_id,
                                     doc_title=article.document.title_uz_lat, label=f"{article.article_number}-modda",
                                     text=article.content_uz_lat, lex_url="x", score=1.0, **hit))

    def kinds(self, answer, sources, on_date=None):
        return sorted(i.kind for i in verify_legal(answer, sources, on_date))

    def test_invented_article_is_an_error(self):
        sources = [self.source("M1", self.a226)]
        self.assertEqual(self.kinds("JPK 226-moddasiga koʻra muddat 48 soat [M1].", sources), [])
        self.assertEqual(self.kinds("JK 999-moddasi buni taqiqlaydi [M1].", sources), ["modda_yoq"])

    def test_article_not_in_force_on_event_date(self):
        sources = [self.source("M1", self.a226)]
        answer = "JPK 226-moddasiga koʻra [M1] ushlab turish 48 soat."
        self.assertEqual(self.kinds(answer, sources, date(2021, 5, 1)), [])
        issues = verify_legal(answer, sources, date(2018, 5, 1))
        self.assertEqual([i.kind for i in issues], ["modda_sanada_kuchda_emas"])
        self.assertIn("01.01.2020 dan kuchga kirgan", issues[0].detail)

    def test_part_number_check(self):
        sources = [self.source("M1", self.a226)]
        self.assertEqual(self.kinds("JPK 226-moddasining ikkinchi qismi [M1].", sources), [])
        self.assertEqual(self.kinds("JPK 226-moddasining 3-qismi [M1].", sources), ["qism_yoq"])  # a) band — qism emas

    def test_repealed_document(self):
        old = self._doc(20596, "Eski Konstitutsiya", status="REPEALED")
        art = self._article(old, "25", "Har kim erkinlik huquqiga ega.")
        self.assertEqual(self.kinds("Erkinlik huquqi [M1].", [self.source("M1", art)]), ["hujjat_kuchda_emas"])

    def test_dropped_exception_is_flagged(self):
        sources = [self.source("M1", self.a45)]
        quote = "«Tadbirkorlik faoliyati bilan shugʻullanayotgan shaxslarga nisbatan bunday jazo tayinlanmaydi» [M1]."
        issues = verify_legal(f"Qonunga koʻra {quote}", sources)
        self.assertEqual([i.kind for i in issues], ["istisno_tushgan"])
        self.assertIn("ogʻir oqibatlarga sabab boʻlgan hollar mustasno", issues[0].detail)
        mentioned = f"{quote} Lekin odam oʻlishiga yoki boshqa ogʻir oqibatlarga sabab boʻlgan hollar mustasno."
        self.assertEqual(self.kinds(mentioned, sources), [])
        whole = ("«bunday jazo tayinlanmaydi, bundan odam oʻlishiga yoki boshqa ogʻir oqibatlarga sabab boʻlgan "
                 "hollar mustasno» [M1].")
        self.assertEqual(self.kinds(whole, sources), [])

    def test_note_and_unknown_edition(self):
        issues = verify_legal("«Kodeksda qoʻllanilgan atamalar» [M1].", [self.source("M1", self.a8)])
        self.assertEqual([(i.kind, i.severity) for i in issues], [("izoh_bor", "info")])
        src = self.source("M1", self.a226, as_of={"state": "unknown", "date": "2010-01-01", "note": "tarix yoʻq"})
        issues = verify_legal("Muddat [M1].", [src], date(2010, 1, 1))  # tarix 2016 dan — eski tahrir tekshirilmadi
        self.assertEqual([(i.kind, i.severity) for i in issues], [("tahrir_nomalum", "warning")])
        src = self.source("M1", self.a45, as_of={"state": "unknown", "date": "2010-01-01", "note": "tarix yoʻq"})
        issues = verify_legal("Jazo [M1].", [src], date(2010, 1, 1))  # JK tarixi umuman yuklanmagan
        self.assertEqual([(i.kind, i.severity) for i in issues], [("tahrir_nomalum", "info")])
