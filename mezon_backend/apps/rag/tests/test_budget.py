from types import SimpleNamespace
from unittest import mock

from django.test import SimpleTestCase, override_settings

from apps.rag.llm import AnthropicProvider, BudgetExceeded


def fake_response():
    usage = SimpleNamespace(input_tokens=100_000, output_tokens=10_000, cache_read_input_tokens=0)
    return SimpleNamespace(usage=usage, stop_reason="end_turn", content=[SimpleNamespace(type="text", text="{}")])


class BudgetTests(SimpleTestCase):
    @override_settings(LLM_BUDGET_USD=0.5)
    def test_calls_stop_after_budget_is_spent(self):
        with mock.patch("anthropic.Anthropic") as client_cls, mock.patch("builtins.open", mock.mock_open()):
            client_cls.return_value.with_options.return_value.messages.create.return_value = fake_response()
            llm = AnthropicProvider("claude-opus-5-5", api_key="test", base_url="http://localhost")
            llm.chat_json("s", "u")  # 100k*4 + 10k*20 = $0.60
            self.assertAlmostEqual(llm.cost_usd(), 0.60)
            with self.assertRaises(BudgetExceeded):
                llm.chat_json("s", "u")
            # chegara tugagach API ga so'rov yuborilmaydi
            self.assertEqual(client_cls.return_value.with_options.return_value.messages.create.call_count, 1)

    @override_settings(LLM_BUDGET_USD=0.5)
    def test_parallel_calls_wait_for_reservation(self):
        """Ikkita parallel chaqiruvning eng yuqori narxlari chegaraga sig'masa, ikkinchisi birinchisini kutadi va
        haqiqiy sarf chegaraga yetgan bo'lsa — yuborilmaydi."""
        import threading
        import time

        started = []

        def slow_create(**kwargs):
            started.append(time.monotonic())
            time.sleep(0.2)
            return fake_response()  # $0.60 — chegaradan oshadi

        with mock.patch("anthropic.Anthropic") as client_cls, mock.patch("builtins.open", mock.mock_open()):
            client_cls.return_value.with_options.return_value.messages.create.side_effect = slow_create
            llm = AnthropicProvider("claude-opus-5-5", api_key="test", base_url="http://localhost")
            errors = []

            def call():
                try:
                    llm.chat_json("s", "u", max_tokens=20_000)  # eng yuqori narx $0.40 — ikkitasi $0.5 ga sig'maydi
                except BudgetExceeded as e:
                    errors.append(e)

            threads = [threading.Thread(target=call) for _ in range(2)]
            [t.start() for t in threads]
            [t.join() for t in threads]
        self.assertEqual(len(started), 1)   # ikkinchi chaqiruv API ga ketmadi
        self.assertEqual(len(errors), 1)
        self.assertAlmostEqual(llm.cost_usd(), 0.60)
