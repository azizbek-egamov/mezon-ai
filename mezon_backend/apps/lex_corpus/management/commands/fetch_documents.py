"""lex.uz dan hujjat matnini yuklab, moddalarga ajratib bazaga yozish.

    python manage.py fetch_documents 111453 111460      # aniq hujjatlar (abs_id yoki lex id)
    python manage.py fetch_documents --tier CORE --limit 50
"""
from django.core.management.base import BaseCommand, CommandError

from apps.lex_corpus.ingest import store_parsed
from apps.lex_corpus.lexuz_client import LexUzClient
from apps.lex_corpus.models import LegalActDocument


class Command(BaseCommand):
    help = "lex.uz hujjatlarini yuklab, moddalarga ajratadi."

    def add_arguments(self, parser):
        parser.add_argument("ids", nargs="*", help="abs_id yoki lex.uz id (masalan -111453)")
        parser.add_argument("--tier", choices=["CORE", "EXTENDED", "ON_DEMAND"])
        parser.add_argument("--limit", type=int)
        parser.add_argument("--refresh", action="store_true", help="Keshni e'tiborsiz qoldirish")
        parser.add_argument("--skip-synced", action="store_true", help="Avval yuklanganlarni o'tkazib yuborish")

    def handle(self, *args, ids, tier, limit, refresh, skip_synced, **opts):
        if ids:
            qs = LegalActDocument.objects.filter(abs_id__in=[abs(int(i)) for i in ids])
        elif tier:
            qs = LegalActDocument.objects.filter(corpus_tier=tier).order_by("-hierarchy_weight", "-adoption_date")
        else:
            raise CommandError("ids yoki --tier kerak")
        if skip_synced:
            qs = qs.filter(last_synced_at__isnull=True)
        if limit:
            qs = qs[:limit]
        client = LexUzClient()
        ok = failed = 0
        for doc in qs:
            lex_id = doc.primary_lex_id
            try:
                html = client.get_document_html(lex_id, refresh=refresh)
                edition, n = store_parsed(doc, html, client)
            except Exception as e:  # bitta hujjat xatosi butun jarayonni to'xtatmasin
                failed += 1
                self.stderr.write(f"[X] {lex_id}: {e}")
                continue
            ok += 1
            self.stdout.write(f"[+] {lex_id} {doc.title_uz_lat[:60]!r}: {n} modda, tahrir {edition.edition_label or '-'}")
        self.stdout.write(f"Tayyor: {ok}, xato: {failed}")
