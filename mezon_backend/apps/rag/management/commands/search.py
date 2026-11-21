"""Qidiruvni konsoldan sinash: python manage.py search "firibgarlik uchun jazo" [-n 5] [--no-rerank]"""
import time

from django.core.management.base import BaseCommand

from apps.rag.search import search
from apps.rag.store import get_client


class Command(BaseCommand):
    help = "Gibrid huquqiy qidiruv"

    def add_arguments(self, parser):
        parser.add_argument("query", nargs="+")
        parser.add_argument("-n", type=int, default=5)
        parser.add_argument("--no-rerank", action="store_true")
        parser.add_argument("--include-amending", action="store_true", help="O'zgartirish kirituvchi hujjatlar ham")
        parser.add_argument("--rewrite", action="store_true", help="LLM bilan huquqiy atamalarga o'girish")

    def handle(self, *args, query, n, no_rerank, include_amending, rewrite, **opts):
        q = " ".join(query)
        t0 = time.monotonic()
        hits = search(q, limit=n, rerank=not no_rerank, include_amending=include_amending, rewrite=rewrite)
        self.stdout.write(f"«{q}» — {time.monotonic() - t0:.2f} s")
        for i, h in enumerate(hits, 1):
            tag = " [ANIQ]" if h.exact else ""
            self.stdout.write(f"{i}. {h.score:.3f}{tag} {h.doc_title[:55]} — {h.label[:70]}")
            self.stdout.write(f"   {h.text[:160].replace(chr(10), ' / ')}")
            self.stdout.write(f"   {h.lex_url}")
        get_client().close()
