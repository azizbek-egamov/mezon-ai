"""lex.uz bilan sinxronizatsiya (TZ §6.4). Har kecha (`manage.py sync_lex`):

1. RSS va reyestr qidiruvining birinchi sahifalari (oxirgi `days` kun) o'qiladi.
2. Yangi hujjatlar reyestrga qo'shiladi; mavjudlarining maqomi (kuchda / kuchini yo'qotgan) yangilanadi.
   Kuchini yo'qotib yadrodan chiqqan hujjat qidiruv indeksidan o'chiriladi.
3. Qayta yuklanadigan yadro hujjatlari:
   - yangi yadro hujjatlari (yangi qonun, Plenum qarori…);
   - yangi o'zgartirish kirituvchi hujjatlar havola qilgan yadro hujjatlari (sahifasidagi /docs/<id> havolalari);
   - kuchga kirish sanasi yetib kelgan tahriri bor hujjatlar (avval kelajak sanali bo'lgan tahrir endi joriy);
   - `check_codes` — barcha kodekslar va Konstitutsiya (haftalik to'liq tekshiruv uchun).
   Joriy tahrir yorlig'i o'zgargan bo'lsa — qayta parsing, qayta indekslash va (bo'lsa) tahrirlar tarixini yangilash.
4. Natija `SyncRun` jurnaliga yoziladi. lex.uz ga so'rovlar orasida LEX_REQUEST_DELAY (≥ 0.5 s).
"""
import logging
from dataclasses import dataclass, field
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from . import normalize as N
from .history import build_history
from .ingest import register_editions, store_parsed
from .lexuz_client import LexUzClient
from .models import CorpusTier, DocType, LegalActArticle, LegalActDocument, LegalActEdition, SyncRun
from .parser import parse_document
from .registry import fetch_recent, fetch_rss, linked_documents
from .translations import fetch_translations

logger = logging.getLogger(__name__)


@dataclass
class SyncStats:
    seen: int = 0
    new_documents: list[int] = field(default_factory=list)
    status_changed: list[int] = field(default_factory=list)
    left_core: list[int] = field(default_factory=list)
    refreshed: list[int] = field(default_factory=list)   # joriy tahriri o'zgargan, qayta yuklangan
    unchanged: list[int] = field(default_factory=list)   # tekshirildi, o'zgarmagan
    translations_updated: list[int] = field(default_factory=list)  # kirill/rus versiyasi yangilangan
    indexed_chunks: int = 0
    errors: list[str] = field(default_factory=list)


def upsert_registry(rows: list[dict], stats: SyncStats) -> None:
    """Reyestr yozuvlarini bazaga yozadi: yangilarini qo'shadi, maqomi o'zgarganlarini yangilaydi."""
    from .management.commands.import_registry import build_documents

    effective = {abs(int(r["id"])): r.get("effective_from") for r in rows if r.get("effective_from")}
    built = build_documents(rows)
    stats.seen = len(built)
    existing = LegalActDocument.objects.in_bulk(list(built))
    with transaction.atomic():
        for abs_id, doc in built.items():
            old = existing.get(abs_id)
            if old is None:
                doc.effective_from = effective.get(abs_id)
                doc.save()
                stats.new_documents.append(abs_id)
                continue
            if old.status != doc.status:
                was_core = old.corpus_tier == CorpusTier.CORE
                old.status = doc.status
                old.corpus_tier = N.corpus_tier(old.doc_type, old.status)
                old.save(update_fields=["status", "corpus_tier"])
                stats.status_changed.append(abs_id)
                if was_core and old.corpus_tier != CorpusTier.CORE:
                    stats.left_core.append(abs_id)
            for f in ("lex_id_lat", "lex_id_cyr", "title_uz_lat", "title_uz_cyr", "title_ru"):  # yangi til versiyasi
                if getattr(doc, f) and not getattr(old, f):
                    setattr(old, f, getattr(doc, f))
                    old.save(update_fields=[f])


