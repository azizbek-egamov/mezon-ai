"""Kirill va rus matnlari (TZ §5.4, 8-bosqich): til almashtirgichi, moslashtirish, tahrir sanasi, bo'laklash, qidiruv."""
from datetime import date
from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, TestCase

from apps.lex_corpus.ingest import store_parsed
from apps.lex_corpus.models import LegalActArticle, LegalActDocument, corpus_lang
from apps.lex_corpus.parser import parse_document, parse_language_links
from apps.lex_corpus.sync import SyncStats, refresh_stale_translations
from apps.lex_corpus.tests.test_parser import elem
from apps.lex_corpus.translations import fetch_translations
from apps.rag.chunking import split_article
from apps.rag.search import SearchHit, apply_date, dedupe_languages, localize_hits


def words(text: str) -> int:
    return len(text.split())


def lang_bar(ru: str = "", cyr: str = "", lat: str = "") -> str:
    """lex.uz hujjat sarlavhasidagi til almashtirgichi: joriy til bosilmaydi (onclick yo'q)."""
    def item(label, title, target):
        click = f' onclick="openUrl(\'/uz/docs/{target}\')"' if target else ""
        active = "" if target else " active"
        return f'<div class="docContentHeader__item-link{active}"{click} title="{title}">{label}</div>'
    return (item("Рус", "На русском", ru) + item("Ўзб", "Ўзбекча", cyr) + item("O’zb", "O'zbekcha", lat)
            + '<div class="docContentHeader__item-link-language" onclick="openTwoLang(1)">Ўзб|Рус</div>')


def page(title: str, articles: list[tuple[str, str, str]], bar: str = "", current: str = "15.10.2026",
         editions: tuple[str, ...] = ("15.10.2026",), section: str = "") -> str:
    """articles: (modda sarlavhasi 'N-modda. Nomi', element id, matn)."""
    menu = "".join(
        f'<div class="dropdown-menu__item {"lx_date_selected" if e == current else "lx_date_link"}">{e}</div>'
        for e in editions)
    body = [bar, f'<div id="lx_var_t">{menu}</div>', elem("ACT_TITLE", "t1", title)]
    if section:
        body.append(elem("TEXT_HEADER_DEFAULT", "s1", section))
    for head, eid, text in articles:
        body += [elem("CLAUSE_DEFAULT", eid, head), elem("ACT_TEXT", eid + "t", text)]
    return "".join(body)


LAT = page("Oʻzbekiston Respublikasining Jinoyat kodeksi", [
    ("168-modda. Firibgarlik", "-10", "Firibgarlik jazolanadi."),
    ("169-modda. Oʻgʻrilik", "-20", "Oʻgʻrilik jazolanadi."),
    ("170-modda. Talonchilik", "-30", "Talonchilik jazolanadi."),
], bar=lang_bar(ru="111457", cyr="111453"), section="X bob. Oʻzgalar mulki")
CYR = page("ЎЗБЕКИСТОН РЕСПУБЛИКАСИНИНГ ЖИНОЯТ КОДЕКСИ", [
    ("168-модда. Фирибгарлик", "10", "Фирибгарлик жазоланади."),
    ("169-модда. Ўғрилик", "20", "Ўғрилик жазоланади."),
    ("170-модда. Талончилик", "30", "Талончилик жазоланади."),
], bar=lang_bar(ru="111457", lat="-111453"), current="15.10.2026 01", editions=("15.10.2026 01", "15.10.2026"),
    section="Х боб. Ўзгалар мулки")
RU = page("УГОЛОВНЫЙ КОДЕКС РЕСПУБЛИКИ УЗБЕКИСТАН", [
    ("Статья 168. Мошенничество", "100", "Мошенничество наказывается."),
    ("Статья 169. Кража", "200", "Кража наказывается."),
], bar=lang_bar(cyr="111453", lat="-111453"), section="Глава X. Хищение")


