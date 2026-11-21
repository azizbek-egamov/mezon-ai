"""Gibrid huquqiy qidiruv: aniq modda havolasi + Qdrant (dense + sparse) + RRF + reranker + iyerarxiya vazni.

Zanjir:
  1. So'rovdagi aniq havolalar ("JK 168-modda") — bazadan to'g'ridan-to'g'ri, har doim birinchi.
  2. Asl savol + (ixtiyoriy) LLM o'girgan huquqiy atamalar bitta paketda embedding qilinadi.
  3. Har bir so'rov uchun dense va sparse ro'yxatlar (Qdrant filtrsiz — ichki rejimda filtr sekin),
     barcha ro'yxatlar RRF bilan birlashtiriladi; o'zgartirish kirituvchi hujjatlar Python da chiqariladi.
  4. Eng yaxshi RERANK_TOP nomzod reranker bilan baholanadi.
Yakuniy baho = reranker (0..1) × (0.75 + 0.25 × hierarchy_weight) × (0.6 agar o'zgartirish kirituvchi bo'lsa).

Tillar (TZ §5.4): indeksda har bir modda lotin, kirill va rus matnlari bilan turadi (payload["lang"]). Qidiruv
tilga qaramay barcha bo'laklar orasidan ishlaydi (bge-m3 ko'p tilli), bir moddaning turli tildagi nusxalari
nomzodlarda bir marta qoldiriladi. Natija `lang` parametridagi tilga o'tkaziladi (`localize_hits`): rasmiy
matn lex.uz ning shu tildagi versiyasidan; u yo'q bo'lsa — asosiy tilda (payload["lang_fallback"]).
"""
import re
from collections import defaultdict
from contextlib import nullcontext
from dataclasses import dataclass, field
from datetime import date

from django.conf import settings
from qdrant_client import models

from apps.lex_corpus.history import as_of
from apps.lex_corpus.models import LegalActArticle
from apps.lex_corpus.normalize import normalize_apostrophes

from .models_runtime import get_embedder, get_reranker
from .query_rewrite import plan_aspects, rewrite_query
from .source_select import select_sources
from .store import DENSE, SPARSE, build_filter, get_client, to_sparse

AMENDING_PENALTY = 0.6
PER_LIST = 60        # har bir dense/sparse ro'yxatdan olinadigan nuqtalar
RERANK_TOP = 40      # reranker ga beriladigan nomzodlar
RERANK_MAX_LEN = 512
RRF_K = 60
EXACT = models.SearchParams(exact=True)

# Qisqartma / nom -> hujjat abs_id. Uzunroq kalitlar birinchi tekshiriladi.
CODE_ALIASES: dict[str, list[int]] = {
    r"jinoyat[- ]protsessual": [111460], r"\bjpk": [111460],
    r"jinoyat[- ]ijroiya": [163629], r"\bjik\b": [163629],
    r"jinoyat kodeks": [111453], r"\bjk": [111453],
    r"fuqarolik protsessual": [3517337], r"\bfpk": [3517337],
    r"iqtisodiy protsessual": [3523891], r"\bipk": [3523891],
    r"ma.muriy sud ishlarini": [3527353], r"\bmsiyuk": [3527353],
    r"ma.muriy javobgarlik": [97664], r"\bmjtk": [97664],
    r"fuqarolik kodeks": [111189, 180552], r"\bfk": [111189, 180552],
    r"mehnat kodeks": [6257288], r"\bmk\b": [6257288],
    r"soliq kodeks": [4674902], r"\bsk\b": [4674902],
    r"oila kodeks": [104720], r"uy-joy kodeks": [106136], r"yer kodeks": [152653],
    r"bojxona kodeks": [2876354], r"budjet kodeks": [2304138], r"saylov kodeks": [4386848],
    r"shaharsozlik kodeks": [5307951], r"suv kodeks": [7655343], r"havo kodeks": [55594],
    r"konstitutsiya(si|ning|ga|da|dan)?\b": [6445145],
}
ARTICLE_REF_RE = re.compile(r"(\d+[⁰¹²³⁴⁵⁶⁷⁸⁹]*)\s*-?\s*modda")


