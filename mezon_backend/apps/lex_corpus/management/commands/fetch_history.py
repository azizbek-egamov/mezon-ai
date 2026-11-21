"""Hujjat moddalarining tahrirlar tarixini yuklash va versiyalarni qurish (apps/lex_corpus/history.py).

    python manage.py fetch_history 111453 111460 --since 2016-01-01   # aniq hujjatlar
    python manage.py fetch_history --scope criminal                    # jinoyat ishi doirasidagi hujjatlar
    python manage.py fetch_history --scope civil economic administrative   # boshqa ish turlari (12-bosqich)
    python manage.py fetch_history --codes                             # barcha kuchdagi kodekslar + Konstitutsiya

Sahifalar diskda keshlanadi (DATA_DIR/lex_cache), qayta ishga tushirish faqat yetishmaganlarini yuklaydi.
Bitta tahrir sahifasi ~1–4 MB, so'rovlar orasida LEX_REQUEST_DELAY kechikish.
"""
from datetime import date

from django.core.management.base import BaseCommand, CommandError

from apps.lex_corpus.history import build_history
from apps.lex_corpus.lexuz_client import LexUzClient
from apps.lex_corpus.models import LegalActDocument

# Ish turlari doiralari (apps/cases/case_types.py — huquqiy asoslash qidirgan hujjatlar bilan bir xil).
from apps.cases.case_types import CASE_TYPES  # noqa: E402

SCOPES = {code: t.scope["document_ids"] for code, t in CASE_TYPES.items() if t.scope.get("document_ids")}


class Command(BaseCommand):
    help = "Moddalar tahrirlari tarixini yuklaydi (voqea sanasidagi matn uchun)"

    def add_arguments(self, parser):
        parser.add_argument("ids", nargs="*", type=int, help="abs_id lar")
        parser.add_argument("--scope", nargs="+", choices=sorted(SCOPES), help="Ish turi doira(lar)i")
        parser.add_argument("--codes", action="store_true", help="Barcha kuchdagi kodekslar va Konstitutsiya")
        parser.add_argument("--since", default="2016-01-01", help="Shu sanadan keyingi tahrirlar (YYYY-MM-DD)")

    def handle(self, *args, ids, scope, codes, since, **opts):
        since_date = date.fromisoformat(since)
        if ids:
            qs = LegalActDocument.objects.filter(abs_id__in=ids)
        elif scope:
            qs = LegalActDocument.objects.filter(abs_id__in={i for name in scope for i in SCOPES[name]})
        elif codes:
            qs = LegalActDocument.objects.filter(doc_type__in=["CODE", "CONSTITUTION"], status="ACTIVE",
                                                 corpus_tier="CORE")
        else:
            raise CommandError("ids, --scope yoki --codes kerak")
        client = LexUzClient()
        for doc in qs.filter(last_synced_at__isnull=False):
            self.stdout.write(f"== {doc.abs_id} {doc.title_uz_lat[:60]}")

            def progress(n, total, edition):
                if n == 1 or n % 10 == 0 or n == total:
                    self.stdout.write(f"   {n}/{total} tahrir {edition.edition_label}")

            try:
                stats = build_history(doc, client, since_date, on_edition=progress)
            except Exception as e:
                self.stderr.write(f"[X] {doc.abs_id}: {e}")
                continue
            self.stdout.write(f"[+] {doc.abs_id}: {stats.editions} tahrir, {stats.versions} versiya, "
                              f"{stats.changed_units} birlikning eski matni bor, tarix {stats.history_from}")
            for err in stats.errors:
                self.stderr.write(f"    ! {err}")
