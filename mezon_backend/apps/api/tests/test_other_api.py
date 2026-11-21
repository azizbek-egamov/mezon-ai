from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.api.tests.test_cases_api import bearer
from apps.billing.models import UsageLog
from apps.doc_builder.models import DocumentTemplate
from apps.lex_corpus.models import LegalActArticle, LegalActDocument, LegalActEdition
from apps.rag.search import SearchHit
from apps.rag.tests.test_views import FakeLLM, fake_hits, parse_sse


class ApiTestBase(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("+998901112233", "Kuchli-parol-77", full_name="Test Advokat")
        self.client = bearer(APIClient(), self.user)


@override_settings(BILLING_ENFORCED=False)
class ChatApiTests(ApiTestBase):
    def test_validation_is_json(self):
        resp = self.client.post("/api/v1/chat/ask", {"question": ""}, format="json")
        self.assertEqual((resp.status_code, resp.json()["code"]), (400, "invalid"))
        resp = self.client.post("/api/v1/chat/ask", {"question": "x", "lang": "de"}, format="json")
        self.assertEqual(resp.status_code, 400)

    @mock.patch("apps.rag.views.get_llm", return_value=FakeLLM())
    @mock.patch("apps.rag.views.search_aspects", side_effect=fake_hits)
    def test_stream_events_with_sse_accept_header(self, _search, _llm):
        resp = self.client.post("/api/v1/chat/ask", {"question": "Firibgarlik nima?"}, format="json",
                                HTTP_ACCEPT="text/event-stream")
        self.assertEqual(resp["Content-Type"], "text/event-stream")
        events = parse_sse(b"".join(resp.streaming_content).decode())
        self.assertEqual([e[0] for e in events], ["aspects", "sources", "delta", "delta", "verification", "done"])

    @override_settings(BILLING_ENFORCED=True)
    @mock.patch("apps.rag.views.search_aspects", side_effect=RuntimeError("Qdrant yoʻq"))
    def test_failed_question_refunds_quota(self, _search):
        """Qidiruv xatosi bilan tugagan savol kvotani yemaydi (bepul: umrbod 3 ta)."""
        for _ in range(4):   # 3 dan ko'p urinish ham 429 olmaydi, chunki har biri qaytariladi
            resp = self.client.post("/api/v1/chat/ask", {"question": "Firibgarlik nima?"}, format="json")
            self.assertEqual(resp.status_code, 200)
            events = parse_sse(b"".join(resp.streaming_content).decode())
            self.assertEqual(events[-1][0], "error")
        self.assertEqual(sum(UsageLog.objects.filter(user=self.user).values_list("chat_questions", flat=True)), 0)

    @mock.patch("apps.rag.views.get_llm", return_value=FakeLLM())
    @mock.patch("apps.rag.views.search_aspects", side_effect=fake_hits)
    def test_ask_is_rate_limited_per_user(self, _search, _llm):
        from django.core.cache import caches

        from apps.api.throttling import ClientIpScopedRateThrottle

        caches["security"].clear()
        with mock.patch.dict(ClientIpScopedRateThrottle.THROTTLE_RATES, {"ask": "2/min"}):
            codes = []
            for _ in range(3):
                resp = self.client.post("/api/v1/chat/ask", {"question": "Firibgarlik nima?"}, format="json")
                if resp.streaming:
                    b"".join(resp.streaming_content)
                codes.append(resp.status_code)
        self.assertEqual(codes, [200, 200, 429])
        self.assertEqual(resp.json()["code"], "throttled")
        self.assertNotIn("throttled", resp.json()["detail"].lower())   # tarjima qilingan xabar

    @override_settings(BILLING_ENFORCED=True)
    def test_quota_exhausted_is_429_json(self):
        UsageLog.objects.create(user=self.user, date="2026-01-01", chat_questions=3)   # bepul: umrbod 3 ta savol
        resp = self.client.post("/api/v1/chat/ask", {"question": "Firibgarlik nima?"}, format="json")
        self.assertEqual((resp.status_code, resp.json()["code"]), (429, "quota_lifetime"))


@override_settings(BILLING_ENFORCED=False)
class TemplateApiTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.template = DocumentTemplate.objects.create(
            title="Ariza", category="MOTION", is_published=True, legal_basis="JPK 85-modda\n\nJPK 86-modda",
            form_schema=[{"name": "fio", "label": "F.I.Sh.", "type": "text"},
                         {"name": "sana", "label": "Sana", "type": "date"},
                         {"name": "summa", "label": "Summa", "type": "money", "required": False}],
            body="## ARIZA\n{{ fio }}, {{ sana }}{% if summa %}, {{ summa }} soʻm{% endif %}\n~ Imzo | {{ bugun }}")
        DocumentTemplate.objects.create(title="Qoralama", category="OTHER", form_schema=[], body="x")

    def test_list_and_detail(self):
        data = self.client.get("/api/v1/templates/").json()
        self.assertEqual([t["title"] for t in data], ["Ariza"])           # faqat e'lon qilinganlar
        self.assertEqual(self.client.get("/api/v1/templates/?category=CLAIM").json(), [])
        detail = self.client.get(f"/api/v1/templates/{self.template.id}").json()
        self.assertEqual(detail["legal_basis"], ["JPK 85-modda", "JPK 86-modda"])
        self.assertEqual(detail["form_schema"][1]["type"], "date")
        self.assertFalse(detail["is_approved"])   # moderator hali tasdiqlamagan

    def test_preview_and_errors(self):
        url = f"/api/v1/templates/{self.template.id}/preview"
        resp = self.client.post(url, {"values": {"fio": "Karimov A.", "sana": "2026-10-29", "summa": 1250000}},
                                format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        blocks = resp.json()["blocks"]
        self.assertEqual(blocks[0], {"kind": "center", "text": "ARIZA"})
        self.assertEqual(blocks[1]["text"], "Karimov A., 29.10.2026, 1 250 000 soʻm")
        resp = self.client.post(url, {"values": {"sana": "notogri"}}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(set(resp.json()), {"fio", "sana"})

    def test_preview_errors_follow_profile_language(self):
        self.user.language = "ru"
        self.user.save(update_fields=["language"])
        url = f"/api/v1/templates/{self.template.id}/preview"
        resp = self.client.post(url, {"values": {"sana": "notogri"}}, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertEqual(resp.json()["fio"], ["Заполните это поле."])
        self.assertEqual(resp.json()["sana"], ["Неверный формат значения."])

    def test_render_counts_quota(self):
        url = f"/api/v1/templates/{self.template.id}/render/docx"
        resp = self.client.post(url, {"values": {"fio": "Karimov A.", "sana": "2026-10-29"}}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertIn(".docx", resp["Content-Disposition"])
        self.assertEqual(UsageLog.objects.get(user=self.user).templates_used, 1)
        self.assertEqual(self.client.post(url, {"values": {}}, format="json").status_code, 400)
        self.assertEqual(UsageLog.objects.get(user=self.user).templates_used, 1)   # xato forma kvota olmaydi


class BillingApiTests(ApiTestBase):
    def test_usage_and_plans(self):
        usage = self.client.get("/api/v1/billing/usage").json()
        self.assertEqual(usage["plan"], "FREE")
        self.assertIn("limit", usage["usage"][0])
        plans = APIClient().get("/api/v1/billing/plans").json()   # kirmaganlar uchun ham
        self.assertEqual(plans[0]["code"], "FREE")
        self.assertEqual(plans[0]["lifetime_case_limit"], 1)


class LawsApiTests(ApiTestBase):
    def setUp(self):
        super().setUp()
        self.doc = LegalActDocument.objects.create(
            abs_id=111453, lex_id_lat="-111453", doc_type="CODE", hierarchy_weight=0.9, status="ACTIVE",
            corpus_tier="CORE", title_uz_lat="Oʻzbekiston Respublikasining Jinoyat kodeksi",
            title_search="oʻzbekiston respublikasining jinoyat kodeksi", title_ru="Уголовный кодекс")
        LegalActDocument.objects.create(abs_id=5, doc_type="LAW", hierarchy_weight=0.5, status="ACTIVE",
                                        corpus_tier="EXTENDED", title_uz_lat="Matnsiz qonun", title_search="matnsiz qonun")
        edition = LegalActEdition.objects.create(document=self.doc, edition_label="15.10.2026", is_current=True,
                                                 source_url="https://lex.uz/docs/-111453")
        self.article = LegalActArticle.objects.create(
            document=self.doc, edition=edition, position=1, article_number="168", heading="Firibgarlik",
            content_uz_lat="Firibgarlik, yaʼni aldash…", parts=[{"n": 1, "elem_ids": ["1"], "text": "Firibgarlik…"}],
            lex_elem_id="-3090249", section_path="Maxsus qism")

    def test_documents(self):
        data = self.client.get("/api/v1/laws/documents").json()
        self.assertEqual([d["id"] for d in data["results"]], [111453])   # matni bazada borlar
        self.assertEqual(self.client.get("/api/v1/laws/documents?q=Jinoyat").json()["count"], 1)
        self.assertEqual(self.client.get("/api/v1/laws/documents?q=Уголовный").json()["count"], 1)
        self.assertEqual(self.client.get("/api/v1/laws/documents?q=fuqarolik").json()["count"], 0)
        detail = self.client.get("/api/v1/laws/documents/111453").json()
        self.assertEqual(detail["articles"][0]["label"], "168-modda. Firibgarlik")
        self.assertEqual(self.client.get("/api/v1/laws/documents/5").json()["code"], "no_text")

    def test_article_falls_back_to_source_language(self):
        data = self.client.get(f"/api/v1/laws/articles/{self.article.id}?lang=ru").json()
        self.assertEqual(data["lang"], "lat")   # rus matni yo'q
        self.assertEqual(data["parts"][0]["n"], "1")
        self.assertEqual(data["lex_url"], "https://lex.uz/uz/docs/-111453#-3090249")

    def test_search(self):
        hit = fake_hits()[0][0]
        with mock.patch("apps.rag.search.search", return_value=[hit]) as search:
            data = self.client.get("/api/v1/laws/search?q=firibgarlik&lang=cyr").json()
        search.assert_called_once_with("firibgarlik", limit=10, rewrite=False, lang="cyr")   # LLM siz
        self.assertEqual(data[0]["label"], "168-modda. Firibgarlik")
        self.assertEqual(self.client.get("/api/v1/laws/search?q=").status_code, 400)
        with mock.patch("apps.rag.search.search", side_effect=RuntimeError("Qdrant yo'q")):
            self.assertEqual(self.client.get("/api/v1/laws/search?q=x").status_code, 503)
        self.assertIsInstance(hit, SearchHit)


class MetaApiTests(TestCase):
    def test_languages_and_schema_are_public_in_dev(self):
        client = APIClient()
        langs = client.get("/api/v1/i18n/languages").json()
        self.assertEqual([l["tz_code"] for l in langs], ["uz-Latn", "uz-Latn-2026", "uz-Cyrl", "ru", "kaa", "en"])
        with override_settings(DEBUG=True):
            resp = client.get("/api/v1/schema/?format=json")
        self.assertEqual(resp.status_code, 200)
        paths = resp.json()["paths"]
        self.assertIn("/api/v1/cases/{run_id}/report", paths)
        self.assertIn("jwtAuth", resp.json()["components"]["securitySchemes"])