@dataclass
class SearchHit:
    article_id: int
    document_id: int
    doc_title: str
    label: str
    text: str
    lex_url: str
    score: float
    rerank_score: float = 0.0
    exact: bool = False
    payload: dict = field(default_factory=dict)
    topic: str = ""  # qaysi huquqiy yo'nalish uchun topilgan (search_aspects)
    # Voqea sanasi berilganda (apply_date): {"state": same|changed|unknown, "date": "YYYY-MM-DD", "note": ...};
    # state == changed bo'lsa text — sanadagi tahrir matni, current_text — hozirgi matn.
    as_of: dict = field(default_factory=dict)
    current_text: str = ""


def apply_date(hits: list[SearchHit], on_date: date | None) -> list[SearchHit]:
    """Natijalarni voqea sanasiga moslaydi (TZ §4.2.3). Qidiruv joriy matn bo'yicha ishlaydi; bu yerda har bir
    modda uchun sanadagi versiya bazadan olinadi. Sanada hali kuchga kirmagan normalar natijadan chiqariladi."""
    if on_date is None or not hits:
        return hits
    articles = LegalActArticle.objects.select_related("document", "edition").in_bulk([h.article_id for h in hits])
    out = []
    for h in hits:
        article = articles.get(h.article_id)
        if article is None:
            out.append(h)
            continue
        info = as_of(article, on_date)
        if info.state == "not_yet":
            continue
        h.as_of = {"state": info.state, "date": on_date.isoformat(), "note": info.note,
                   "version_id": info.version.pk if info.version else None}
        if info.state == "changed":
            v = info.version
            h.current_text = h.text
            h.text = v.primary_text  # eski tahrirlar faqat asosiy tilda saqlanadi
            h.lex_url = v.direct_lex_url
            h.payload = {**h.payload, "edition": v.edition.edition_label, "lang": v.source_lang,
                         "lang_fallback": h.payload.get("lang", v.source_lang) != v.source_lang or
                         h.payload.get("lang_fallback", False)}
            if h.payload["lang_fallback"]:
                h.label = v.lang_label(v.source_lang)
        out.append(h)
    return out


def find_exact_articles(query: str) -> list[LegalActArticle]:
    """So'rovdagi aniq havolalar: 'JK 168-modda', 'Jinoyat kodeksining 168-moddasi'."""
    q = normalize_apostrophes(query.lower()).replace("ʻ", "'").replace("ʼ", "'")
    numbers = ARTICLE_REF_RE.findall(q)
    if not numbers:
        return []
    doc_ids: list[int] = []
    rest = q
    for pattern, ids in CODE_ALIASES.items():
        if re.search(pattern, rest):
            doc_ids.extend(i for i in ids if i not in doc_ids)
            rest = re.sub(pattern, " ", rest)
    if not doc_ids:
        return []
    return list(LegalActArticle.objects.filter(
        document_id__in=doc_ids, article_number__in=numbers, unit_type="ARTICLE", edition__is_current=True,
    ).select_related("document", "edition"))


def _hit_from_article(a: LegalActArticle) -> SearchHit:
    doc = a.document
    return SearchHit(article_id=a.pk, document_id=doc.abs_id, doc_title=doc.title_uz_lat or doc.title_uz_cyr,
                     label=f"{a.article_number}-modda. {a.heading}".strip(), text=a.primary_text,
                     lex_url=a.direct_lex_url, score=1.0, rerank_score=1.0, exact=True,
                     payload={"edition": a.edition.edition_label, "doc_type": doc.doc_type, "lang": a.source_lang,
                              "article_number": a.article_number, "unit_type": a.unit_type})


def localize_hits(hits: list[SearchHit], lang: str | None) -> list[SearchHit]:
    """Natijalarni `lang` ('lat' | 'cyr' | 'ru') tiliga o'tkazadi: matn, yorliq, hujjat nomi va havola lex.uz ning
    shu tildagi versiyasidan. lang=None — har bir modda o'zining asosiy tilida (o'zbek lotin). Moddaning bu tilda
    matni yo'q bo'lsa — asosiy tilda qoladi va payload["lang_fallback"]=True. Tarjima tahriri asosiy tahrirdan
    sanasi bilan farq qilsa payload["translation_stale"]=True (matn eskirgan bo'lishi mumkin)."""
    if not hits:
        return hits
    articles = LegalActArticle.objects.select_related("document", "edition").in_bulk({h.article_id for h in hits})
    for h in hits:
        a = articles.get(h.article_id)
        if a is None:
            continue
        want = lang or a.source_lang
        fallback = lang is not None and lang != a.source_lang and not a.has_lang(lang)
        if fallback:
            want = a.source_lang
        stale = bool(a.document.translations.get(want, {}).get("stale")) if want != a.source_lang else False
        if (h.payload.get("lang") or a.source_lang) != want:
            nums = set(h.payload.get("part_numbers") or [])
            parts = [p for p in a.parts_in(want) if not nums or p["n"] in nums]
            if parts:
                h.text = "\n".join(p["text"] for p in parts)
                elem = next((e for p in parts for e in p["elem_ids"]), a.elem_id_in(want))
            else:
                h.text, elem = a.text_in(want), a.elem_id_in(want)
            lex_id = a.document.primary_lex_id if want == a.source_lang else a.document.lex_id_for(want)
            h.label, h.doc_title = a.lang_label(want), a.document.title_for(want)
            h.lex_url = f"https://lex.uz/uz/docs/{lex_id}#{elem}"
        h.payload = {**h.payload, "lang": want, "lang_fallback": fallback, "translation_stale": stale}
    return hits


