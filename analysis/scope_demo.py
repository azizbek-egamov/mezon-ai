import time
from apps.rag.search import search
from apps.rag.store import get_client
SCOPE = dict(document_ids=[111460, 111453, 6445145, 163629], doc_types=["PLENUM"])
cases = [
    ("Ekspertiza tayinlash qarori bilan kech tanishtirish", ["ekspertiza tayinlash toʻgʻrisidagi qaror bilan tanishtirish", "ayblanuvchining ekspertiza tayinlashdagi huquqlari"]),
    ("Tanib olish bitta fotosurat bilan oʻtkazilgan", ["tanib olish uchun koʻrsatish tartibi", "fotosurat boʻyicha tanib olish"]),
    ("Himoya iltimosnomasining asossiz rad etilishi", ["iltimosnomani rad qilish toʻgʻrisida qaror", "iltimoslar qilish va ularni hal qilish"]),
]
for q, exp in cases:
    for name, kw in (("cheklovsiz", {}), ("jinoyat doirasi", SCOPE)):
        t = time.monotonic(); hits = search(q, limit=5, expansions=exp, **kw)
        print(f"{name:<16} {time.monotonic()-t:4.1f}s | {q[:40]:<40} | " + "; ".join(f"{h.doc_title[15:40]} {h.label[:28]}" for h in hits[:4]))
get_client().close()
