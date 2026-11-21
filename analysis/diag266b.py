from apps.rag.search import _fused_candidates, plan_aspects
from apps.rag.store import get_client
from apps.lex_corpus.normalize import normalize_apostrophes
q = normalize_apostrophes("Haydovchi mast holda avtohalokat qilib, piyodani og'ir jarohatladi va voqea joyidan qochib ketdi. Unga qanday ma'muriy va jinoiy javobgarlik bor, jabrlanuvchiga zarar qanday qoplanadi?")
for mx in (4, 6):
    aspects = plan_aspects(q, mx)
    for i, a in enumerate(aspects):
        texts = ([q] if i == 0 else []) + [normalize_apostrophes(x) for x in a["queries"]]
        c = [p for p in _fused_candidates(texts, None, 1) if not p.payload["is_amending"]]
        ids = []
        for p in c:
            if p.payload["article_id"] not in ids: ids.append(p.payload["article_id"])
        r = ids.index(60778) + 1 if 60778 in ids else None
        top = [f"{p.payload['doc_title'][15:30]} {p.payload['article_number']}" for p in c[:4]]
        print(mx, i, a["topic"][:40], "| JK266 fused:", r, "| top4:", top)
get_client().close()