def dedupe_languages(points: list) -> list:
    """Bir moddaning turli tildagi nusxalari nomzodlarda bir marta qoladi (eng yaxshi o'rindagisi): kalit — modda va
    bo'lakning birinchi qismi. Aks holda 3 tilli indeks 40 ta reranker o'rnini 3 marta kam modda bilan to'ldirardi."""
    seen, out = set(), []
    for p in points:
        nums = p.payload.get("part_numbers") or [0]
        key = (p.payload["article_id"], nums[0])
        if key not in seen:
            seen.add(key)
            out.append(p)
    return out


def _label(p: dict) -> str:
    if p.get("label"):
        return p["label"]
    if p["unit_type"] == "ARTICLE":
        return f"{p['article_number']}-modda. {p['heading']}".strip()
    if p["unit_type"] == "BAND":
        return f"{p['article_number']}-band"
    return "Kirish qismi" if p["unit_type"] == "PREAMBLE" else "Matn"


def _fused_candidates(texts: list[str], flt, sparse_for: int) -> list:
    """Har bir so'rov uchun dense (+ birinchi `sparse_for` ta so'rov uchun sparse) ro'yxat, RRF bilan birlashtirilgan.
    Qdrant 1.10+ native Prefetch + RRF orqali server darajasida birlashtiriladi."""
    client, col = get_client(), settings.QDRANT_COLLECTION
    vectors = get_embedder().encode(texts)
    if not vectors:
        return []

    # 1. Native Qdrant Prefetch + RRF Fusion (Rust darajasida bitta so'rovda birlashtirish)
    try:
        prefetches = []
        for i, (dense, sparse) in enumerate(vectors):
            prefetches.append(models.Prefetch(
                query=dense, using=DENSE, limit=PER_LIST, filter=flt, params=EXACT
            ))
            if i < sparse_for:
                prefetches.append(models.Prefetch(
                    query=to_sparse(sparse), using=SPARSE, limit=PER_LIST, filter=flt
                ))
        if prefetches:
            res = client.query_points(
                col,
                prefetch=prefetches,
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                limit=PER_LIST * 2,
                with_payload=True,
            )
            return res.points
    except Exception:
        # Qdrant ichki/test rejimida yoki mock qilingan client da Prefetch qo'llanmasa — Python fallback
        pass

    scores: dict = defaultdict(float)
    points: dict = {}
    for i, (dense, sparse) in enumerate(vectors):
        # exact=True: 41 ming nuqtada aniq qidiruv ham ~10 ms — taxminiy HNSW (99.5% mos) shart emas.
        lists = [client.query_points(col, query=dense, using=DENSE, limit=PER_LIST, query_filter=flt,
                                     search_params=EXACT, with_payload=True).points]
        if i < sparse_for:
            lists.append(client.query_points(col, query=to_sparse(sparse), using=SPARSE, limit=PER_LIST,
                                             query_filter=flt, with_payload=True).points)
        for lst in lists:
            for rank, p in enumerate(lst):
                scores[p.id] += 1.0 / (RRF_K + rank + 1)
                points[p.id] = p
    return [points[pid] for pid, _ in sorted(scores.items(), key=lambda x: -x[1])]


