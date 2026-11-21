import inspect
import json
from unittest import mock

from django.test import SimpleTestCase

from apps.rag.llm import AnthropicProvider, GeminiProvider, OllamaProvider


class GeminiProviderTests(SimpleTestCase):
    def test_interface_compatibility(self):
        """GeminiProvider signaturasi AnthropicProvider bilan mos bo'lishi kerak."""
        for method in ("chat_json", "stream_text", "transcribe_image"):
            anthropic = set(inspect.signature(getattr(AnthropicProvider, method)).parameters)
            gemini = set(inspect.signature(getattr(GeminiProvider, method)).parameters)
            self.assertLessEqual(anthropic - {"self"}, gemini, method)

    def test_chat_json_mock(self):
        provider = GeminiProvider("gemini-flash-lite-latest", "fake_key", "https://example.com")
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{
                "content": {"parts": [{"text": json.dumps({"test": 123})}]},
                "finishReason": "STOP"
            }],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 20}
        }
        with mock.patch("apps.rag.llm.requests.post", return_value=mock_resp):
            res = provider.chat_json("system", "user")
        self.assertEqual(res, {"test": 123})
        self.assertGreater(provider.cost_usd(), 0)

    def test_stream_text_mock(self):
        provider = GeminiProvider("gemini-flash-lite-latest", "fake_key", "https://example.com")
        lines = [
            b"data: " + json.dumps({"candidates": [{"content": {"parts": [{"text": "Sa"}]}}]}).encode(),
            b"data: " + json.dumps({"candidates": [{"content": {"parts": [{"text": "lom"}]}}]}).encode(),
            b"data: " + json.dumps({
                "candidates": [{"content": {"parts": [{"text": ""}]}, "finishReason": "STOP"}],
                "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 15}
            }).encode(),
        ]
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.iter_lines.return_value = lines

        meta = {}
        with mock.patch("apps.rag.llm.requests.post", return_value=mock_resp):
            text = "".join(provider.stream_text("system", "user", meta=meta))

        self.assertEqual(text, "Salom")
        self.assertEqual(meta["input_tokens"], 5)
        self.assertEqual(meta["output_tokens"], 15)
        self.assertEqual(meta["stop_reason"], "STOP")
        self.assertGreater(meta["cost_usd"], 0)

    def test_transcribe_image_mock(self):
        provider = GeminiProvider("gemini-flash-lite-latest", "fake_key", "https://example.com")
        mock_resp = mock.MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "candidates": [{
                "content": {"parts": [{"text": "O'zbekiston Respublikasi Sud Hukmi"}]},
                "finishReason": "STOP"
            }],
            "usageMetadata": {"promptTokenCount": 258, "candidatesTokenCount": 50}
        }
        with mock.patch("apps.rag.llm.requests.post", return_value=mock_resp):
            text, cost = provider.transcribe_image(b"fake_image_bytes", mime_type="image/jpeg")
        self.assertEqual(text, "O'zbekiston Respublikasi Sud Hukmi")
        self.assertGreater(cost, 0)
        self.assertGreater(provider.cost_usd(), 0)



def _sse(text, finish=None):
    cand = {"content": {"parts": [{"text": text}]}}
    if finish:
        cand["finishReason"] = finish
    return b"data: " + json.dumps({"candidates": [cand]}).encode()


class GeminiStreamInterruptionTests(SimpleTestCase):
    """Gemini oqim boshlangach xato qaytarsa (503 "high demand") javob jim kesilib, to'liq bo'lib ko'rinmasin."""

    def run_stream(self, lines):
        from apps.rag.llm import LLMInterrupted  # noqa: F401  (import xatosini aniq ko'rsatish uchun)

        provider = GeminiProvider("gemini-flash-lite-latest", "fake_key", "https://example.com")
        resp = mock.MagicMock()
        resp.status_code = 200
        resp.iter_lines.return_value = lines
        got = []
        with mock.patch("apps.rag.llm.requests.post", return_value=resp):
            try:
                for chunk in provider.stream_text("system", "user", meta={}):
                    got.append(chunk)
            except Exception as e:  # noqa: BLE001
                return got, e
        return got, None

    def test_error_json_after_partial_text_is_interrupted(self):
        from apps.rag.llm import LLMInterrupted

        error = [b"{", b'  "error": {', b'    "code": 503,', b'    "status": "UNAVAILABLE"', b"  }", b"}"]
        got, exc = self.run_stream([_sse("Birinchi qism. ")] + error)
        self.assertEqual(got, ["Birinchi qism. "])
        self.assertIsInstance(exc, LLMInterrupted)

    def test_stream_without_finish_reason_is_interrupted(self):
        from apps.rag.llm import LLMInterrupted

        got, exc = self.run_stream([_sse("Yarim "), _sse("gap")])
        self.assertIsInstance(exc, LLMInterrupted)

    def test_connection_drop_is_interrupted(self):
        import requests

        from apps.rag.llm import LLMInterrupted

        def broken():
            yield _sse("Boshi ")
            raise requests.exceptions.ChunkedEncodingError("uzildi")

        got, exc = self.run_stream(broken())
        self.assertEqual(got, ["Boshi "])
        self.assertIsInstance(exc, LLMInterrupted)

    def test_complete_stream_is_fine(self):
        got, exc = self.run_stream([_sse("To'liq "), _sse("javob.", finish="STOP")])
        self.assertIsNone(exc)
        self.assertEqual("".join(got), "To'liq javob.")
