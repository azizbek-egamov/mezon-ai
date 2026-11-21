import json
import shutil
import tempfile
from pathlib import Path
from unittest import mock, skipUnless

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

from apps.cases import storage
from apps.cases.models import CaseRun
from apps.cases.tests.test_views import CASE_PDF, REPORT


def bearer(client: APIClient, user) -> APIClient:
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {RefreshToken.for_user(user).access_token}")
    return client


@override_settings(BILLING_ENFORCED=False)
class CaseApiTests(TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        override = override_settings(DATA_DIR=self.tmp, DATA_KEYS=[Fernet.generate_key().decode()])
        override.enable()
        self.addCleanup(override.disable)
        storage._fernet.cache_clear()
        self.addCleanup(storage._fernet.cache_clear)
        patcher = mock.patch("apps.cases.worker.enqueue")   # fon oqimi va API ishga tushmasin
        self.enqueue = patcher.start()
        self.addCleanup(patcher.stop)
        User = get_user_model()
        self.user = User.objects.create_user("+998901112233", "Kuchli-parol-77", full_name="Test Advokat")
        self.other = User.objects.create_user("+998907778899", "Boshqa-parol-77", full_name="Boshqa Advokat")
        self.client = bearer(APIClient(), self.user)

    def make_run(self, owner=None, **kw):
        return CaseRun.objects.create(owner=owner or self.user, title=kw.pop("title", "t"), pdf_path=str(CASE_PDF),
                                      pages=30, **kw)

    def done_run(self, **kw):
        path = storage.write_encrypted(self.tmp / "case_runs" / f"{len(kw)}.json", json.dumps(REPORT).encode())
        return self.make_run(status=CaseRun.Status.DONE, report_path=path, **kw)

    def upload(self, *files, **data):
        files = files or (SimpleUploadedFile("ish.pdf", CASE_PDF.read_bytes(), "application/pdf"),)
        return self.client.post("/api/v1/cases/", {"files": list(files), **data}, format="multipart")

    def test_upload_creates_run(self):
        resp = self.upload(title="Sintetik ish", category="criminal", zero_retention="true")
        self.assertEqual(resp.status_code, 201, resp.content)
        data = resp.json()
        run = CaseRun.objects.get(pk=data["id"])
        self.assertEqual((run.owner, run.title, run.pages, run.zero_retention), (self.user, "Sintetik ish", 30, True))
        self.assertEqual(data["status"], "QUEUED")
        self.assertEqual(data["sources"][0]["name"], "ish.pdf")
        self.enqueue.assert_called_once_with(run.id)

    def test_upload_validation(self):
        self.assertEqual(self.client.post("/api/v1/cases/", {}, format="multipart").json()["code"], "no_files")
        self.assertEqual(self.upload(category="nomalum").json()["code"], "category")
        bad = SimpleUploadedFile("bu.pdf", b"bu pdf emas", "application/pdf")
        self.assertEqual(self.upload(bad).status_code, 400)
        self.assertFalse(CaseRun.objects.exists())

    @override_settings(BILLING_ENFORCED=True)
    def test_upload_quota_is_429(self):
        resp = self.upload()   # bepul tarif: 15 varaq, ish 30 varaq
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.json()["code"], "quota_pages")

    def test_list_is_paginated_and_private(self):
        mine = self.make_run(title="meniki")
        self.make_run(owner=self.other, title="begona")
        data = self.client.get("/api/v1/cases/").json()
        self.assertEqual(data["count"], 1)
        self.assertEqual(data["results"][0]["id"], str(mine.id))
        foreign = self.make_run(owner=self.other)
        # model nomi oshkor qilinmaydi
        self.assertEqual(self.client.get(f"/api/v1/cases/{foreign.id}").json(), {"detail": "Topilmadi", "code": "not_found"})
        for url in ("", "/report", "/pdf", "/confirmation", "/export/docx"):
            self.assertEqual(self.client.get(f"/api/v1/cases/{foreign.id}{url}").status_code, 404, url)
        self.assertEqual(self.client.delete(f"/api/v1/cases/{foreign.id}").status_code, 404)

    def test_options(self):
        data = self.client.get("/api/v1/cases/options").json()
        self.assertIn("criminal", [t["code"] for t in data["case_types"]])
        self.assertEqual(data["max_files"], 20)
        self.assertEqual(data["server_max_pages"], 200)

    @override_settings(BILLING_ENFORCED=True)
    def test_options_reflects_user_plan_limit(self):
        data = self.client.get("/api/v1/cases/options").json()
        self.assertEqual(data["plan_code"], "FREE")
        self.assertEqual(data["max_pages"], 15)
        self.assertEqual(data["server_max_pages"], 200)
        self.assertEqual(data["cases_remaining"], 1)
        self.assertFalse(data["cases_exhausted"])

    def test_report_and_pdf(self):
        queued = self.make_run()
        self.assertEqual(self.client.get(f"/api/v1/cases/{queued.id}/report").status_code, 409)
        run = self.done_run()
        resp = self.client.get(f"/api/v1/cases/{run.id}/report")
        self.assertEqual(resp.json()["summary"], REPORT["summary"])
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        resp = self.client.get(f"/api/v1/cases/{run.id}/pdf", HTTP_ACCEPT="application/pdf")
        self.assertEqual((resp.status_code, resp["Content-Type"]), (200, "application/pdf"))
        self.assertEqual(b"".join(resp.streaming_content), CASE_PDF.read_bytes())
        CaseRun.objects.filter(pk=run.pk).update(pdf_path="")
        self.assertEqual(self.client.get(f"/api/v1/cases/{run.id}/pdf").json()["code"], "pdf_deleted")

    @skipUnless((Path("C:/Windows/Fonts") / "times.ttf").exists(), "Times New Roman shrifti yo'q")
    def test_confirm_then_export(self):
        run = self.done_run()
        self.assertEqual(self.client.get(f"/api/v1/cases/{run.id}/export/docx").status_code, 403)
        info = self.client.get(f"/api/v1/cases/{run.id}/confirmation").json()
        self.assertIsNone(info["confirmed_at"])
        url = f"/api/v1/cases/{run.id}/confirmation"
        self.assertEqual(self.client.post(url, {}, format="json").json()["code"], "not_acknowledged")
        resp = self.client.post(url, {"acknowledged": True}, format="json")
        self.assertIsNotNone(resp.json()["confirmed_at"])
        for fmt in ("docx", "pdf"):
            resp = self.client.get(f"/api/v1/cases/{run.id}/export/{fmt}")
            self.assertEqual(resp.status_code, 200, fmt)
            self.assertIn(f".{fmt}", resp["Content-Disposition"])
            self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertEqual(self.client.get(f"/api/v1/cases/{run.id}/export/txt").status_code, 404)

    def test_delete_and_retry(self):
        running = self.make_run(status=CaseRun.Status.RUNNING)
        self.assertEqual(self.client.delete(f"/api/v1/cases/{running.id}").json()["code"], "running")
        self.assertEqual(self.client.post(f"/api/v1/cases/{running.id}/retry").json()["code"], "not_failed")
        failed = self.make_run(status=CaseRun.Status.FAILED, error="xato")
        resp = self.client.post(f"/api/v1/cases/{failed.id}/retry")
        self.assertEqual((resp.status_code, resp.json()["status"]), (200, "QUEUED"))
        self.enqueue.assert_called_once_with(failed.id)
        path = storage.write_encrypted(self.tmp / "uploads" / "x.pdf", b"%PDF")
        done = self.done_run(title="o'chiriladi")
        CaseRun.objects.filter(pk=done.pk).update(pdf_path=path)
        report = Path(done.report_path)
        self.assertEqual(self.client.delete(f"/api/v1/cases/{done.id}").status_code, 204)
        self.assertFalse(CaseRun.objects.filter(pk=done.pk).exists())
        self.assertFalse(Path(path).exists() or report.exists())
