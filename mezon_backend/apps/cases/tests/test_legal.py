from unittest import mock

from django.test import TestCase

from apps.cases.analysis import Finding
from apps.cases.extract import Fact
from apps.cases.legal import ground_findings
from apps.rag.search import SearchHit

ART_226 = ("Ushlab turish muddati shaxs amalda ushlangan paytdan (erkin harakatlanishga boʻlgan huquqlarning haqiqiy "
           "cheklangan payti) eʼtiboran koʻpi bilan qirq sakkiz soatni tashkil etadi.")


class FakeLLM:
    def __init__(self):
        self.calls = []

    def chat_json(self, system, user, schema=None, effort=None, max_tokens=4096, model=None, timeout=300):
        self.calls.append(user)
        if "TOPILMALAR" in user:
            return {"items": [{"index": 0, "queries": ["ushlab turish muddati"]}]}
        return {"assessments": [{
            "index": 0, "verdict": "qonun_buzilishi", "correction_needed": True,
            "assessment": "Qonunga koʻra «koʻpi bilan qirq sakkiz soatni tashkil etadi» [M1]. Muddat oshgan [M1].",
            "corrections": "Topilmada 72 soat deyilgan, qonunda 48 soat [M1].",
            "defense_action": "Ushlab turishni qonunga xilof deb topishni soʻrash."}]}


class CascadeLLM(FakeLLM):
    """Arzon model iqtibosni o'zgartirib yozadi (tekshiruvdan o'tmaydi), kuchli model — to'g'ri."""

    def chat_json(self, system, user, schema=None, effort=None, max_tokens=4096, model=None, timeout=300):
        data = super().chat_json(system, user, schema, effort, max_tokens, model, timeout)
        if "TOPILMALAR" not in user and model == "cheap-model":
            data["assessments"][0]["assessment"] = "Qonunda: «koʻpi bilan yetmish ikki soat» [M1]."
        self.calls.append(f"model={model}")
        return data


class NoQuoteLLM(FakeLLM):
    """Arzon model qonun buzilishini iqtibossiz da'vo qiladi; kuchli model iqtibos bilan asoslaydi."""

    def __init__(self, cheap_verdict="qonun_buzilishi"):
        super().__init__()
        self.cheap_verdict = cheap_verdict

    def chat_json(self, system, user, schema=None, effort=None, max_tokens=4096, model=None, timeout=300):
        data = super().chat_json(system, user, schema, effort, max_tokens, model, timeout)
        if "TOPILMALAR" not in user and model == "cheap-model":
            item = data["assessments"][0]
            item.update(verdict=self.cheap_verdict, assessment="Ushlab turish muddati oshgan [M1].", corrections="")
        self.calls.append(f"model={model}")
        return data


def fake_search(*args, **kwargs):
    return [SearchHit(article_id=1, document_id=111460, doc_title="Jinoyat-protsessual kodeksi",
                      label="226-modda. Ushlab turish muddati", text=ART_226,
                      lex_url="https://lex.uz/uz/docs/-111460#-254639", score=0.9,
                      payload={"article_number": "226", "unit_type": "ARTICLE", "edition": "15.10.2026"})]


