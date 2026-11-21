"""Ish turlari (12-bosqich): qidiruv doiralari, turga mos promptlar, yuklash va tahlil zanjiriga ulanish."""
from unittest import mock

from django.test import SimpleTestCase, TestCase, override_settings

from apps.cases import analysis, case_types as ct, extract, legal
from apps.cases.analysis import Finding, find_issues
from apps.cases.extract import Fact, extract_block
from apps.cases.legal import ground_findings
from apps.cases.models import CaseRun
from apps.cases.pdf_text import Page
from apps.cases.tests.test_legal import FakeLLM, fake_search
from apps.cases.tests.test_views import CASE_PDF, CaseTestBase

OTHERS = ["civil", "economic", "administrative", "any"]
# Jinoyat ishiga xos so'zlar: boshqa turlarning promptlarida qolmasligi kerak
CRIMINAL_WORDS = ["jinoyat", "Jinoyat", "himoyachi", "ayblov", "tintuv", "qamoq", "ushlab turish"]


def fact(i=1):
    return Fact(id=f"F{i}", type="statement", page=1, date="2026-03-18", time="", source="s", summary="s", quote="q",
                verified=True, verified_page=1)


class ScopeTests(SimpleTestCase):
    def test_criminal_scope_unchanged(self):
        self.assertEqual(ct.CRIMINAL.scope, {"document_ids": [111460, 111453, 6445145, 163629], "doc_types": ["PLENUM"]})
        self.assertEqual(legal.CASE_SCOPES["criminal"], ct.CRIMINAL.scope)
        self.assertEqual(legal.CASE_SCOPES["any"], {})

    def test_other_scopes_have_own_procedural_codes(self):
        self.assertIn(ct.FPK, ct.CIVIL.scope["document_ids"])
        self.assertIn(ct.IPK, ct.ECONOMIC.scope["document_ids"])
        self.assertIn(ct.MSIYUK, ct.ADMINISTRATIVE.scope["document_ids"])
        self.assertIn(ct.MJTK, ct.ADMINISTRATIVE.scope["document_ids"])
        # jinoyat kodekslari boshqa turlarga aralashmaydi (case_01 da boshqa soha kodekslari chalg'itgan edi)
        for code in ("civil", "economic", "administrative"):
            ids = ct.CASE_TYPES[code].scope["document_ids"]
            self.assertFalse({ct.JK, ct.JPK, ct.JIK} & set(ids), code)
            self.assertEqual(len(ids), len(set(ids)), f"{code}: takroriy id")
            self.assertIn(ct.CONSTITUTION, ids)
            self.assertEqual(ct.CASE_TYPES[code].scope["doc_types"], ["PLENUM"])
        self.assertNotIn(ct.IPK, ct.CIVIL.scope["document_ids"])
        self.assertNotIn(ct.FPK, ct.ECONOMIC.scope["document_ids"])

    def test_unknown_code_falls_back_to_criminal(self):
        self.assertEqual(ct.get_case_type("xyz").code, "criminal")
        self.assertEqual(ct.get_case_type(None).code, "criminal")
        self.assertEqual(ct.scope_of("civil"), ct.CIVIL.scope)


class PromptTests(SimpleTestCase):
    BASES = {
        "extract": (extract.SYSTEM, ct.adapt_extract),
        "common": (analysis.COMMON, ct.adapt_analysis_common),
        "contradiction": (analysis.TASKS["contradiction"][2], ct.adapt_contradiction_task),
        "query": (legal.QUERY_SYSTEM, ct.adapt_query_system),
        "assess": (legal.ASSESS_SYSTEM, ct.adapt_assess_system),
    }

    def test_replaced_phrases_exist_in_criminal_prompts(self):
        """Asl promptlar o'zgarsa, moslashtirish jimgina buzilmasin."""
        phrases = {
            "extract": [ct.EXTRACT_CASE_PHRASE, ct.EXTRACT_ACTIONS_PHRASE],
            "common": [ct.PERSONA_PHRASE],
            "contradiction": [ct.CONTRADICTION_FINAL_PHRASE, ct.CONTRADICTION_EXCL_PHRASE, ct.CONTRADICTION_ROLE_PHRASE],
            "query": [ct.QUERY_CASE_PHRASE, ct.QUERY_CODES_PHRASE, ct.QUERY_EXAMPLES_PHRASE],
            "assess": [ct.PERSONA_PHRASE, ct.ASSESS_DEFENSE_PHRASE, ct.ASSESS_RETRO_PHRASE],
        }
        for name, items in phrases.items():
            for phrase in items:
                self.assertIn(phrase, self.BASES[name][0], f"{name}: {phrase[:40]!r}")

    def test_criminal_prompts_identical(self):
        for name, (base, adapt) in self.BASES.items():
            self.assertEqual(adapt(base, ct.CRIMINAL), base, name)
        self.assertEqual(ct.procedural_task(analysis.TASKS["procedural"][2], ct.CRIMINAL), analysis.TASKS["procedural"][2])

    def test_other_types_have_no_criminal_wording(self):
        for code in OTHERS:
            t = ct.CASE_TYPES[code]
            texts = {name: adapt(base, t) for name, (base, adapt) in self.BASES.items()}
            texts["procedural"] = ct.procedural_task(analysis.TASKS["procedural"][2], t)
            for name, text in texts.items():
                for word in CRIMINAL_WORDS:
                    self.assertNotIn(word, text, f"{code}/{name}: {word!r}")

    def test_type_specific_content(self):
        civil = ct.procedural_task(analysis.TASKS["procedural"][2], ct.CIVIL)
        self.assertIn("daʼvo muddati", civil)
        self.assertIn("pretenziya", ct.procedural_task("", ct.ECONOMIC))
        self.assertIn("maʼmuriy jazo qoʻllash muddati", ct.procedural_task("", ct.ADMINISTRATIVE))
        self.assertIn("vakil nima talab qilishi kerak", ct.adapt_assess_system(legal.ASSESS_SYSTEM, ct.CIVIL))
        self.assertIn("Fuqarolik protsessual kodeksi", ct.adapt_query_system(legal.QUERY_SYSTEM, ct.CIVIL))
        self.assertIn("fuqarolik ishidan", ct.adapt_extract(extract.SYSTEM, ct.CIVIL))
        # yengillashtiruvchi qonun orqaga qaytish kuchi — faqat maʼmuriy javobgarlikda eslatiladi
        self.assertIn("yengillashtiruvchi", ct.adapt_assess_system(legal.ASSESS_SYSTEM, ct.ADMINISTRATIVE))
        self.assertNotIn("yengillashtiruvchi", ct.adapt_assess_system(legal.ASSESS_SYSTEM, ct.CIVIL))


