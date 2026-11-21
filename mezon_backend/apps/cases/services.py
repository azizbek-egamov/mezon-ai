"""Ish bilan amallar — HTML sahifalar (views.py) va API v1 (apps/api) uchun umumiy biznes mantiq.

Xatolar `CaseError` bilan qaytadi: `message` foydalanuvchiga ko'rsatiladi (interfeys tilida), `status` — HTTP kodi
(400 noto'g'ri so'rov, 403 tasdiqsiz eksport, 409 holat mos emas, 429 tarif limiti), `code` — mijoz uchun barqaror kod.
"""
import json
import uuid

from django.conf import settings
from django.utils import timezone, translation
from django.utils.translation import gettext as _

from apps.billing import quota

from . import export, storage, worker
from .case_types import CASE_TYPES, DEFAULT as DEFAULT_CASE_TYPE
from .intake import IntakeError, build_case_pdf
from .models import CaseRun

_recovered = False


class CaseError(Exception):
    def __init__(self, message: str, status: int = 400, code: str = "invalid"):
        super().__init__(message)
        self.message, self.status, self.code = message, status, code


def recover_interrupted() -> None:
    """Server qayta ishga tushganda: yarim qolgan tahlillar — xato, navbatdagilar — qaytadan navbatga.
    Shu jarayonda allaqachon navbatda/bajarilayotgan ishlarga tegmaydi (birinchi so'rovdan oldin boshlangan bo'lishi mumkin)."""
    global _recovered
    if _recovered:
        return
    _recovered = True
    for run in CaseRun.objects.filter(status=CaseRun.Status.RUNNING).select_related("owner"):
        if not worker.is_active(run.id):
            language = getattr(run.owner, "language", settings.LANGUAGE_CODE) if run.owner_id else settings.LANGUAGE_CODE
            with translation.override(language):
                restart_error = _("Server qayta ishga tushdi — tahlilni qaytadan boshlang")
            CaseRun.objects.filter(pk=run.id, status=CaseRun.Status.RUNNING).update(
                status=CaseRun.Status.FAILED, error=restart_error)
    for run_id in CaseRun.objects.filter(status=CaseRun.Status.QUEUED).values_list("id", flat=True):
        worker.enqueue(run_id)   # allaqachon navbatdagini enqueue o'zi o'tkazib yuboradi


def upload_limits(user=None) -> dict:
    limits = {
        "max_files": settings.CASE_MAX_FILES,
        "max_mb": settings.CASE_MAX_MB,
        "max_pages": settings.CASE_MAX_PAGES,
        "server_max_pages": settings.CASE_MAX_PAGES,
        "plan_code": None,
        "plan_name": None,
        "unlimited": False,
        "cases_remaining": None,
        "cases_exhausted": False,
    }
    if user and getattr(user, "is_authenticated", False):
        plan = quota.plan_for(user)
        limits["max_pages"] = quota.max_pages(plan)
        limits["plan_code"] = plan.code
        limits["plan_name"] = plan.display_name
        limits["unlimited"] = quota.is_exempt(user)

        if limits["unlimited"]:
            limits["cases_remaining"] = None
            limits["cases_exhausted"] = False
        else:
            today = timezone.localdate()
            remaining = None
            exhausted = False
            field, scopes = quota.LIMITS["case"]
            for attr, scope in scopes:
                limit = getattr(plan, attr)
                if limit is not None:
                    used = quota._used(user, field, scope, today)
                    rem = max(0, limit - used)
                    if remaining is None or rem < remaining:
                        remaining = rem
                    if used >= limit:
                        exhausted = True
            limits["cases_remaining"] = remaining
            limits["cases_exhausted"] = exhausted
    return limits


def create_case(user, uploads, category: str = "", title: str = "", zero_retention: bool = False) -> CaseRun:
    """Bir yoki bir nechta fayl (PDF, DOCX, JPG/PNG; Django UploadedFile) -> bitta shifrlangan PDF, kvota band qilinadi,
    tahlil navbatga qo'yiladi."""
    category = category or DEFAULT_CASE_TYPE
    if category not in CASE_TYPES:
        raise CaseError(_("Ish turi notoʻgʻri"), code="category")
    if not uploads:
        raise CaseError(_("Fayl tanlang"), code="no_files")
    if len(uploads) > settings.CASE_MAX_FILES:
        raise CaseError(_("Bir ishga %(n)s tadan ortiq fayl yuklab boʻlmaydi") % {"n": settings.CASE_MAX_FILES},
                        code="too_many_files")
    if sum(f.size for f in uploads) > settings.CASE_MAX_MB * 1024 * 1024:
        raise CaseError(_("Fayllar jami %(mb)s MB dan katta") % {"mb": settings.CASE_MAX_MB}, code="too_large")
    try:
        # CASE_MAX_MB gacha — xotirada tekshirib, faqat shifrlangan holda diskka yoziladi
        intake = build_case_pdf([(f.name, b"".join(f.chunks())) for f in uploads])
    except IntakeError as e:
        raise CaseError(str(e), code="intake")
    if intake.pages > settings.CASE_MAX_PAGES:
        raise CaseError(_("Hozircha %(max)s varaqdan oshmasin (%(n)s varaq)") % {"max": settings.CASE_MAX_PAGES,
                                                                                  "n": intake.pages}, code="too_many_pages")
    decision = quota.reserve_case(user, intake.pages)   # tarif: sahifalar soni va kunlik/oylik/umrbod limit
    if not decision.ok:
        raise CaseError(decision.message, status=429, code=f"quota_{decision.code}")
    run_id = uuid.uuid4()
    path = storage.write_encrypted(settings.DATA_DIR / "uploads" / f"{run_id}.pdf", intake.pdf)
    title = (title or "").strip() or (
        uploads[0].name if len(uploads) == 1 else _("%(name)s + %(n)s fayl") % {"name": uploads[0].name, "n": len(uploads) - 1})
    run = CaseRun.objects.create(id=run_id, owner=user, title=title[:255], pdf_path=path, pages=intake.pages,
                                 category=category, sources=[s.to_dict() for s in intake.sources],
                                 zero_retention=bool(zero_retention))
    worker.enqueue(run.id)
    return run


