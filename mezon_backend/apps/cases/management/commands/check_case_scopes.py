"""Ish turlari qidiruv doiralarini tekshirish (12-bosqich, apps/cases/case_types.py).

    python manage.py check_case_scopes            # har bir id bazada bormi: yadro, kuchda, joriy tahrirda moddalar
    python manage.py check_case_scopes --eval     # + har bir tur uchun tezkor qidiruv sinovi (GPU/Qdrant kerak, API siz)

Sinov hujjat darajasida: savolga javob beradigan hujjat (kodeks/qonun) doira ichida birinchi 5 natijada chiqadimi.
Modda raqamlari bu yerda yozilmaydi — ular tekshirilgan emas.
"""
from django.core.management.base import BaseCommand

from apps.cases.case_types import ADMINISTRATIVE, CIVIL, ECONOMIC, FK1, FK2, FPK, IPK, MJTK, MSIYUK, CASE_TYPES
from apps.lex_corpus.models import LegalActArticle, LegalActDocument

# (savol, kutilgan hujjatlardan istalgani) — hujjat id lari bazadan tekshirilgan.
EVAL = {
    "civil": [
        ("daʼvo muddati qancha va qachon oʻtadi", {FK1}),
        ("nikohni bekor qilish tartibi va farzandlar aliment", {104720}),
        ("ish beruvchi xodimni ishdan boʻshatganda mehnat nizosi", {6257288}),
        ("meros qoldiruvchining merosxoʻrlari va vasiyat", {FK2}),
        ("fuqarolik ishida sud majlisi haqida taraflarga xabar berish", {FPK}),
        ("nuqsonli tovar sotib olgan iste'molchining huquqlari", {4704, FK2}),
    ],
    "economic": [
        ("shartnoma majburiyatini bajarmaganlik uchun penya va jarima", {FK1, FK2}),
        ("iqtisodiy sudga daʼvo arizasi berish tartibi", {IPK}),
        ("masʼuliyati cheklangan jamiyat ishtirokchisining jamiyatdan chiqishi", {8151376}),
        ("hakamlik kelishuvi va hakamlik sudi", {1072079}),
        ("raqobatni cheklovchi kelishuv", {6518381}),
        ("lizing shartnomasi", {85259, FK2}),
    ],
    "administrative": [
        ("maʼmuriy jarima qoʻllash muddati", {MJTK}),
        ("maʼmuriy sudga daʼvo arizasi berish muddati", {MSIYUK}),
        ("soliq tekshiruvi natijalariga shikoyat qilish", {4674902}),
        ("maʼmuriy tartib-taomilni oʻtkazish va eshitish", {3492199}),
        ("bojxona deklaratsiyasi va bojxona toʻlovlari", {2876354}),
        ("litsenziya berish va bekor qilish", {5511879}),
    ],
}
LABELS = {FK1: "FK-1", FK2: "FK-2", FPK: "FPK", IPK: "IPK", MSIYUK: "MSIYuK", MJTK: "MJtK"}


class Command(BaseCommand):
    help = "Ish turlari qidiruv doiralarini tekshiradi"

    def add_arguments(self, parser):
        parser.add_argument("--eval", action="store_true")

    def handle(self, *args, eval, **opts):
        bad = 0
        for code, ct in CASE_TYPES.items():
            ids = ct.scope.get("document_ids", [])
            self.stdout.write(f"== {code}: {len(ids)} hujjat" + (f" + {ct.scope['doc_types']}" if ct.scope.get("doc_types") else ""))
            for doc in LegalActDocument.objects.filter(abs_id__in=ids):
                n = LegalActArticle.objects.filter(document=doc, edition__is_current=True).count()
                ok = doc.corpus_tier == "CORE" and doc.status == "ACTIVE" and n > 0
                bad += not ok
                self.stdout.write(f"   {'OK ' if ok else 'XATO'} {doc.abs_id:8} {n:4} modda  {doc.title_uz_lat[:70]}")
            for missing in set(ids) - set(LegalActDocument.objects.filter(abs_id__in=ids).values_list("abs_id", flat=True)):
                bad += 1
                self.stdout.write(f"   XATO {missing}: bazada yo'q")
        if eval:
            from apps.rag.search import search

            for code, cases in EVAL.items():
                scope = CASE_TYPES[code].scope
                hit5 = hit1 = 0
                self.stdout.write(f"== sinov: {code}")
                for question, expected in cases:
                    hits = search(question, limit=5, **scope)
                    docs = [h.document_id for h in hits]
                    outside = [d for d in docs if d not in scope.get("document_ids", []) and not _is_plenum(d)]
                    ok5, ok1 = bool(expected & set(docs)), bool(docs and docs[0] in expected)
                    hit5, hit1 = hit5 + ok5, hit1 + ok1
                    self.stdout.write(f"   {'✓' if ok5 else '✗'} {question[:60]:60} -> "
                                      f"{[LABELS.get(d, d) for d in docs[:3]]}{'  DOIRADAN TASHQARI ' + str(outside) if outside else ''}")
                self.stdout.write(f"   Hit@1 {hit1}/{len(cases)}  Hit@5 {hit5}/{len(cases)}")
        if bad:
            self.stderr.write(f"{bad} ta muammo")


def _is_plenum(doc_id: int) -> bool:
    return LegalActDocument.objects.filter(abs_id=doc_id, doc_type="PLENUM").exists()
