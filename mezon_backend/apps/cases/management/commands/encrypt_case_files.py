"""Shifrlash joriy etilishidan oldin saqlangan ish fayllarini (PDF, hisobot) shifrlaydi va ochiq nusxasini o'chiradi.

    python manage.py encrypt_case_files [--dry-run]

Faqat DATA_DIR ichidagi fayllarga tegadi (repodagi fixture PDF lar o'zgarmaydi). Qayta ishga tushirish xavfsiz.
"""
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.cases import storage
from apps.cases.models import CaseRun


class Command(BaseCommand):
    help = "Eski (ochiq) ish fayllarini shifrlaydi"

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, dry_run, **opts):
        done = 0
        for run in CaseRun.objects.all():
            updates = {}
            for field in ("pdf_path", "report_path"):
                path = getattr(run, field)
                if not path or path.endswith(storage.SUFFIX) or not storage.is_managed(path):
                    continue
                if not Path(path).exists():
                    self.stdout.write(f"  topilmadi: {path}")
                    continue
                self.stdout.write(f"  {run.id} {field}: {path}")
                if not dry_run:
                    updates[field] = storage.write_encrypted(path, Path(path).read_bytes())
                    Path(path).unlink()
                done += 1
            if updates:
                CaseRun.objects.filter(pk=run.pk).update(**updates)
        self.stdout.write(f"{'Shifrlanadi' if dry_run else 'Shifrlandi'}: {done} ta fayl")
