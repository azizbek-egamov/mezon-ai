"""Qidiruv sifatini kichik sinov to'plamida o'lchash: Hit@1, Hit@5, MRR.

    python manage.py eval_search [--no-rerank]

Kutilgan moddalar bazadagi rasmiy sarlavhalar bo'yicha tekshirilgan (2026-10-24). Savollar sarlavhani
so'zma-so'z takrorlamasligi uchun oddiy tilda yozilgan. Bu yurist tuzadigan to'liq sinov to'plami
(TZ §10) o'rnini bosmaydi — faqat qidiruvni sozlash uchun tezkor tekshiruv.
"""
import time

from django.core.management.base import BaseCommand

from apps.lex_corpus.models import LegalActArticle
from apps.rag.llm import get_llm
from apps.rag.query_rewrite import rewrite_query
from apps.rag.search import search
from apps.rag.store import get_client

JK, JPK, MK, MJTK, OK, FK1 = 111453, 111460, 6257288, 97664, 104720, 111189

CASES: list[tuple[str, int, str]] = [
    ("aldab birovning pulini olib qo'ygan odamga qanday jazo beriladi", JK, "168"),
    ("yashirincha boshqa birovning telefonini o'g'irlab ketish", JK, "169"),
    ("qurol bilan hujum qilib mol-mulkni tortib olish", JK, "164"),
    ("ochiqdan-ochiq ko'z oldida sumkani yulib qochish", JK, "166"),
    ("ishonib topshirilgan pulni kassir o'zlashtirib yuborsa", JK, "167"),
    ("pul talab qilib qo'rqitish, aks holda sirni oshkor qilaman deyish", JK, "165"),
    ("mansabdor shaxs ish bitirish uchun pul olsa", JK, "210"),
    ("amaldorga ish hal qilish uchun pul berish javobgarligi", JK, "211"),
    ("ataylab inson hayotiga qasd qilib o'ldirish", JK, "97"),
    ("avtohalokatda ehtiyotsizlik tufayli odam vafot etdi", JK, "102"),
    ("zo'rlash jinoyati uchun javobgarlik", JK, "118"),
    ("narkotik moddalarni sotish maqsadida saqlash", JK, "273"),
    ("gumon qilinuvchini necha soatgacha ushlab turish mumkin", JPK, "226"),
    ("shaxsni ushlab turish uchun qanday asoslar bo'lishi kerak", JPK, "221"),
    ("hibsga olish ehtiyot chorasini tanlash tartibi", JPK, "243"),
    ("ish beruvchi xodimni o'z tashabbusi bilan ishdan bo'shatishi", MK, "161"),
    ("mast holda mashina haydagan haydovchiga jarima", MJTK, "131"),
    ("necha yoshdan nikohdan o'tish mumkin", OK, "15"),
    ("ota-ona voyaga yetmagan farzandiga aliment to'lash majburiyati", OK, "96"),
    ("JK 168-modda", JK, "168"),
]


class Command(BaseCommand):
    help = "Qidiruvni sinov to'plamida o'lchaydi"

    def add_arguments(self, parser):
        parser.add_argument("--no-rerank", action="store_true")
        parser.add_argument("--rewrite", action="store_true", help="LLM bilan huquqiy atamalarga o'girish")
        parser.add_argument("--include-amending", action="store_true")
        parser.add_argument("--sparse-for", type=int, default=1, help="Sparse qidiruv nechta so'rov uchun")

    def handle(self, *args, no_rerank, rewrite, include_amending, sparse_for, **opts):
        expansions: dict[str, list[str]] = {}
        if rewrite:
            # Avval barcha so'rovlarni o'giramiz, keyin LLM ni VRAM dan bo'shatamiz (8 GB karta).
            t0 = time.monotonic()
            for q, _, _ in CASES:
                expansions[q] = rewrite_query(q)
                self.stdout.write(f"  ~ {q[:45]:<45} => {expansions[q]}")
            llm = get_llm()
            cost = f", ${llm.cost_usd():.4f}" if hasattr(llm, "cost_usd") else ""
            self.stdout.write(f"O'girish ({llm.name}): {(time.monotonic() - t0) / len(CASES):.1f} s/so'rov, "
                              f"{llm.usage.input_tokens} in / {llm.usage.output_tokens} out token{cost}\n")
            llm.unload()
        expected = {
            (d, n): LegalActArticle.objects.get(document_id=d, article_number=n, unit_type="ARTICLE",
                                                edition__is_current=True).pk
            for _, d, n in CASES
        }
        hit1 = hit5 = 0
        rr = 0.0
        times = []
        for q, d, n in CASES:
            t0 = time.monotonic()
            hits = search(q, limit=10, rerank=not no_rerank, include_amending=include_amending,
                          expansions=expansions.get(q, []), sparse_for=sparse_for)
            times.append(time.monotonic() - t0)
            ids = [h.article_id for h in hits]
            want = expected[(d, n)]
            rank = ids.index(want) + 1 if want in ids else None
            hit1 += rank == 1
            hit5 += bool(rank and rank <= 5)
            rr += 1 / rank if rank else 0
            top = hits[0] if hits else None
            mark = "✓" if rank == 1 else (f"#{rank}" if rank else "✗")
            self.stdout.write(f"{mark:>3}  {q[:60]:<60} -> {top.doc_title[:28] + ' ' + top.label[:40] if top else '-'}")
        n = len(CASES)
        self.stdout.write(f"\nHit@1 {hit1}/{n} ({hit1 / n:.0%}) | Hit@5 {hit5}/{n} ({hit5 / n:.0%}) | MRR {rr / n:.3f} | "
                          f"o'rtacha {sum(times[1:]) / max(1, n - 1):.2f} s/so'rov (birinchisi model yuklash bilan {times[0]:.1f} s)")
        get_client().close()
