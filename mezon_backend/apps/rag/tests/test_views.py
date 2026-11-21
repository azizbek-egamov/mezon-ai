import json
from unittest import mock

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from apps.rag.search import SearchHit

TEXT = "Firibgarlik, yaʼni aldash yoki ishonchni suiisteʼmol qilish yoʻli bilan oʻzganing mulkini qoʻlga kiritish —"


def fake_hits(*args, **kwargs):
    hits = [SearchHit(article_id=1, document_id=111453, doc_title="Jinoyat kodeksi", label="168-modda. Firibgarlik",
                      text=TEXT, lex_url="https://lex.uz/uz/docs/-111453#-3090249", score=0.9, topic="Jinoiy javobgarlik",
                      payload={"article_number": "168", "unit_type": "ARTICLE", "edition": "15.10.2026"})]
    return hits, [{"topic": "Jinoiy javobgarlik", "queries": ["firibgarlik"]}]


class FakeLLM:
    def stream_text(self, system, user, effort=None, meta=None, model=None, max_tokens=None):
        yield "Bu firibgarlik [M1]: "
        yield "«aldash yoki ishonchni suiisteʼmol qilish» [M1]."
        meta.update(input_tokens=100, output_tokens=20, stop_reason="end_turn", cost_usd=0.001)


def parse_sse(body: str) -> list[tuple[str, dict]]:
    events = []
    for block in body.strip().split("\n\n"):
        lines = block.split("\n")
        events.append((lines[0].removeprefix("event: "), json.loads(lines[1].removeprefix("data: "))))
    return events


@override_settings(BILLING_ENFORCED=False)   # kvotalar alohida sinaladi (apps/billing/tests)
class AskViewTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user("+998901112233", "Kuchli-parol-77", full_name="Test Advokat")
        self.client.force_login(user)

    def test_anonymous_is_rejected(self):
        self.client.logout()
        self.assertRedirects(self.client.get("/"), "/accounts/login/?next=/", fetch_redirect_response=False)
        resp = self.client.post("/api/ask", json.dumps({"question": "savol"}), content_type="application/json")
        self.assertEqual(resp.status_code, 401)

    def test_chat_page_sets_csrf_cookie(self):
        resp = self.client.get("/")
        self.assertEqual(resp.status_code, 200)
        self.assertIn("csrftoken", resp.cookies)

    def test_validation(self):
        self.assertEqual(self.client.post("/api/ask", "{}", content_type="application/json").status_code, 400)
        bad_lang = json.dumps({"question": "savol", "lang": "fr"})
        self.assertEqual(self.client.post("/api/ask", bad_lang, content_type="application/json").status_code, 400)
        self.assertEqual(self.client.get("/api/ask").status_code, 405)

    @mock.patch("apps.rag.views.get_llm", return_value=FakeLLM())
    @mock.patch("apps.rag.views.search_aspects", side_effect=fake_hits)
    def test_stream_events(self, _search, _llm):
        resp = self.client.post("/api/ask", json.dumps({"question": "aldab pul olish"}), content_type="application/json")
        self.assertEqual(resp["Content-Type"], "text/event-stream")
        events = parse_sse(b"".join(resp.streaming_content).decode())
        self.assertEqual([e[0] for e in events], ["aspects", "sources", "delta", "delta", "verification", "done"])
        self.assertEqual(events[1][1][0]["key"], "M1")
        self.assertEqual(events[1][1][0]["topic"], "Jinoiy javobgarlik")
        verification = events[4][1]
        self.assertTrue(verification["ok"], verification)
        self.assertEqual(verification["quotes_checked"], 1)
        self.assertEqual(events[5][1]["usage"]["cost_usd"], 0.001)
