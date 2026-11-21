"""/api/v1/admin/* — SuperAdmin panel (TZ §9.2): dashboard, foydalanuvchilar, tariflar, obunalar, to'lovlar,
AI xarajat radari, anti-fraud, lex.uz sinxronizatsiyasi, shablon moderatsiyasi, amallar jurnali.

Ruxsat: MODERATOR — shablonlar va sinxronizatsiya holati; qolgani — faqat SUPERADMIN (`permissions.py`).
Har bir o'zgartiruvchi amal `AuditEvent` ga yoziladi. Advokatlik siri: ish nomi/mazmuni admin javoblarida yo'q.
"""
import logging
import threading
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.translation import gettext as _
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.audit import audit
from apps.accounts.models import STAFF_ROLES, AuditEvent, Role, User
from apps.billing import quota
from apps.billing.models import Payment, Plan, Subscription, UsageLog
from apps.cases.models import CaseRun
from apps.doc_builder.models import DocumentTemplate
from apps.doc_builder.rendering import fill
from apps.lex_corpus.models import SyncRun

from .. import serializers as s
from .. import serializers_admin as a
from ..permissions import IsStaffRole, IsSuperAdmin
from .common import error, raise_form_errors

logger = logging.getLogger(__name__)
TAGS = ["admin"]
SYNC_STALE_HOURS = 6   # shundan uzoq "RUNNING" turgan yozuv — osilib qolgan deb hisoblanadi


def _money(value) -> float:
    return round(float(value or 0), 4)


# --- umumiy -----------------------------------------------------------------------------------------------------

class StaffMeView(APIView):
    permission_classes = [IsStaffRole]

    @extend_schema(responses=a.StaffMeSerializer, tags=TAGS)
    def get(self, request):
        return Response(a.StaffMeSerializer.for_user(request.user))


def cost_by_day(days: int = 30) -> list[dict]:
    """Kunlik AI xarajati (UsageLog: ish tahlili + savol-javob), ishlar va savollar soni."""
    since = timezone.localdate() - timedelta(days=days - 1)
    rows = {r["date"]: r for r in UsageLog.objects.filter(date__gte=since).values("date").annotate(
        usd=Sum("llm_cost_usd"), cases=Sum("cases_used"), chat=Sum("chat_questions"), pages=Sum("pages_processed"))}
    out = []
    for i in range(days):
        day = since + timedelta(days=i)
        r = rows.get(day, {})
        out.append({"date": day.isoformat(), "usd": _money(r.get("usd")), "cases": r.get("cases") or 0,
                    "chat": r.get("chat") or 0, "pages": r.get("pages") or 0})
    return out


def shared_ip_groups(min_accounts: int = 3) -> list[dict]:
    """Bitta IP dan ro'yxatdan o'tgan yoki kirgan ko'p akkaunt (anti-fraud, TZ §8.2 — hozircha oddiy qoida).
    Xodimlar (moderator, superadmin) hisobga olinmaydi — ofis IP si umumiy. Diqqat: NAT/advokatlik byurosi ortidagi
    halol foydalanuvchilar ham bitta IP da bo'lishi mumkin — bu signal, avtomatik bloklash emas."""
    users = User.objects.exclude(role__in=STAFF_ROLES).exclude(is_superuser=True)
    groups: dict[str, set] = {}
    for field in ("registered_ip", "last_login_ip"):
        for row in (users.exclude(**{f"{field}__isnull": True}).values(field)
                    .annotate(n=Count("id")).filter(n__gte=2)):
            ip = row[field]
            groups.setdefault(ip, set()).update(users.filter(**{field: ip}).values_list("id", flat=True))
    out = []
    for ip, ids in groups.items():
        if len(ids) < min_accounts:
            continue
        users = User.objects.filter(id__in=ids).order_by("date_joined")
        out.append({"ip": ip, "count": len(ids), "flagged": sum(u.is_fraud_flagged for u in users),
                    "accounts": [{"id": str(u.id), "phone_number": u.phone_number, "full_name": u.full_name,
                                  "role": u.role, "date_joined": u.date_joined, "is_fraud_flagged": u.is_fraud_flagged,
                                  "is_active": u.is_active} for u in users]})
    return sorted(out, key=lambda g: -g["count"])