class FakeClient:
    """LexUzClient o'rnida: sahifalar (lex_id, tahrir yorlig'i) bo'yicha."""

    def __init__(self, pages: dict):
        self.pages, self.calls = pages, []

    @staticmethod
    def document_url(lex_id, label=None):
        return f"https://lex.uz/uz/docs/{lex_id}" + (f"?ONDATE={label}" if label else "")

    def get_document_html(self, lex_id, label=None, refresh=False):
        self.calls.append((lex_id, label, refresh))
        return self.pages[(lex_id, label)] if (lex_id, label) in self.pages else self.pages[(lex_id, None)]


class LanguageLinksTests(SimpleTestCase):
    def test_links_from_switcher(self):
        self.assertEqual(parse_language_links(LAT), {"ru": "111457", "cyr": "111453"})
        self.assertEqual(parse_language_links(CYR), {"ru": "111457", "lat": "-111453"})
        self.assertEqual(parse_language_links("<html></html>"), {})

    def test_russian_sections(self):
        article = parse_document(RU).articles[0]
        self.assertEqual(article.number, "168")
        self.assertEqual(article.section_path, ["Глава X. Хищение"])

    def test_corpus_lang(self):
        self.assertEqual([corpus_lang(x) for x in ("uz-Latn", "uz-Cyrl", "ru", "kaa", "en", None)],
                         ["lat", "cyr", "ru", "lat", "lat", "lat"])


class TranslationBase(TestCase):
    def setUp(self):
        self.doc = LegalActDocument.objects.create(
            abs_id=111453, lex_id_lat="-111453", doc_type="CODE", hierarchy_weight=0.95, status="ACTIVE",
            corpus_tier="CORE", title_uz_lat="Oʻzbekiston Respublikasining Jinoyat kodeksi")
        self.pages = {("-111453", None): LAT, ("111453", None): CYR, ("111457", None): RU}
        self.client = FakeClient(self.pages)
        store_parsed(self.doc, LAT, self.client)
        self.doc.refresh_from_db()

    def article(self, number: str) -> LegalActArticle:
        return LegalActArticle.objects.select_related("document", "edition").get(
            document=self.doc, article_number=number, edition__is_current=True)


