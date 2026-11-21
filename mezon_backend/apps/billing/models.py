"""Tariflar, obuna, foydalanish kvotasi va to'lovlar (TZ §7.2, §8).

Barcha limitlar Admin paneldan boshqariladi (TZ §8.1): `None` — cheklov yo'q. Foydalanuvchining joriy tarifi —
muddati tugamagan faol obuna, bo'lmasa FREE (`quota.plan_for`).
"""
from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

FREE, STUDENT, PRO, ENTERPRISE = "FREE", "STUDENT", "PRO_MONTHLY", "ENTERPRISE_YEARLY"

# Tarif nomlari tarjima qilinadi (kod bo'yicha); noma'lum kodli tarif — `name` maydoni.
PLAN_NAMES = {
    FREE: _("Bepul"),
    STUDENT: _("Talaba (oylik)"),
    PRO: _("Pro (oylik)"),
    ENTERPRISE: _("Enterprise (yillik)"),
}


class Plan(models.Model):
    code = models.CharField(max_length=30, unique=True, help_text="FREE, PRO_MONTHLY, ENTERPRISE_YEARLY yoki yangi kod")
    name = models.CharField(max_length=80, help_text="Interfeysda ko'rsatiladigan nom (standart kodlar tarjima qilinadi)")
    price_uzs = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True,
                                    help_text="So'm; bo'sh — narx hali belgilanmagan")
    duration_days = models.PositiveIntegerField(null=True, blank=True, help_text="Obuna muddati (kun); FREE uchun bo'sh")
    # Ish tahlili. Bo'sh qoldirilgan chegara — cheksiz.
    daily_case_limit = models.PositiveIntegerField(null=True, blank=True)
    monthly_case_limit = models.PositiveIntegerField(null=True, blank=True)
    lifetime_case_limit = models.PositiveIntegerField(null=True, blank=True, help_text="Umrbod (FREE = 1)")
    max_pages_per_case = models.PositiveIntegerField(default=15)
    # Huquqiy savol-javob (chat)
    daily_chat_limit = models.PositiveIntegerField(null=True, blank=True)
    lifetime_chat_limit = models.PositiveIntegerField(null=True, blank=True)
    # Shablonlar: faqat DOCX/PDF yuklab olish hisoblanadi (ko'rib chiqish bepul)
    daily_template_limit = models.PositiveIntegerField(null=True, blank=True)
    lifetime_template_limit = models.PositiveIntegerField(null=True, blank=True)
    watermark = models.BooleanField(default=False, help_text="Shablonlarga \"bepul tarif\" belgisi qo'shiladi")
    priority_queue = models.BooleanField(default=False, help_text="Ish tahlili navbatida oldinda")
    is_active = models.BooleanField(default=True, help_text="Faolsiz tarif yangi obunaga berilmaydi")
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["sort_order", "id"]
        verbose_name = "tarif"
        verbose_name_plural = "tariflar"

    def __str__(self):
        return f"{self.code} ({self.name})"

    @property
    def display_name(self) -> str:
        return str(PLAN_NAMES.get(self.code) or self.name)


class Subscription(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE", "Faol"
        CANCELED = "CANCELED", "Bekor qilingan"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="subscriptions")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.ACTIVE)
    started_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Bo'sh — muddatsiz")
    source = models.CharField(max_length=20, default="ADMIN", help_text="ADMIN | PAYMENT")
    payment = models.ForeignKey("Payment", null=True, blank=True, on_delete=models.SET_NULL, related_name="subscriptions")

    class Meta:
        ordering = ["-started_at"]
        verbose_name = "obuna"
        verbose_name_plural = "obunalar"

    def __str__(self):
        return f"{self.user} → {self.plan.code}"

    @property
    def is_current(self) -> bool:
        return self.status == self.Status.ACTIVE and (self.expires_at is None or self.expires_at > timezone.now())


class UsageLog(models.Model):
    """billing_user_quota_log: foydalanuvchining kunlik sarfi. Umrbod va oylik hisob shu jadval yig'indisidan."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="usage_logs")
    date = models.DateField(db_index=True)
    cases_used = models.PositiveIntegerField(default=0)
    pages_processed = models.PositiveIntegerField(default=0)
    chat_questions = models.PositiveIntegerField(default=0)
    templates_used = models.PositiveIntegerField(default=0)
    llm_cost_usd = models.DecimalField(max_digits=10, decimal_places=4, default=0)

    class Meta:
        unique_together = [("user", "date")]
        ordering = ["-date"]
        verbose_name = "kunlik sarf"
        verbose_name_plural = "kunlik sarf"

    def __str__(self):
        return f"{self.user} {self.date}"


class Payment(models.Model):
    class Provider(models.TextChoices):
        CLICK = "CLICK", "Click"
        PAYME = "PAYME", "Payme"
        MANUAL = "MANUAL", "Qo'lda (admin)"

    class Status(models.TextChoices):
        PENDING = "PENDING", "Kutilmoqda"
        PAID = "PAID", "To'langan"
        FAILED = "FAILED", "Muvaffaqiyatsiz"
        CANCELED = "CANCELED", "Bekor qilingan"

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="payments")
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT, related_name="payments")
    provider = models.CharField(max_length=10, choices=Provider.choices)
    amount_uzs = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.PENDING, db_index=True)
    external_id = models.CharField(max_length=100, blank=True, db_index=True, help_text="Payme/Click tranzaksiya id si")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "to'lov"
        verbose_name_plural = "to'lovlar"

    def __str__(self):
        return f"{self.get_provider_display()} {self.amount_uzs} ({self.get_status_display()})"
