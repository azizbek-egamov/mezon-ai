"""Hujjat shablonlari (TZ §5.1.1, §7.4 templates_document_template) — AI siz, deterministik to'ldirish.

Shablon = forma sxemasi (JSON: maydonlar ro'yxati) + matn (Django shablon tili: {{ maydon }}, {% if maydon %}).
Matn qatorlari belgilari (rendering.py):
    >> Kimga / kimdan rekvizitlari (o'ngga tekislanadi)
    ## HUJJAT NOMI (markazda, qalin)
    ### Bo'lim sarlavhasi
    - ro'yxat bandi
    ~ chap matn | o'ng matn   (imzo qatori)
    (bo'sh qator — oraliq; boshqa qatorlar — oddiy abzats)
Shablonni yurist-moderator yozadi va tasdiqlaydi; matn yoki sxema o'zgarsa versiya oshadi va tasdiq bekor bo'ladi.
To'ldirilgan ma'lumotlar saqlanmaydi — hujjat xotirada yaratilib, darhol yuklab beriladi.
"""
import re
import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.template import Engine, TemplateSyntaxError

FIELD_TYPES = {"text", "textarea", "date", "number", "money", "select", "phone", "jshshir"}
AUTO_VARS = {"bugun"}  # avtomatik: bugungi sana (dd.mm.yyyy)
NAME_RE = re.compile(r"^[a-z][a-z0-9_]*$")
ENGINE = Engine(autoescape=False, string_if_invalid="")


class Category(models.TextChoices):
    CONTRACTS = "CONTRACTS", _("Shartnomalar")
    STATEMENTS = "STATEMENTS", _("Arizalar")
    PERSONAL = "PERSONAL", _("Shaxsiy tarkibga oid hujjatlar")
    NOTARIAL = "NOTARIAL", _("Notarial tasdiqlanadigan hujjatlar")
    COURT = "COURT", _("Sudga oid hujjatlar")
    CORPORATE = "CORPORATE", _("Korporativ hujjatlar")
    ADVOCATE_REQUEST = "ADVOCATE_REQUEST", _("Advokat soʻrovi")
    MOTION = "MOTION", _("Iltimosnoma")
    CLAIM = "CLAIM", _("Daʼvo arizasi")
    APPEAL = "APPEAL", _("Shikoyat")
    POWER_OF_ATTORNEY = "POWER_OF_ATTORNEY", _("Ishonchnoma")
    CONTRACT = "CONTRACT", _("Shartnoma")
    ORDER = "ORDER", _("Buyruq")
    OTHER = "OTHER", _("Boshqa")


def template_variables(body: str) -> set[str]:
    """Matnda ishlatilgan o'zgaruvchilar: {{ x }}, {{ x|filtr }}, {% if x %}, {% if not x %}."""
    names = set(re.findall(r"{{\s*([a-zA-Z_]\w*)", body))
    names |= set(re.findall(r"{%\s*(?:el)?if\s+(?:not\s+)?([a-zA-Z_]\w*)", body))
    return names


def validate_schema(schema) -> None:
    if not isinstance(schema, list) or not schema:
        raise ValidationError(_("Forma sxemasi — maydonlar roʻyxati boʻlishi kerak"))
    seen = set()
    for i, f in enumerate(schema, 1):
        if not isinstance(f, dict):
            raise ValidationError(_("%(n)s-maydon obyekt boʻlishi kerak") % {"n": i})
        name, ftype = f.get("name", ""), f.get("type", "text")
        if not NAME_RE.match(name) or name in AUTO_VARS:
            raise ValidationError(_("%(n)s-maydon nomi notoʻgʻri: %(name)s (kichik lotin harflari, raqam, _)") %
                                  {"n": i, "name": repr(name)})
        if name in seen:
            raise ValidationError(_("Maydon nomi takrorlangan: %(name)s") % {"name": name})
        seen.add(name)
        if not f.get("label"):
            raise ValidationError(_("%(name)s: label (yorliq) kerak") % {"name": name})
        if ftype not in FIELD_TYPES:
            raise ValidationError(_("%(name)s: nomaʼlum tur %(type)s (mumkin: %(types)s)") %
                                  {"name": name, "type": repr(ftype), "types": ", ".join(sorted(FIELD_TYPES))})
        if ftype == "select" and not f.get("options"):
            raise ValidationError(_("%(name)s: select uchun options kerak") % {"name": name})