class PipelinePlumbingTests(TestCase):
    def test_extract_uses_case_type_prompt(self):
        llm = mock.Mock(chat_json=mock.Mock(return_value={"facts": []}))
        with mock.patch("apps.cases.extract.get_llm", return_value=llm):
            extract_block([Page(1, "matn " * 30)], model="m", case_type="economic")
            extract_block([Page(1, "matn " * 30)], model="m")
        economic, criminal = (c.args[0] for c in llm.chat_json.call_args_list)
        self.assertIn("iqtisodiy nizo ishidan", economic)
        self.assertIn("jinoyat ishidan", criminal)

    def test_find_issues_uses_case_type_prompts(self):
        prompts = []

        def chat_json(system, user, schema, **kw):
            prompts.append(system)
            return {"contradictions": [], "procedural_issues": [], "summary": ""}

        llm = mock.Mock(chat_json=mock.Mock(side_effect=chat_json))
        with mock.patch("apps.cases.analysis.get_llm", return_value=llm):
            find_issues([fact()], model="m", case_type="administrative")
        self.assertEqual(len(prompts), 2)
        self.assertTrue(all("maʼmuriy ishlar" in p for p in prompts))
        self.assertTrue(any("maʼmuriy jazo qoʻllash muddati" in p for p in prompts))

    def test_ground_findings_searches_type_scope_with_type_prompts(self):
        finding = Finding(kind="procedural", topic="Daʼvo muddati", fact_ids=["F1"], pages=[1], explanation="e",
                          importance="high")
        llm = FakeLLM()
        search = mock.Mock(side_effect=fake_search)
        with mock.patch("apps.cases.legal.get_llm", return_value=llm), mock.patch("apps.cases.legal.search", search):
            ground_findings([finding], [fact()], category="civil")
        self.assertEqual(search.call_args.kwargs["document_ids"], ct.CIVIL.scope["document_ids"])
        self.assertEqual(search.call_args.kwargs["doc_types"], ["PLENUM"])

        with mock.patch("apps.cases.legal.search", search), mock.patch("apps.cases.legal.get_llm") as get_llm:
            get_llm.return_value = mock.Mock(chat_json=mock.Mock(return_value={"items": []}))
            ground_findings([finding], [fact()], category="economic")
            query_system = get_llm.return_value.chat_json.call_args_list[0].args[0]
        self.assertIn("iqtisodiy nizo ishi boʻyicha", query_system)
        self.assertEqual(search.call_args.kwargs["document_ids"], ct.ECONOMIC.scope["document_ids"])

    def test_any_type_searches_whole_corpus(self):
        finding = Finding(kind="procedural", topic="t", fact_ids=["F1"], pages=[1], explanation="e", importance="high")
        search = mock.Mock(side_effect=fake_search)
        with mock.patch("apps.cases.legal.get_llm", return_value=FakeLLM()), mock.patch("apps.cases.legal.search", search):
            ground_findings([finding], [fact()], category="any")
        self.assertNotIn("document_ids", search.call_args.kwargs)


@override_settings(BILLING_ENFORCED=False)
class UploadCategoryTests(CaseTestBase):
    def upload_with(self, **extra):
        from django.core.files.uploadedfile import SimpleUploadedFile

        return self.client.post("/cases/upload", {"files": SimpleUploadedFile("ish.pdf", CASE_PDF.read_bytes()), **extra})

    def test_category_saved_and_defaults_to_criminal(self):
        self.upload_with(category="civil")
        self.upload_with()
        self.assertEqual(sorted(CaseRun.objects.values_list("category", flat=True)), ["civil", "criminal"])

    def test_invalid_category_rejected(self):
        self.assertIn("error=", self.upload_with(category="space")["Location"])
        self.assertEqual(CaseRun.objects.count(), 0)

    def test_worker_passes_category_to_pipeline(self):
        from apps.cases import worker

        self.upload_with(category="administrative")
        run = CaseRun.objects.get()
        report = {"pages": 30, "cost_usd": 0, "facts": [], "findings": [], "timeline": [], "summary": "ok"}
        with mock.patch("apps.cases.pipeline.analyze_pdf", return_value=report) as analyze:
            worker.process(str(run.id))
        self.assertEqual(analyze.call_args.kwargs["category"], "administrative")

    def test_list_page_offers_types_and_shows_them(self):
        self.upload_with(category="economic")
        html = self.client.get("/cases/").content.decode()
        for label in ("Jinoyat ishi", "Fuqarolik ishi", "Iqtisodiy ish", "Maʼmuriy ish", "Boshqa / aralash"):
            self.assertIn(label, html)
        self.assertIn('<option value="economic">', html)
        self.client.post("/i18n/set/", {"language": "ru"})
        html = self.client.get("/cases/").content.decode()
        self.assertIn("Экономическое дело", html)