class DashboardView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(responses=OpenApiTypes.OBJECT, tags=TAGS)
    def get(self, request):
        now = timezone.now()
        today = timezone.localdate()
        month_start = today.replace(day=1)
        users = User.objects.all()
        days = cost_by_day(30)
        last_sync = SyncRun.objects.first()
        return Response({
            "users": {
                "total": users.count(),
                "lawyers": users.filter(role=Role.LAWYER).count(),
                "clients": users.filter(role=Role.CLIENT).count(),
                "staff": users.filter(role__in=[Role.MODERATOR, Role.SUPERADMIN]).count(),
                "active_7d": users.filter(last_login__gte=now - timedelta(days=7)).count(),
                "new_today": users.filter(date_joined__date=today).count(),
                "flagged": users.filter(is_fraud_flagged=True).count(),
            },
            "subscriptions": list(Subscription.objects.filter(status=Subscription.Status.ACTIVE)
                                  .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now))
                                  .values("plan__code", "plan__name").annotate(count=Count("user", distinct=True))
                                  .order_by("plan__code")),
            "cases": {
                "today": CaseRun.objects.filter(created_at__date=today).count(),
                "month": CaseRun.objects.filter(created_at__date__gte=month_start).count(),
                "active": CaseRun.objects.filter(status__in=[CaseRun.Status.QUEUED, CaseRun.Status.RUNNING]).count(),
                "failed_today": CaseRun.objects.filter(created_at__date=today, status=CaseRun.Status.FAILED).count(),
            },
            "cost": {"today": days[-1]["usd"], "month": round(sum(d["usd"] for d in days if d["date"] >= month_start.isoformat()), 4),
                     "by_day": days},
            "chat_today": days[-1]["chat"],
            "payments_pending": Payment.objects.filter(status=Payment.Status.PENDING).count(),
            "fraud_signals": len(shared_ip_groups()),
            "last_sync": a.SyncRunSerializer(last_sync).data if last_sync else None,
            "recent_audit": a.AuditEventSerializer(AuditEvent.objects.select_related("actor")[:8], many=True).data,
        })


# --- foydalanuvchilar -------------------------------------------------------------------------------------------

