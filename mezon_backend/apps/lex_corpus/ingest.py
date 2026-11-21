"""lex.uz hujjat sahifasini bazaga yozish (fetch_documents va sinxronizatsiya uchun umumiy)."""
from django.db import transaction
from django.utils import timezone

from .history import article_fields, unit_keys
from .lexuz_client import LexUzClient, content_hash
from .models import LegalActArticle, LegalActDocument, LegalActEdition
from .normalize import text_lang
from .parser import edition_label_date, parse_document


def register_editions(doc: LegalActDocument, labels: list[str], client: LexUzClient) -> int:
    """Sahifadagi tahrirlar ro'yxatini (kelajak sanalilari bilan) bazaga qo'shadi; yangilari soni."""
    created = 0
    for label in labels:
        _, new = LegalActEdition.objects.get_or_create(
            document=doc, edition_label=label,
            defaults={"edition_date": edition_label_date(label),
                      "source_url": client.document_url(doc.primary_lex_id, label)},
        )
        created += new
    return created


def store_parsed(doc: LegalActDocument, html: str, client: LexUzClient) -> tuple[LegalActEdition, int]:
    parsed = parse_document(html)
    lex_id = doc.primary_lex_id
    label = parsed.current_edition or ""
    now = timezone.now()
    with transaction.atomic():
        LegalActEdition.objects.filter(document=doc, is_current=True).update(is_current=False)
        edition, _ = LegalActEdition.objects.update_or_create(
            document=doc, edition_label=label,
            defaults={"is_current": True, "edition_date": edition_label_date(label) if label else None,
                      "source_url": client.document_url(lex_id, label or None),
                      "content_hash": content_hash(html), "fetched_at": now},
        )
        register_editions(doc, parsed.editions, client)
        # Avvalgi joriy tahrir qatorlari va tarixiy versiyalar eskirdi — tarix `fetch_history` bilan qayta quriladi.
        LegalActArticle.objects.filter(document=doc).delete()
        lang = text_lang(parsed.title or doc.title_uz_lat or doc.title_uz_cyr or doc.title_ru)
        LegalActArticle.objects.bulk_create([
            LegalActArticle(document=doc, edition=edition, unit_key=key, **article_fields(a, lang))
            for key, a in zip(unit_keys(parsed.articles), parsed.articles)
        ], batch_size=500)
        if doc.history_from:
            doc.history_from = None
            doc.save(update_fields=["history_from"])
        doc.content_hash = edition.content_hash
        doc.last_synced_at = now
        doc.translations = {}  # moddalar qayta yozildi — kirill/rus matnlari `fetch_translations` bilan qaytadan olinadi
        doc.save(update_fields=["content_hash", "last_synced_at", "translations"])
    return edition, len(parsed.articles)
