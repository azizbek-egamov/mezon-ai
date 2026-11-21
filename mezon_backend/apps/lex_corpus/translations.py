"""Hujjatning boshqa til versiyalari: o'zbek kirill va rus matnlari (TZ §5.4).

lex.uz da har bir til versiyasi alohida hujjat (id) sifatida turadi: lotin — manfiy id (-111453), kirill — musbat
(111453), rus — boshqa raqam (111457). Hujjat sahifasidagi til almashtirgichdan (`parse_language_links`) id lar
olinadi, o'sha sahifalar yuklanadi va har bir modda asosiy (lotin) moddaga `unit_key` ("ARTICLE:168#1") bo'yicha
moslashtiriladi — modda raqamlari barcha tillarda bir xil.

Saqlash: matn `content_uz_cyr` / `content_ru` da, sarlavha, qismlar (lex.uz element id lari bilan — havola uchun)
va bo'lim yo'li `LegalActArticle.i18n[til]` da. Holat — `LegalActDocument.translations[til]`:

    lex_id, edition (tahrir yorlig'i), matched / total (nechta modda moslashdi), stale (tarjima tahriri asosiy
    tahrirdan sanasi bilan farq qiladi — matn eskirgan bo'lishi mumkin), rejected (tuzilma mos kelmadi —
    saqlanmadi), fetched_at.

Tarjima tahriri asosiydan farq qilsa va uning tahrirlar ro'yxatida asosiy tahrir sanasi bor bo'lsa, shu tahrir
(`?ONDATE=`) olinadi — shunda matnlar bir sanadagi holatda bo'ladi.
"""
import logging

from django.utils import timezone

from . import normalize as N
from .history import article_fields, unit_keys
from .lexuz_client import LexUzClient
from .models import LANG_FIELDS, LANGS, LegalActArticle, LegalActDocument
from .parser import ParsedDocument, edition_label_date, parse_document, parse_language_links

logger = logging.getLogger(__name__)

MIN_MATCH_RATIO = 0.5   # moddalarning kamida shu qismi moslashmasa — tuzilma boshqacha, tarjima saqlanmaydi
TITLE_FIELDS = {"lat": "title_uz_lat", "cyr": "title_uz_cyr", "ru": "title_ru"}
LEX_ID_FIELDS = {"lat": "lex_id_lat", "cyr": "lex_id_cyr", "ru": "lex_id_ru"}


def _aligned_page(client: LexUzClient, lex_id: str, current_date, refresh: bool) -> tuple[ParsedDocument, bool]:
    """Tarjima sahifasi asosiy tahrir sanasiga moslab olinadi. Qaytaradi: (sahifa, stale)."""
    parsed = parse_document(client.get_document_html(lex_id, refresh=refresh))
    if current_date is None or not parsed.current_edition or edition_label_date(parsed.current_edition) == current_date:
        return parsed, False
    same_day = sorted(label for label in parsed.editions if edition_label_date(label) == current_date)
    if not same_day:
        return parsed, True
    return parse_document(client.get_document_html(lex_id, same_day[-1], refresh=refresh)), False


def _clear(rows: list[LegalActArticle], lang: str) -> None:
    for row in rows:
        setattr(row, LANG_FIELDS[lang], "")
        row.i18n = {k: v for k, v in (row.i18n or {}).items() if k != lang}


def fetch_translations(doc: LegalActDocument, client: LexUzClient | None = None,
                       langs: tuple[str, ...] | list[str] | None = None, refresh: bool = False) -> dict[str, dict]:
    """Hujjatning kirill va rus versiyalarini yuklab, joriy tahrir moddalariga yozadi. Qaytaradi: {til: holat}.
    refresh=True: tarjima sahifalari keshdan emas, lex.uz dan qayta olinadi (asosiy sahifa keshdan)."""
    client = client or LexUzClient()
    current = doc.editions.filter(is_current=True).first()
    rows = list(doc.articles.filter(edition=current).order_by("position")) if current else []
    if not rows:
        return {}
    source = rows[0].source_lang
    links = parse_language_links(client.get_document_html(doc.primary_lex_id))
    keys = unit_keys(rows)
    by_key = dict(zip(keys, rows))
    result: dict[str, dict] = {}
    for lang in LANGS:
        if lang == source or lang not in links or (langs is not None and lang not in langs):
            continue
        lex_id = links[lang]
        try:
            parsed, stale = _aligned_page(client, lex_id, current.edition_date, refresh)
        except Exception as e:  # bitta tilning xatosi qolgan tilni to'xtatmasin
            logger.warning("Tarjima %s/%s: %s", doc.abs_id, lang, e)
            result[lang] = {"lex_id": lex_id, "error": str(e)[:200]}
            continue
        translated = dict(zip(unit_keys(parsed.articles), parsed.articles))
        matched = [k for k in by_key if k in translated]
        info = {"lex_id": lex_id, "edition": parsed.current_edition or "", "matched": len(matched),
                "total": len(rows), "stale": stale, "fetched_at": timezone.now().isoformat(timespec="seconds")}
        if not matched or len(matched) < MIN_MATCH_RATIO * len(rows):
            info["rejected"] = f"tuzilma mos kelmadi ({len(matched)}/{len(rows)} modda)"
            _clear(rows, lang)
        else:
            for key, row in by_key.items():
                art = translated.get(key)
                if art is None:  # bu moddaning tarjimasi yo'q (masalan, rus tilida 230³ yo'q)
                    _clear([row], lang)
                    continue
                f = article_fields(art, lang)
                setattr(row, LANG_FIELDS[lang], art.text)
                row.i18n = {**(row.i18n or {}), lang: {
                    "heading": f["heading"], "parts": f["parts"], "section_path": f["section_path"],
                    "elem_id": f["lex_elem_id"]}}
        LegalActArticle.objects.bulk_update(rows, [LANG_FIELDS[lang], "i18n"], batch_size=500)
        if parsed.title and not getattr(doc, TITLE_FIELDS[lang]):
            setattr(doc, TITLE_FIELDS[lang], N.normalize_title(parsed.title))
        setattr(doc, LEX_ID_FIELDS[lang], lex_id)
        doc.translations = {**doc.translations, lang: info}
        doc.save(update_fields=[TITLE_FIELDS[lang], LEX_ID_FIELDS[lang], "translations"])
        result[lang] = info
    return result
