"""Korpusning joriy tahrirdagi moddalarini bo'laklab, bge-m3 bilan Qdrant ga yozish.

    python manage.py build_index --tier CORE [--recreate] [--limit-docs N]
    python manage.py build_index --langs cyr ru          # kirill va rus matnlarini mavjud indeksga QO'SHISH
    python manage.py build_index --recreate --langs lat cyr ru   # hammasini noldan (lat — asosiy tildagi matn)

`--langs` berilmasa faqat moddaning asosiy tili indekslanadi. Tillar bo'laklari id si alohida (`modda:til:n`), shuning
uchun qo'shish mavjud nuqtalarni o'zgartirmaydi va takroran ishga tushirish xavfsiz (ustidan yoziladi).
"""
import time

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.lex_corpus.models import LegalActArticle
from apps.rag.indexer import build_chunks, upsert_chunks
from apps.rag.models_runtime import get_embedder
from apps.rag.store import ensure_collection, get_client


class Command(BaseCommand):
    help = "Yadro korpusini Qdrant ga indekslaydi (dense + sparse)."

    def add_arguments(self, parser):
        parser.add_argument("--tier", default="CORE")
        parser.add_argument("--recreate", action="store_true", help="Kolleksiyani noldan yaratish")
        parser.add_argument("--limit-docs", type=int)
        parser.add_argument("--batch", type=int, default=16)
        parser.add_argument("--langs", nargs="+", choices=["lat", "cyr", "ru"],
                            help="Qaysi til matnlari indekslansin (sukut: faqat asosiy til)")

    def handle(self, *args, tier, recreate, limit_docs, batch, langs, **opts):
        qs = (LegalActArticle.objects.filter(edition__is_current=True, document__corpus_tier=tier)
              .select_related("document", "edition").order_by("document_id", "position"))
        if limit_docs:
            doc_ids = list(qs.values_list("document_id", flat=True).distinct()[:limit_docs])
            qs = qs.filter(document_id__in=doc_ids)

        t0 = time.monotonic()
        chunks = build_chunks(qs.iterator(chunk_size=2000), langs=langs)
        self.stdout.write(f"Bo'laklar: {len(chunks)} ({time.monotonic() - t0:.0f} s)")
        ensure_collection(recreate=recreate)
        self.stdout.write(f"Model qurilmasi: {get_embedder().device}")
        t1 = time.monotonic()

        def progress(done, total):
            self.stdout.write(f"  {done}/{total}  ({done / (time.monotonic() - t1):.1f} bo'lak/s)")

        upsert_chunks(chunks, batch=batch, on_progress=progress)
        client = get_client()
        self.stdout.write(f"Tayyor: {client.count(settings.QDRANT_COLLECTION).count} nuqta, {time.monotonic() - t0:.0f} s")
        client.close()
