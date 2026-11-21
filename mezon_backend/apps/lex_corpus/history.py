"""Moddalar tahrirlari tarixi (TZ §4.2.3 "vaqt filtri", §6.1 tahrirlar).

lex.uz da hujjatning har bir tahriri `?ONDATE=<yorliq>` bilan ochiladi. Tahrirlar xronologik tartibda o'qiladi va
har bir matn birligi (modda/band) uchun faqat matni O'ZGARGANDA yangi versiya yoziladi:

    versiya.valid_from  = shu matn birinchi paydo bo'lgan tahrir sanasi
    versiya.valid_until = keyingi (boshqacha matnli) tahrir sanasidan bir kun oldin; joriy matn uchun — bo'sh

Joriy tahrir qatorlari (Qdrant da indekslangan) o'z o'rnida qoladi — ularga faqat valid_from/valid_until va
unit_key yoziladi. Boshqa versiyalar o'zi birinchi paydo bo'lgan tahrirga bog'langan alohida qatorlar bo'ladi
(Qdrant ga kirmaydi; qidiruv joriy matn bo'yicha topadi, keyin voqea sanasidagi versiya bazadan olinadi).

Taxmin: tahrir yorlig'idagi sana — o'sha tahrir kuchga kirgan sana (lex.uz shunday ko'rsatadi). Kelajak sanali
tahrirlar ham yuklanadi: ularning versiyalari valid_from > bugun bo'ladi (hali kuchga kirmagan).
"""
import re
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta

from django.db import transaction

from .models import LegalActArticle, LegalActDocument, LegalActEdition
from .parser import Article, parse_document


def unit_keys(units) -> list[str]:
    """Barqaror kalit: 'ARTICLE:168#1'. Raqam bir hujjatda takrorlansa (masalan, Plenum bandlari bo'limlarda),
    takror tartibi bilan ajratiladi. `units` — parser Article lari yoki LegalActArticle lar (tartib bo'yicha)."""
    seen: Counter = Counter()
    keys = []
    for u in units:
        unit_type = getattr(u, "unit_type", "ARTICLE")
        number = getattr(u, "number", None) or getattr(u, "article_number", "") or ""
        base = f"{unit_type}:{number}"
        seen[base] += 1
        keys.append(f"{base}#{seen[base]}")
    return keys


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def article_fields(a: Article, lang: str = "lat") -> dict:
    """Matn birligi -> LegalActArticle maydonlari. `lang` — sahifa tili ('lat' | 'cyr' | 'ru')."""
    return {
        "position": a.position, "unit_type": a.unit_type, "article_number": a.number, "heading": a.heading,
        "section_path": " / ".join(a.section_path), "source_lang": lang,
        "content_uz_lat": a.text if lang == "lat" else "", "content_uz_cyr": a.text if lang == "cyr" else "",
        "content_ru": a.text if lang == "ru" else "",
        "parts": [{"n": p["n"], "elem_ids": [x["elem_id"] for x in p["paragraphs"]], "text": p["text"]}
                  for p in a.parts],
        "lex_elem_id": a.elem_id,
    }


@dataclass
class Version:
    key: str
    article: Article
    edition: LegalActEdition
    valid_from: date
    valid_until: date | None = None
    in_current: bool = False


@dataclass
class HistoryStats:
    editions: int = 0
    versions: int = 0
    changed_units: int = 0
    history_from: date | None = None
    errors: list[str] = field(default_factory=list)


def _edition_html(client, doc: LegalActDocument, edition: LegalActEdition) -> str:
    # Joriy tahrir — mavjud keshdan (fetch_documents yuklagan sahifa), qolganlari — ONDATE bilan.
    label = None if edition.is_current else edition.edition_label
    return client.get_document_html(doc.primary_lex_id, label)