def search(query: str, limit: int = 10, document_ids: list[int] | None = None, doc_types: list[str] | None = None,
           include_amending: bool = False, rerank: bool = True, rewrite: bool = False,
           expansions: list[str] | None = None, sparse_for: int = 1, on_date: date | None = None,
           lang: str | None = None) -> list[SearchHit]:
    """include_amending=False: o'zgartirish kirituvchi hujjatlar natijaga kirmaydi (ular asl matnni takrorlaydi).
    rewrite=True: LLM savolni huquqiy atamalarga o'giradi; expansions — tayyor so'rovlar.
    sparse_for: sparse qidiruv nechta so'rov uchun bajariladi (1 = faqat asl savol; ichki Qdrant da sparse sekin).
    on_date: voqea sanasi — natijalar o'sha sanadagi tahrirga almashtiriladi (apply_date).
    lang: natija matni tili ('lat' | 'cyr' | 'ru'; `corpus_lang(interfeys_tili)`); None — asosiy til."""
    exact = [_hit_from_article(a) for a in find_exact_articles(query)]
    query = normalize_apostrophes(query)  # "o'g'irlik" -> "oʻgʻirlik" (korpusdagi yozuv)
    if expansions is None:
        expansions = rewrite_query(query) if rewrite else []
    expansions = [normalize_apostrophes(e) for e in expansions]

    # Hujjat/tur filtri kamdan-kam va tor — Qdrant da qo'llanadi; amending — Python da.
    flt = build_filter(document_ids, doc_types) if (document_ids or doc_types) else None
    candidates = dedupe_languages(_fused_candidates([query, *expansions], flt, sparse_for))
    if not include_amending:
        candidates = [p for p in candidates if not p.payload["is_amending"]]
    candidates = candidates[:RERANK_TOP]

    rerank_query = f"{query}\n{'; '.join(expansions)}" if expansions else query
    rerank_scores = (get_reranker().score(rerank_query, [f"{p.payload['header']}\n{p.payload['text']}" for p in candidates],
                                          max_length=RERANK_MAX_LEN)
                     if rerank and candidates else [1.0 / (i + 1) for i in range(len(candidates))])
    hits: dict[int, SearchHit] = {}
    for point, rs in zip(candidates, rerank_scores):
        p = point.payload
        score = rs * (0.75 + 0.25 * p["hierarchy_weight"]) * (AMENDING_PENALTY if p["is_amending"] else 1.0)
        prev = hits.get(p["article_id"])
        if prev is None or score > prev.score:
            hits[p["article_id"]] = SearchHit(
                article_id=p["article_id"], document_id=p["document_id"], doc_title=p["doc_title"], label=_label(p),
                text=p["text"], lex_url=p["lex_url"], score=score, rerank_score=rs, payload=p)

    exact_ids = {h.article_id for h in exact}
    ranked = sorted((h for h in hits.values() if h.article_id not in exact_ids), key=lambda h: h.score, reverse=True)
    return apply_date(localize_hits(exact + ranked, lang), on_date)[:limit]


# Tahlil chuqurligi -> (yo'nalishlar soni, har bir yo'nalishdan manba, jami manba)
SCOPE = {"low": (2, 4, 8), "medium": (4, 5, 15), "high": (6, 5, 25)}
FUSED_KEEP = 2
POOL_PER_ASPECT = 10