class UserListView(generics.ListAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = a.AdminUserSerializer

    def get_queryset(self):
        qs = User.objects.annotate(cases_count=Count("case_runs")).order_by("-date_joined")
        p = self.request.query_params
        if q := p.get("q", "").strip():
            digits = "".join(ch for ch in q if ch.isdigit())
            qs = qs.filter(Q(full_name__icontains=q) | Q(advocate_license_no__icontains=q)
                           | (Q(phone_number__contains=digits) if digits else Q(pk__in=[])))
        if role := p.get("role"):
            qs = qs.filter(role=role)
        if p.get("flagged") in ("1", "true"):
            qs = qs.filter(is_fraud_flagged=True)
        if ip := p.get("ip"):
            qs = qs.filter(Q(registered_ip=ip) | Q(last_login_ip=ip))
        return qs

    @extend_schema(parameters=[OpenApiParameter("q", str), OpenApiParameter("role", str), OpenApiParameter("flagged", bool),
                               OpenApiParameter("ip", str)], tags=TAGS)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class UserDetailView(APIView):
    permission_classes = [IsSuperAdmin]

    def _user(self, user_id):
        return get_object_or_404(User.objects.annotate(cases_count=Count("case_runs")), pk=user_id)

    @extend_schema(responses=OpenApiTypes.OBJECT, tags=TAGS,
                   description="Profil, sarf, obunalar, to'lovlar, ishlar metama'lumoti, jurnal")
    def get(self, request, user_id):
        user = self._user(user_id)
        summary = quota.usage_summary(user)
        cost = UsageLog.objects.filter(user=user).aggregate(total=Sum("llm_cost_usd"))
        return Response({
            "user": a.AdminUserSerializer(user, context={"request": request}).data,
            "usage": [{"label": str(r["label"]), "used": r["used"], "limit": r["limit"]} for r in summary["rows"]],
            "max_pages": summary["max_pages"],
            "cost_total_usd": _money(cost["total"]),
            "subscriptions": a.SubscriptionSerializer(user.subscriptions.select_related("plan", "user")[:20], many=True).data,
            "payments": a.PaymentSerializer(user.payments.select_related("plan", "user")[:20], many=True).data,
            "cases": a.AdminCaseSerializer(user.case_runs.select_related("owner")[:20], many=True).data,
            "audit": a.AuditEventSerializer(AuditEvent.objects.filter(target=f"user:{user.pk}").select_related("actor")[:20],
                                            many=True).data,
        })

    @extend_schema(request=a.AdminUserSerializer, responses=a.AdminUserSerializer, tags=TAGS,
                   description="O'zgartirish mumkin: full_name, role, advocate_license_no, is_active, is_fraud_flagged")
    def patch(self, request, user_id):
        user = self._user(user_id)
        allowed = {k: v for k, v in request.data.items() if k in ("full_name", "role", "advocate_license_no", "is_active",
                                                                  "is_fraud_flagged")}
        serializer = a.AdminUserSerializer(user, data=allowed, partial=True, context={"request": request})
        serializer.is_valid(raise_exception=True)
        before = {k: getattr(user, k) for k in allowed}
        serializer.save()
        changed = {k: [before[k], getattr(user, k)] for k in allowed if before[k] != getattr(user, k) and k != "full_name"}
        if changed or "full_name" in allowed:
            audit(request, "user.update", f"user:{user.pk}", **changed)
        return Response(serializer.data)


class UserGrantView(APIView):
    """Obuna berish (qo'lda): tarif va muddat; shu tarifning faol obunasi bo'lsa — oxiridan uzaytiriladi."""
    permission_classes = [IsSuperAdmin]

    @extend_schema(request=a.GrantSerializer, responses={201: a.SubscriptionSerializer}, tags=TAGS)
    def post(self, request, user_id):
        user = get_object_or_404(User, pk=user_id)
        serializer = a.GrantSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        plan, days = serializer.validated_data["plan"], serializer.validated_data.get("days")
        sub = quota.activate_subscription(user, plan, days=days, source="ADMIN")
        audit(request, "subscription.grant", f"user:{user.pk}", plan=plan.code, days=days or plan.duration_days)
        return Response(a.SubscriptionSerializer(sub).data, status=status.HTTP_201_CREATED)


class SubscriptionListView(generics.ListAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = a.SubscriptionSerializer

    def get_queryset(self):
        qs = Subscription.objects.select_related("plan", "user")
        if self.request.query_params.get("current") in ("1", "true"):
            qs = qs.filter(status=Subscription.Status.ACTIVE).filter(
                Q(expires_at__isnull=True) | Q(expires_at__gt=timezone.now()))
        return qs

    @extend_schema(parameters=[OpenApiParameter("current", bool)], tags=TAGS)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SubscriptionCancelView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(request=None, responses=a.SubscriptionSerializer, tags=TAGS)
    def post(self, request, sub_id):
        sub = get_object_or_404(Subscription.objects.select_related("plan", "user"), pk=sub_id)
        if sub.status != Subscription.Status.CANCELED:
            sub.status = Subscription.Status.CANCELED
            sub.save(update_fields=["status"])
            audit(request, "subscription.cancel", f"user:{sub.user_id}", plan=sub.plan.code, subscription=sub.pk)
        return Response(a.SubscriptionSerializer(sub).data)


# --- tariflar ---------------------------------------------------------------------------------------------------

def _plans():
    now = timezone.now()
    active = Q(subscriptions__status=Subscription.Status.ACTIVE) & (
        Q(subscriptions__expires_at__isnull=True) | Q(subscriptions__expires_at__gt=now))
    # GROUP BY so'rovida Meta.ordering qo'llanmaydi — tartib aniq beriladi
    return (Plan.objects.annotate(subscribers=Count("subscriptions__user", filter=active, distinct=True))
            .order_by("sort_order", "id"))


class PlanListView(generics.ListCreateAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = a.AdminPlanSerializer
    pagination_class = None

    def get_queryset(self):
        quota.free_plan()
        return _plans()

    def perform_create(self, serializer):
        plan = serializer.save()
        audit(self.request, "plan.create", f"plan:{plan.code}")

    @extend_schema(tags=TAGS)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=TAGS)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PlanDetailView(generics.RetrieveUpdateAPIView):
    """Tarif konstruktori: limitlar, narx, muddat, faollik. O'chirish yo'q — `is_active=false` (obunalar saqlanadi)."""
    permission_classes = [IsSuperAdmin]
    serializer_class = a.AdminPlanSerializer
    lookup_url_kwarg = "plan_id"
    http_method_names = ["get", "patch"]

    def get_queryset(self):
        return _plans()

    def perform_update(self, serializer):
        before = {f: getattr(serializer.instance, f) for f in serializer.validated_data}
        plan = serializer.save()
        changed = {f: [str(before[f]), str(getattr(plan, f))] for f in before if before[f] != getattr(plan, f)}
        if changed:
            audit(self.request, "plan.update", f"plan:{plan.code}", **changed)

    @extend_schema(tags=TAGS)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=TAGS)
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


# --- to'lovlar --------------------------------------------------------------------------------------------------

class PaymentListView(generics.ListCreateAPIView):
    """To'lovlar; qo'lda yaratish (provider=MANUAL — naqd/bank o'tkazmasi), keyin "to'langan deb belgilash"."""
    permission_classes = [IsSuperAdmin]
    serializer_class = a.PaymentSerializer

    def get_queryset(self):
        qs = Payment.objects.select_related("user", "plan")
        if st := self.request.query_params.get("status"):
            qs = qs.filter(status=st)
        return qs

    def perform_create(self, serializer):
        payment = serializer.save()
        audit(self.request, "payment.create", f"user:{payment.user_id}", payment=payment.pk, plan=payment.plan.code,
              amount_uzs=str(payment.amount_uzs), provider=payment.provider)

    @extend_schema(parameters=[OpenApiParameter("status", str, enum=list(Payment.Status.values))], tags=TAGS)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=TAGS)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class PaymentMarkPaidView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(request=None, responses=a.PaymentSerializer, tags=TAGS,
                   description="To'lov tasdiqlandi → obuna yoqiladi (quota.mark_paid; takror chaqirish xavfsiz)")
    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, pk=payment_id)
        if payment.status in (Payment.Status.CANCELED, Payment.Status.FAILED):
            return error(_("Bekor qilingan toʻlovni tasdiqlab boʻlmaydi"), 409, "payment_closed")
        was_paid = payment.status == Payment.Status.PAID
        quota.mark_paid(payment)
        payment.refresh_from_db()
        if not was_paid:
            audit(request, "payment.mark_paid", f"user:{payment.user_id}", payment=payment.pk, plan=payment.plan.code)
        return Response(a.PaymentSerializer(payment).data)


