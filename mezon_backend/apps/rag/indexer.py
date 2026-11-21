"""Moddalarni bo'laklab, bge-m3 bilan Qdrant ga yozish (build_index va lex.uz sinxronizatsiyasi uchun umumiy)."""
from django.conf import settings
from qdrant_client import models
from transformers import AutoTokenizer

from apps.lex_corpus.models import LANGS, LegalActArticle

from .chunking import split_article
from .models_runtime import get_embedder
from .store import DENSE, SPARSE, ensure_collection, get_client, to_sparse

UPSERT_STEP = 512


def build_chunks(articles, langs=None) -> list:
    """Joriy tahrirdagi moddalar -> payload bilan bo'laklar.
    langs=None: faqat moddaning asosiy tili; aks holda ro'yxatdagi tillar ('lat', 'cyr', 'ru') — matni bor moddalar
    uchun. Har bir til alohida bo'laklar bo'ladi (payload["lang"]); qidiruv ularni modda bo'yicha birlashtiradi."""
    tokenizer = AutoTokenizer.from_pretrained(settings.EMBEDDING_MODEL_PATH)

    def count_tokens(text: str) -> int:
        return len(tokenizer(text, add_special_tokens=False, truncation=False)["input_ids"])

    chunks = []
    for a in articles:
        doc = a.document
        for lang in ([None] if langs is None else [x for x in LANGS if x in langs and a.has_lang(x)]):
            lang_code = a.source_lang if lang is None else lang
            source = lang_code == a.source_lang
            title = (doc.title_uz_lat or doc.title_uz_cyr or doc.title_ru) if source else doc.title_for(lang_code)
            lex_id = doc.primary_lex_id if source else doc.lex_id_for(lang_code)
            for c in split_article(a, title, count_tokens, settings.CHUNK_MAX_TOKENS, None if source else lang_code):
                elem = c.elem_ids[0] if c.elem_ids else a.elem_id_in(lang_code)
                c.payload = {
                    "article_id": a.pk, "document_id": doc.abs_id, "lex_id": lex_id,
                    "doc_title": title, "doc_type": doc.doc_type, "hierarchy_weight": doc.hierarchy_weight,
                    "is_amending": doc.is_amending, "unit_type": a.unit_type,
                    "article_number": a.article_number, "heading": a.heading_in(lang_code),
                    "section": a.section_in(lang_code), "lang": lang_code, "chunk_no": c.index,
                    "label": a.lang_label(lang_code),
                    "part_numbers": c.part_numbers, "elem_ids": c.elem_ids,
                    "lex_url": f"https://lex.uz/uz/docs/{lex_id}#{elem}",
                    "edition": a.edition.edition_label, "header": c.header, "text": c.body,
                }
                chunks.append(c)
    return chunks


def upsert_chunks(chunks: list, batch: int = 16, on_progress=None) -> None:
    name, client, embedder = ensure_collection(), get_client(), get_embedder()
    for start in range(0, len(chunks), UPSERT_STEP):
        part = chunks[start:start + UPSERT_STEP]
        vectors = embedder.encode([c.text for c in part], batch_size=batch)
        client.upsert(name, points=[
            models.PointStruct(id=c.chunk_id, vector={DENSE: dense, SPARSE: to_sparse(sparse)}, payload=c.payload)
            for c, (dense, sparse) in zip(part, vectors)
        ])
        if on_progress:
            on_progress(start + len(part), len(chunks))


def remove_documents(doc_ids: list[int]) -> None:
    """Hujjatlarning barcha bo'laklarini indeksdan o'chiradi (qayta yuklash yoki yadrodan chiqish)."""
    if not doc_ids:
        return
    get_client().delete(settings.QDRANT_COLLECTION, points_selector=models.FilterSelector(filter=models.Filter(
        must=[models.FieldCondition(key="document_id", match=models.MatchAny(any=list(doc_ids)))])))


def reindex_documents(doc_ids: list[int]) -> int:
    """Hujjatlarni indeksda yangilaydi: joriy tahrir yoziladi, so'ng eskirgan bo'laklar o'chiriladi. Bo'laklar soni.
    Tartib muhim: avval yozish, keyin o'chirish — embedding paytida xato (GPU OOM) bo'lsa hujjat indeksdan yo'qolmaydi."""
    articles = (LegalActArticle.objects.filter(document_id__in=doc_ids, edition__is_current=True)
                .select_related("document", "edition").order_by("document_id", "position"))
    chunks = build_chunks(articles, langs=LANGS)
    upsert_chunks(chunks)
    client, fresh = get_client(), {}
    for c in chunks:
        fresh.setdefault(c.payload["document_id"], []).append(c.chunk_id)
    for doc_id in doc_ids:
        if doc_id not in fresh:   # yangi bo'lak yo'q — hujjat indeksdan butunlay chiqadi
            remove_documents([doc_id])
            continue
        client.delete(settings.QDRANT_COLLECTION, points_selector=models.FilterSelector(filter=models.Filter(
            must=[models.FieldCondition(key="document_id", match=models.MatchValue(value=doc_id))],
            must_not=[models.HasIdCondition(has_id=fresh[doc_id])])))
    return len(chunks)
