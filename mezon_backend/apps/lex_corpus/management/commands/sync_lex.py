"""lex.uz bilan sinxronizatsiya (apps/lex_corpus/sync.py). Har kecha 02:00 da ishga tushiriladi (TZ §6.4).

    python manage.py sync_lex                    # oxirgi 60 kun, o'zgargan yadro hujjatlari
    python manage.py sync_lex --check-codes      # + barcha kodekslarni qayta tekshirish (haftalik)
    python manage.py sync_lex --days 7 --no-index

Qdrant server ishlab turishi kerak (QDRANT_URL) — veb server bilan bir vaqtda ishlay oladi.
"""
from django.core.management.base import BaseCommand

from apps.lex_corpus.sync import run_sync


class Command(BaseCommand):
    help = "lex.uz dan yangi hujjatlar va tahrirlarni olib, korpus va indeksni yangilaydi"

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=60, help="Shuncha kunlik hujjatlar qayta tekshiriladi")
        parser.add_argument("--max-pages", type=int, default=30, help="Reyestr qidiruvining ko'pi bilan sahifalari")
        parser.add_argument("--check-codes", action="store_true", help="Barcha kodekslar va Konstitutsiyani tekshirish")
        parser.add_argument("--no-index", action="store_true", help="Qdrant indeksini yangilamaslik")

    def handle(self, *args, days, max_pages, check_codes, no_index, **opts):
        run = run_sync(days=days, max_pages=max_pages, check_codes=check_codes, index=not no_index,
                       log=self.stdout.write)
        self.stdout.write(f"Natija: {run.get_status_display()} (jurnal #{run.pk})")
