from apps.lex_corpus.models import LegalActArticle as A
from apps.rag.search import _fused_candidates, RERANK_TOP
from apps.rag.models_runtime import get_reranker
from apps.rag.store import get_client
from apps.lex_corpus.normalize import normalize_apostrophes
for n in ["266", "267"]:
    a = A.objects.get(document_id=111453, article_number=n, edition__is_current=True, unit_type="ARTICLE"); print(n, a.heading, a.pk)
want = A.objects.get(document_id=111453, article_number="266", edition__is_current=True, unit_type="ARTICLE").pk
q = normalize_apostrophes("Haydovchi mast holda avtohalokat qilib, piyodani og'ir jarohatladi va voqea joyidan qochib ketdi. Unga qanday ma'muriy va jinoiy javobgarlik bor, jabrlanuvchiga zarar qanday qoplanadi?")
qs = ["transport vositalari harakati xavfsizligi qoidalarini buzish badanga ogʻir shikast", "transport vositasini boshqaruvchi shaxs harakat xavfsizligi qoidalarini buzish"]
for texts in ([q] + qs[:1], qs, [qs[1]]):
    c = _fused_candidates(texts, None, sparse_for=1)
    ids = [p.payload["article_id"] for p in c]
    r = ids.index(want) + 1 if want in ids else None
    s = get_reranker().score(q + "\n" + "; ".join(texts), [f"{p.payload['header']}\n{p.payload['text']}" for p in c[:RERANK_TOP]], max_length=512)
    order = [p.payload["article_id"] for _, p in sorted(zip(s, c[:RERANK_TOP]), key=lambda x: -x[0])]
    print("fused rank:", r, "| rerank rank:", order.index(want) + 1 if want in order else None, "|", [t[:30] for t in texts])
get_client().close()
