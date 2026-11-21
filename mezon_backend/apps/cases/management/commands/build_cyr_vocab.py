"""O'zbek kirill OCR tuzatishi (apps/cases/cyr_fix.py) uchun lug'atni korpusdan qayta qurish.

    python manage.py build_cyr_vocab

Lug'at `data/cache/uz_cyr_vocab.json` da keshlanadi; korpusga yangi kirill matnlar qo'shilgandan keyin
(`fetch_translations`) qayta quring.
"""
from django.core.management.base import BaseCommand

from apps.cases import cyr_fix


class Command(BaseCommand):
    help = "lex.uz o'zbek kirill matnlaridan so'z chastotalari lug'atini quradi."

    def handle(self, *args, **opts):
        counts = cyr_fix.build_vocab()
        path = cyr_fix.save_vocab(counts)
        self.stdout.write(f"Lugʻat: {len(counts)} soʻz (kamida 2 marta uchragan: {sum(1 for n in counts.values() if n >= 2)}) -> {path}")
