"""Huquqqa aloqasiz savol (suhbat): lex.uz da qidirilmaydi, javob LLM siz, savol kvotasi qaytariladi."""
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import SimpleTestCase, TestCase, override_settings

from apps.billing.models import UsageLog
from apps.rag import query_rewrite

from .test_views import parse_sse


class PlanLegalFlagTests(SimpleTestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def plan(self, data):
        llm = mock.Mock(chat_json=mock.Mock(return_value=data), model="m")
        llm.name = "fake"
        with mock.patch("apps.rag.query_rewrite.get_llm", return_value=llm):
            return query_rewrite.plan_aspects("savol")

    def test_non_legal_gives_empty_plan(self):
        self.assertEqual(self.plan({"legal": False, "aspects": []}), [])

    def test_legal_gives_aspects(self):
        out = self.plan({"legal": True, "aspects": [{"topic": "Jazo", "queries": ["firibgarlik"]}]})
        self.assertEqual(out, [{"topic": "Jazo", "queries": ["firibgarlik"]}])

    def test_missing_flag_is_treated_as_legal(self):
        """Eski/noaniq javob (legal yo'q) huquqiy savolni rad etmasligi kerak."""
        out = self.plan({"aspects": [{"topic": "Jazo", "queries": ["firibgarlik"]}]})
        self.assertEqual(out[0]["topic"], "Jazo")


class NonLegalChatTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("+998901112233", "Kuchli-parol-77", full_name="Test")
        self.client.force_login(self.user)

    @override_settings(BILLING_ENFORCED=True)
    @mock.patch("apps.rag.views.get_llm")
    @mock.patch("apps.rag.views.search_aspects", return_value=([], []))
    def test_small_talk_is_answered_by_ai_without_sources_or_quota(self, _search, llm):
        """Tayyor andoza gap yo'q: javobni LLM yozadi (har safar boshqacha), lex.uz manbalari chiqmaydi."""
        import json

        def fake_stream(system, user, effort=None, max_tokens=None, meta=None, model=None):
            self.assertIn("andoza", system)          # suhbat uchun alohida ko'rsatma
            self.assertEqual(user, "salem")
            yield "Vaalaykum "
            yield "assalom!"
            meta.update(cost_usd=0.0001)

        llm.return_value.stream_text.side_effect = fake_stream
        resp = self.client.post("/api/ask", json.dumps({"question": "salem"}), content_type="application/json")
        events = parse_sse(b"".join(resp.streaming_content).decode())
        self.assertEqual([e[0] for e in events], ["aspects", "sources", "delta", "delta", "verification", "done"])
        self.assertEqual(events[1][1], [])
        self.assertTrue(events[4][1]["ok"])               # "Xato topildi" ko'rsatilmaydi
        self.assertEqual(events[2][1]["text"] + events[3][1]["text"], "Vaalaykum assalom!")
        used = sum(UsageLog.objects.filter(user=self.user).values_list("chat_questions", flat=True))
        self.assertEqual(used, 0)                          # huquqiy tahlil bo'lmadi — kvota qaytarildi

    @mock.patch("apps.rag.views.get_llm")
    @mock.patch("apps.rag.views.search_aspects", return_value=([], []))
    def test_small_talk_llm_failure_is_an_error_event(self, _search, llm):
        import json

        llm.return_value.stream_text.side_effect = RuntimeError("tarmoq")
        resp = self.client.post("/api/ask", json.dumps({"question": "salem"}), content_type="application/json")
        events = parse_sse(b"".join(resp.streaming_content).decode())
        self.assertEqual(events[-1][0], "error")


class StreamRetryTests(SimpleTestCase):
    """_llm_stream: oqim uzilsa yarim matn `None` (reset) bilan tashlanadi va qayta uriniladi."""

    def test_retry_after_partial_output_emits_reset_then_full_text(self):
        from apps.rag.llm import LLMInterrupted
        from apps.rag.views import _llm_stream

        attempts = []

        def fake_stream(system, user, **kw):
            attempts.append(1)
            if len(attempts) == 1:
                yield "Yarim "
                raise LLMInterrupted("503")
            yield "To'liq "
            yield "javob."

        parts: list[str] = []
        llm = mock.Mock(stream_text=fake_stream)
        with mock.patch("apps.rag.views.get_llm", return_value=llm), mock.patch("apps.rag.views.time.sleep"):
            out = list(_llm_stream(parts, "s", "u"))
        self.assertEqual(out, ["Yarim ", None, "To'liq ", "javob."])
        self.assertEqual("".join(parts), "To'liq javob.")

    def test_second_interruption_raises(self):
        from apps.rag.llm import LLMInterrupted
        from apps.rag.views import _llm_stream

        def always_broken(system, user, **kw):
            yield "x"
            raise LLMInterrupted("503")

        llm = mock.Mock(stream_text=always_broken)
        with mock.patch("apps.rag.views.get_llm", return_value=llm), mock.patch("apps.rag.views.time.sleep"):
            with self.assertRaises(LLMInterrupted):
                list(_llm_stream([], "s", "u"))
