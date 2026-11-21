import time
from django.conf import settings
from qdrant_client import models
from apps.lex_corpus.models import LegalActArticle
from apps.lex_corpus.normalize import normalize_apostrophes
from apps.rag.management.commands.eval_search import CASES
from apps.rag.models_runtime import get_embedder, get_reranker
from apps.rag.store import DENSE, SPARSE, get_client, to_sparse, build_filter

client, emb, rr = get_client(), get_embedder(), get_reranker()
flt = build_filter(exclude_amending=True)
res = {}
for limit in (50, 100):
    for q, d, n in CASES:
        want = LegalActArticle.objects.get(document_id=d, article_number=n, unit_type="ARTICLE", edition__is_current=True).pk
        qn = normalize_apostrophes(q)
        dense, sparse = emb.encode([qn])[0]
        pts = client.query_points(settings.QDRANT_COLLECTION, prefetch=[
            models.Prefetch(query=dense, using=DENSE, limit=limit, filter=flt),
            models.Prefetch(query=to_sparse(sparse), using=SPARSE, limit=limit, filter=flt)],
            query=models.FusionQuery(fusion=models.Fusion.RRF), limit=limit, with_payload=True).points
        sc = rr.score(qn, [f"{p.payload['header']}\n{p.payload['text']}" for p in pts])
        for name, alpha in [("A_rerank", 1.0), ("B_mix0.8", 0.8), ("B_mix0.6", 0.6)]:
            scored = []
            for i, (p, s) in enumerate(zip(pts, sc)):
                rrf = 1 / (1 + i / 10)  # 1.0 -> pasayuvchi
                w = 0.75 + 0.25 * p.payload["hierarchy_weight"]
                scored.append((w * (alpha * s + (1 - alpha) * rrf), p.payload["article_id"]))
            order = []
            for _, a in sorted(scored, reverse=True):
                if a not in order: order.append(a)
            r = order.index(want) + 1 if want in order else None
            res.setdefault((name, limit), []).append(r)
for (name, limit), ranks in sorted(res.items()):
    n = len(ranks)
    print(f"{name:<10} cand={limit:<4} Hit@1 {sum(r == 1 for r in ranks)}/{n}  Hit@5 {sum(bool(r and r <= 5) for r in ranks)}/{n}  MRR {sum(1/r for r in ranks if r)/n:.3f}")
client.close()