class FetchTranslationsTests(TranslationBase):
    def test_matches_and_stores_both_languages(self):
        result = fetch_translations(self.doc, self.client)
        self.assertEqual(set(result), {"cyr", "ru"})
        self.doc.refresh_from_db()
        self.assertEqual((self.doc.lex_id_cyr, self.doc.lex_id_ru), ("111453", "111457"))
        self.assertEqual(self.doc.title_ru, "УГОЛОВНЫЙ КОДЕКС РЕСПУБЛИКИ УЗБЕКИСТАН")
        self.assertEqual(self.doc.title_uz_cyr, "ЎЗБЕКИСТОН РЕСПУБЛИКАСИНИНГ ЖИНОЯТ КОДЕКСИ")
        self.assertEqual(self.doc.translations["cyr"]["matched"], 3)
        self.assertEqual((self.doc.translations["ru"]["matched"], self.doc.translations["ru"]["total"]), (2, 3))
        self.assertTrue(self.doc.has_lang("ru") and self.doc.has_lang("cyr"))
        self.assertFalse(self.doc.has_lang("lat"))  # asosiy til — tarjima emas

        a = self.article("168")
        self.assertEqual(a.source_lang, "lat")
        self.assertEqual(a.content_uz_cyr, "Фирибгарлик жазоланади.")
        self.assertEqual(a.content_ru, "Мошенничество наказывается.")
        self.assertEqual((a.lang_label("lat"), a.lang_label("cyr"), a.lang_label("ru")),
                         ("168-modda. Firibgarlik", "168-модда. Фирибгарлик", "Статья 168. Мошенничество"))
        self.assertEqual(a.parts_in("ru")[0]["elem_ids"], ["100t"])
        self.assertEqual(a.section_in("ru"), "Глава X. Хищение")
        self.assertEqual(a.url_in("ru"), "https://lex.uz/uz/docs/111457#100")
        self.assertEqual(a.url_in("lat"), "https://lex.uz/uz/docs/-111453#-10")
        self.assertEqual(a.primary_text, "Firibgarlik jazolanadi.")

    def test_article_missing_in_translation_stays_empty(self):
        fetch_translations(self.doc, self.client)
        a = self.article("170")
        self.assertEqual(a.content_ru, "")
        self.assertFalse(a.has_lang("ru"))
        self.assertTrue(a.has_lang("cyr"))

    def test_structure_mismatch_is_rejected(self):
        self.pages[("111457", None)] = page("УК", [("Статья 900. Другая", "9", "Текст.")],
                                           bar=lang_bar(lat="-111453"))
        result = fetch_translations(self.doc, self.client, langs=["ru"])
        self.assertIn("rejected", result["ru"])
        self.doc.refresh_from_db()
        self.assertFalse(self.doc.has_lang("ru"))
        self.assertEqual(self.article("168").content_ru, "")

    def test_edition_date_alignment(self):
        # rus tarjimasi eski tahrirda, lekin asosiy tahrir sanasi uning ro'yxatida bor — o'sha tahrir olinadi
        newer = page("УК", [("Статья 168. Мошенничество", "100", "НОВАЯ редакция."), ("Статья 169. Кража", "200", "Кража.")], current="20.10.2026",
                     editions=("20.10.2026", "15.10.2026"), bar=lang_bar(lat="-111453"))
        older = page("УК", [("Статья 168. Мошенничество", "100", "Старая редакция."), ("Статья 169. Кража", "200", "Кража.")], current="15.10.2026",
                     editions=("20.10.2026", "15.10.2026"), bar=lang_bar(lat="-111453"))
        self.pages[("111457", None)], self.pages[("111457", "15.10.2026")] = newer, older
        self.pages[("-111453", None)] = LAT  # asosiy tahrir 15.10.2026
        result = fetch_translations(self.doc, self.client, langs=["ru"])
        self.assertFalse(result["ru"]["stale"])
        self.assertEqual(self.article("168").content_ru, "Старая редакция.")
        # tahrir ro'yxatida asosiy sana yo'q — stale
        self.pages[("111457", None)] = page("УК", [("Статья 168. Мошенничество", "100", "Другая."), ("Статья 169. Кража", "200", "Кража.")],
                                           current="01.01.2027", editions=("01.01.2027",), bar=lang_bar(lat="-111453"))
        result = fetch_translations(self.doc, self.client, langs=["ru"], refresh=True)
        self.assertTrue(result["ru"]["stale"])
        self.assertTrue(self.client.calls[-1][2])  # refresh uzatildi

    def test_store_parsed_resets_translations(self):
        fetch_translations(self.doc, self.client)
        store_parsed(self.doc, LAT, self.client)
        self.doc.refresh_from_db()
        self.assertEqual(self.doc.translations, {})
        self.assertEqual(self.article("168").content_ru, "")

    def test_cyrillic_source_gets_latin_translation(self):
        kk = LegalActDocument.objects.create(abs_id=5, lex_id_cyr="5", doc_type="CODE", hierarchy_weight=0.95,
                                             status="ACTIVE", corpus_tier="CORE", title_uz_cyr="КОДЕКС")
        cyr_page = page("ЎЗБЕКИСТОН КОДЕКСИ", [("1-модда. Умумий", "1", "Матн.")], bar=lang_bar(lat="-5"))
        lat_page = page("Oʻzbekiston kodeksi", [("1-modda. Umumiy", "-1", "Matn.")], bar=lang_bar(cyr="5"))
        client = FakeClient({("5", None): cyr_page, ("-5", None): lat_page})
        store_parsed(kk, cyr_page, client)
        kk.refresh_from_db()
        self.assertEqual(kk.primary_lex_id, "5")
        fetch_translations(kk, client)
        a = LegalActArticle.objects.get(document=kk)
        self.assertEqual((a.source_lang, a.content_uz_cyr, a.content_uz_lat), ("cyr", "Матн.", "Matn."))
        self.assertEqual(a.primary_text, "Матн.")
        self.assertEqual(a.heading_in("lat"), "Umumiy")
        self.assertEqual(a.heading_in("cyr"), "Умумий")