class GroundFindingsTests(TestCase):
    def test_assessment_is_verified_against_sources(self):
        fact = Fact(id="F25", type="procedural_action", page=8, date="2026-03-18", time="09:30", source="Bayonnoma",
                    summary="09:30 da ushlab turildi", quote="soat 09:30 da", verified=True, verified_page=8)
        finding = Finding(kind="procedural", topic="Ushlab turish muddati", fact_ids=["F25"], pages=[8],
                          explanation="72 soat oshgan", importance="high")
        llm = FakeLLM()
        with mock.patch("apps.cases.legal.get_llm", return_value=llm), \
                mock.patch("apps.cases.legal.search", side_effect=fake_search):
            [result] = ground_findings([finding], [fact])
        self.assertEqual(result.verdict, "qonun_buzilishi")
        self.assertTrue(result.verification["ok"], result.verification)
        self.assertEqual(result.verification["quotes_checked"], 1)
        self.assertTrue(result.correction_needed)
        self.assertIn("48 soat", result.corrections)
        self.assertIn("«soat 09:30 da»", llm.calls[1])  # baholashga fakt iqtiboslari ham beriladi

    def test_failed_assessment_is_retried_with_stronger_model(self):
        fact = Fact(id="F25", type="procedural_action", page=8, date="2026-03-18", time="09:30", source="Bayonnoma",
                    summary="09:30 da ushlab turildi", quote="soat 09:30 da", verified=True, verified_page=8)
        finding = Finding(kind="procedural", topic="Ushlab turish muddati", fact_ids=["F25"], pages=[8],
                          explanation="72 soat oshgan", importance="high")
        llm = CascadeLLM()
        models = {"legal": "cheap-model", "legal_retry": "strong-model"}
        with mock.patch("apps.cases.legal.get_llm", return_value=llm), \
                mock.patch("apps.cases.legal.search", side_effect=fake_search), \
                mock.patch("apps.cases.legal.task_model", side_effect=lambda t: models.get(t)):
            [result] = ground_findings([finding], [fact])
        self.assertEqual([c for c in llm.calls if c.startswith("model=")],
                         ["model=cheap-model", "model=cheap-model", "model=strong-model"])  # so'rovlar, baho, qayta baho
        self.assertTrue(result.retried)
        self.assertEqual(result.model, "strong-model")
        self.assertTrue(result.verification["ok"], result.verification)

    def _ground_with(self, llm):
        fact = Fact(id="F25", type="procedural_action", page=8, date="2026-03-18", time="09:30", source="Bayonnoma",
                    summary="09:30 da ushlab turildi", quote="soat 09:30 da", verified=True, verified_page=8)
        finding = Finding(kind="procedural", topic="Ushlab turish muddati", fact_ids=["F25"], pages=[8],
                          explanation="72 soat oshgan", importance="high")
        models = {"legal": "cheap-model", "legal_retry": "strong-model"}
        with mock.patch("apps.cases.legal.get_llm", return_value=llm), \
                mock.patch("apps.cases.legal.search", side_effect=fake_search), \
                mock.patch("apps.cases.legal.task_model", side_effect=lambda t: models.get(t)):
            [result] = ground_findings([finding], [fact])
        return result

    def test_violation_without_law_quote_is_retried(self):
        result = self._ground_with(NoQuoteLLM("qonun_buzilishi"))
        self.assertTrue(result.retried)
        self.assertTrue(result.verification["ok"])
        self.assertEqual(result.verification["quotes_checked"], 1)

    def test_non_violation_without_quote_only_warns(self):
        result = self._ground_with(NoQuoteLLM("huquqiy_ahamiyatli"))
        self.assertFalse(result.retried)
        self.assertTrue(result.verification["ok"])
        self.assertEqual([i["kind"] for i in result.verification["issues"]], ["qonun_iqtibosi_yoq"])
        self.assertEqual(result.verification["issues"][0]["severity"], "warning")

    def test_medium_importance_is_not_retried(self):
        fact = Fact(id="F25", type="procedural_action", page=8, date="2026-03-18", time="09:30", source="Bayonnoma",
                    summary="09:30 da ushlab turildi", quote="soat 09:30 da", verified=True, verified_page=8)
        finding = Finding(kind="procedural", topic="Ushlab turish muddati", fact_ids=["F25"], pages=[8],
                          explanation="72 soat oshgan", importance="medium")
        llm = CascadeLLM()
        models = {"legal": "cheap-model", "legal_retry": "strong-model"}
        with mock.patch("apps.cases.legal.get_llm", return_value=llm), \
                mock.patch("apps.cases.legal.search", side_effect=fake_search), \
                mock.patch("apps.cases.legal.task_model", side_effect=lambda t: models.get(t)):
            [result] = ground_findings([finding], [fact], min_importance="medium")
        self.assertFalse(result.retried)
        self.assertFalse(result.verification["ok"])  # tekshiruvdan o'tmagan baho ogohlantirish bilan qoladi


class BatchLLM(FakeLLM):
    """Ikki topilma bitta partiyada; ikkinchisining bahosi birinchisining manbasidan (M1) aynan iqtibos keltiradi."""

    def chat_json(self, system, user, schema=None, effort=None, max_tokens=4096, model=None, timeout=300):
        self.calls.append(user)
        if "TOPILMALAR" in user:
            return {"items": []}
        good = "Qonunga koʻra «koʻpi bilan qirq sakkiz soatni tashkil etadi» [M1]."
        return {"assessments": [
            {"index": i, "verdict": "qonun_buzilishi", "correction_needed": False, "corrections": "",
             "assessment": good, "defense_action": "-"} for i in (0, 1)]}


class CrossBatchCitationTests(TestCase):
    def test_quote_from_other_finding_source_is_accepted(self):
        fact = Fact(id="F25", type="procedural_action", page=8, date="", time="", source="", summary="s",
                    quote="q", verified=True, verified_page=8)
        findings = [Finding(kind="procedural", topic=f"T{i}", fact_ids=["F25"], pages=[8], explanation="e",
                            importance="high") for i in (0, 1)]
        with mock.patch("apps.cases.legal.get_llm", return_value=BatchLLM()), \
                mock.patch("apps.cases.legal.search", side_effect=fake_search):
            first, second = ground_findings(findings, [fact])
        self.assertTrue(second.verification["ok"], second.verification)
        self.assertFalse(second.retried)
        self.assertEqual([s["key"] for s in second.sources], ["M2", "M1"])  # o'z manbasi + iqtibos olingan manba
        self.assertEqual([s["key"] for s in first.sources], ["M1"])