def retry_case(user, run: CaseRun) -> None:
    """Xato bilan tugagan tahlilni qaytadan navbatga qo'yish."""
    if run.status != CaseRun.Status.FAILED:
        raise CaseError(_("Faqat xato bilan tugagan tahlilni qayta boshlash mumkin"), status=409, code="not_failed")
    if run.quota_refunded:  # kvota qaytarilgan edi — qayta urinish yana kvota band qiladi
        decision = quota.reserve_case(user, run.pages)
        if not decision.ok:
            raise CaseError(decision.message, status=429, code=f"quota_{decision.code}")
    # Atomik o'tish: ikki parallel "qayta urinish" faqat bittasini navbatga qo'yadi (ikki marta xarajat/kvota bo'lmasin)
    moved = CaseRun.objects.filter(pk=run.pk, status=CaseRun.Status.FAILED).update(
        status=CaseRun.Status.QUEUED, stage="Qayta navbatda", progress=0, error="", quota_refunded=False)
    if not moved:
        if run.quota_refunded:   # yuqorida band qilingan kvota qaytariladi
            quota.refund_case(user, run.pages)
        raise CaseError(_("Faqat xato bilan tugagan tahlilni qayta boshlash mumkin"), status=409, code="not_failed")
    worker.enqueue(run.id)


def delete_case(run: CaseRun) -> None:
    """Ishni butunlay o'chirish: PDF, hisobot va yozuv. Tahlil ketayotgan ishni o'chirib bo'lmaydi."""
    if run.status == CaseRun.Status.RUNNING:
        raise CaseError(_("Tahlil ketayotgan ishni oʻchirib boʻlmaydi"), status=409, code="running")
    storage.delete_file(run.pdf_path)
    storage.delete_file(run.report_path)
    run.delete()


def read_pdf(run: CaseRun) -> bytes | None:
    try:
        return storage.read_file(run.pdf_path) if run.pdf_path else None
    except FileNotFoundError:
        return None


def read_report(run: CaseRun) -> dict:
    if run.status != CaseRun.Status.DONE:
        raise CaseError(_("Tahlil hali tayyor emas"), status=409, code="not_ready")
    return json.loads(storage.read_file(run.report_path))


def confirmation_info(run: CaseRun) -> dict:
    info = export.confirmation_info(read_report(run))
    info["confirmed_at"] = run.lawyer_confirmed_at.isoformat() if run.lawyer_confirmed_at else None
    return info


def confirm_case(run: CaseRun) -> None:
    """TZ §12: advokat "asosiy dalillar va qonun moddalari bilan tanishdim" deb tasdiqlaydi."""
    if run.status != CaseRun.Status.DONE:
        raise CaseError(_("Tahlil hali tayyor emas"), status=409, code="not_ready")
    run.lawyer_confirmed_at = timezone.now()
    CaseRun.objects.filter(pk=run.pk).update(lawyer_confirmed_at=run.lawyer_confirmed_at)


EXPORT_TYPES = {
    "docx": ("application/vnd.openxmlformats-officedocument.wordprocessingml.document", export.to_docx),
    "pdf": ("application/pdf", export.to_pdf),
}


def export_file(run: CaseRun, fmt: str, lawyer_name: str) -> tuple[bytes, str, str]:
    """Rasmiy fayl (faqat tasdiqdan keyin). Qaytaradi: (mazmun, content_type, fayl nomi)."""
    if fmt not in EXPORT_TYPES:
        raise CaseError(_("Nomaʼlum format"), status=404, code="format")
    report = read_report(run)
    if run.lawyer_confirmed_at is None:  # TZ §12: tasdiqsiz rasmiy fayl yaratilmaydi
        raise CaseError(_("Avval “tanishdim” tasdigʻini bering"), status=403, code="not_confirmed")
    content_type, render_file = EXPORT_TYPES[fmt]
    blocks = export.build_blocks(report, run.title, lawyer_name, run.lawyer_confirmed_at)
    return render_file(blocks), content_type, f"MEZON_tahlil_{run.id.hex[:8]}.{fmt}"
