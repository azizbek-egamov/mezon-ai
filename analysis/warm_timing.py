import time
from apps.rag.search import search
from apps.rag.store import get_client
for q in ["mansabdor shaxs ish bitirish uchun pul olsa", "mansabdor shaxs ish bitirish uchun pul olsa", "mast holda mashina haydagan haydovchiga jarima"]:
    t = time.monotonic(); hits = search(q, limit=5, rewrite=True); print(f"{time.monotonic()-t:5.2f} s  {q[:40]:<40} -> {hits[0].label[:50]}")
get_client().close()
