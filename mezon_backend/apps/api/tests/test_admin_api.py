from datetime import timedelta
from decimal import Decimal
from unittest import mock

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import AuditEvent, Role
from apps.api.tests.test_cases_api import bearer
from apps.billing import quota
from apps.billing.models import Payment, Plan, UsageLog
from apps.cases.models import CaseRun
from apps.doc_builder.models import DocumentTemplate
from apps.lex_corpus.models import SyncRun
from apps.rag.tests.test_views import FakeLLM, fake_hits, parse_sse

PASSWORD = "Kuchli-parol-77"


class AdminTestBase(TestCase):
    def setUp(self):
        cache.clear()
        User = get_user_model()
        self.admin_user = User.objects.create_user("+998900000001", PASSWORD, full_name="Bosh Admin",
                                                   role=Role.SUPERADMIN, is_staff=True)
        self.moderator = User.objects.create_user("+998900000002", PASSWORD, full_name="Yurist Moderator",
                                                  role=Role.MODERATOR, is_staff=True)
        self.lawyer = User.objects.create_user("+998900000003", PASSWORD, full_name="Oddiy Advokat", role=Role.LAWYER)
        self.admin = bearer(APIClient(), self.admin_user)
        self.mod = bearer(APIClient(), self.moderator)
        self.law = bearer(APIClient(), self.lawyer)


class PermissionTests(AdminTestBase):
    def test_roles(self):
        self.assertEqual(self.law.get("/api/v1/admin/dashboard").status_code, 403)
        self.assertEqual(self.law.get("/api/v1/admin/templates/").status_code, 403)
        self.assertEqual(self.mod.get("/api/v1/admin/templates/").status_code, 200)
        self.assertEqual(self.mod.get("/api/v1/admin/sync/").status_code, 200)
        for url in ("/api/v1/admin/dashboard", "/api/v1/admin/users/", "/api/v1/admin/plans/", "/api/v1/admin/payments/",
                    "/api/v1/admin/costs", "/api/v1/admin/antifraud", "/api/v1/admin/audit/"):
            self.assertEqual(self.mod.get(url).status_code, 403, url)
            self.assertEqual(self.admin.get(url).status_code, 200, url)
        self.assertEqual(self.mod.get("/api/v1/admin/me").json(), {"is_staff_role": True, "is_superadmin": False})
        self.assertEqual(APIClient().get("/api/v1/admin/me").status_code, 401)


