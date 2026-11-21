import inspect
import json
from unittest import mock

from django.test import SimpleTestCase

from apps.rag.llm import AnthropicProvider, OllamaProvider


class ProviderInterfaceTests(SimpleTestCase):
    """Chaqiruvchilar (views, ask, cases) ikkala provayderga bir xil kalit so'zlarni beradi — biri qabul
    qilmasa, faqat o'sha rejimda (masalan, LLM siz server) TypeError chiqadi."""

    def test_same_keyword_arguments(self):
        for method in ("chat_json", "stream_text"):
            anthropic = set(inspect.signature(getattr(AnthropicProvider, method)).parameters)
            ollama = set(inspect.signature(getattr(OllamaProvider, method)).parameters)
            self.assertLessEqual(anthropic - {"self"}, ollama, method)

    def test_ollama_stream_uses_model_override(self):
        lines = [json.dumps({"message": {"content": "Sa"}}).encode(), json.dumps({"message": {"content": "lom"}}).encode(),
                 json.dumps({"done": True, "prompt_eval_count": 3, "eval_count": 2, "done_reason": "stop"}).encode()]
        with mock.patch("apps.rag.llm.requests.post") as post:
            post.return_value.iter_lines.return_value = lines
            meta = {}
            text = "".join(OllamaProvider("lokal").stream_text("s", "u", meta=meta, model="boshqa"))
        self.assertEqual(text, "Salom")
        self.assertEqual(post.call_args.kwargs["json"]["model"], "boshqa")
        self.assertEqual(meta["output_tokens"], 2)
        with mock.patch("apps.rag.llm.requests.post") as post:
            post.return_value.iter_lines.return_value = lines
            list(OllamaProvider("lokal").stream_text("s", "u", model=None))
        self.assertEqual(post.call_args.kwargs["json"]["model"], "lokal")
