"""Foydalanuvchilar (TZ §1.3, §7.1 users_user). Kirish — tasdiqlangan +998 telefon raqami va parol;
SMS OTP (Eskiz.uz / PlayMobile) keyingi bosqichda shu modelga qo'shiladi."""
import re
import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext
from django.utils.translation import gettext_lazy as _

CONSENT_VERSION = "2026-10"


def normalize_phone(value: str) -> str:
    """'90 123-45-67', '998901234567', '+998 (90) 123 45 67' -> '+998901234567'. Faqat O'zbekiston raqamlari."""
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 9:
        digits = "998" + digits
    if len(digits) != 12 or not digits.startswith("998"):
        raise ValidationError(gettext("Telefon raqami +998 XX XXX XX XX koʻrinishida boʻlsin"))
    return "+" + digits


class Role(models.TextChoices):
    LAWYER = "LAWYER", _("Advokat / yurist")
    STUDENT = "STUDENT", _("Talaba")
    CLIENT = "CLIENT", _("Fuqaro")
    MODERATOR = "MODERATOR", _("Yurist-moderator")
    SUPERADMIN = "SUPERADMIN", _("Superadmin")


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, phone_number: str, password: str | None = None, **extra):
        user = self.model(phone_number=normalize_phone(phone_number), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, phone_number: str, password: str | None = None, **extra):
        extra.update(role=Role.SUPERADMIN, is_staff=True, is_superuser=True)
        return self.create_user(phone_number, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    phone_number = models.CharField("telefon", max_length=20, unique=True)
    full_name = models.CharField("F.I.Sh.", max_length=255)
    role = models.CharField(max_length=12, choices=Role.choices, default=Role.CLIENT, db_index=True)
    advocate_license_no = models.CharField("advokatlik guvohnomasi", max_length=50, blank=True)
    university = models.CharField("OTM / Universitet", max_length=150, blank=True)
    study_level = models.CharField("Bosqich / Kurs", max_length=50, blank=True)
    student_id_no = models.CharField("Talabalik guvohnomasi / HEMIS ID", max_length=50, blank=True)
    language = models.CharField("til", max_length=16, default="uz-latn", help_text="Interfeys tili (settings.LANGUAGES)")
    is_fraud_flagged = models.BooleanField(default=False)
    consents_json = models.JSONField(default=dict, blank=True,
                                     help_text="Shaxsiy ma'lumotlarni qayta ishlashga rozilik: sana va versiya")
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False, help_text="Admin panelga kira oladi")
    date_joined = models.DateTimeField(default=timezone.now)
    # Anti-fraud (TZ §8.2): bitta IP dan ko'p akkaunt — admin panel radarida. Faqat xodimlarga ko'rinadi.
    registered_ip = models.GenericIPAddressField(null=True, blank=True)
    last_login_ip = models.GenericIPAddressField(null=True, blank=True)

    objects = UserManager()
    USERNAME_FIELD = "phone_number"
    REQUIRED_FIELDS = ["full_name"]

    class Meta:
        verbose_name = "foydalanuvchi"
        verbose_name_plural = "foydalanuvchilar"

    def __str__(self):
        return f"{self.full_name} ({self.phone_number})"

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.phone_number

    def record_consent(self, kind: str = "pii") -> None:
        self.consents_json = {**self.consents_json,
                              kind: {"version": CONSENT_VERSION, "accepted_at": timezone.now().isoformat()}}


STAFF_ROLES = (Role.MODERATOR, Role.SUPERADMIN)


class AuditEvent(models.Model):
    """Admin amallari jurnali: kim, qachon, nimani o'zgartirdi (rol, tarif, to'lov, shablon tasdig'i, sinxronizatsiya).
    `details` ga shaxsiy ma'lumot (parol, hujjat matni) yozilmaydi — faqat o'zgargan maydonlar va qiymat kodlari."""

    actor = models.ForeignKey(User, null=True, blank=True, on_delete=models.SET_NULL, related_name="audit_actions")
    action = models.CharField(max_length=50, db_index=True, help_text="user.update, subscription.grant, payment.mark_paid…")
    target = models.CharField(max_length=100, db_index=True, help_text="user:<id>, plan:<kod>, template:<id>…")
    details = models.JSONField(default=dict, blank=True)
    ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "admin amali"
        verbose_name_plural = "admin amallari jurnali"

    def __str__(self):
        return f"{self.created_at:%d.%m.%Y %H:%M} {self.action} {self.target}"
