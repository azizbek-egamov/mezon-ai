"""Hujjatlarning o'zbek kirill va rus tilidagi matnlarini yuklash (TZ §5.4, 8-bosqich).

    python manage.py fetch_translations 111453 111460          # aniq hujjatlar (abs_id)
    python manage.py fetch_translations --tier CORE --skip-done  # yadro; avval yuklanganlar o'tkaziladi
    python manage.py fetch_translations --tier CORE --lang ru    # faqat rus tili

Sahifalar `data/lex_cache` ga keshlanadi (so'rovlar orasida LEX_REQUEST_DELAY). Yuklangandan keyin yangi matnlarni
qidiruvga qo'shish: `manage.py build_index --langs cyr ru --add`.
"""
import time

from django.core.management.base import BaseCommand, CommandError

from apps.lex_corpus.lexuz_client import LexUzClient
from apps.lex_corpus.models import LegalActDocument
from apps.lex_corpus.translations import fetch_translations


class Command(BaseCommand):
    help = "Hujjatlarning kirill va rus versiyalarini yuklab, moddalarga moslashtiradi."

    def add_arguments(self, parser):
        parser.add_argument("ids", nargs="*", help="abs_id")
        parser.add_argument("--tier", choices=["CORE", "EXTENDED", "ON_DEMAND"])
        parser.add_argument("--lang", nargs="+", choices=["lat", "cyr", "ru"], help="Sukut: barcha mavjud tillar")
        parser.add_argument("--limit", type=int)
        parser.add_argument("--skip-done", action="store_true", help="Tarjimasi yuklangan hujjatlarni o'tkazish (rad etilgan yoki xatolilar qayta uriniladi)")
        parser.add_argument("--refresh", action="store_true", help="Tarjima sahifalarini lex.uz dan qayta olish")

    def handle(self, *args, ids, tier, lang, limit, skip_done, refresh, **opts):
        if ids:
            qs = LegalActDocument.objects.filter(abs_id__in=[abs(int(i)) for i in ids])
        elif tier:
            qs = LegalActDocument.objects.filter(corpus_tier=tier, last_synced_at__isnull=False)
            qs = qs.order_by("-hierarchy_weight", "-adoption_date")
        else:
            raise CommandError("ids yoki --tier kerak")
        client = LexUzClient()
        done = failed = skipped = 0
        total_matched = total_rejected = 0
        t0 = time.monotonic()
        for doc in qs.iterator(chunk_size=200):
            if skip_done and doc.translations and (lang is None or all(x in doc.translations for x in lang)) \
                    and not any(i.get("rejected") or i.get("error") for i in doc.translations.values()):
                skipped += 1
                continue
            if limit and done + failed >= limit:
                break
            try:
                result = fetch_translations(doc, client, langs=lang, refresh=refresh)
            except Exception as e:  # bitta hujjat xatosi butun jarayonni to'xtatmasin
                failed += 1
                self.stderr.write(f"[X] {doc.abs_id}: {e}")
                continue
            done += 1
            parts = []
            for lg, info in result.items():
                if info.get("rejected") or info.get("error"):
                    total_rejected += 1
                    parts.append(f"{lg}: RAD ETILDI ({info.get('rejected') or info.get('error')})")
                else:
                    total_matched += 1
                    stale = ", tahrir farqli" if info["stale"] else ""
                    parts.append(f"{lg}: {info['matched']}/{info['total']}{stale}")
            self.stdout.write(f"[{done}] {doc.abs_id} {doc.title_for('lat')[:50]!r}: {'; '.join(parts) or 'tarjima yoʻq'}")
        self.stdout.write(f"Tayyor: {done}, xato: {failed}, oʻtkazildi: {skipped}; tillar: {total_matched} yaxshi, "
                          f"{total_rejected} rad etilgan; {time.monotonic() - t0:.0f} s")
