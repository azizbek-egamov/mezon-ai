"""Savol -> qidiruv -> iqtibosli javob (stream) -> tekshiruv. Konsolda sinash uchun.

    python manage.py ask "aldab pul olgan odamga qanday jazo" [--lang ru] [--effort medium]
"""
import sys
import time

from django.core.management.base import BaseCommand

from apps.rag.answer import build_prompt, build_sources, verify_answer
from apps.rag.llm import get_llm, task_model
from apps.rag.search import search_aspects
from apps.rag.store import get_client


class Command(BaseCommand):
    help = "Iqtibosli huquqiy javob (stream + tekshiruv)"

    def add_arguments(self, parser):
        parser.add_argument("question", nargs="+")
        parser.add_argument("--lang", default="uz-Latn", choices=["uz-Latn", "uz-Cyrl", "ru", "kaa", "en"])
        parser.add_argument("--effort", default="medium", choices=["low", "medium", "high"])

    def handle(self, *args, question, lang, effort, **opts):
        q = " ".join(question)
        llm = get_llm()
        t0 = time.monotonic()
        hits, aspects = search_aspects(q, effort=effort)
        t_search = time.monotonic() - t0
        srcs = build_sources(hits)
        self.stdout.write("Yo'nalishlar: " + " | ".join(a["topic"] for a in aspects))
        self.stdout.write(f"Manbalar: {len(srcs)} ta ({t_search:.1f} s):")
        for s in srcs:
            self.stdout.write(f"  [{s.key}] ({s.hit.topic[:28]}) {s.hit.doc_title[:45]} — {s.hit.label[:55]}")
        self.stdout.write("\nJavob:\n")

        system, user = build_prompt(q, srcs, lang)
        t1 = time.monotonic()
        first_token = None
        parts = []
        for chunk in llm.stream_text(system, user, effort=effort, model=task_model("answer")):
            if first_token is None:
                first_token = time.monotonic() - t1
            parts.append(chunk)
            sys.stdout.write(chunk)
            sys.stdout.flush()
        answer = "".join(parts)
        t_answer = time.monotonic() - t1

        report = verify_answer(answer, srcs)
        self.stdout.write("\n\n--- Tekshiruv ---")
        self.stdout.write(f"Holat: {'✓ o‘tdi' if report.ok else '⚠ XATO bor'} | manbalar: {', '.join(report.citations) or '-'} | "
                          f"tekshirilgan iqtiboslar: {report.quotes_checked}")
        for issue in report.issues:
            self.stdout.write(f"  {'✗' if issue.severity == 'error' else '!'} {issue.detail}")
        for key in report.citations:
            s = next((x for x in srcs if x.key == key), None)
            if s:
                self.stdout.write(f"  [{key}] {s.hit.lex_url}")
        cost = f" | ${llm.cost_usd():.4f}" if hasattr(llm, "cost_usd") else ""
        self.stdout.write(f"Vaqt: qidiruv {t_search:.1f} s, birinchi so'z {first_token or 0:.1f} s, javob {t_answer:.1f} s | "
                          f"token: {llm.usage.input_tokens} in / {llm.usage.output_tokens} out{cost} "
                          f"| to'xtash: {getattr(llm, 'last_stop_reason', '-')}")
        get_client().close()