class PaymentCancelView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(request=None, responses=a.PaymentSerializer, tags=TAGS)
    def post(self, request, payment_id):
        payment = get_object_or_404(Payment, pk=payment_id)
        if payment.status != Payment.Status.PENDING:
            return error(_("Faqat kutilayotgan toʻlovni bekor qilish mumkin"), 409, "payment_not_pending")
        payment.status = Payment.Status.CANCELED
        payment.save(update_fields=["status"])
        audit(request, "payment.cancel", f"user:{payment.user_id}", payment=payment.pk)
        return Response(a.PaymentSerializer(payment).data)


# --- xarajat radari va anti-fraud -------------------------------------------------------------------------------

class CostsView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(parameters=[OpenApiParameter("days", int, description="7–90, sukut 30")], responses=OpenApiTypes.OBJECT,
                   tags=TAGS)
    def get(self, request):
        try:
            days = min(max(int(request.query_params.get("days", 30)), 7), 90)
        except ValueError:
            days = 30
        since = timezone.localdate() - timedelta(days=days - 1)
        top = (UsageLog.objects.filter(date__gte=since).values("user", "user__phone_number", "user__full_name")
               .annotate(usd=Sum("llm_cost_usd"), cases=Sum("cases_used"), chat=Sum("chat_questions"))
               .filter(usd__gt=0).order_by("-usd")[:15])
        expensive = (CaseRun.objects.filter(created_at__date__gte=since, cost_usd__gt=0).select_related("owner")
                     .order_by("-cost_usd")[:15])
        return Response({
            "by_day": cost_by_day(days),
            "top_users": [{"user": str(r["user"]), "phone_number": r["user__phone_number"], "full_name": r["user__full_name"],
                           "usd": _money(r["usd"]), "cases": r["cases"] or 0, "chat": r["chat"] or 0} for r in top],
            "expensive_cases": a.AdminCaseSerializer(expensive, many=True).data,
        })