def search_aspects(question: str, effort: str = "medium", aspects: list[dict] | None = None,
                   include_amending: bool = False, use_llm_select: bool = True,
                   on_date: date | None = None, lang: str | None = None,
                   slot=None) -> tuple[list[SearchHit], list[dict]]:
    """Murakkab savol: LLM savolni huquqiy yo'nalishlarga ajratadi, har bir yo'nalish alohida qidiriladi va
    qayta tartiblanadi, keyin natijalar birlashtiriladi. Shunda bitta kuchli mavzu (masalan, jinoyat) boshqa
    yo'nalishlar (zararni qoplash, protsess) uchun joy qoldirmay qo'ymaydi.
    use_llm_select=True: har bir yo'nalishdan POOL_PER_ASPECT nomzod yig'iladi va yakuniy manbalarni LLM tanlaydi
    (source_select); LLM ishlamasa — har bir yo'nalishdan per_aspect ta (reranker tartibi).
    slot — GPU/Qdrant qismi uchun qulf (context manager yaratuvchi, masalan `locks.search_slot`); None — qulfsiz.
    Qaytaradi: (manbalar, yo'nalishlar)."""
    max_aspects, per_aspect, total = SCOPE.get(effort, SCOPE["medium"])
    question_n = normalize_apostrophes(question)
    if aspects is None:
        aspects = plan_aspects(question_n, max_aspects)
        if not aspects:   # huquqqa aloqasiz savol (suhbat) — lex.uz da qidirilmaydi
            return [], []
    # Manbalar yo'nalishlar orasida teng taqsimlanadi — oxirgi yo'nalish bo'sh qolmasin.
    per_aspect = max(3, min(per_aspect, total // max(1, len(aspects))))

    # Faqat GPU/Qdrant qismi qulf ostida; LLM chaqiruvlari (yo'nalishlar rejasi, manba tanlovi) qulfdan tashqarida —
    # sekin tarmoq javobi boshqa foydalanuvchilarning qidiruvini to'sib qo'ymasin.
    with (slot() if slot else nullcontext()):
        chosen: list[SearchHit] = [_hit_from_article(a) for a in find_exact_articles(question)]
        for h in chosen:
            h.topic = "Soʻrovdagi havola"
        seen = {h.article_id for h in chosen}
        reranker = get_reranker()
        fallback: list[SearchHit] = []   # LLM tanlovi ishlamasa: har bir yo'nalishdan per_aspect ta
        pool: list[SearchHit] = []       # LLM tanlovi uchun nomzodlar: har bir yo'nalishdan POOL_PER_ASPECT ta
        pooled: set[int] = set(seen)

        for i, aspect in enumerate(aspects):
            queries = [normalize_apostrophes(q) for q in aspect["queries"]]
            texts = ([question_n] if i == 0 else []) + queries  # asl savol faqat asosiy yo'nalishda
            candidates = dedupe_languages(_fused_candidates(texts, None, sparse_for=1))
            if not include_amending:
                candidates = [p for p in candidates if not p.payload["is_amending"]]
            candidates = [p for p in candidates if p.payload["article_id"] not in seen][:RERANK_TOP]
            if not candidates:
                continue
            rerank_query = f"{question_n}\n{aspect['topic']}: {'; '.join(queries)}"
            scores = reranker.score(rerank_query, [f"{p.payload['header']}\n{p.payload['text']}" for p in candidates],
                                    max_length=RERANK_MAX_LEN)
            best: dict[int, SearchHit] = {}
            for point, rs in zip(candidates, scores):
                p = point.payload
                score = rs * (0.75 + 0.25 * p["hierarchy_weight"])
                if p["article_id"] not in best or score > best[p["article_id"]].score:
                    best[p["article_id"]] = SearchHit(
                        article_id=p["article_id"], document_id=p["document_id"], doc_title=p["doc_title"],
                        label=_label(p), text=p["text"], lex_url=p["lex_url"], score=score, rerank_score=rs,
                        payload=p, topic=aspect["topic"])
            # Dense+sparse birlashmasining eng yaxshi FUSED_KEEP tasi reranker bahosidan qat'i nazar olinadi:
            # ikki xil qidiruv bir xil moddani tepaga qo'ysa — bu kuchli dalil, reranker esa ba'zan uni pastga tushiradi.
            keep: list[int] = []
            for p in candidates:
                if p.payload["article_id"] not in keep:
                    keep.append(p.payload["article_id"])
                if len(keep) == FUSED_KEEP:
                    break
            ranked = sorted(best.values(), key=lambda h: h.score, reverse=True)
            picked = [best[a] for a in keep] + [h for h in ranked if h.article_id not in keep]

            # Xilma-xillik: bitta yo'nalishda bitta hujjatdan cheklangan son — aks holda o'xshash moddalar
            # (masalan, MJtK 131/133/134/140) yo'nalishni to'ldirib, boshqa kodeksdagi asosiy moddani siqib chiqaradi.
            for limit, cap, out in ((per_aspect, 2 if per_aspect <= 5 else 3, fallback), (POOL_PER_ASPECT, 4, pool)):
                per_doc: dict[int, int] = defaultdict(int)
                taken = 0
                for h in picked:
                    if taken == limit:
                        break
                    if per_doc[h.document_id] >= cap or (out is pool and h.article_id in pooled):
                        continue
                    per_doc[h.document_id] += 1
                    out.append(h)
                    taken += 1
                    if out is pool:
                        pooled.add(h.article_id)
                    else:
                        seen.add(h.article_id)

    chosen, pool, fallback = (apply_date(localize_hits(x, lang), on_date) for x in (chosen, pool, fallback))
    selected = select_sources(question_n, pool, total - len(chosen)) if use_llm_select else None
    return (chosen + (selected if selected is not None else fallback))[:total], aspects
