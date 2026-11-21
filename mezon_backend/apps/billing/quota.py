"""Tarif va kvotalar mantiqi (TZ §8.1).

    plan_for(user)            — joriy tarif (faol obuna, aks holda FREE; xodim/superadmin — cheksiz)
    reserve_case(user, pages) — ish tahlili boshlashdan oldin: sahifalar va kunlik/oylik/umrbod limit; o'tsa sarfni oshiradi
    refund_case(user, pages)  — tahlil bizning xatomiz bilan tugasa kvota qaytariladi
    reserve_chat / reserve_template — huquqiy savol va shablonni DOCX/PDF yuklab olish
    record_cost(user, usd)    — tahlil narxi (billing_user_quota_log.llm_cost_usd)

`settings.BILLING_ENFORCED=False` (env BILLING_ENFORCED=0) — kvotalar o'chiriladi (ichki sinov).
Limit tekshiruvi va sarfni oshirish bitta tranzaksiyada (parallel so'rovlar limitdan oshirib yubormasin).
"""
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.db.models import F, Q, Sum
from django.db.models.functions import Greatest
from django.utils import timezone
from django.utils.translation import gettext as _

from .models import ENTERPRISE, FREE, PRO, STUDENT, Plan, Subscription, UsageLog

# TZ §8.1 boshlang'ich qiymatlari (24 GB server uchun taklif); Admin paneldan o'zgartiriladi.
DEFAULT_PLANS = {
    FREE: dict(name="Bepul", sort_order=0, lifetime_case_limit=1, max_pages_per_case=15, lifetime_chat_limit=3,
               lifetime_template_limit=1, watermark=True),
    STUDENT: dict(name="Talaba (oylik)", sort_order=5, duration_days=30, daily_case_limit=5, monthly_case_limit=150,
                  max_pages_per_case=50, daily_chat_limit=30, daily_template_limit=5, watermark=False, price_uzs=49000),
    PRO: dict(name="Pro (oylik)", sort_order=10, duration_days=30, daily_case_limit=10, monthly_case_limit=300,
              max_pages_per_case=150, daily_chat_limit=100),
    ENTERPRISE: dict(name="Enterprise (yillik)", sort_order=20, duration_days=365, daily_case_limit=35,
                     max_pages_per_case=500, priority_queue=True),
}

# kind -> (UsageLog maydoni, [(Plan maydoni, qamrov)])
LIMITS = {
    "case": ("cases_used", [("daily_case_limit", "daily"), ("monthly_case_limit", "monthly"),
                            ("lifetime_case_limit", "lifetime")]),
    "chat": ("chat_questions", [("daily_chat_limit", "daily"), ("lifetime_chat_limit", "lifetime")]),
    "template": ("templates_used", [("daily_template_limit", "daily"), ("lifetime_template_limit", "lifetime")]),
}


@dataclass
class Decision:
    ok: bool
    code: str = ""          # "" | pages | daily | monthly | lifetime
    message: str = ""
    plan: Plan | None = None


def _message(kind: str, scope: str, limit: int) -> str:
    texts = {
        ("case", "daily"): _("Kunlik ish tahlili limiti tugadi (%(limit)s ta). Ertaga qayta urinib koʻring yoki yuqoriroq tarifga oʻting."),
        ("case", "monthly"): _("Oylik ish tahlili limiti tugadi (%(limit)s ta). Keyingi oyda qayta urinib koʻring yoki yuqoriroq tarifga oʻting."),
        ("case", "lifetime"): _("Bu tarifdagi ish tahlili limiti tugadi (jami %(limit)s ta). Davom etish uchun obuna rasmiylashtiring."),
        ("chat", "daily"): _("Kunlik savol limiti tugadi (%(limit)s ta). Ertaga qayta urinib koʻring yoki yuqoriroq tarifga oʻting."),
        ("chat", "lifetime"): _("Bu tarifdagi savol limiti tugadi (jami %(limit)s ta). Davom etish uchun obuna rasmiylashtiring."),
        ("template", "daily"): _("Kunlik hujjat yuklab olish limiti tugadi (%(limit)s ta). Ertaga qayta urinib koʻring yoki yuqoriroq tarifga oʻting."),
        ("template", "lifetime"): _("Bu tarifdagi hujjat yuklab olish limiti tugadi (jami %(limit)s ta). Davom etish uchun obuna rasmiylashtiring."),
    }
    return texts[(kind, scope)] % {"limit": limit}


def free_plan() -> Plan:
    plan, _created = Plan.objects.get_or_create(code=FREE, defaults=DEFAULT_PLANS[FREE])
    return plan


def unlimited_plan() -> Plan:
    """Saqlanmaydigan tarif: xodim/superadmin va kvotalar o'chirilgan rejim uchun."""
    return Plan(code="UNLIMITED", name="Unlimited", max_pages_per_case=settings.CASE_MAX_PAGES, priority_queue=True)


def is_exempt(user) -> bool:
    return (not settings.BILLING_ENFORCED or user.is_staff or user.is_superuser
            or getattr(user, "role", "") == "SUPERADMIN")


def current_subscription(user) -> Subscription | None:
    now = timezone.now()
    subs = (Subscription.objects.filter(user=user, status=Subscription.Status.ACTIVE)
            .filter(Q(expires_at__isnull=True) | Q(expires_at__gt=now)).select_related("plan"))
    return max(subs, key=lambda s: (s.plan.sort_order, s.expires_at or now), default=None)


