"""Xato javoblarining yagona shakli: {"detail": "...", "code": "..."} (validatsiya xatolari — {maydon: [xabar]}).

404 da model nomi oshkor qilinmaydi ("No CaseRun matches…" o'rniga "Topilmadi"); autentifikatsiya xabarlari
foydalanuvchi tilida.
"""
import math

from django.http import Http404
from django.utils.translation import gettext as _
from rest_framework import exceptions
from rest_framework.views import exception_handler as drf_exception_handler

from apps.i18n.errors import localize_error_data


def exception_handler(exc, context):
    original_detail = getattr(exc, "detail", None)
    original_code = getattr(original_detail, "code", None) or getattr(exc, "default_code", None)
    if isinstance(exc, Http404):
        exc = exceptions.NotFound(_("Topilmadi"))
    elif isinstance(exc, exceptions.NotAuthenticated):
        exc = exceptions.NotAuthenticated(_("Avval tizimga kiring"))
    elif isinstance(exc, exceptions.AuthenticationFailed):
        exc = exceptions.AuthenticationFailed(_("Sessiya yaroqsiz. Qaytadan kiring."))
    elif isinstance(exc, exceptions.ParseError):
        exc = exceptions.ParseError(_("Soʻrov formati notoʻgʻri."))
    elif isinstance(exc, exceptions.MethodNotAllowed):
        exc = exceptions.MethodNotAllowed(getattr(exc, "method", ""), _("Bu HTTP usuli ushbu amal uchun ruxsat etilmagan."))
    elif isinstance(exc, exceptions.UnsupportedMediaType):
        exc = exceptions.UnsupportedMediaType(getattr(exc, "media_type", ""), _("Bu fayl turi qoʻllab-quvvatlanmaydi."))
    elif isinstance(exc, exceptions.NotAcceptable):
        exc = exceptions.NotAcceptable(_("Soʻralgan javob formati qoʻllab-quvvatlanmaydi."))
    elif isinstance(exc, exceptions.PermissionDenied):
        exc = exceptions.PermissionDenied(_("Bu amal uchun ruxsat yoʻq."))
    elif isinstance(exc, exceptions.NotFound):
        exc = exceptions.NotFound(_("Topilmadi"))
    elif isinstance(exc, exceptions.Throttled):
        wait = max(1, int(exc.wait or 1))
        if wait >= 60:
            minutes = math.ceil(wait / 60)
            detail = _("Soʻrovlar juda tez. %(n)s daqiqadan keyin qayta urinib koʻring.") % {"n": minutes}
        else:
            detail = _("Soʻrovlar juda tez. %(n)s soniyadan keyin qayta urinib koʻring.") % {"n": wait}
        exc = exceptions.Throttled(wait=exc.wait, detail=detail)
    response = drf_exception_handler(exc, context)
    if response is not None:
        detail = response.data.get("detail") if isinstance(response.data, dict) else None
        detail_code = getattr(detail, "code", None)
        response.data = localize_error_data(response.data)
        if isinstance(response.data, dict) and "detail" in response.data:
            response.data.setdefault("code", original_code or detail_code or getattr(exc, "default_code", "error"))
    return response
