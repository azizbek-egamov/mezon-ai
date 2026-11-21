"""Semantik kesh va Qdrant optimizatsiyalari bo'yicha testlar."""
from datetime import date
from unittest import mock

from django.test import TestCase, override_settings
from qdrant_client import QdrantClient, models

from apps.rag.search import _fused_candidates
from apps.rag.semantic_cache import (
    clear_semantic_cache,
    ensure_cache_collection,
    get_cached_answer,
    set_cached_answer,
)
from apps.rag.store import ensure_collection


class SemanticCacheTestCase(TestCase):
    def setUp(self):
        # Testlar uchun in-memory Qdrant client
        self.client = QdrantClient(":memory:")
        self.col = "test_cache"

    def test_ensure_cache_collection(self):
        name = ensure_cache_collection(recreate=True, name=self.col, client=self.client)
        self.assertEqual(name, self.col)
        self.assertTrue(self.client.collection_exists(self.col))

    @mock.patch("apps.rag.semantic_cache.get_embedder")
    def test_set_and_get_cached_answer(self, mock_embedder):
        # Soxta embedding: 1024 o'lchamli vektor
        vec = [0.05] * 1024
        mock_embedder.return_value.encode.return_value = [(vec, {1: 1.0})]

        question = "Firibgarlik uchun qanday jazo bor?"
        lang = "uz-Latn"
        effort = "medium"
        aspects = [{"topic": "Jinoyat", "queries": ["firibgarlik"]}]
        sources = [{"key": "M1", "doc_title": "Jinoyat kodeksi", "label": "168-modda"}]
        answer = "JK 168-moddasi bo'yicha firibgarlik uchun jarima yoki ozodlikdan mahrum qilish jazosi tayinlanadi."
        verification = {"ok": True, "citations": ["168-modda"], "quotes_checked": 1, "issues": []}

        # Keshga yozish
        with override_settings(SEMANTIC_CACHE_ENABLED=True, QDRANT_CACHE_COLLECTION=self.col):
            saved = set_cached_answer(
                question=question, lang=lang, effort=effort, aspects=aspects,
                sources=sources, answer=answer, verification=verification,
                client=self.client,
            )
            self.assertTrue(saved)

            # Bir xil savol bilan o'qish (o'xshashlik 1.0)
            cached = get_cached_answer(question=question, lang=lang, effort=effort, client=self.client)
            self.assertIsNotNone(cached)
            self.assertTrue(cached["cached"])
            self.assertEqual(cached["answer"], answer)
            self.assertEqual(cached["sources"], sources)
            self.assertGreaterEqual(cached["similarity"], 0.94)

            # Boshqa tilda so'ralsa keshdan chiqmasligi kerak
            cached_ru = get_cached_answer(question=question, lang="ru", effort=effort, client=self.client)
            self.assertIsNone(cached_ru)

    @mock.patch("apps.rag.semantic_cache.get_embedder")
    def test_unverified_answer_not_cached(self, mock_embedder):
        vec = [0.05] * 1024
        mock_embedder.return_value.encode.return_value = [(vec, {1: 1.0})]

        with override_settings(SEMANTIC_CACHE_ENABLED=True, QDRANT_CACHE_COLLECTION=self.col):
            saved = set_cached_answer(
                question="Savol", lang="uz-Latn", effort="low",
                aspects=[], sources=[], answer="Xato javob",
                verification={"ok": False, "issues": [{"severity": "critical", "detail": "noto'g'ri"}]},
                client=self.client,
            )
            self.assertFalse(saved)
            cached = get_cached_answer(question="Savol", lang="uz-Latn", effort="low", client=self.client)
            self.assertIsNone(cached)

    def test_cache_disabled_setting(self):
        with override_settings(SEMANTIC_CACHE_ENABLED=False):
            res = get_cached_answer("Savol", "uz-Latn", "medium", client=self.client)
            self.assertIsNone(res)
            saved = set_cached_answer("Savol", "uz-Latn", "medium", [], [], "Javob", {"ok": True}, client=self.client)
            self.assertFalse(saved)

    def test_clear_cache(self):
        ensure_cache_collection(recreate=True, name=self.col, client=self.client)
        ok = clear_semantic_cache(client=self.client)
        self.assertTrue(ok)


class StoreOptimizationTestCase(TestCase):
    def test_ensure_collection_quantization_and_indexes(self):
        client = QdrantClient(":memory:")
        name = "test_store_opt"
        res = ensure_collection(recreate=True, name=name, client=client)
        self.assertEqual(res, name)
        self.assertTrue(client.collection_exists(name))


class NativeRrfFallbackTestCase(TestCase):
    @mock.patch("apps.rag.search.get_embedder")
    @mock.patch("apps.rag.search.get_client")
    def test_fused_candidates_fallback_on_exception(self, mock_get_client, mock_embedder):
        vec = [0.01] * 1024
        mock_embedder.return_value.encode.return_value = [(vec, {1: 0.5})]

        # Mock client query_points prefetch bilan chaqirilganda xato bersa, fallback ishlashi kerak
        mock_client = mock.MagicMock()
        mock_get_client.return_value = mock_client

        # Prefetch bilan xato berish:
        def side_effect(*args, **kwargs):
            if "prefetch" in kwargs:
                raise RuntimeError("Prefetch not supported")
            pt = mock.MagicMock()
            pt.id = "uuid-1"
            return mock.MagicMock(points=[pt])

        mock_client.query_points.side_effect = side_effect
        res = _fused_candidates(["so'rov"], None, sparse_for=1)
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0].id, "uuid-1")
