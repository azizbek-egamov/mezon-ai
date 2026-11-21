from datetime import date, timedelta
from types import SimpleNamespace
from unittest import mock

from bs4 import BeautifulSoup
from django.test import TestCase
from django.utils import timezone

from apps.lex_corpus.models import LegalActDocument, LegalActEdition, SyncRun
from apps.lex_corpus.registry import _parse_row, linked_documents, parse_rss
from apps.lex_corpus.sync import SyncStats, documents_to_refresh, refresh_document, run_sync, upsert_registry

RSS = """﻿<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel>
<item><title>Toʻlov tizimi toʻgʻrisidagi nizomni tasdiqlash haqida</title><link>/uz/docs/8554315</link>
<description><![CDATA[Oʻzbekiston Respublikasi Markaziy banki boshqaruvining qarori рег. № МЮ 3960. Qabul qilingan sana 23.10.2026. Kuchga kirish sanasi 25.01.2027]]></description></item>
<item><title>Oʻzbekiston Respublikasining Jinoyat kodeksiga oʻzgartirish kiritish haqida</title><link>/uz/docs/-8554999</link>
<description><![CDATA[Oʻzbekiston Respublikasining Qonuni, 21.10.2026 yildagi OʻRQ-1100-son. Qabul qilingan sana 21.10.2026.]]></description></item>
</channel></rss>"""
ROW = """<table><tr class="dd-table__main-item"><td><a class="lx_link" href="/uz/docs/-8545690">Pensiyalar haqida</a>
<span class="badge">Vazirlar Mahkamasining qarori, 19.10.2026 yildagi 576-son</span>
<span class="lx_act_state"><i class="fa status_code_y"></i></span></td></tr></table>"""


def doc(abs_id, title, doc_type="CODE", status="ACTIVE", tier="CORE", amending=False):
    return LegalActDocument.objects.create(abs_id=abs_id, lex_id_lat=f"-{abs_id}", doc_type=doc_type, status=status,
                                           corpus_tier=tier, hierarchy_weight=0.95, title_uz_lat=title,
                                           is_amending=amending, last_synced_at=timezone.now())


class ParsingTests(TestCase):
    def test_rss(self):
        rows = parse_rss(RSS)
        self.assertEqual([r["id"] for r in rows], ["8554315", "-8554999"])
        self.assertEqual(rows[0]["act_number"], "")  # ro'yxatga olish raqami hujjat raqami emas
        self.assertEqual((rows[0]["act_date"], rows[0]["effective_from"]), ("23.10.2026", date(2027, 1, 25)))
        self.assertEqual(rows[1]["act_number"], "OʻRQ-1100-son")

    def test_registry_row_and_links(self):
        row = _parse_row(BeautifulSoup(ROW, "lxml").select_one("tr"))
        self.assertEqual((row["id"], row["act_date"], row["act_number"], row["status"]),
                         ("-8545690", "19.10.2026", "576-son", "kuchda"))
        self.assertEqual(linked_documents('<a href="/uz/docs/-111453#-310589">JK</a> <a href="/ru/docs/97664">'),
                         {111453, 97664})


