"""Ichki (fayl) rejimdagi Qdrant kolleksiyasini Qdrant serverga ko'chiradi — qayta embedding qilmasdan.

    python manage.py migrate_qdrant --url http://127.0.0.1:6333

Nuqtalar (id, dense, sparse, payload) o'zgarmasdan ko'chiriladi; server kolleksiyasi diskdan ishlaydi
(store.ensure_collection). Keyin .env ga QDRANT_URL yoziladi.
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from qdrant_client import QdrantClient, models

from apps.rag.store import ensure_collection


class Command(BaseCommand):
    help = "Ichki Qdrant kolleksiyasini serverga ko'chiradi"

    def add_arguments(self, parser):
        parser.add_argument("--url", required=True)
        parser.add_argument("--batch", type=int, default=256)

    def handle(self, *args, url, batch, **opts):
        name = settings.QDRANT_COLLECTION
        src = QdrantClient(path=str(settings.QDRANT_PATH))
        dst = QdrantClient(url=url, timeout=120)
        ensure_collection(name=name, client=dst)
        total = src.count(name).count
        offset, done = None, 0
        while True:
            points, offset = src.scroll(name, limit=batch, offset=offset, with_payload=True, with_vectors=True)
            if not points:
                break
            dst.upsert(name, [models.PointStruct(id=p.id, vector=p.vector, payload=p.payload) for p in points],
                       wait=True)
            done += len(points)
            if done % (batch * 20) < batch or offset is None:
                self.stdout.write(f"  {done}/{total}")
            if offset is None:
                break
        src.close()
        self.stdout.write(f"Ko'chirildi: {dst.count(name).count}/{total} nuqta → {url}")