def documents_to_refresh(client: LexUzClient, stats: SyncStats, check_codes: bool) -> set[int]:
    targets: set[int] = set()
    new_docs = LegalActDocument.objects.filter(abs_id__in=stats.new_documents)
    targets |= {d.abs_id for d in new_docs if d.corpus_tier == CorpusTier.CORE}
    core = set(LegalActDocument.objects.filter(corpus_tier=CorpusTier.CORE).values_list("abs_id", flat=True))
    for doc in new_docs.filter(is_amending=True):
        try:
            html = client.get_document_html(doc.primary_lex_id)
        except Exception as e:
            stats.errors.append(f"{doc.abs_id} (o'zgartirish hujjati): {e}")
            continue
        targets |= (linked_documents(html) & core) - {doc.abs_id}
    # Kelajak sanali tahriri kuchga kirgan hujjatlar: joriy tahrir sanasidan keyingi, bugungacha bo'lgan tahrir bor.
    today = timezone.localdate()
    for cur in LegalActEdition.objects.filter(is_current=True, document__corpus_tier=CorpusTier.CORE,
                                              edition_date__isnull=False):
        if LegalActEdition.objects.filter(document_id=cur.document_id, edition_date__gt=cur.edition_date,
                                          edition_date__lte=today).exists():
            targets.add(cur.document_id)
    if check_codes:
        targets |= set(LegalActDocument.objects.filter(corpus_tier=CorpusTier.CORE, doc_type__in=[
            DocType.CODE, DocType.CONSTITUTION]).values_list("abs_id", flat=True))
    return targets


class SuspiciousPage(Exception):
    """lex.uz javobi buzuq/bo'sh ko'rinadi — mavjud moddalar o'chirib yuborilmaydi."""


def check_page_sane(doc: LegalActDocument, parsed) -> None:
    """lex.uz xizmat sahifasi yoki dizayn o'zgarishi bo'sh/qisqa parse bersa, korpusdagi hujjatni o'chirib yubormaslik uchun:
    moddalar yo'qolsa yoki yarmidan ko'pi kamaysa — yangilash rad etiladi (xato `SyncRun` jurnaliga tushadi)."""
    existing = LegalActArticle.objects.filter(document=doc, edition__is_current=True).count()
    if not existing:
        return
    new = len(parsed.articles)
    if new == 0 or (existing >= 10 and new < existing * 0.5):
        raise SuspiciousPage(f"sahifada {new} ta modda (bazada {existing} ta) — yangilanmadi, lex.uz javobini tekshiring")


def refresh_document(doc: LegalActDocument, client: LexUzClient, stats: SyncStats, index: bool) -> None:
    cache_path = client._cache_path(doc.primary_lex_id, None)
    previous = cache_path.read_text(encoding="utf-8") if cache_path.exists() else None
    html = client.get_document_html(doc.primary_lex_id, refresh=True)
    parsed = parse_document(html)
    try:
        check_page_sane(doc, parsed)
    except SuspiciousPage:
        client.restore_cache(doc.primary_lex_id, previous)   # yaroqsiz sahifa keshni buzmasin
        raise
    current = doc.editions.filter(is_current=True).first()
    if current is not None and current.edition_label == (parsed.current_edition or ""):
        register_editions(doc, parsed.editions, client)  # yangi kelajak sanali tahrirlar ro'yxatga qo'shiladi
        stats.unchanged.append(doc.abs_id)
        return
    history_from = doc.history_from
    store_parsed(doc, html, client)
    stats.refreshed.append(doc.abs_id)
    try:  # kirill va rus matnlari asosiy matn bilan birga yangilanadi (store_parsed moddalarni qayta yozadi)
        fetch_translations(doc, client, refresh=True)
    except Exception as e:  # tarjima xatosi asosiy matnni yangilashga xalaqit bermasin
        logger.exception("Tarjimalar: %s", doc.abs_id)
        stats.errors.append(f"{doc.abs_id} (tarjimalar): {e}")
    if history_from:  # tarix bor edi — yangi tahrir bilan qayta quriladi (eski tahrirlar keshdan)
        doc.refresh_from_db()
        build_history(doc, client, since=history_from)
    if index:
        from apps.rag.indexer import reindex_documents
        stats.indexed_chunks += reindex_documents([doc.abs_id])