class SyncTests(TestCase):
    def setUp(self):
        self.jk = doc(111453, "Oʻzbekiston Respublikasining Jinoyat kodeksi")
        self.cur = LegalActEdition.objects.create(document=self.jk, edition_label="15.10.2026",
                                                  edition_date=date(2026, 10, 15), is_current=True, source_url="x")

    def test_upsert_new_status_change_and_left_core(self):
        old_law = doc(5000, "Eski qonun", doc_type="LAW")
        stats = SyncStats()
        upsert_registry(parse_rss(RSS) + [
            {"id": "-5000", "title": "Eski qonun", "act_type": "Oʻzbekiston Respublikasining Qonuni", "act_number": "",
             "act_date": "01.01.2000", "status": "kuchini_yoqotgan"}], stats)
        self.assertEqual(sorted(stats.new_documents), [8554315, 8554999])
        self.assertEqual(LegalActDocument.objects.get(abs_id=8554315).effective_from, date(2027, 1, 25))
        old_law.refresh_from_db()
        self.assertEqual((old_law.status, stats.left_core), ("REPEALED", [5000]))

    def test_refresh_targets(self):
        stats = SyncStats()
        upsert_registry(parse_rss(RSS), stats)
        amending = LegalActDocument.objects.get(abs_id=8554999)
        self.assertTrue(amending.is_amending)
        client = mock.Mock()
        client.get_document_html.return_value = '<a href="/uz/docs/-111453">JK</a><a href="/uz/docs/-8554999">o‘zi</a>'
        self.assertEqual(documents_to_refresh(client, stats, check_codes=False) & {111453}, {111453})
        # kelajak sanali tahrir kuchga kirgan — joriy tahrir eskirgan
        stats2 = SyncStats()
        self.assertNotIn(111453, documents_to_refresh(client, stats2, check_codes=False))
        LegalActEdition.objects.create(document=self.jk, edition_label="20.10.2026", edition_date=date(2026, 10, 20),
                                       source_url="x")
        self.assertIn(111453, documents_to_refresh(client, stats2, check_codes=False))
        LegalActEdition.objects.filter(edition_label="20.10.2026").update(
            edition_date=timezone.localdate() + timedelta(days=30))  # hali kuchga kirmagan
        self.assertNotIn(111453, documents_to_refresh(client, stats2, check_codes=False))
        self.assertIn(111453, documents_to_refresh(client, stats2, check_codes=True))

    @mock.patch("apps.rag.indexer.reindex_documents", return_value=7)
    @mock.patch("apps.lex_corpus.sync.store_parsed")
    @mock.patch("apps.lex_corpus.sync.parse_document")
    def test_refresh_only_when_edition_changed(self, parse, store, reindex):
        client = mock.Mock()
        client.get_document_html.return_value = "<html/>"
        client.document_url.return_value = "x"
        parse.return_value = SimpleNamespace(current_edition="15.10.2026", editions=["15.10.2026", "30.12.2026"])
        stats = SyncStats()
        refresh_document(self.jk, client, stats, index=True)
        store.assert_not_called()
        self.assertEqual(stats.unchanged, [111453])
        self.assertTrue(LegalActEdition.objects.filter(document=self.jk, edition_label="30.12.2026").exists())
        parse.return_value = SimpleNamespace(current_edition="30.12.2026", editions=["30.12.2026"])
        refresh_document(self.jk, client, stats, index=True)
        store.assert_called_once()
        reindex.assert_called_once_with([111453])
        self.assertEqual((stats.refreshed, stats.indexed_chunks), ([111453], 7))

    @mock.patch("apps.lex_corpus.sync.store_parsed")
    @mock.patch("apps.lex_corpus.sync.parse_document")
    def test_empty_or_shrunken_page_is_rejected(self, parse, store):
        """lex.uz xizmat sahifasi (0 modda) korpusni o'chirib yubormasin; keshdagi yaxshi nusxa qaytariladi."""
        from apps.lex_corpus.models import LegalActArticle
        from apps.lex_corpus.sync import SuspiciousPage

        for i in range(12):
            LegalActArticle.objects.create(document=self.jk, edition=self.cur, position=i, article_number=str(i + 1),
                                           lex_elem_id=f"e{i}")
        client = mock.Mock()
        client.get_document_html.return_value = "<html>Texnik ishlar</html>"
        client._cache_path.return_value.exists.return_value = True
        client._cache_path.return_value.read_text.return_value = "<yaxshi/>"
        for n in (0, 5):   # bo'sh va yarmidan kam
            parse.return_value = SimpleNamespace(current_edition="30.12.2026", editions=[], articles=[object()] * n)
            with self.assertRaises(SuspiciousPage):
                refresh_document(self.jk, client, SyncStats(), index=False)
            store.assert_not_called()
        client.restore_cache.assert_called_with(self.jk.primary_lex_id, "<yaxshi/>")
        parse.return_value = SimpleNamespace(current_edition="30.12.2026", editions=[], articles=[object()] * 12)
        refresh_document(self.jk, client, SyncStats(), index=False)   # normal sahifa o'tadi
        store.assert_called_once()

    @mock.patch("apps.lex_corpus.sync.fetch_recent", return_value=[])
    @mock.patch("apps.lex_corpus.sync.fetch_rss", side_effect=ConnectionError("lex.uz javob bermadi"))
    def test_run_is_logged_even_on_failure(self, rss, recent):
        run = run_sync(client=mock.Mock(), log=lambda m: None)
        self.assertEqual(run.status, SyncRun.Status.FAILED)
        self.assertIn("lex.uz javob bermadi", run.log)
        self.assertIsNotNone(run.finished_at)
