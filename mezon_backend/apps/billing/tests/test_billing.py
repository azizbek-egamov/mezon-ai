"""Tariflar va kvotalar (TZ §8.1, 11-bosqich)."""
import json
import shutil
import tempfile
from datetime import timedelta
from decimal import Decimal
from pathlib import Path
from unittest import mock

from cryptography.fernet import Fernet
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from django.utils.translation import override as lang_override

from apps.billing import quota
from apps.billing.models import ENTERPRISE, FREE, PRO, Payment, Plan, Subscription, UsageLog
from apps.cases import storage, worker
from apps.cases.models import CaseRun
from apps.cases.tests.test_views import CASE_PDF

User = get_user_model()


class BillingBase(TestCase):
    def setUp(self):
        self.user = User.objects.create_user("+998901112233", "Kuchli-parol-77", full_name="Test Advokat")
        self.free, self.pro, self.ent = (Plan.objects.get(code=c) for c in (FREE, PRO, ENTERPRISE))

    def grant(self, plan, days=None):
        return quota.activate_subscription(self.user, plan, days=days)


class DefaultPlansTests(BillingBase):
    def test_tz_values(self):
        self.assertEqual((self.free.lifetime_case_limit, self.free.max_pages_per_case, self.free.lifetime_chat_limit,
                          self.free.watermark), (1, 15, 3, True))
        self.assertEqual((self.pro.daily_case_limit, self.pro.monthly_case_limit, self.pro.max_pages_per_case,
                          self.pro.daily_chat_limit), (10, 300, 150, 100))
        self.assertEqual((self.ent.daily_case_limit, self.ent.max_pages_per_case, self.ent.priority_queue),
                         (35, 500, True))

    def test_default_is_free_and_staff_unlimited(self):
        self.assertEqual(quota.plan_for(self.user).code, FREE)
        staff = User.objects.create_user("+998901112244", "Kuchli-parol-77", full_name="Xodim", is_staff=True)
        self.assertEqual(quota.plan_for(staff).code, "UNLIMITED")
        with override_settings(BILLING_ENFORCED=False):
            self.assertEqual(quota.plan_for(self.user).code, "UNLIMITED")
            self.assertTrue(quota.reserve_case(self.user, 150).ok)


class CaseQuotaTests(BillingBase):
    def test_free_lifetime_one_case_and_page_limit(self):
        self.assertEqual(quota.reserve_case(self.user, 16).code, "pages")
        self.assertEqual(UsageLog.objects.count(), 0)          # rad etilgan urinish sarfni oshirmaydi
        self.assertTrue(quota.reserve_case(self.user, 15).ok)
        second = quota.reserve_case(self.user, 3)
        self.assertEqual((second.ok, second.code), (False, "lifetime"))
        self.assertIn("jami 1 ta", second.message)

    def test_pro_daily_and_monthly_limits(self):
        self.grant(self.pro)
        for _ in range(10):
            self.assertTrue(quota.reserve_case(self.user, 100).ok)
        blocked = quota.reserve_case(self.user, 100)
        self.assertEqual((blocked.ok, blocked.code), (False, "daily"))
        self.assertEqual(quota.reserve_case(self.user, 151).code, "pages")
        # oylik: oldingi kunlarga 295 ta yozamiz (bugun 10 ta) -> 305 > 300
        yesterday = timezone.localdate().replace(day=1)
        if yesterday == timezone.localdate():
            yesterday -= timedelta(days=1)   # oy 1-sanasida: o'tgan oy hisobga kirmaydi — sinov mantig'i uchun oraliq
        UsageLog.objects.filter(date=timezone.localdate()).update(cases_used=0)
        UsageLog.objects.create(user=self.user, date=yesterday, cases_used=300)
        if yesterday.month == timezone.localdate().month:
            self.assertEqual(quota.reserve_case(self.user, 10).code, "monthly")

    def test_expired_subscription_falls_back_to_free(self):
        sub = self.grant(self.pro, days=30)
        self.assertEqual(quota.plan_for(self.user).code, PRO)
        Subscription.objects.filter(pk=sub.pk).update(expires_at=timezone.now() - timedelta(seconds=1))
        self.assertEqual(quota.plan_for(self.user).code, FREE)

    def test_highest_plan_wins_and_renewal_extends(self):
        first = self.grant(self.pro, days=30)
        self.grant(self.ent, days=365)
        self.assertEqual(quota.plan_for(self.user).code, ENTERPRISE)
        renewed = self.grant(self.pro, days=30)    # mavjud faol Pro tugashidan keyin uzayadi
        self.assertEqual(renewed.expires_at, first.expires_at + timedelta(days=30))

    def test_refund_returns_quota(self):
        self.assertTrue(quota.reserve_case(self.user, 10).ok)
        quota.refund_case(self.user, 10)
        log = UsageLog.objects.get()
        self.assertEqual((log.cases_used, log.pages_processed), (0, 0))
        self.assertTrue(quota.reserve_case(self.user, 10).ok)

    def test_limits_editable_in_admin_data(self):
        Plan.objects.filter(code=FREE).update(lifetime_case_limit=None, daily_case_limit=2)   # TZ: admin paneldan
        self.assertTrue(quota.reserve_case(self.user, 5).ok)
        self.assertTrue(quota.reserve_case(self.user, 5).ok)
        self.assertEqual(quota.reserve_case(self.user, 5).code, "daily")


