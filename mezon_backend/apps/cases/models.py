"""Advokat yuklagan ish va uning tahlili (TZ §7.4 cases_legal_case ning soddalashtirilgan birinchi bosqichi)."""
import uuid

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from .case_types import CASE_TYPES, DEFAULT as DEFAULT_CASE_TYPE


class CaseRun(models.Model):
    class Status(models.TextChoices):
        QUEUED = "QUEUED", _("Navbatda")
        RUNNING = "RUNNING", _("Tahlil qilinmoqda")
        DONE = "DONE", _("Tayyor")
        FAILED = "FAILED", _("Xato")

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Ishni faqat egasi ko'radi (advokatlik siri). Akkauntlar paydo bo'lishidan oldingi ishlarda — bo'sh,
    # ularni `manage.py assign_cases <telefon>` bilan egaga biriktirish mumkin.
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE,
                              related_name="case_runs")
    created_at = models.DateTimeField(auto_now_add=True)
    title = models.CharField(max_length=255)
    pdf_path = models.CharField(max_length=500, blank=True, help_text="Shifrlangan PDF; bo'sh — o'chirilgan")
    zero_retention = models.BooleanField(default=False, help_text="Tahlil tugagach yuklangan PDF o'chiriladi (TZ §5.3)")
    category = models.CharField(max_length=20, default=DEFAULT_CASE_TYPE, choices=[(c, t.label) for c, t in CASE_TYPES.items()],
                                help_text="Ish turi: huquqiy qidiruv doirasi va tahlil promptlari (case_types.py)")
    pages = models.PositiveIntegerField(default=0)
    sources = models.JSONField(default=list, blank=True, help_text=(
        "Yuklangan fayllar: [{name, kind, first_page, last_page}] — hammasi bitta PDF ga birlashtirilgan"))
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.QUEUED, db_index=True)
    stage = models.CharField(max_length=200, blank=True, help_text="Joriy bosqich (progress uchun)")
    progress = models.PositiveSmallIntegerField(default=0, help_text="0–100")
    report_path = models.CharField(max_length=500, blank=True)
    cost_usd = models.DecimalField(max_digits=8, decimal_places=4, default=0)
    error = models.TextField(blank=True)
    # TZ §12 Human-in-the-Loop: advokat "asosiy dalillar va qonun moddalari bilan tanishdim" deb tasdiqlagan vaqt.
    # Tasdiqsiz rasmiy fayl (DOCX/PDF) yaratilmaydi.
    lawyer_confirmed_at = models.DateTimeField(null=True, blank=True)
    # Tahlil bizning xatomiz bilan tugasa tarif kvotasi qaytariladi (apps/billing); qayta urinishda yana band qilinadi.
    quota_refunded = models.BooleanField(default=False)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} ({self.get_status_display()})"
