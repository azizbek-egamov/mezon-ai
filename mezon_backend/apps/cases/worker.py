"""Ish tahlillarini fonda bajaruvchi navbat (dev rejimi: server jarayoni ichida bitta oqim).

GPU bitta bo'lgani uchun ishlar ketma-ket bajariladi. Production da Celery (TZ §9.1, `gpu` navbati) bilan almashtiriladi.
"""
import json
import itertools
import logging
import queue
import threading

from django.conf import settings
from django.db import close_old_connections
from django.utils import timezone, translation
from django.utils.translation import gettext as _, gettext_noop

from apps.billing import quota

from . import storage
from .models import CaseRun

logger = logging.getLogger(__name__)

# (ustuvorlik, tartib raqami, run_id): Enterprise (priority_queue) tarifi oldinda, qolganlar kelish tartibida
_queue: "queue.PriorityQueue[tuple[int, int, str]]" = queue.PriorityQueue()
_counter = itertools.count()
_thread: threading.Thread | None = None
_start_lock = threading.Lock()
_active: set[str] = set()   # shu jarayonda navbatda yoki bajarilayotgan ishlar
_active_lock = threading.Lock()


def report_path(run: CaseRun) -> str:
    return str(settings.DATA_DIR / "case_runs" / f"web_{run.id}.json")


GENERIC_ERROR = gettext_noop(
    "Tahlil vaqtida texnik xato yuz berdi. Qayta urinib koʻring; takrorlansa — administratorga murojaat qiling.")
BUDGET_ERROR = gettext_noop("AI xarajat chegarasi tugadi — administratorga murojaat qiling.")


def user_error(exc: Exception) -> str:
    """Foydalanuvchiga ko'rinadigan xato: ichki tafsilot (manzil, port, stack) yo'q — u faqat server logida.
    Bizning o'zimiz yozgan, foydalanuvchiga mo'ljallangan xatolar (masalan, BudgetExceeded) — umumiy matn bilan."""
    from apps.rag.llm import BudgetExceeded

    return _(BUDGET_ERROR if isinstance(exc, BudgetExceeded) else GENERIC_ERROR)


def process(run_id: str) -> None:
    from .pipeline import analyze_pdf  # og'ir importlar (torch) faqat ish boshlanganda

    # Atomik "egallash": faqat QUEUED ish boshlanadi. Navbatda o'chirilgan ish, ikki marta navbatga tushgan yoki
    # allaqachon bajarilgan ish — jim o'tkazib yuboriladi (ikki marta LLM xarajati bo'lmasin, oqim o'lmasin).
    claimed = CaseRun.objects.filter(pk=run_id, status=CaseRun.Status.QUEUED).update(
        status=CaseRun.Status.RUNNING, stage="Boshlandi", progress=1)
    if not claimed:
        logger.info("Ish o'tkazib yuborildi (navbatda emas yoki o'chirilgan): %s", run_id)
        return
    run = CaseRun.objects.select_related("owner").get(pk=run_id)
    day = timezone.localtime(run.created_at).date()

    def progress(pct: int, stage: str) -> None:
        CaseRun.objects.filter(pk=run_id).update(progress=pct, stage=stage[:200])

    try:
        with storage.decrypted_copy(run.pdf_path) as pdf:
            report = analyze_pdf(pdf, progress=progress, category=run.category)
        # Hisobotda F.I.Sh. va boshqa shaxsiy ma'lumotlar ochiq — faqat shifrlangan holda saqlanadi.
        path = storage.write_encrypted(report_path(run), json.dumps(report, ensure_ascii=False).encode("utf-8"))
        pdf_path = run.pdf_path
        if run.zero_retention:  # TZ §5.3: tahlil tugagach yuklangan fayl o'chiriladi
            storage.delete_file(run.pdf_path)
            pdf_path = ""
        CaseRun.objects.filter(pk=run_id).update(
            status=CaseRun.Status.DONE, progress=100, stage="Tayyor", report_path=path, pdf_path=pdf_path,
            pages=report["pages"], cost_usd=report["cost_usd"])
    except Exception as e:  # foydalanuvchiga — xavfsiz matn; batafsil (sabab, stack) — faqat server logida
        logger.exception("Ish tahlili xatosi: %s", run_id)
        language = getattr(run.owner, "language", settings.LANGUAGE_CODE) if run.owner_id else settings.LANGUAGE_CODE
        with translation.override(language):
            safe_error = user_error(e)
        CaseRun.objects.filter(pk=run_id).update(status=CaseRun.Status.FAILED, error=safe_error,
                                                 quota_refunded=bool(run.owner_id))
        if run.owner_id:  # foydalanuvchi aybi yo'q — kvota qaytariladi
            quota.refund_case(run.owner, run.pages, day)
        return
    if run.owner_id:
        try:
            quota.record_cost(run.owner, report["cost_usd"], day)
        except Exception:  # hisobot tayyor — xarajat yozuvi xatosi ishni buzmasin
            logger.exception("Xarajatni yozib boʻlmadi: %s", run_id)


def _loop() -> None:
    while True:
        _, _, run_id = _queue.get()
        close_old_connections()
        try:
            process(run_id)
        except Exception:  # bitta ish xatosi butun navbatni to'xtatmasin
            logger.exception("Navbat oqimi xatosi: %s", run_id)
        finally:
            with _active_lock:
                _active.discard(run_id)
            close_old_connections()
            _queue.task_done()


def is_active(run_id) -> bool:
    """Ish shu jarayonda navbatda yoki bajarilmoqdami (server qayta yonganidan keyingi tiklash ularga tegmasin)."""
    with _active_lock:
        return str(run_id) in _active


def enqueue(run_id) -> None:
    global _thread
    with _start_lock:
        if _thread is None or not _thread.is_alive():
            _thread = threading.Thread(target=_loop, name="case-worker", daemon=True)
            _thread.start()
    run_id = str(run_id)
    run = CaseRun.objects.select_related("owner").filter(pk=run_id).first()
    priority = 0 if run is not None and run.owner_id and quota.plan_for(run.owner).priority_queue else 1
    with _active_lock:
        if run_id in _active:  # allaqachon navbatda yoki bajarilmoqda — ikki marta qo'yilmasin
            return
        _active.add(run_id)
        _queue.put((priority, next(_counter), run_id))
