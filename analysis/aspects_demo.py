import time
from apps.rag.search import search_aspects
from apps.rag.store import get_client
q = "Haydovchi mast holda avtohalokat qilib, piyodani og'ir jarohatladi va voqea joyidan qochib ketdi. Unga qanday ma'muriy va jinoiy javobgarlik bor, jabrlanuvchiga zarar qanday qoplanadi?"
for effort in ("medium", "high"):
    t = time.monotonic(); hits, aspects = search_aspects(q, effort=effort)
    print(f"\n== {effort}: {len(hits)} manba, {time.monotonic()-t:.1f} s")
    for a in aspects: print("  Y:", a["topic"], "|", "; ".join(a["queries"]))
    for i, h in enumerate(hits, 1): print(f"  M{i:<2} [{h.topic[:26]:<26}] {h.doc_title[:38]:<38} {h.label[:60]}")
get_client().close()
