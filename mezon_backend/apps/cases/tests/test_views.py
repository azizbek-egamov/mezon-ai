import json
import shutil
import tempfile
from pathlib import Path
from unittest import mock, skipUnless

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings

from cryptography.fernet import Fernet
from django.core.exceptions import ImproperlyConfigured

from apps.cases import storage, worker
from apps.cases.models import CaseRun

CASE_PDF = Path(__file__).resolve().parents[3] / "fixtures" / "cases" / "case_01" / "case_01.pdf"


@override_settings(BILLING_ENFORCED=False)   # kvotalar alohida sinaladi (apps/billing/tests)
class CaseTestBase(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        override = override_settings(DATA_DIR=self.tmp, DATA_KEYS=[Fernet.generate_key().decode()])
        override.enable()
        self.addCleanup(override.disable)
        storage._fernet.cache_clear()
        self.addCleanup(storage._fernet.cache_clear)
        # Testlar hech qachon haqiqiy fon oqimini (va API ni) ishga tushirmasin.
        patcher = mock.patch("apps.cases.worker.enqueue")
        self.enqueue = patcher.start()
        self.addCleanup(patcher.stop)
        User = get_user_model()
        self.user = User.objects.create_user("+998901112233", "Kuchli-parol-77", full_name="Test Advokat")
        self.other = User.objects.create_user("+998907778899", "Boshqa-parol-77", full_name="Boshqa Advokat")
        self.client.force_login(self.user)

    def make_run(self, owner=None, **kw):
        return CaseRun.objects.create(owner=owner or self.user, title=kw.pop("title", "t"), pdf_path=str(CASE_PDF),
                                      pages=30, **kw)

    def upload(self, name="ish.pdf", content=None, **extra):
        content = CASE_PDF.read_bytes() if content is None else content
        return self.client.post("/cases/upload", {"pdf": SimpleUploadedFile(name, content, "application/pdf"), **extra})



class CaseViewsTests(CaseTestBase):
    def test_upload_creates_run_and_enqueues(self):
        enqueue = self.enqueue
        resp = self.upload(title="Sintetik ish")
        run = CaseRun.objects.get()
        self.assertRedirects(resp, f"/cases/{run.id}/", fetch_redirect_response=False)
        self.assertEqual((run.title, run.pages, run.status), ("Sintetik ish", 30, CaseRun.Status.QUEUED))
        self.assertEqual(run.owner, self.user)
        self.assertTrue(Path(run.pdf_path).exists())
        enqueue.assert_called_once_with(run.id)

    def test_upload_validation(self):
        enqueue = self.enqueue
        self.assertIn("error=", self.upload(name="ish.txt")["Location"])
        self.assertIn("error=", self.upload(content=b"bu pdf emas")["Location"])
        with override_settings(CASE_MAX_PAGES=10):
            self.assertIn("error=", self.upload()["Location"])
        self.assertEqual(CaseRun.objects.count(), 0)
        enqueue.assert_not_called()

    def test_worker_process_saves_report(self):
        run = self.make_run()
        fake_report = {"pages": 30, "cost_usd": 0.12, "facts": [], "findings": [], "timeline": [], "summary": "ok"}

        def fake_analyze(path, progress, category="criminal"):
            progress(50, "Faktlar: 3/6 blok")
            self.assertEqual(CaseRun.objects.get(pk=run.id).progress, 50)
            return fake_report

        with mock.patch("apps.cases.pipeline.analyze_pdf", side_effect=fake_analyze):
            worker.process(str(run.id))
        run.refresh_from_db()
        self.assertEqual((run.status, run.progress), (CaseRun.Status.DONE, 100))
        self.assertEqual(float(run.cost_usd), 0.12)
        status = self.client.get(f"/api/cases/{run.id}").json()
        self.assertEqual(status["status"], "DONE")
        self.assertEqual(self.client.get(f"/api/cases/{run.id}/report").json()["summary"], "ok")

    def test_worker_failure_is_reported(self):
        run = self.make_run()
        with mock.patch("apps.cases.pipeline.analyze_pdf",
                        side_effect=RuntimeError("HTTPConnectionPool(host='127.0.0.1', port=9): API xatosi")):
            worker.process(str(run.id))
        run.refresh_from_db()
        self.assertEqual(run.status, CaseRun.Status.FAILED)
        self.assertEqual(run.error, worker.GENERIC_ERROR)   # ichki manzil/port foydalanuvchiga ko'rinmaydi
        self.assertNotIn("127.0.0.1", run.error)
        self.assertEqual(self.client.get(f"/api/cases/{run.id}/report").status_code, 404)

    def test_pages_render(self):
        run = self.make_run(title="Ish")
        self.assertContains(self.client.get("/cases/"), "Ish")
        self.assertContains(self.client.get(f"/cases/{run.id}/"), str(run.id))
        self.assertEqual(self.client.get(f"/cases/{run.id}/pdf")["Content-Type"], "application/pdf")

    def test_retry_requeues_only_failed_runs(self):
        run = self.make_run(status=CaseRun.Status.FAILED, error="max_tokens")
        self.client.post(f"/cases/{run.id}/retry")
        run.refresh_from_db()
        self.assertEqual((run.status, run.error, run.progress), (CaseRun.Status.QUEUED, "", 0))
        self.enqueue.assert_called_once_with(run.id)
        done = self.make_run(title="d", status=CaseRun.Status.DONE)
        self.client.post(f"/cases/{done.id}/retry")
        done.refresh_from_db()
        self.assertEqual(done.status, CaseRun.Status.DONE)
        self.assertEqual(self.enqueue.call_count, 1)

    def test_anonymous_is_redirected_or_rejected(self):
        run = self.make_run()
        self.client.logout()
        for url in ("/cases/", f"/cases/{run.id}/", f"/cases/{run.id}/pdf"):
            self.assertRedirects(self.client.get(url), f"/accounts/login/?next={url}", fetch_redirect_response=False)
        self.assertEqual(self.client.get(f"/api/cases/{run.id}").status_code, 401)
        self.assertIn("/accounts/login/", self.upload()["Location"])
        self.assertEqual(CaseRun.objects.count(), 1)

    def test_other_users_case_is_invisible(self):
        foreign = self.make_run(owner=self.other, title="Begona ish", status=CaseRun.Status.FAILED)
        mine = self.make_run(title="Mening ishim")
        page = self.client.get("/cases/")
        self.assertContains(page, "Mening ishim")
        self.assertNotContains(page, "Begona ish")
        for url in (f"/cases/{foreign.id}/", f"/cases/{foreign.id}/pdf", f"/api/cases/{foreign.id}"):
            self.assertEqual(self.client.get(url).status_code, 404, url)
        self.assertEqual(self.client.post(f"/cases/{foreign.id}/retry").status_code, 404)
        foreign.refresh_from_db()
        self.assertEqual(foreign.status, CaseRun.Status.FAILED)
        self.assertEqual(self.client.get(f"/api/cases/{mine.id}").status_code, 200)


class EncryptedStorageTests(CaseTestBase):
    """Fayllar diskda faqat shifrlangan holda; zero-retention va ishni o'chirish."""

    def test_upload_is_encrypted_on_disk_and_served_decrypted(self):
        self.upload()
        run = CaseRun.objects.get()
        self.assertTrue(run.pdf_path.endswith(".enc"))
        self.assertNotIn(b"%PDF", Path(run.pdf_path).read_bytes()[:64])
        self.assertEqual(list((self.tmp / "uploads").iterdir()), [Path(run.pdf_path)])  # ochiq nusxa qolmagan
        body = b"".join(self.client.get(f"/cases/{run.id}/pdf").streaming_content)
        self.assertEqual(body, CASE_PDF.read_bytes())

    def _process(self, run):
        fake = {"pages": 30, "cost_usd": 0.1, "facts": [], "findings": [], "timeline": [],
                "summary": "Qodirova Malika Anvarovna"}
        with mock.patch("apps.cases.pipeline.analyze_pdf", return_value=fake) as analyze:
            worker.process(str(run.id))
        run.refresh_from_db()
        return run, analyze

    def test_report_is_encrypted_and_temp_copy_removed(self):
        self.upload()
        run, analyze = self._process(CaseRun.objects.get())
        tmp_pdf = analyze.call_args.args[0]
        self.assertFalse(Path(tmp_pdf).exists())  # tahlil uchun ochilgan vaqtinchalik nusxa o'chirilgan
        self.assertTrue(run.report_path.endswith(".enc"))
        self.assertNotIn("Qodirova".encode(), Path(run.report_path).read_bytes())
        self.assertEqual(self.client.get(f"/api/cases/{run.id}/report").json()["summary"], "Qodirova Malika Anvarovna")
        self.assertTrue(Path(run.pdf_path).exists())

    def test_zero_retention_deletes_pdf_after_analysis(self):
        self.upload(zero_retention="1")
        run, _ = self._process(CaseRun.objects.get())
        self.assertEqual(run.pdf_path, "")
        self.assertEqual(list((self.tmp / "uploads").iterdir()), [])
        self.assertEqual(self.client.get(f"/cases/{run.id}/pdf").status_code, 404)
        self.assertContains(self.client.get(f"/cases/{run.id}/"), "serverdan oʻchirilgan")
        self.assertEqual(self.client.get(f"/api/cases/{run.id}/report").status_code, 200)

    def test_delete_removes_files_but_never_outside_data_dir(self):
        self.upload()
        run, _ = self._process(CaseRun.objects.get())
        files = [Path(run.pdf_path), Path(run.report_path)]
        self.assertEqual(self.client.post(f"/cases/{run.id}/delete").status_code, 302)
        self.assertFalse(CaseRun.objects.exists())
        self.assertFalse(any(f.exists() for f in files))
        imported = self.make_run(status=CaseRun.Status.DONE)  # pdf_path — repodagi fixture
        self.client.post(f"/cases/{imported.id}/delete")
        self.assertTrue(CASE_PDF.exists())
        foreign = self.make_run(owner=self.other)
        self.assertEqual(self.client.post(f"/cases/{foreign.id}/delete").status_code, 404)
        self.assertTrue(CaseRun.objects.filter(pk=foreign.pk).exists())

    def test_production_requires_key(self):
        with override_settings(DEBUG=False, DATA_KEYS=[""]):
            storage._fernet.cache_clear()
            with self.assertRaises(ImproperlyConfigured):
                storage.write_encrypted(self.tmp / "x", b"data")
        key = Fernet.generate_key().decode()
        with override_settings(DEBUG=False, DATA_KEYS=[key]):
            storage._fernet.cache_clear()
            path = storage.write_encrypted(self.tmp / "x", b"data")
            self.assertEqual(storage.read_file(path), b"data")


REPORT = {
    "pages": 30, "summary": "Ushlab turish muddati oshgan.", "timeline": ["F1"], "pii_counts": {}, "errors": [],
    "facts": [{"id": "F1", "type": "procedural_action", "page": 8, "date": "2026-03-18", "time": "09:30", "source": "Bayonnoma",
               "summary": "Qodirova Malika ushlab turildi", "quote": "soat 09:30 da", "verified": True, "verified_page": 8}],
    "findings": [
        {"kind": "procedural", "topic": "Ushlab turish muddati", "importance": "high", "pages": [8], "fact_ids": ["F1"],
         "explanation": "73 soat", "legal": {
             "verdict": "qonun_buzilishi", "assessment": "Qonunda «koʻpi bilan qirq sakkiz soat» [M1].",
             "correction_needed": False, "corrections": "", "defense_action": "Shikoyat qilish.",
             "verification": {"ok": True, "issues": []}, "skipped": False, "error": "",
             "sources": [{"key": "M1", "doc_title": "Jinoyat-protsessual kodeksi", "label": "226-modda. Ushlab turish muddati",
                          "lex_url": "https://lex.uz/uz/docs/-111460#-254639"},
                         {"key": "M2", "doc_title": "JPK", "label": "227-modda", "lex_url": "https://lex.uz/uz/docs/-111460#-1"}]}},
        {"kind": "contradiction", "topic": "Uchrashuv vaqti", "importance": "high", "pages": [5, 9], "fact_ids": ["F1"],
         "explanation": "14:00 va 19:30", "legal": {
             "verdict": "buzilish_ehtimoli", "assessment": "Iqtibossiz baho [M7].", "correction_needed": False,
             "corrections": "", "defense_action": "", "skipped": False, "error": "",
             "verification": {"ok": False, "issues": [{"severity": "error", "detail": "[M7] — bunday manba berilmagan"}]},
             "sources": []}},
    ],
}


@skipUnless((Path("C:/Windows/Fonts") / "times.ttf").exists(), "Times New Roman shrifti yo'q")
class ConfirmAndExportTests(CaseTestBase):
    def setUp(self):
        super().setUp()
        path = storage.write_encrypted(self.tmp / "case_runs" / "r.json", json.dumps(REPORT).encode())
        self.run_ = self.make_run(status=CaseRun.Status.DONE, report_path=path)

    def test_confirmation_info(self):
        data = self.client.get(f"/api/cases/{self.run_.id}/confirmation").json()
        self.assertIsNone(data["confirmed_at"])
        self.assertEqual([a["label"] for a in data["articles"]], ["226-modda. Ushlab turish muddati"])  # faqat keltirilgan
        self.assertEqual(data["articles"][0]["edition"], "joriy tahrir")
        self.assertEqual([u["topic"] for u in data["unverified"]], ["Uchrashuv vaqti"])

    def test_export_requires_confirmation(self):
        url = f"/cases/{self.run_.id}/export.docx"
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(f"/cases/{self.run_.id}/confirm").status_code, 400)  # belgisiz
        self.client.post(f"/cases/{self.run_.id}/confirm", {"acknowledged": "1"})
        self.run_.refresh_from_db()
        self.assertIsNotNone(self.run_.lawyer_confirmed_at)
        docx = self.client.get(url)
        self.assertEqual(docx.status_code, 200)
        self.assertTrue(docx.content.startswith(b"PK"))
        self.assertIn("attachment", docx["Content-Disposition"])
        pdf = self.client.get(f"/cases/{self.run_.id}/export.pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertEqual(self.client.get(f"/cases/{self.run_.id}/export.exe").status_code, 404)
        self.assertFalse(any((self.tmp).rglob("*.docx")) or any((self.tmp).rglob("*.pdf")))  # diskka yozilmaydi

    def test_document_content(self):
        from apps.cases.export import build_blocks, to_docx
        from django.utils import timezone
        blocks = build_blocks(REPORT, "Ish", "Test Advokat", timezone.now())
        text = "\n".join(b.text for b in blocks)
        self.assertIn("Test Advokat", text)
        self.assertIn("[226-modda]", text)            # [M1] -> modda nomi
        self.assertIn("TASDIQLANMAGAN", text)          # tekshiruvdan o'tmagan baho belgilangan
        self.assertIn("yuridik maslahat hisoblanmaydi", text)
        self.assertNotIn("227-modda", text)            # keltirilmagan manba ro'yxatga kirmaydi
        import docx, io
        paragraphs = [p.text for p in docx.Document(io.BytesIO(to_docx(blocks))).paragraphs]
        self.assertIn("Ish hujjatlari tahlili", paragraphs)

    def test_foreign_case_cannot_be_confirmed_or_exported(self):
        foreign = self.make_run(owner=self.other, status=CaseRun.Status.DONE, report_path=self.run_.report_path)
        self.assertEqual(self.client.post(f"/cases/{foreign.id}/confirm", {"acknowledged": "1"}).status_code, 404)
        self.assertEqual(self.client.get(f"/cases/{foreign.id}/export.pdf").status_code, 404)
        self.assertEqual(self.client.get(f"/api/cases/{foreign.id}/confirmation").status_code, 404)