class UserAdminTests(AdminTestBase):
    def test_list_search_and_detail_hide_case_titles(self):
        CaseRun.objects.create(owner=self.lawyer, title="Mijoz Karimov ishi", pages=12, cost_usd=Decimal("0.2"))
        data = self.admin.get("/api/v1/admin/users/?q=90 000 00 03").json()
        self.assertEqual([u["full_name"] for u in data["results"]], ["Oddiy Advokat"])
        self.assertEqual(data["results"][0]["cases_count"], 1)
        self.assertEqual(self.admin.get("/api/v1/admin/users/?role=MODERATOR").json()["count"], 1)
        detail = self.admin.get(f"/api/v1/admin/users/{self.lawyer.pk}").json()
        self.assertEqual(detail["user"]["plan"], "FREE")
        self.assertEqual(detail["cases"][0]["pages"], 12)
        self.assertNotIn("title", detail["cases"][0])   # advokatlik siri
        self.assertNotIn("Karimov", str(detail))

    def test_patch_role_and_flag_is_audited(self):
        resp = self.admin.patch(f"/api/v1/admin/users/{self.lawyer.pk}", {"role": "MODERATOR", "is_fraud_flagged": True,
                                                                         "phone_number": "+998911111111"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.lawyer.refresh_from_db()
        self.assertEqual((self.lawyer.role, self.lawyer.is_staff, self.lawyer.is_fraud_flagged), ("MODERATOR", True, True))
        self.assertEqual(self.lawyer.phone_number, "+998900000003")   # telefon o'zgarmaydi
        event = AuditEvent.objects.get(action="user.update")
        self.assertEqual((event.actor, event.target), (self.admin_user, f"user:{self.lawyer.pk}"))
        self.assertEqual(event.details["role"], ["LAWYER", "MODERATOR"])

    def test_guards(self):
        own = self.admin.patch(f"/api/v1/admin/users/{self.admin_user.pk}", {"is_active": False}, format="json")
        self.assertEqual(own.status_code, 400)
        resp = self.admin.patch(f"/api/v1/admin/users/{self.lawyer.pk}", {"role": "SUPERADMIN"}, format="json")
        self.assertEqual(resp.status_code, 400)   # superadminni faqat Django superuser beradi

    @override_settings(BILLING_ENFORCED=True)
    def test_grant_and_cancel_subscription(self):
        resp = self.admin.post(f"/api/v1/admin/users/{self.lawyer.pk}/subscriptions", {"plan": "PRO_MONTHLY", "days": 10},
                               format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(quota.plan_for(self.lawyer).code, "PRO_MONTHLY")
        sub_id = resp.json()["id"]
        self.assertEqual(self.admin.post(f"/api/v1/admin/subscriptions/{sub_id}/cancel").json()["status"], "CANCELED")
        self.assertEqual(quota.plan_for(self.lawyer).code, "FREE")
        self.assertEqual(list(AuditEvent.objects.values_list("action", flat=True).order_by("created_at")),
                         ["subscription.grant", "subscription.cancel"])


class PlanAndPaymentTests(AdminTestBase):
    def test_plan_constructor(self):
        plans = self.admin.get("/api/v1/admin/plans/").json()
        self.assertEqual([p["code"] for p in plans], ["FREE", "PRO_MONTHLY", "ENTERPRISE_YEARLY"])   # sort_order
        resp = self.admin.post("/api/v1/admin/plans/", {"code": "trial_week", "name": "Sinov haftasi", "duration_days": 7,
                                                        "daily_case_limit": 2, "max_pages_per_case": 30}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        self.assertEqual(resp.json()["code"], "TRIAL_WEEK")
        plan_id = resp.json()["id"]
        resp = self.admin.patch(f"/api/v1/admin/plans/{plan_id}", {"price_uzs": 99000, "code": "OTHER"}, format="json")
        self.assertEqual(resp.status_code, 400)   # kod o'zgarmaydi
        resp = self.admin.patch(f"/api/v1/admin/plans/{plan_id}", {"price_uzs": 99000, "is_active": False}, format="json")
        self.assertEqual((resp.json()["price_uzs"], resp.json()["is_active"]), (99000, False))
        self.assertEqual(AuditEvent.objects.filter(action="plan.update").count(), 1)

    @override_settings(BILLING_ENFORCED=True)
    def test_manual_payment_flow(self):
        resp = self.admin.post("/api/v1/admin/payments/", {"user": str(self.lawyer.pk), "plan_code": "PRO_MONTHLY",
                                                           "provider": "MANUAL", "amount_uzs": 490000}, format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        pid = resp.json()["id"]
        self.assertEqual(self.admin.get("/api/v1/admin/payments/?status=PENDING").json()["count"], 1)
        paid = self.admin.post(f"/api/v1/admin/payments/{pid}/mark-paid").json()
        self.assertEqual(paid["status"], "PAID")
        self.assertEqual(quota.plan_for(self.lawyer).code, "PRO_MONTHLY")
        self.admin.post(f"/api/v1/admin/payments/{pid}/mark-paid")   # takror — yangi obuna yaratilmaydi
        self.assertEqual(self.lawyer.subscriptions.count(), 1)
        self.assertEqual(self.admin.post(f"/api/v1/admin/payments/{pid}/cancel").status_code, 409)
        other = Payment.objects.create(user=self.lawyer, plan=Plan.objects.get(code="PRO_MONTHLY"), provider="MANUAL",
                                       amount_uzs=1, status=Payment.Status.CANCELED)
        self.assertEqual(self.admin.post(f"/api/v1/admin/payments/{other.pk}/mark-paid").status_code, 409)


class RadarTests(AdminTestBase):
    def test_costs_and_dashboard(self):
        today = timezone.localdate()
        UsageLog.objects.create(user=self.lawyer, date=today, llm_cost_usd=Decimal("0.75"), cases_used=2, chat_questions=3)
        UsageLog.objects.create(user=self.lawyer, date=today - timedelta(days=40), llm_cost_usd=Decimal("9"))
        CaseRun.objects.create(owner=self.lawyer, title="maxfiy", pages=40, cost_usd=Decimal("0.5"))
        costs = self.admin.get("/api/v1/admin/costs?days=30").json()
        self.assertEqual(len(costs["by_day"]), 30)
        self.assertEqual(costs["by_day"][-1], {"date": today.isoformat(), "usd": 0.75, "cases": 2, "chat": 3, "pages": 0})
        self.assertEqual(costs["top_users"][0]["usd"], 0.75)   # 40 kun oldingisi kirmaydi
        self.assertNotIn("title", costs["expensive_cases"][0])
        self.admin.post(f"/api/v1/admin/users/{self.lawyer.pk}/subscriptions", {"plan": "PRO_MONTHLY", "days": 10}, format="json")
        dash = self.admin.get("/api/v1/admin/dashboard").json()
        self.assertEqual(dash["users"]["total"], 3)
        # admin panel tarifni kod emas, nomi bilan ko'rsatadi
        sub = next(s for s in dash["subscriptions"] if s["plan__code"] == "PRO_MONTHLY")
        self.assertEqual((sub["count"], bool(sub["plan__name"])), (1, True))
        self.assertEqual(dash["cost"]["today"], 0.75)
        self.assertEqual(dash["cases"]["today"], 1)

    def test_antifraud_shared_ip(self):
        User = get_user_model()
        for i in range(3):
            User.objects.create_user(f"+99893000000{i}", PASSWORD, full_name=f"Shubhali {i}", registered_ip="10.0.0.7")
        get_user_model().objects.filter(role__in=["MODERATOR", "SUPERADMIN"]).update(registered_ip="10.0.0.9")
        data = self.admin.get("/api/v1/admin/antifraud?min=2").json()
        self.assertEqual([(g["ip"], g["count"]) for g in data["shared_ips"]], [("10.0.0.7", 3)])   # xodimlar radarda yo'q
        self.assertEqual(self.admin.get("/api/v1/admin/antifraud?min=4").json()["shared_ips"], [])
        self.assertEqual(self.admin.get("/api/v1/admin/users/?ip=10.0.0.7").json()["count"], 3)

    def test_login_and_register_record_ip(self):
        client = APIClient(REMOTE_ADDR="10.1.2.3")
        client.post("/api/v1/auth/register", {"phone_number": "+998945556677", "full_name": "Yangi", "role": "CLIENT",
                                              "password1": PASSWORD, "password2": PASSWORD, "consent": True}, format="json")
        user = get_user_model().objects.get(phone_number="+998945556677")
        self.assertEqual((user.registered_ip, user.last_login_ip), ("10.1.2.3", "10.1.2.3"))
        APIClient(REMOTE_ADDR="10.9.9.9").post("/api/v1/auth/login", {"phone_number": "+998945556677", "password": PASSWORD},
                                               format="json")
        user.refresh_from_db()
        self.assertEqual((user.registered_ip, user.last_login_ip), ("10.1.2.3", "10.9.9.9"))

    @override_settings(BILLING_ENFORCED=False)
    @mock.patch("apps.rag.views.get_llm", return_value=FakeLLM())
    @mock.patch("apps.rag.views.search_aspects", side_effect=fake_hits)
    def test_chat_cost_is_recorded(self, _search, _llm):
        resp = self.law.post("/api/v1/chat/ask", {"question": "Firibgarlik nima?"}, format="json")
        parse_sse(b"".join(resp.streaming_content).decode())
        self.assertEqual(UsageLog.objects.get(user=self.lawyer).llm_cost_usd, Decimal("0.0010"))


class SyncAdminTests(AdminTestBase):
    @mock.patch("apps.api.views.admin.threading.Thread")
    def test_start_sync(self, thread):
        self.assertEqual(self.mod.post("/api/v1/admin/sync/start", {}, format="json").status_code, 403)
        resp = self.admin.post("/api/v1/admin/sync/start", {"days": 3}, format="json")
        self.assertEqual(resp.status_code, 202)
        self.assertEqual(thread.call_args.kwargs["args"], (3, False))
        thread.return_value.start.assert_called_once()
        SyncRun.objects.create()   # RUNNING
        self.assertEqual(self.admin.post("/api/v1/admin/sync/start", {}, format="json").json()["code"], "sync_running")
        runs = self.mod.get("/api/v1/admin/sync/").json()["results"]
        self.assertEqual(runs[0]["status"], "RUNNING")


class TemplateModerationTests(AdminTestBase):
    SCHEMA = [{"name": "fio", "label": "F.I.Sh.", "type": "text"}]

    def test_create_validate_edit_approve_preview(self):
        bad = self.mod.post("/api/v1/admin/templates/", {"title": "X", "category": "MOTION", "form_schema": self.SCHEMA,
                                                         "body": "{{ yoq_maydon }}"}, format="json")
        self.assertEqual(bad.status_code, 400)
        self.assertIn("body", bad.json())
        resp = self.mod.post("/api/v1/admin/templates/", {"title": "Iltimosnoma", "category": "MOTION",
                                                          "form_schema": self.SCHEMA, "body": "## ILTIMOSNOMA\n{{ fio }}"},
                             format="json")
        self.assertEqual(resp.status_code, 201, resp.content)
        tid = resp.json()["id"]
        # e'lon qilinmagan — foydalanuvchiga ko'rinmaydi, moderator sinab ko'radi
        self.assertEqual(self.law.get("/api/v1/templates/").json(), [])
        preview = self.mod.post(f"/api/v1/admin/templates/{tid}/preview", {"values": {"fio": "Aliyev"}}, format="json")
        self.assertEqual(preview.json()["blocks"][1], {"kind": "p", "text": "Aliyev"})
        approved = self.mod.post(f"/api/v1/admin/templates/{tid}/approve").json()
        self.assertTrue(approved["is_published"] and approved["approved_at"])
        self.assertEqual(approved["approved_by_name"], "Yurist Moderator")
        edited = self.mod.patch(f"/api/v1/admin/templates/{tid}", {"body": "## ILTIMOSNOMA\n{{ fio }}, {{ bugun }}"},
                                format="json").json()
        self.assertEqual((edited["version"], edited["approved_at"]), (2, None))   # yangi versiya — qayta tasdiq
        self.assertEqual(DocumentTemplate.objects.get(pk=tid).version, 2)
        self.assertEqual(self.mod.get("/api/v1/admin/templates/?pending=1").json()[0]["id"], tid)
        self.assertEqual(AuditEvent.objects.filter(target=f"template:{tid}").count(), 3)