class ChunkingByLanguageTests(TranslationBase):
    def test_language_chunks_have_own_ids_and_headers(self):
        fetch_translations(self.doc, self.client)
        a = self.article("168")
        lat = split_article(a, self.doc.title_uz_lat, words, 1000)
        also_lat = split_article(a, self.doc.title_uz_lat, words, 1000, lang="lat")
        ru = split_article(a, self.doc.title_ru, words, 1000, lang="ru")
        cyr = split_article(a, self.doc.title_uz_cyr, words, 1000, lang="cyr")
        self.assertEqual(lat[0].chunk_id, also_lat[0].chunk_id)  # asosiy til id si o'zgarmagan
        self.assertEqual(len({lat[0].chunk_id, ru[0].chunk_id, cyr[0].chunk_id}), 3)
        self.assertEqual(ru[0].header, "УГОЛОВНЫЙ КОДЕКС РЕСПУБЛИКИ УЗБЕКИСТАН | Глава X. Хищение | "
                                       "Статья 168. Мошенничество")
        self.assertEqual((ru[0].lang, ru[0].elem_ids, ru[0].body), ("ru", ["100t"], "Мошенничество наказывается."))

    def test_build_chunks_payload(self):
        from apps.rag import indexer
        fetch_translations(self.doc, self.client)
        tokenizer = mock.Mock(side_effect=lambda text, **kw: {"input_ids": text.split()})
        with mock.patch.object(indexer.AutoTokenizer, "from_pretrained", return_value=tokenizer):
            articles = LegalActArticle.objects.filter(edition__is_current=True).select_related("document", "edition")
            primary = indexer.build_chunks(articles)
            only_ru = indexer.build_chunks(articles, langs=["ru"])
            everything = indexer.build_chunks(articles, langs=["lat", "cyr", "ru"])
        self.assertEqual(len(primary), 3)
        self.assertEqual({c.payload["lang"] for c in primary}, {"lat"})
        self.assertEqual(len(only_ru), 2)  # 170-moddaning rus tarjimasi yo'q
        self.assertEqual(len(everything), 3 + 3 + 2)
        c = next(c for c in only_ru if c.payload["article_number"] == "168")
        self.assertEqual((c.payload["lang"], c.payload["lex_id"], c.payload["label"], c.payload["doc_title"]),
                         ("ru", "111457", "Статья 168. Мошенничество", "УГОЛОВНЫЙ КОДЕКС РЕСПУБЛИКИ УЗБЕКИСТАН"))
        self.assertEqual(c.payload["lex_url"], "https://lex.uz/uz/docs/111457#100t")


def make_hit(article: LegalActArticle, lang: str, **payload) -> SearchHit:
    return SearchHit(article_id=article.pk, document_id=article.document_id, doc_title="x", label="x", text="x",
                     lex_url="x", score=1.0, payload={"lang": lang, "part_numbers": [1], "article_id": article.pk,
                                                      **payload})