class DocumentTemplate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    doc_id = models.IntegerField(null=True, blank=True, db_index=True, help_text="Yurxizmat ID raqami")
    title = models.CharField(max_length=255)
    title_translations = models.JSONField(default=dict, blank=True, help_text="Har bir tildagi sarlavha: {'uz-Latn': '...', 'uz-Cyrl': '...', 'ru': '...'}")
    category = models.CharField(max_length=32, choices=Category.choices, db_index=True)
    subcategory = models.CharField(max_length=150, blank=True, db_index=True, help_text="Ichki boʻlim nomi")
    subcategory_slug = models.CharField(max_length=100, blank=True, db_index=True)
    subcategory_translations = models.JSONField(default=dict, blank=True, help_text="Har bir tildagi bo'lim nomi: {'uz-Latn': '...', 'uz-Cyrl': '...', 'ru': '...'}")
    language = models.CharField(max_length=8, default="uz-Latn")
    available_languages = models.JSONField(default=list, blank=True, help_text="Mavjud tillar: ['uz-Latn', 'uz-Cyrl', 'ru']")
    variants = models.JSONField(default=dict, blank=True, help_text="Til variantlari: {'uz-Latn': {'title': ..., 'form_schema': [...], 'body': '...'}, ...}")
    description = models.TextField(blank=True, help_text="Qachon ishlatiladi (foydalanuvchiga ko'rinadi)")
    legal_basis = models.TextField(blank=True, help_text="Qonuniy asoslar, har biri yangi qatorda (ma'lumot uchun)")
    form_schema = models.JSONField(help_text='[{"name": "fio", "label": "F.I.Sh.", "type": "text", "required": true}]')
    body = models.TextField(help_text="Hujjat matni: {{ maydon }}, {% if maydon %}…{% endif %}; qator belgilari — modul izohida")
    version = models.PositiveIntegerField(default=1)
    is_published = models.BooleanField(default=False, help_text="Foydalanuvchilarga ko'rinadi")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="approved_templates")
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["category", "title"]
        verbose_name = "hujjat shabloni"
        verbose_name_plural = "hujjat shablonlari"

    def __str__(self):
        return f"{self.title} (v{self.version})"

    def title_for(self, lang: str | None) -> str:
        if lang and self.title_translations:
            l = str(lang).lower().replace("_", "-")
            for k, v in self.title_translations.items():
                k_norm = k.lower().replace("_", "-")
                if k_norm == l or (l.startswith("uz-cyr") and "cyr" in k_norm) or ((l == "uz" or l.startswith("uz-lat")) and "lat" in k_norm) or (l.startswith("ru") and "ru" in k_norm):
                    return v
        return self.title

    def subcategory_for(self, lang: str | None) -> str:
        if lang and self.subcategory_translations:
            l = str(lang).lower().replace("_", "-")
            for k, v in self.subcategory_translations.items():
                k_norm = k.lower().replace("_", "-")
                if k_norm == l or (l.startswith("uz-cyr") and "cyr" in k_norm) or ((l == "uz" or l.startswith("uz-lat")) and "lat" in k_norm) or (l.startswith("ru") and "ru" in k_norm):
                    return v
        return self.subcategory

    def variant_for(self, lang: str | None) -> dict:
        if lang and self.variants:
            l = str(lang).lower().replace("_", "-")
            for k, v in self.variants.items():
                k_norm = k.lower().replace("_", "-")
                if k_norm == l or (l.startswith("uz-cyr") and "cyr" in k_norm) or ((l == "uz" or l.startswith("uz-lat")) and "lat" in k_norm) or (l.startswith("ru") and "ru" in k_norm):
                    return v
        return {
            "title": self.title,
            "form_schema": self.form_schema,
            "body": self.body,
        }

    @property
    def field_names(self) -> set[str]:
        return {f["name"] for f in self.form_schema}

    def clean(self):
        validate_schema(self.form_schema)
        try:
            ENGINE.from_string(self.body)
        except TemplateSyntaxError as e:
            raise ValidationError({"body": _("Shablon matnida xato: %(error)s") % {"error": e}})
        unknown = template_variables(self.body) - self.field_names - AUTO_VARS
        if unknown:
            raise ValidationError({"body": _("Sxemada yoʻq maydonlar ishlatilgan: %(fields)s") %
                                           {"fields": ", ".join(sorted(unknown))}})

    def save(self, *args, **kwargs):
        # Matn yoki forma o'zgarsa — yangi versiya, moderator qayta tasdiqlashi kerak.
        if self.pk:
            old = DocumentTemplate.objects.filter(pk=self.pk).values("body", "form_schema").first()
            if old and (old["body"] != self.body or old["form_schema"] != self.form_schema):
                self.version += 1
                self.approved_by, self.approved_at = None, None
        super().save(*args, **kwargs)
