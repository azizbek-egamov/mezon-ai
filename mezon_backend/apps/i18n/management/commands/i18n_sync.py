"""Tarjima kataloglarini yangilash (makemessages + compilemessages o'rnida; Windows da gettext yo'q).

    python manage.py i18n_sync            # matnlarni ajratish, locale/*/django.po ni yangilash, .mo yozish
    python manage.py i18n_sync --strict   # tarjimasi yo'q yoki placeholder mos kelmasa xato bilan chiqish

Yangi matn har bir tilga bo'sh msgstr bilan qo'shiladi (uz-cyrl — avtomatik transliteratsiya). ru / en / kaa
tarjimalarini locale/<til>/LC_MESSAGES/django.po da to'ldiring va qayta ishga tushiring.
"""
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.i18n import catalog


class Command(BaseCommand):
    help = "Tarjima kataloglarini yangilaydi va kompilyatsiya qiladi."

    def add_arguments(self, parser):
        parser.add_argument("--strict", action="store_true")
        parser.add_argument("--show-missing", action="store_true", help="Tarjima qilinmagan matnlarni chiqarish")

    def handle(self, *args, strict, show_missing, **opts):
        report = catalog.sync()
        problems = 0
        for lang, name in settings.LANGUAGES:
            r = report[lang]
            self.stdout.write(f"{lang:8} {r['translated']:4}/{r['total']:<4} tarjima qilingan"
                              f"{'  (manba til)' if lang == catalog.SOURCE_LANG else ''}")
            if show_missing:
                for msgid in r["missing"]:
                    self.stdout.write(f"    ? {msgid[:100]}")
            for msgid in r["placeholder_errors"]:
                self.stderr.write(f"    ! {lang}: placeholder mos emas: {msgid[:80]}")
            problems += len(r["missing"]) + len(r["placeholder_errors"])
        if strict and problems:
            raise CommandError(f"{problems} ta muammo")