class ChatAndTemplateQuotaTests(BillingBase):
    def test_free_three_questions(self):
        self.assertTrue(all(quota.reserve_chat(self.user).ok for _ in range(3)))
        self.assertEqual(quota.reserve_chat(self.user).code, "lifetime")

    def test_pro_unlimited_templates_free_one_with_watermark(self):
        self.assertTrue(quota.reserve_template(self.user).ok)
        self.assertEqual(quota.reserve_template(self.user).code, "lifetime")
        self.assertTrue(quota.plan_for(self.user).watermark)
        self.grant(self.pro)
        self.assertTrue(all(quota.reserve_template(self.user).ok for _ in range(5)))

    def test_messages_follow_language(self):
        for _ in range(3):
            quota.reserve_chat(self.user)
        with lang_override("ru"):
            self.assertIn("Лимит вопросов", quota.reserve_chat(self.user).message)
        with lang_override("en"):
            self.assertIn("question limit", quota.reserve_chat(self.user).message)


class PaymentTests(BillingBase):
    def test_mark_paid_activates_once(self):
        payment = Payment.objects.create(user=self.user, plan=self.pro, provider=Payment.Provider.CLICK,
                                         amount_uzs=Decimal("199000"), external_id="CLK-1")
        sub = quota.mark_paid(payment)
        again = quota.mark_paid(payment)               # webhook takrorlansa ham bitta obuna
        self.assertEqual(sub.pk, again.pk)
        self.assertEqual(Subscription.objects.filter(user=self.user).count(), 1)
        payment.refresh_from_db()
        self.assertEqual((payment.status, quota.plan_for(self.user).code), (Payment.Status.PAID, PRO))
        self.assertEqual(sub.source, "PAYMENT")
        self.assertEqual((sub.expires_at - sub.started_at).days, 30)

    def test_grant_plan_command(self):
        call_command("grant_plan", "+998901112233", "PRO_MONTHLY", "--days", "7", stdout=mock.Mock())
        self.assertEqual(quota.plan_for(self.user).code, PRO)
        self.assertEqual((quota.current_subscription(self.user).expires_at - timezone.now()).days, 6)


class BillingPageTests(BillingBase):
    def test_page_and_api(self):
        self.client.force_login(self.user)
        quota.reserve_chat(self.user)
        html = self.client.get("/billing/").content.decode()
        self.assertIn("Bepul", html)
        self.assertIn("Pro (oylik)", html)
        self.assertIn("1 / 3", html)                    # savollar jami: 1 / 3
        data = self.client.get("/api/billing/usage").json()
        self.assertEqual((data["plan"], data["max_pages"]), (FREE, 15))
        self.assertIn({"label": "Savollar — jami", "used": 1, "limit": 3}, data["usage"])
        self.client.post("/i18n/set/", {"language": "ru"})
        self.assertIn("Бесплатный", self.client.get("/billing/").content.decode())

    def test_requires_login(self):
        self.assertEqual(self.client.get("/billing/").status_code, 302)
        self.assertEqual(self.client.get("/api/billing/usage").status_code, 401)


