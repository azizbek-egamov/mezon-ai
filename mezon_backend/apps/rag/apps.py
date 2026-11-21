import os
import sys
import threading

from django.apps import AppConfig


class RagConfig(AppConfig):
    name = "apps.rag"
    verbose_name = "Gibrid qidiruv (RAG)"

    def ready(self):
        # runserver ishga tushganda modellar va Qdrant fonda yuklanadi (~20 s) — birinchi savol kutmasin.
        # Autoreload rejimida faqat ishchi jarayonda (RUN_MAIN=true) ishlaydi; testlar va boshqa buyruqlarda yo'q.
        if os.environ.get("RAG_WARMUP", "1") != "1" or "runserver" not in sys.argv:
            return
        if os.environ.get("RUN_MAIN") != "true" and "--noreload" not in sys.argv:
            return
        from .views import warmup

        threading.Thread(target=warmup, name="rag-warmup", daemon=True).start()