class AntiFraudView(APIView):
    permission_classes = [IsSuperAdmin]

    @extend_schema(parameters=[OpenApiParameter("min", int, description="Bitta IP dagi kamida akkaunt (sukut 3)")],
                   responses=OpenApiTypes.OBJECT, tags=TAGS)
    def get(self, request):
        try:
            min_accounts = max(int(request.query_params.get("min", 3)), 2)
        except ValueError:
            min_accounts = 3
        flagged = User.objects.filter(is_fraud_flagged=True).annotate(cases_count=Count("case_runs")).order_by("-date_joined")[:50]
        return Response({"shared_ips": shared_ip_groups(min_accounts),
                         "flagged": a.AdminUserSerializer(flagged, many=True, context={"request": request}).data})


# --- lex.uz sinxronizatsiyasi -----------------------------------------------------------------------------------

_sync_lock = threading.Lock()


def _sync_running() -> bool:
    cutoff = timezone.now() - timedelta(hours=SYNC_STALE_HOURS)
    return SyncRun.objects.filter(status=SyncRun.Status.RUNNING, started_at__gte=cutoff).exists()


def _run_sync_thread(days: int, check_codes: bool) -> None:
    from django.db import connection

    from apps.lex_corpus.sync import run_sync
    try:
        run_sync(days=days, check_codes=check_codes, log=logger.info)
    except Exception:
        logger.exception("Admin sinxronizatsiyasi xatosi")
    finally:
        connection.close()


class SyncListView(generics.ListAPIView):
    permission_classes = [IsStaffRole]
    serializer_class = a.SyncRunSerializer

    def get_queryset(self):
        return SyncRun.objects.all()

    @extend_schema(tags=TAGS)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SyncStartView(APIView):
    """Majburiy sinxronizatsiya (fonda). lex.uz dan yuklaydi va Qdrant indeksini yangilaydi — LLM chaqirmaydi."""
    permission_classes = [IsSuperAdmin]

    @extend_schema(request=OpenApiTypes.OBJECT, responses={202: s.DetailSerializer, 409: s.DetailSerializer}, tags=TAGS,
                   description='{"days": 7, "check_codes": false}')
    def post(self, request):
        try:
            days = min(max(int(request.data.get("days", 7)), 1), 365)
        except (TypeError, ValueError):
            days = 7
        check_codes = request.data.get("check_codes") in (True, "true", "1", 1)
        with _sync_lock:
            if _sync_running():
                return error(_("Sinxronizatsiya allaqachon bajarilmoqda"), 409, "sync_running")
            threading.Thread(target=_run_sync_thread, args=(days, check_codes), name="admin-sync", daemon=True).start()
        audit(request, "sync.start", "sync", days=days, check_codes=check_codes)
        return Response({"detail": _("Sinxronizatsiya boshlandi"), "code": "sync_started"}, status=status.HTTP_202_ACCEPTED)