def refresh_stale_translations(client: LexUzClient, stats: SyncStats, index: bool) -> None:
    """Tarjimasi asosiy matndan orqada qolgan (stale) yadro hujjatlari: tarjima sahifasi qayta olinadi — lex.uz
    tarjimani keyin yangilagan bo'lishi mumkin. Tahriri o'zgargan hujjat qayta indekslanadi."""
    for doc in LegalActDocument.objects.filter(corpus_tier=CorpusTier.CORE).exclude(translations={}):
        if not any(i.get("stale") for i in doc.translations.values()):
            continue
        before = {lang: i.get("edition") for lang, i in doc.translations.items()}
        try:
            result = fetch_translations(doc, client, refresh=True)
        except Exception as e:
            stats.errors.append(f"{doc.abs_id} (tarjimalar): {e}")
            continue
        if any(info.get("edition") != before.get(lang) for lang, info in result.items()):
            stats.translations_updated.append(doc.abs_id)
            if index:
                from apps.rag.indexer import reindex_documents
                stats.indexed_chunks += reindex_documents([doc.abs_id])


def run_sync(days: int = 60, max_pages: int = 30, check_codes: bool = False, index: bool = True,
             client: LexUzClient | None = None, log=print) -> SyncRun:
    client = client or LexUzClient()
    run = SyncRun.objects.create()
    stats = SyncStats()
    lines: list[str] = []

    def say(msg: str) -> None:
        lines.append(msg)
        log(msg)

    try:
        since = timezone.localdate() - timedelta(days=days)
        rows = fetch_rss(client)
        say(f"RSS: {len(rows)} ta yozuv")
        recent = fetch_recent(client, since, max_pages=max_pages)
        say(f"Reyestr: {len(recent)} ta yozuv ({since:%d.%m.%Y} dan beri)")
        upsert_registry(rows + recent, stats)
        say(f"Yangi hujjatlar: {len(stats.new_documents)}, maqomi o'zgargan: {len(stats.status_changed)}")
        if index and stats.left_core:
            from apps.rag.indexer import remove_documents
            remove_documents(stats.left_core)
            say(f"Yadrodan chiqib, indeksdan o'chirildi: {stats.left_core}")
        targets = documents_to_refresh(client, stats, check_codes)
        say(f"Tekshiriladigan yadro hujjatlari: {len(targets)}")
        for doc in LegalActDocument.objects.filter(abs_id__in=targets):
            try:
                refresh_document(doc, client, stats, index)
            except Exception as e:  # bitta hujjat xatosi butun sinxronizatsiyani to'xtatmasin
                logger.exception("Sinxronizatsiya: %s", doc.abs_id)
                stats.errors.append(f"{doc.abs_id}: {e}")
        refresh_stale_translations(client, stats, index)
        if stats.translations_updated:
            say(f"Tarjimasi yangilandi: {stats.translations_updated}")
        say(f"Qayta yuklandi: {stats.refreshed or 'yoʻq'}; oʻzgarmagan: {len(stats.unchanged)}; "
            f"indekslangan boʻlaklar: {stats.indexed_chunks}")
        run.status = SyncRun.Status.PARTIAL if stats.errors else SyncRun.Status.OK
    except Exception as e:
        logger.exception("Sinxronizatsiya xatosi")
        stats.errors.append(str(e))
        run.status = SyncRun.Status.FAILED
    for err in stats.errors:
        say(f"! {err}")
    run.stats = {k: v for k, v in stats.__dict__.items()}
    run.log, run.finished_at = "\n".join(lines), timezone.now()
    run.save()
    return run
