"""Hujjatlar konstruktori sahifalari.

GET  /templates/          — shablonlar ro'yxati (turlari bo'yicha)
GET  /templates/<id>/     — forma
POST /templates/<id>/     — action=preview: ko'rib chiqish; action=docx|pdf: fayl yuklab olish
To'ldirilgan ma'lumotlar (F.I.Sh., JSHSHIR, pasport) saqlanmaydi va logga yozilmaydi.
"""
from itertools import groupby
from urllib.parse import quote

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.utils import timezone
from django.utils.translation import gettext as _
from django.views.decorators.http import require_http_methods

from apps.billing import quota

from .models import Category, DocumentTemplate
from .rendering import fill
from .writers import Block, to_docx, to_pdf

FORMATS = {
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", to_docx),
    "pdf": ("application/pdf", to_pdf),
}


def file_response(template: DocumentTemplate, blocks: list[Block], fmt: str, watermark: bool) -> HttpResponse:
    """To'ldirilgan hujjat -> DOCX/PDF javobi (HTML forma va API v1 uchun umumiy). Kvota chaqiruvchida band qilinadi."""
    if watermark:   # bepul tarif: hujjat boshida va oxirida belgi (TZ §8.1)
        mark = Block("meta", _("MEZON AI bepul tarifida tayyorlandi"))
        blocks = [mark, *blocks, mark]
    content_type, render_file = FORMATS[fmt]
    response = HttpResponse(render_file(blocks), content_type=content_type)
    name = f"{template.get_category_display()}_{timezone.localdate():%Y%m%d}".replace(" ", "_")
    response["Content-Disposition"] = f"attachment; filename*=UTF-8''{quote(name)}.{fmt}"
    response["Cache-Control"] = "private, no-store"
    return response


@login_required
def template_list(request):
    templates = DocumentTemplate.objects.filter(is_published=True)
    labels = dict(Category.choices)
    groups = [(labels.get(cat, cat), list(items)) for cat, items in groupby(templates, key=lambda t: t.category)]
    return render(request, "doc_builder/list.html", {"groups": groups})


@login_required
@require_http_methods(["GET", "POST"])
def template_fill(request, template_id):
    template = get_object_or_404(DocumentTemplate, pk=template_id, is_published=True)
    action = request.POST.get("action", "preview")
    form, blocks = fill(template, request.POST if request.method == "POST" else None)
    quota_error = ""
    if request.method == "POST" and blocks is not None and action in FORMATS:
        decision = quota.reserve_template(request.user)   # faqat DOCX/PDF yuklab olish hisoblanadi
        if not decision.ok:
            quota_error = decision.message
    if request.method == "POST" and blocks is not None and action in FORMATS and not quota_error:
        return file_response(template, blocks, action, decision.plan.watermark)
    return render(request, "doc_builder/fill.html", {
        "quota_error": quota_error, "template": template, "form": form, "blocks": blocks if request.method == "POST" else None,
        "legal_basis": [line for line in template.legal_basis.splitlines() if line.strip()],
    })