def build_history(doc: LegalActDocument, client, since: date, on_edition=None) -> HistoryStats:
    stats = HistoryStats()
    current = doc.editions.filter(is_current=True).first()
    if current is None:
        raise ValueError("Joriy tahrir yuklanmagan — avval fetch_documents")
    editions = [e for e in doc.editions.exclude(edition_date=None).order_by("edition_date", "edition_label")
                if e.edition_date >= since or e.pk == current.pk]
    if current not in editions:
        editions.append(current)

    open_: dict[str, Version] = {}
    closed: list[Version] = []
    parsed_any = False
    for n, edition in enumerate(editions, 1):
        try:
            parsed = parse_document(_edition_html(client, doc, edition))
        except Exception as e:  # bitta tahrir yuklanmasa — tarixda bo'shliq, lekin butun hujjat to'xtamasin
            stats.errors.append(f"{edition.edition_label}: {e}")
            continue
        day = edition.edition_date
        if not parsed_any:
            stats.history_from = day
            parsed_any = True
        units = dict(zip(unit_keys(parsed.articles), parsed.articles))
        for key in list(open_):
            if key not in units:  # birlik chiqarib tashlangan
                v = open_.pop(key)
                v.valid_until = day - timedelta(days=1)
                closed.append(v)
        for key, art in units.items():
            v = open_.get(key)
            if v is not None and _norm(v.article.text) == _norm(art.text) and v.article.heading == art.heading:
                if edition.pk == current.pk:
                    v.in_current = True
                continue
            if v is not None:
                v.valid_until = day - timedelta(days=1)
                closed.append(v)
            open_[key] = Version(key, art, edition, day, in_current=edition.pk == current.pk)
        stats.editions += 1
        if on_edition:
            on_edition(n, len(editions), edition)
    if not parsed_any:
        return stats
    versions = closed + list(open_.values())
    # Bir kunda bir nechta tahrir: oraliq versiya hech qachon alohida kuchda bo'lmagan — tashlanadi.
    versions = [v for v in versions if v.valid_until is None or v.valid_until >= v.valid_from]
    _store(doc, current, versions, stats)
    return stats


def _store(doc: LegalActDocument, current: LegalActEdition, versions: list[Version], stats: HistoryStats) -> None:
    with transaction.atomic():
        LegalActArticle.objects.filter(document=doc).exclude(edition=current).delete()
        current_rows = list(LegalActArticle.objects.filter(document=doc, edition=current).order_by("position"))
        by_key = dict(zip(unit_keys(current_rows), current_rows))
        lang = current_rows[0].source_lang if current_rows else "lat"
        new_rows = []
        for v in versions:
            row = by_key.get(v.key) if v.in_current else None
            if row is not None:
                row.unit_key, row.valid_from, row.valid_until = v.key, v.valid_from, v.valid_until
                continue
            edition = v.edition if v.edition.pk != current.pk else None
            if edition is None:  # joriy tahrirdagi, lekin bazada mos qatori yo'q (kesh va baza farqi) — o'tkazamiz
                continue
            new_rows.append(LegalActArticle(document=doc, edition=edition, unit_key=v.key, valid_from=v.valid_from,
                                            valid_until=v.valid_until, **article_fields(v.article, lang)))
        LegalActArticle.objects.bulk_update(current_rows, ["unit_key", "valid_from", "valid_until"], batch_size=500)
        LegalActArticle.objects.bulk_create(new_rows, batch_size=500)
        doc.history_from = stats.history_from
        doc.save(update_fields=["history_from"])
    stats.versions = len(versions)
    stats.changed_units = len({v.key for v in versions if not v.in_current})


# ---------------------------------------------------------------------------- sana bo'yicha so'rovlar

def _d(day: date | None) -> str:
    return f"{day:%d.%m.%Y}" if day else "…"


@dataclass
class AsOf:
    """Joriy modda matnining voqea sanasidagi holati."""
    state: str                 # same | changed | not_yet | unknown
    on_date: date
    version: LegalActArticle | None = None   # sanadagi versiya (state == changed)
    note: str = ""


def as_of(article: LegalActArticle, on_date: date) -> AsOf:
    doc = article.document
    if doc.history_from is None or on_date < doc.history_from:
        since = f" ({doc.history_from:%d.%m.%Y} dan)" if doc.history_from else ""
        return AsOf("unknown", on_date, note=f"bu sanadagi tahrir bazada yoʻq{since} — joriy matn koʻrsatilgan")
    if article.is_valid_on(on_date):
        return AsOf("same", on_date)
    if article.unit_key:
        version = (LegalActArticle.objects.select_related("edition", "document")
                   .filter(document_id=article.document_id, unit_key=article.unit_key)
                   .exclude(pk=article.pk)
                   .filter(valid_from__lte=on_date).order_by("-valid_from").first())
        if version is not None and version.is_valid_on(on_date):
            return AsOf("changed", on_date, version=version,
                        note=f"{on_date:%d.%m.%Y} da boshqacha tahrirda edi "
                             f"({_d(version.valid_from)}–{_d(version.valid_until)})")
    if article.valid_from and on_date < article.valid_from:
        return AsOf("not_yet", on_date, note=f"bu norma {article.valid_from:%d.%m.%Y} dan kuchga kirgan — "
                                              f"{on_date:%d.%m.%Y} da yoʻq edi")
    return AsOf("unknown", on_date, note="sanadagi tahrir aniqlanmadi")
