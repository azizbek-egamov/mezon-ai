import time
from django.conf import settings
from qdrant_client import models
from apps.rag.models_runtime import get_embedder, get_reranker
from apps.rag.store import DENSE, SPARSE, get_client, to_sparse, build_filter
emb, rr, client = get_embedder(), get_reranker(), get_client()
qs = ["mansabdor shaxs ish bitirish uchun pul olsa", "pora olish", "mansabdor shaxs tomonidan pora olish javobgarlik", "mansab vakolatini suiisteʼmol qilish"]
emb.encode(qs[:1]); rr.score("x", ["y"])  # isitish
t = time.monotonic(); [emb.encode([q]) for q in qs]; print(f"embed alohida: {time.monotonic()-t:.2f}s")
t = time.monotonic(); vecs = emb.encode(qs); print(f"embed paket: {time.monotonic()-t:.2f}s")
flt = build_filter(exclude_amending=True)
d, s = vecs[0]
t = time.monotonic(); client.query_points(settings.QDRANT_COLLECTION, query=d, using=DENSE, limit=50, query_filter=flt); print(f"dense 1 so'rov: {time.monotonic()-t:.2f}s")
t = time.monotonic(); client.query_points(settings.QDRANT_COLLECTION, query=to_sparse(s), using=SPARSE, limit=50, query_filter=flt); print(f"sparse 1 so'rov: {time.monotonic()-t:.2f}s")
t = time.monotonic(); client.query_points(settings.QDRANT_COLLECTION, query=d, using=DENSE, limit=50); print(f"dense filtrsiz: {time.monotonic()-t:.2f}s")
pts = client.query_points(settings.QDRANT_COLLECTION, query=d, using=DENSE, limit=100, with_payload=True).points
texts = [f"{p.payload['header']}\n{p.payload['text']}" for p in pts]
for n, ml in [(100, 1024), (100, 512), (40, 512)]:
    t = time.monotonic(); rr.score(qs[0], texts[:n], max_length=ml); print(f"rerank {n} ta, max_len {ml}: {time.monotonic()-t:.2f}s")
client.close()