# --- shablon moderatsiyasi --------------------------------------------------------------------------------------

class AdminTemplateListView(generics.ListCreateAPIView):
    permission_classes = [IsStaffRole]
    pagination_class = None

    def get_serializer_class(self):
        return a.AdminTemplateSerializer if self.request.method == "POST" else a.TemplateListItemSerializer

    def get_queryset(self):
        qs = DocumentTemplate.objects.select_related("approved_by")
        p = self.request.query_params
        if p.get("pending") in ("1", "true"):
            qs = qs.filter(approved_at__isnull=True)
        return qs

    def perform_create(self, serializer):
        template = serializer.save()
        audit(self.request, "template.create", f"template:{template.pk}", title=template.title)

    @extend_schema(parameters=[OpenApiParameter("pending", bool, description="Faqat tasdiqlanmaganlar")], tags=TAGS)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(request=a.AdminTemplateSerializer, responses={201: a.AdminTemplateSerializer}, tags=TAGS)
    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)


class AdminTemplateDetailView(generics.RetrieveUpdateAPIView):
    """Matn yoki sxema o'zgarsa — versiya oshadi va tasdiq bekor bo'ladi (DocumentTemplate.save)."""
    permission_classes = [IsStaffRole]
    serializer_class = a.AdminTemplateSerializer
    lookup_url_kwarg = "template_id"
    http_method_names = ["get", "patch"]
    queryset = DocumentTemplate.objects.select_related("approved_by")

    def perform_update(self, serializer):
        old_version = serializer.instance.version
        template = serializer.save()
        audit(self.request, "template.update", f"template:{template.pk}", fields=sorted(serializer.validated_data),
              version=[old_version, template.version])

    @extend_schema(tags=TAGS)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

    @extend_schema(tags=TAGS)
    def patch(self, request, *args, **kwargs):
        return super().patch(request, *args, **kwargs)


class AdminTemplateApproveView(APIView):
    permission_classes = [IsStaffRole]

    @extend_schema(request=None, responses=a.AdminTemplateSerializer, tags=TAGS,
                   description="Joriy versiyani tasdiqlash va e'lon qilish (yurist-moderator)")
    def post(self, request, template_id):
        template = get_object_or_404(DocumentTemplate, pk=template_id)
        with transaction.atomic():
            DocumentTemplate.objects.filter(pk=template.pk).update(approved_by=request.user, approved_at=timezone.now(),
                                                                   is_published=True)
        template.refresh_from_db()
        audit(request, "template.approve", f"template:{template.pk}", version=template.version)
        return Response(a.AdminTemplateSerializer(template).data)


class AdminTemplatePreviewView(APIView):
    """Moderator e'lon qilinmagan shablonni ham sinab ko'radi (kvota olinmaydi, ma'lumot saqlanmaydi)."""
    permission_classes = [IsStaffRole]

    @extend_schema(request=s.TemplateValuesSerializer, responses=s.PreviewSerializer, tags=TAGS)
    def post(self, request, template_id):
        template = get_object_or_404(DocumentTemplate, pk=template_id)
        values = request.data.get("values") if isinstance(request.data.get("values"), dict) else {}
        form, blocks = fill(template, {k: "" if v is None else str(v) for k, v in values.items()})
        if blocks is None:
            raise_form_errors(form)
        return Response({"blocks": [{"kind": b.kind, "text": b.text} for b in blocks]})


# --- jurnal -----------------------------------------------------------------------------------------------------

class AuditListView(generics.ListAPIView):
    permission_classes = [IsSuperAdmin]
    serializer_class = a.AuditEventSerializer

    def get_queryset(self):
        qs = AuditEvent.objects.select_related("actor")
        p = self.request.query_params
        if action := p.get("action"):
            qs = qs.filter(action__startswith=action)
        if target := p.get("target"):
            qs = qs.filter(target=target)
        return qs

    @extend_schema(parameters=[OpenApiParameter("action", str), OpenApiParameter("target", str)], tags=TAGS)
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)

