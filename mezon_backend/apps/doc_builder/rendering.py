"""Shablon sxemasidan forma yasash, qiymatlarni formatlash va to'ldirilgan matnni hujjat bloklariga aylantirish."""
import re
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError
from django.template import Context
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from apps.accounts.models import normalize_phone

from .models import ENGINE, DocumentTemplate
from .writers import Block


def _field(spec: dict) -> forms.Field:
    common = {"label": spec["label"], "required": spec.get("required", True), "help_text": spec.get("help", ""),
              "error_messages": {"required": _("Bu maydonni toʻldiring."),
                                 "invalid": _("Qiymat formati notoʻgʻri."),
                                 "max_length": _("Kiritilgan matn juda uzun."),
                                 "min_value": _("Qiymat manfiy boʻlmasin."),
                                 "invalid_choice": _("Tanlangan qiymat ruxsat etilmagan.")}}
    kind = spec.get("type", "text")
    if kind == "textarea":
        return forms.CharField(widget=forms.Textarea(attrs={"rows": 4}), max_length=5000, **common)
    if kind == "date":
        return forms.DateField(widget=forms.DateInput(attrs={"type": "date"}), **common)
    if kind in ("number", "money"):
        return forms.DecimalField(min_value=0, max_digits=18, decimal_places=2, **common)
    if kind == "select":
        choices = [(o, o) for o in spec["options"]]
        return forms.ChoiceField(choices=([("", "—")] if not common["required"] else []) + choices, **common)
    if kind == "phone":
        return forms.CharField(max_length=32, validators=[normalize_phone], **common)
    if kind == "jshshir":
        return forms.RegexField(regex=r"^\d{14}$", max_length=14,
                                **(common | {"error_messages": common["error_messages"] |
                                            {"invalid": _("JSHSHIR — 14 ta raqam")}}))
    return forms.CharField(max_length=500, **common)


def build_form(template: DocumentTemplate, data=None, lang=None) -> forms.Form:
    form = forms.Form(data=data)
    variant = template.variant_for(lang) if hasattr(template, "variant_for") else {}
    schema = variant.get("form_schema") or template.form_schema
    for spec in schema:
        form.fields[spec["name"]] = _field(spec)
    return form


def _money(value: Decimal) -> str:
    whole = f"{int(value):,}".replace(",", " ")
    frac = value - int(value)
    return f"{whole},{int(frac * 100):02d}" if frac else whole


def format_values(template: DocumentTemplate, cleaned: dict, lang=None) -> dict:
    """Forma qiymatlari -> matnga qo'yiladigan satrlar (sana dd.mm.yyyy, summa "1 250 000", telefon +998…)."""
    variant = template.variant_for(lang) if hasattr(template, "variant_for") else {}
    schema = variant.get("form_schema") or template.form_schema
    types = {f["name"]: f.get("type", "text") for f in schema}
    out = {"bugun": timezone.localdate().strftime("%d.%m.%Y")}
    for name, value in cleaned.items():
        if value in (None, ""):
            out[name] = ""
        elif types.get(name) == "date":
            out[name] = value.strftime("%d.%m.%Y")
        elif types.get(name) == "money":
            out[name] = _money(value)
        elif types.get(name) == "number":
            out[name] = str(int(value)) if value == value.to_integral() else format(value.normalize(), "f")
        elif types.get(name) == "phone":
            out[name] = normalize_phone(value)
        else:
            out[name] = str(value).strip()
    return out


LINE_KINDS = [(">>", "right"), ("###", "h2"), ("##", "center"), ("- ", "item"), ("~", "sign")]


def render_blocks(template: DocumentTemplate, values: dict, lang=None) -> list[Block]:
    variant = template.variant_for(lang) if hasattr(template, "variant_for") else {}
    body = variant.get("body") or template.body
    text = ENGINE.from_string(body).render(Context(values, autoescape=False))
    blocks: list[Block] = []
    for raw in text.split("\n"):
        line = raw.rstrip()
        if not line.strip():
            if blocks and blocks[-1].kind != "space":
                blocks.append(Block("space"))
            continue
        for prefix, kind in LINE_KINDS:
            if line.lstrip().startswith(prefix):
                blocks.append(Block(kind, line.lstrip()[len(prefix):].strip()))
                break
        else:
            blocks.append(Block("p", re.sub(r"\s+", " ", line).strip()))
    while blocks and blocks[-1].kind == "space":
        blocks.pop()
    return blocks


def fill(template: DocumentTemplate, data, lang=None) -> tuple[forms.Form, list[Block] | None]:
    form = build_form(template, data, lang=lang)
    if not form.is_valid():
        return form, None
    try:
        return form, render_blocks(template, format_values(template, form.cleaned_data, lang=lang), lang=lang)
    except ValidationError as e:  # masalan, telefon normallashmasa
        form.add_error(None, e)
        return form, None
