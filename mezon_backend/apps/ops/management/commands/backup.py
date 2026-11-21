"""Zaxira nusxa (apps/ops/backup.py):

    manage.py backup                      # baza + ish fayllari -> MEZON_BACKUP_DIR/mezon_YYYYMMDD_HHMMSS.mzb
    manage.py backup --qdrant             # + qidiruv indeksi (Qdrant snapshot, ~1 GB; haftada bir marta yetarli)
    manage.py backup verify <fayl>        # ochib tekshiradi (SHA-256, baza quick_check)
    manage.py backup restore <fayl> <papka>   # yangi papkaga ochadi; ishlab turgan data/ ga tegmaydi

Kalit — MEZON_DATA_KEYS; u arxivga kirmaydi, alohida saqlang.
"""
import sys
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import connection

from apps.ops import backup


class Command(BaseCommand):
    help = "Shifrlangan zaxira nusxa: yaratish, tekshirish, tiklash"

    def add_arguments(self, parser):
        parser.add_argument("action", nargs="?", default="create", choices=["create", "verify", "restore"])
        parser.add_argument("file", nargs="?", help="verify/restore: .mzb fayl")
        parser.add_argument("target", nargs="?", help="restore: bo'sh (yoki yangi) papka")
        parser.add_argument("--dest", help=f"zaxira papkasi (sukut: MEZON_BACKUP_DIR = {settings.BACKUP_DIR})")
        parser.add_argument("--keep", type=int, default=settings.BACKUP_KEEP, help="nechta eng yangi nusxa qoladi")
        parser.add_argument("--qdrant", action="store_true", help="Qdrant snapshot ham qo'shilsin")

    def handle(self, *args, action, file, target, dest, keep, qdrant, **opts):
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8")
        keys = settings.DATA_KEYS
        try:
            if action == "create":
                self._create(Path(dest) if dest else settings.BACKUP_DIR, keep, qdrant, keys)
            elif not file:
                raise CommandError("Zaxira faylini ko'rsating.")
            elif action == "verify":
                manifest = backup.verify_backup(Path(file), keys)
                self.stdout.write(self.style.SUCCESS(
                    f"Zaxira butun: {manifest['created']}, {len(manifest['files'])} fayl, {manifest.get('counts', {})}"))
            else:
                if not target:
                    raise CommandError("Tiklash uchun papkani ko'rsating.")
                manifest = backup.restore_backup(Path(file), Path(target), keys)
                self.stdout.write(self.style.SUCCESS(f"Ochildi: {target} ({len(manifest['files'])} fayl)."))
                self.stdout.write("Keyingi qadamlar (server to'xtatilgach) — README, \"Zaxira nusxa\" bo'limi.")
        except backup.BackupError as e:
            raise CommandError(str(e)) from e

    def _create(self, dest: Path, keep: int, qdrant: bool, keys: list[str]) -> None:
        if connection.vendor != "sqlite":
            raise CommandError("Bu buyruq SQLite uchun. PostgreSQL da baza `pg_dump -Fc` bilan alohida saqlanadi "
                               "(README: \"PostgreSQL ga o'tish\").")
        if qdrant and not settings.QDRANT_URL:
            raise CommandError("--qdrant faqat Qdrant server rejimida (QDRANT_URL).")
        result = backup.create_backup(
            dest, db_path=Path(settings.DATABASES["default"]["NAME"]), data_dir=settings.DATA_DIR, keys=keys,
            keep=keep, qdrant_url=settings.QDRANT_URL if qdrant else "", qdrant_collection=settings.QDRANT_COLLECTION)
        self.stdout.write(self.style.SUCCESS(
            f"Zaxira: {result.path} ({result.size / 1024 / 1024:.1f} MB, {result.entries} fayl)"))
        for old in result.removed:
            self.stdout.write(f"Eski nusxa o'chirildi: {old.name}")
