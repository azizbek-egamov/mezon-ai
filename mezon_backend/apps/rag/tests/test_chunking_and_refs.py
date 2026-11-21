from datetime import date

from django.test import TestCase

from apps.lex_corpus.models import LegalActArticle, LegalActDocument, LegalActEdition
from apps.rag.chunking import split_article
from apps.rag.search import find_exact_articles


def words(text: str) -> int:  # test uchun soddalashtirilgan "token" hisobi
    return len(text.split())


class ChunkingTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.doc = LegalActDocument.objects.create(
            abs_id=111453, lex_id_lat="-111453", doc_type="CODE", hierarchy_weight=0.95, status="ACTIVE",
            corpus_tier="CORE", title_uz_lat="Oʻzbekiston Respublikasining Jinoyat kodeksi")
        cls.edition = LegalActEdition.objects.create(document=cls.doc, edition_label="15.10.2026",
                                                     edition_date=date(2026, 10, 15), is_current=True,
                                                     source_url="https://lex.uz/uz/docs/-111453")
        parts = [{"n": i, "elem_ids": [f"-{i}0", f"-{i}1"], "text": f"qism {i} " + "soʻz " * 40 + "\noxiri"}
                 for i in range(1, 5)]
        cls.article = LegalActArticle.objects.create(
            document=cls.doc, edition=cls.edition, position=0, unit_type="ARTICLE", article_number="168",
            heading="Firibgarlik", section_path="MAXSUS QISM / X bob. Oʻzgalar mulkini talon-toroj qilish",
            content_uz_lat="\n".join(p["text"] for p in parts), parts=parts, lex_elem_id="-310589")

    def test_short_article_single_chunk(self):
        chunks = split_article(self.article, self.doc.title_uz_lat, words, max_tokens=1000)
        self.assertEqual(len(chunks), 1)
        c = chunks[0]
        self.assertEqual(c.header, "Oʻzbekiston Respublikasining Jinoyat kodeksi | X bob. Oʻzgalar mulkini "
                                   "talon-toroj qilish | 168-modda. Firibgarlik")
        self.assertEqual(c.part_numbers, [1, 2, 3, 4])
        self.assertEqual(c.elem_ids[:2], ["-10", "-11"])

    def test_long_article_split_by_parts(self):
        chunks = split_article(self.article, self.doc.title_uz_lat, words, max_tokens=120)
        self.assertEqual([c.part_numbers for c in chunks], [[1, 2], [3, 4]])
        self.assertEqual(len({c.chunk_id for c in chunks}), 2)
        # bir xil kirishda id lar barqaror (qayta indekslashda ustidan yoziladi)
        again = split_article(self.article, self.doc.title_uz_lat, words, max_tokens=120)
        self.assertEqual([c.chunk_id for c in chunks], [c.chunk_id for c in again])

    def test_exact_reference(self):
        for q in ["JK 168-modda", "Jinoyat kodeksining 168-moddasi nima deydi?", "jk 168 modda"]:
            self.assertEqual([a.pk for a in find_exact_articles(q)], [self.article.pk], q)
        self.assertEqual(find_exact_articles("JPK 168-modda"), [])
        self.assertEqual(find_exact_articles("firibgarlik uchun jazo"), [])
