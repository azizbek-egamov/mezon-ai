"""Veb va admin SPA larni Django dan tarqatish (production, `settings.LEGACY_UI = False`).

Build (`npm run build` + `collectstatic`) natijalari /static/web/ va /static/panel/ ostida (whitenoise, xeshlangan
fayllar 1 yil keshda).
Ilova marshrutlari (/cases/…, /panel/users/…) uchun esa har doim tegishli index.html qaytariladi — yo'naltirishni
brauzerdagi React Router bajaradi. index.html keshlanmaydi: yangi build darhol yetib boradi.
"""
import base64
import hashlib
import re
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.http import require_safe


def index_path(app: str) -> Path:
    """Production da — collectstatic nusxasi (whitenoise fayllarni ham shu yerdan beradi: index va assets mos keladi);
    dev da — to'g'ridan-to'g'ri build papkasi (frontend/apps/*/dist)."""
    base = settings.SPA_BUILDS[app] if settings.DEBUG else Path(settings.STATIC_ROOT) / app
    return base / "index.html"


def _index(app: str) -> bytes | None:
    try:
        return index_path(app).read_bytes()
    except FileNotFoundError:
        return None


INLINE_SCRIPT_RE = re.compile(rb"<script(?![^>]*\ssrc=)[^>]*>(.*?)</script>", re.S | re.I)


def content_security_policy(html: bytes) -> str:
    """SPA uchun CSP: faqat o'z manbalar; index.html dagi inline skript (rejim, birinchi chizishdan oldin) — xesh bilan.
    XSS bo'lsa ham begona skript yuklanmaydi va ma'lumot boshqa manzilga yuborilmaydi (connect-src 'self')."""
    # Brauzer skript matnini xeshlashdan oldin qator oxirlarini LF ga keltiradi (HTML spetsifikatsiyasi) —
    # Windows da yig'ilgan index.html (CRLF) da xesh shunda ham mos kelishi uchun biz ham shunday qilamiz.
    hashes = " ".join(
        f"'sha256-{base64.b64encode(hashlib.sha256(body.replace(b'\r\n', b'\n').replace(b'\r', b'\n')).digest()).decode()}'"
        for body in INLINE_SCRIPT_RE.findall(html))
    return "; ".join([
        "default-src 'self'",
        f"script-src 'self' {hashes}".strip(),
        "style-src 'self' 'unsafe-inline'",          # React style={...} atributlari
        "img-src 'self' data: blob:",
        "font-src 'self' data:",
        "connect-src 'self'",
        "worker-src 'self' blob:",                    # pdf.js worker
        "object-src 'none'", "base-uri 'none'", "form-action 'self'", "frame-ancestors 'none'",
    ])


def _serve(app: str) -> HttpResponse:
    html = _index(app)
    if html is None:
        # operator uchun texnik xabar (oddiy foydalanuvchi buni ko'rmasligi kerak) — tarjima qilinmaydi
        text = "Interfeys hali yigʻilmagan: frontend papkasida `npm run build` ni bajaring."
        return HttpResponse(text, status=503, content_type="text/plain; charset=utf-8")
    response = HttpResponse(html, content_type="text/html; charset=utf-8")
    response["Cache-Control"] = "no-cache"
    mode = settings.CSP_MODE
    if mode in ("enforce", "report"):
        header = "Content-Security-Policy" if mode == "enforce" else "Content-Security-Policy-Report-Only"
        response[header] = content_security_policy(html)
    return response


@require_safe
def web(request, path: str = ""):
    return _serve("web")


@require_safe
def panel(request, path: str = ""):
    return _serve("panel")