def plan_for(user) -> Plan:
    if is_exempt(user):
        return unlimited_plan()
    sub = current_subscription(user)
    return sub.plan if sub else free_plan()


def max_pages(plan: Plan) -> int:
    return min(plan.max_pages_per_case, settings.CASE_MAX_PAGES)


def _used(user, field: str, scope: str, today: date) -> int:
    qs = UsageLog.objects.filter(user=user)
    if scope == "daily":
        qs = qs.filter(date=today)
    elif scope == "monthly":
        qs = qs.filter(date__gte=today.replace(day=1))
    return qs.aggregate(total=Sum(field))["total"] or 0


def _reserve(user, kind: str, pages: int = 0) -> Decision:
    plan = plan_for(user)
    if kind == "case" and pages > max_pages(plan):
        return Decision(False, "pages", _("Bu tarifda bitta ish %(max)s varaqdan oshmasligi kerak (yuklangan: %(n)s varaq).")
                        % {"max": max_pages(plan), "n": pages}, plan)
    field, scopes = LIMITS[kind]
    today = timezone.localdate()
    with transaction.atomic():
        log, _created = UsageLog.objects.select_for_update().get_or_create(user=user, date=today)
        for attr, scope in scopes:
            limit = getattr(plan, attr)
            if limit is not None and _used(user, field, scope, today) + 1 > limit:
                return Decision(False, scope, _message(kind, scope, limit), plan)
        setattr(log, field, getattr(log, field) + 1)
        if kind == "case":
            log.pages_processed += pages
        log.save()
    return Decision(True, plan=plan)


def reserve_case(user, pages: int) -> Decision:
    return _reserve(user, "case", pages)


def reserve_chat(user) -> Decision:
    return _reserve(user, "chat")


def refund_chat(user, day: date | None = None) -> None:
    """Savolga javob berilmadi (qidiruv/LLM xatosi, byudjet) — foydalanuvchi aybi yo'q, kvota qaytariladi."""
    UsageLog.objects.filter(user=user, date=day or timezone.localdate()).update(
        chat_questions=Greatest(F("chat_questions") - 1, 0))


def reserve_template(user) -> Decision:
    return _reserve(user, "template")


def refund_case(user, pages: int, day: date | None = None) -> None:
    """Tahlil xato bilan tugadi — kvota qaytariladi (foydalanuvchi aybi yo'q)."""
    # F() bilan — parallel yangilanishlar bir-birini bosib ketmasin
    UsageLog.objects.filter(user=user, date=day or timezone.localdate()).update(
        cases_used=Greatest(F("cases_used") - 1, 0), pages_processed=Greatest(F("pages_processed") - pages, 0))


def record_cost(user, usd, day: date | None = None) -> None:
    log, _created = UsageLog.objects.get_or_create(user=user, date=day or timezone.localdate())
    UsageLog.objects.filter(pk=log.pk).update(llm_cost_usd=F("llm_cost_usd") + Decimal(str(usd)))


def activate_subscription(user, plan: Plan, days: int | None = None, source: str = "ADMIN", payment=None) -> Subscription:
    """Obunani yoqadi; shu tarifning faol obunasi bo'lsa — muddat uning oxiridan uzaytiriladi."""
    days = days if days is not None else plan.duration_days
    now = timezone.now()
    existing = (Subscription.objects.filter(user=user, plan=plan, status=Subscription.Status.ACTIVE,
                                            expires_at__gt=now).order_by("-expires_at").first())
    start = existing.expires_at if existing else now
    expires = start + timedelta(days=days) if days else None
    return Subscription.objects.create(user=user, plan=plan, started_at=now, expires_at=expires, source=source,
                                       payment=payment)


def mark_paid(payment) -> Subscription | None:
    """To'lov tasdiqlandi (Payme/Click webhook yoki admin) — obuna yoqiladi. Takroran chaqirish xavfsiz."""
    from .models import Payment

    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status == Payment.Status.PAID:
            return payment.subscriptions.first()
        payment.status, payment.paid_at = Payment.Status.PAID, timezone.now()
        payment.save(update_fields=["status", "paid_at"])
        return activate_subscription(payment.user, payment.plan, source="PAYMENT", payment=payment)


def usage_summary(user) -> dict:
    """/billing/ sahifasi uchun: tarif, har bir limit bo'yicha sarf."""
    plan = plan_for(user)
    today = timezone.localdate()
    sub = None if is_exempt(user) else current_subscription(user)
    rows = []
    labels = {("case", "daily"): _("Ish tahlili — bugun"), ("case", "monthly"): _("Ish tahlili — shu oy"),
              ("case", "lifetime"): _("Ish tahlili — jami"), ("chat", "daily"): _("Savollar — bugun"),
              ("chat", "lifetime"): _("Savollar — jami"), ("template", "daily"): _("Hujjat yuklab olish — bugun"),
              ("template", "lifetime"): _("Hujjat yuklab olish — jami")}
    for kind, (field, scopes) in LIMITS.items():
        for attr, scope in scopes:
            limit = getattr(plan, attr)
            if limit is not None:
                rows.append({"kind": kind, "scope": scope, "label": labels[(kind, scope)], "used": _used(user, field, scope, today), "limit": limit})
    return {"plan": plan, "subscription": sub, "rows": rows, "max_pages": max_pages(plan), "exempt": is_exempt(user)}
