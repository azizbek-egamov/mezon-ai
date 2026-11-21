"""Qidiruv bosqichlari bo'yicha tashxis: kutilgan modda dense / sparse / RRF / reranker da nechanchi o'rinda.

    python manage.py diag_search
"""
from django.conf import settings
from django.core.management.base import BaseCommand
from qdrant_client import models

from apps.lex_corpus.models import LegalActArticle
from apps.lex_corpus.normalize import normalize_apostrophes
from apps.rag.management.commands.eval_search import CASES
from apps.rag.models_runtime import get_embedder, get_reranker
from apps.rag.store import DENSE, SPARSE, get_client, to_sparse


def rank_of(article_id: int, points) -> int | None:
    seen = []
    for p in points:
        a = p.payload["article_id"]
        if a not in seen:
            seen.append(a)
    return seen.index(article_id) + 1 if article_id in seen else None


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--k", type=int, default=200)

    def handle(self, *args, k, **opts):
        client, emb, rr = get_client(), get_embedder(), get_reranker()
        col = settings.QDRANT_COLLECTION
        self.stdout.write(f"{'savol':<45} dense sparse  rrf50 rerank")
        for q, d, n in CASES:
            want = LegalActArticle.objects.get(document_id=d, article_number=n, unit_type="ARTICLE",
                                               edition__is_current=True).pk
            qn = normalize_apostrophes(q)
            dense, sparse = emb.encode([qn])[0]
            dp = client.query_points(col, query=dense, using=DENSE, limit=k, with_payload=True).points
            sp = client.query_points(col, query=to_sparse(sparse), using=SPARSE, limit=k, with_payload=True).points
            fused = client.query_points(col, prefetch=[
                models.Prefetch(query=dense, using=DENSE, limit=50),
                models.Prefetch(query=to_sparse(sparse), using=SPARSE, limit=50)],
                query=models.FusionQuery(fusion=models.Fusion.RRF), limit=50, with_payload=True).points
            scores = rr.score(qn, [f"{p.payload['header']}\n{p.payload['text']}" for p in fused])
            reranked = [p for _, p in sorted(zip(scores, fused), key=lambda x: -x[0])]
            fmt = lambda r: f"{r:>5}" if r else "    -"
            self.stdout.write(f"{q[:45]:<45} {fmt(rank_of(want, dp))} {fmt(rank_of(want, sp))}  "
                              f"{fmt(rank_of(want, fused))} {fmt(rank_of(want, reranked))}")
        client.close()
