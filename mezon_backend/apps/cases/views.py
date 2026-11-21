"""Ish yuklash va tahlil natijasi sahifalari.

GET  /cases/                 — ishlar ro'yxati + PDF yuklash shakli
POST /cases/upload           — fayllarni (PDF, DOCX, JPG/PNG) bitta PDF ga birlashtirib saqlash va navbatga qo'yish
GET  /cases/<id>/            — progress va hisobot sahifasi
GET  /api/cases/<id>/confirmation — tasdiq oynasi uchun: keltirilgan moddalar, tasdiqlanmagan baholar (TZ §12)
POST /cases/<id>/confirm     — advokat "tanishdim" tasdig'i
GET  /cases/<id>/export.<docx|pdf> — rasmiy fayl (faqat tasdiqdan keyin)
POST /cases/<id>/delete      — ishni (PDF, hisobot) butunlay o'chirish
POST /cases/<id>/retry       — xato bilan tugagan tahlilni qaytadan navbatga qo'yish

Barcha sahifalar faqat tizimga kirganlar uchun; har bir foydalanuvchi faqat o'z ishlarini ko'radi —
begona ish so'ralsa 404 (ish borligi ham oshkor qilinmaydi).
GET  /api/cases/<id>         — holat (JSON, sahifa har 2 s da so'raydi)
GET  /api/cases/<id>/report  — tayyor hisobot (JSON)
"""
import io
from urllib.parse import quote

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import (FileResponse, Http404, HttpResponse, HttpResponseBadRequest, HttpResponseForbidden,
                         JsonResponse)
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext as _
from django.views.decorators.clickjacking import xframe_options_sameorigin
from django.views.decorators.csrf import ensure_csrf_cookie
from django.views.decorators.http import require_GET, require_POST
from apps.accounts.decorators import api_login_required

from . import services
from .case_types import CASE_TYPES
from .models import CaseRun
from .services import CaseError


def _own_run(request, run_id, **filters) -> CaseRun:
    return get_object_or_404(CaseRun, pk=run_id, owner=request.user, **filters)


@require_GET
@login_required
@ensure_csrf_cookie
def case_list(request):
    services.recover_interrupted()
    return render(request, "cases/list.html", {
        "runs": CaseRun.objects.filter(owner=request.user)[:50], "max_mb": settings.CASE_MAX_MB, "max_pages": settings.CASE_MAX_PAGES,
        "error": request.GET.get("error", ""),
        "case_types": [(code, t.label) for code, t in CASE_TYPES.items()],
    })


def _upload_error(message: str):
    return redirect("/cases/?error=" + quote(message))


@require_POST
@login_required
def case_upload(request):
    """Bir yoki bir nechta fayl (PDF, DOCX, JPG/PNG) -> bitta PDF (intake.py). `pdf` — eski maydon nomi."""
    try:
        run = services.create_case(request.user, request.FILES.getlist("files") + request.FILES.getlist("pdf"),
                                   category=request.POST.get("category", ""), title=request.POST.get("title", ""),
                                   zero_retention=bool(request.POST.get("zero_retention")))
    except CaseError as e:
        return _upload_error(e.message)
    return redirect(f"/cases/{run.id}/")


@require_GET
@login_required
def case_detail(request, run_id):
    return render(request, "cases/detail.html", {"run": _own_run(request, run_id)})


@require_POST
@login_required
def case_retry(request, run_id):
    run = _own_run(request, run_id)
    try:
        services.retry_case(request.user, run)
    except CaseError as e:
        if e.status == 429:
            return _upload_error(e.message)
    return redirect(f"/cases/{run.id}/")


@require_GET
@login_required
@xframe_options_sameorigin  # ish sahifasidagi iframe uchun (sukut — DENY)
def case_pdf(request, run_id):
    data = services.read_pdf(_own_run(request, run_id))
    if data is None:
        raise Http404(_("PDF oʻchirilgan yoki topilmadi"))
    response = FileResponse(io.BytesIO(data), content_type="application/pdf")
    response["Cache-Control"] = "private, no-store"
    return response


@require_POST
@login_required
def case_delete(request, run_id):
    """Ishni butunlay o'chirish: PDF, hisobot va yozuv. Tahlil ketayotgan ishni o'chirib bo'lmaydi."""
    run = _own_run(request, run_id)
    try:
        services.delete_case(run)
    except CaseError:
        return redirect(f"/cases/{run.id}/")
    return redirect("/cases/")


@require_GET
@api_login_required
def api_status(request, run_id):
    run = _own_run(request, run_id)
    return JsonResponse({"status": run.status, "status_label": run.get_status_display(), "stage": run.stage,
                         "progress": run.progress, "error": run.error, "pages": run.pages,
                         "cost_usd": float(run.cost_usd)})


@require_GET
@api_login_required
def api_report(request, run_id):
    run = _own_run(request, run_id, status=CaseRun.Status.DONE)
    response = JsonResponse(services.read_report(run), json_dumps_params={"ensure_ascii": False})
    response["Cache-Control"] = "private, no-store"
    return response


@require_GET
@api_login_required
def api_confirmation(request, run_id):
    run = _own_run(request, run_id, status=CaseRun.Status.DONE)
    return JsonResponse(services.confirmation_info(run), json_dumps_params={"ensure_ascii": False})


@require_POST
@login_required
def case_confirm(request, run_id):
    run = _own_run(request, run_id, status=CaseRun.Status.DONE)
    if request.POST.get("acknowledged") != "1":
        return HttpResponseBadRequest(_("Tasdiqlash uchun belgini qoʻying"))
    services.confirm_case(run)
    return redirect(f"/cases/{run.id}/?confirmed=1")


@require_GET
@login_required
def case_export(request, run_id, fmt):
    run = _own_run(request, run_id, status=CaseRun.Status.DONE)
    try:
        content, content_type, filename = services.export_file(run, fmt, request.user.full_name)
    except CaseError as e:
        if e.status == 404:
            raise Http404()
        return HttpResponseForbidden(e.message)
    response = HttpResponse(content, content_type=content_type)
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    response["Cache-Control"] = "private, no-store"
    return response
