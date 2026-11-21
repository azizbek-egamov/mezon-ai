"""Semantik keshni tozalash yoki holatini ko'rish: manage.py clear_cache [--info]"""
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.rag.semantic_cache import clear_semantic_cache, ensure_cache_collection
from apps.rag.store import get_client


class Command(BaseCommand):
    help = "Qdrant semantik keshini tozalash yoki statistikasini ko'rish"

    def add_arguments(self, parser):
        parser.add_argument("--info", action="store_true", help="Keshni tozalash o'rniga ma'lumotlarni ko'rsatish")

    def handle(self, *args, **options):
        client = get_client()
        col = getattr(settings, "QDRANT_CACHE_COLLECTION", "mezon_semantic_cache")

        if options["info"]:
            if not client.collection_exists(col):
                self.stdout.write(self.style.WARNING(f"'{col}' kolleksiyasi mavjud emas."))
                return
            info = client.get_collection(col)
            self.stdout.write(self.style.SUCCESS(
                f"Kolleksiya: {col}\n"
                f"Nuqtalar soni: {info.points_count}\n"
                f"Holati: {info.status}\n"
                f"Vektorlar soni: {info.indexed_vectors_count}"
            ))
            return

        ok = clear_semantic_cache(client=client)
        if ok:
            self.stdout.write(self.style.SUCCESS(f"'{col}' semantik keshi muvaffaqiyatli tozalandi."))
        else:
            self.stdout.write(self.style.ERROR(f"'{col}' keshini tozalashda xatolik yuz berdi."))