class SearchLanguageTests(TranslationBase):
    def setUp(self):
        super().setUp()
        fetch_translations(self.doc, self.client)

    def test_dedupe_keeps_first_copy_per_article_chunk(self):
        def point(article_id, first_part, lang):
            return SimpleNamespace(payload={"article_id": article_id, "part_numbers": [first_part], "lang": lang})
        pts = [point(1, 1, "ru"), point(1, 1, "lat"), point(1, 3, "lat"), point(2, 1, "cyr"), point(1, 1, "cyr")]
        self.assertEqual([(p.payload["article_id"], p.payload["part_numbers"][0], p.payload["lang"])
                          for p in dedupe_languages(pts)], [(1, 1, "ru"), (1, 3, "lat"), (2, 1, "cyr")])

    def test_localize_to_requested_language(self):
        a = self.article("168")
        hit, = localize_hits([make_hit(a, "lat")], "ru")
        self.assertEqual((hit.text, hit.label, hit.lex_url), ("Мошенничество наказывается.", "Статья 168. Мошенничество",
                                                              "https://lex.uz/uz/docs/111457#100t"))
        self.assertEqual(hit.doc_title, "УГОЛОВНЫЙ КОДЕКС РЕСПУБЛИКИ УЗБЕКИСТАН")
        self.assertEqual((hit.payload["lang"], hit.payload["lang_fallback"]), ("ru", False))

    def test_default_language_is_source(self):
        a = self.article("168")
        ru_hit = make_hit(a, "ru", part_numbers=[1])
        ru_hit.text = "Мошенничество наказывается."
        hit, = localize_hits([ru_hit], None)
        self.assertEqual((hit.text, hit.label, hit.payload["lang"]), ("Firibgarlik jazolanadi.", "168-modda. Firibgarlik", "lat"))

    def test_missing_translation_falls_back(self):
        a = self.article("170")  # rus tarjimasi yo'q
        hit, = localize_hits([make_hit(a, "lat")], "ru")
        self.assertEqual((hit.payload["lang"], hit.payload["lang_fallback"]), ("lat", True))
        cyr_hit, = localize_hits([make_hit(a, "lat")], "cyr")
        self.assertEqual((cyr_hit.text, cyr_hit.payload["lang_fallback"]), ("Талончилик жазоланади.", False))

    def test_stale_translation_is_flagged(self):
        self.doc.translations = {**self.doc.translations, "ru": {**self.doc.translations["ru"], "stale": True}}
        self.doc.save()
        hit, = localize_hits([make_hit(self.article("168"), "lat")], "ru")
        self.assertTrue(hit.payload["translation_stale"])
        other, = localize_hits([make_hit(self.article("168"), "lat")], "cyr")
        self.assertFalse(other.payload["translation_stale"])

    def test_as_of_changed_version_is_source_language(self):
        a = self.article("168")
        a.valid_from = date(2026, 1, 1)
        a.save()
        self.doc.history_from = date(2020, 1, 1)
        self.doc.save()
        old = LegalActArticle.objects.create(
            document=self.doc, edition=a.edition, position=99, article_number="168", heading="Firibgarlik",
            content_uz_lat="Eski matn.", unit_key=a.unit_key, lex_elem_id="-1", valid_from=date(2020, 1, 1),
            valid_until=date(2025, 12, 31))
        hit, = apply_date(localize_hits([make_hit(a, "lat")], "ru"), date(2024, 5, 1))
        self.assertEqual((hit.text, hit.as_of["state"], hit.as_of["version_id"]), ("Eski matn.", "changed", old.pk))
        self.assertEqual((hit.payload["lang"], hit.payload["lang_fallback"]), ("lat", True))
        self.assertEqual(hit.current_text, "Мошенничество наказывается.")


class SyncTranslationsTests(TranslationBase):
    def test_stale_translation_is_refetched_and_reindexed(self):
        fetch_translations(self.doc, self.client)
        self.doc.translations = {**self.doc.translations, "ru": {**self.doc.translations["ru"], "stale": True}}
        self.doc.save()
        stats = SyncStats()
        with mock.patch("apps.lex_corpus.sync.fetch_translations",
                        return_value={"ru": {"edition": "20.10.2026", "stale": False}}) as fetch, \
                mock.patch("apps.rag.indexer.reindex_documents", return_value=7) as reindex:
            refresh_stale_translations(self.client, stats, index=True)
        fetch.assert_called_once()
        self.assertTrue(fetch.call_args.kwargs["refresh"])
        reindex.assert_called_once_with([111453])
        self.assertEqual((stats.translations_updated, stats.indexed_chunks), ([111453], 7))

    def test_fresh_translations_are_not_touched(self):
        fetch_translations(self.doc, self.client)
        with mock.patch("apps.lex_corpus.sync.fetch_translations") as fetch:
            refresh_stale_translations(self.client, SyncStats(), index=False)
        fetch.assert_not_called()