class EndpointEnforcementTests(BillingBase):
    def setUp(self):
        super().setUp()
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp, ignore_errors=True)
        override = override_settings(DATA_DIR=self.tmp, DATA_KEYS=[Fernet.generate_key().decode()])
        override.enable()
        self.addCleanup(override.disable)
        storage._fernet.cache_clear()
        self.addCleanup(storage._fernet.cache_clear)
        patcher = mock.patch("apps.cases.worker.enqueue")
        self.enqueue = patcher.start()
        self.addCleanup(patcher.stop)
        self.client.force_login(self.user)

    def upload(self, content=None):
        data = CASE_PDF.read_bytes() if content is None else content
        return self.client.post("/cases/upload", {"files": SimpleUploadedFile("ish.pdf", data)})

    def test_upload_blocked_by_free_page_limit_then_allowed_on_pro(self):
        resp = self.upload()                            # 30 varaq > Bepul 15
        self.assertIn("error=", resp["Location"])
        self.assertEqual(CaseRun.objects.count(), 0)
        self.grant(self.pro)
        self.assertEqual(self.upload().status_code, 302)
        self.assertEqual(CaseRun.objects.count(), 1)
        self.assertEqual(UsageLog.objects.get().pages_processed, 30)

    def test_failed_analysis_refunds_and_retry_reserves_again(self):
        self.grant(self.pro)
        self.upload()
        run = CaseRun.objects.get()
        with mock.patch("apps.cases.pipeline.analyze_pdf", side_effect=RuntimeError("API xatosi")):
            worker.process(str(run.id))
        run.refresh_from_db()
        self.assertEqual((run.status, run.quota_refunded), (CaseRun.Status.FAILED, True))
        self.assertEqual(UsageLog.objects.get().cases_used, 0)
        self.client.post(f"/cases/{run.id}/retry")
        run.refresh_from_db()
        self.assertEqual((run.status, run.quota_refunded), (CaseRun.Status.QUEUED, False))
        self.assertEqual(UsageLog.objects.get().cases_used, 1)

    def test_successful_analysis_records_cost(self):
        self.grant(self.pro)
        self.upload()
        run = CaseRun.objects.get()
        report = {"pages": 30, "cost_usd": 0.1234, "facts": [], "findings": [], "timeline": [], "summary": "ok"}
        with mock.patch("apps.cases.pipeline.analyze_pdf", return_value=report):
            worker.process(str(run.id))
        self.assertEqual(UsageLog.objects.get().llm_cost_usd, Decimal("0.1234"))

    def test_chat_blocked_after_free_questions(self):
        def ask():
            return self.client.post("/api/ask", json.dumps({"question": "Savol?"}), content_type="application/json")

        from apps.rag.tests.test_views import FakeLLM, fake_hits

        # Javob berilgan savollar kvotani yeydi (xato bilan tugaganlari qaytariladi — apps/api/tests/test_other_api.py)
        with mock.patch("apps.rag.views.search_aspects", side_effect=fake_hits), \
                mock.patch("apps.rag.views.get_llm", return_value=FakeLLM()):
            for _ in range(3):
                list(ask().streaming_content)
            blocked = ask()
        self.assertEqual(blocked.status_code, 429)
        self.assertIn("savol limiti", blocked.content.decode())

    def test_template_download_counts_but_preview_is_free(self):
        from apps.doc_builder.models import Category, DocumentTemplate

        template = DocumentTemplate.objects.create(
            title="Sinov", category=Category.OTHER, language="uz-Latn", description="x", is_published=True,
            form_schema=[{"name": "fio", "label": "F.I.Sh.", "type": "text", "required": True}],
            body="Hurmatli {{ fio }}!")
        url = f"/templates/{template.id}/"
        values = {"fio": "Karimov"}
        preview = self.client.post(url, {**values, "action": "preview"})
        self.assertEqual(preview.status_code, 200)
        self.assertEqual(UsageLog.objects.count(), 0)
        first = self.client.post(url, {**values, "action": "docx"})
        self.assertIn("attachment", first["Content-Disposition"])
        second = self.client.post(url, {**values, "action": "docx"})
        self.assertEqual(second.status_code, 200)
        self.assertIn("limiti tugadi", second.content.decode())   # forma xato bilan qaytadi, fayl emas
        self.assertNotIn("attachment", second.get("Content-Disposition", ""))


class QueuePriorityTests(BillingBase):
    def test_enterprise_jobs_run_first(self):
        other = User.objects.create_user("+998901112255", "Kuchli-parol-77", full_name="Boshqa")
        free_run = CaseRun.objects.create(owner=self.user, title="free")
        ent_run = CaseRun.objects.create(owner=other, title="ent")
        quota.activate_subscription(other, self.ent)
        with mock.patch.object(worker, "_thread", mock.Mock(is_alive=lambda: True)):
            worker._queue.queue.clear()
            worker.enqueue(free_run.id)
            worker.enqueue(ent_run.id)
            order = [worker._queue.get()[2], worker._queue.get()[2]]
        self.assertEqual(order, [str(ent_run.id), str(free_run.id)])
