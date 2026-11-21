"""Qdrant asosidagi semantik kesh: o'xshash yuridik savollar uchun javob va manbalarni qayta hisoblashsiz berish.

Savol bge-m3 modeli bilan vektorlanadi (dense 1024) va mezon_semantic_cache kolleksiyasida kosinus o'xshashligi
bo'yicha qidiriladi. Agar o'xshashlik chegaradan (SEMANTIC_CACHE_THRESHOLD, default 0.94) yuqori bo'lsa,
avval tekshirilgan javob, manbalar va yo'nalishlar darhol oqimga uzatiladi. Bu LLM xarajatini 100% tejaydi
va javob berish vaqtini sekundlardan ~15-20 millisekundgacha qisqartiradi.
"""
import logging
import time
import uuid
from datetime import date

from django.conf import settings
from qdrant_client import QdrantClient, models

from apps.lex_corpus.normalize import normalize_apostrophes

from .models_runtime import get_embedder
from .store import get_client

logger = logging.getLogger(__name__)

CACHE_NAMESPACE = uuid.UUID("3c4f7b21-9e5a-4b08-9d22-7f1a8e5c3b99")


def ensure_cache_collection(recreate: bool = False, name: str | None = None,
                            client: QdrantClient | None = None) -> str:
    """Semantik kesh kolleksiyasi: 1024-o'lchamli dense vektorlar (Cosine, on_disk=True),
    xotirani tejash uchun Scalar Quantization (INT8) va payload indekslari."""
    client = client or get_client()
    name = name or getattr(settings, "QDRANT_CACHE_COLLECTION", "mezon_semantic_cache")

    if recreate and client.collection_exists(name):
        client.delete_collection(name)

    if not client.collection_exists(name):
        client.create_collection(
            name,
            vectors_config=models.VectorParams(size=1024, distance=models.Distance.COSINE, on_disk=True),
            quantization_config=models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(
                    type=models.ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True,
                )
            ),
            on_disk_payload=True,
        )
        for field, schema in [
            ("lang", models.PayloadSchemaType.KEYWORD),
            ("effort", models.PayloadSchemaType.KEYWORD),
            ("on_date", models.PayloadSchemaType.KEYWORD),
            ("created_at", models.PayloadSchemaType.FLOAT),
        ]:
            try:
                client.create_payload_index(name, field, schema)
            except Exception:
                pass

    return name


def get_cached_answer(question: str, lang: str, effort: str, on_date: date | None = None,
                      threshold: float | None = None, client: QdrantClient | None = None) -> dict | None:
    """Savolga semantik jihatdan mos keluvchi keshdagi yozuvni qidiradi."""
    if not getattr(settings, "SEMANTIC_CACHE_ENABLED", True):
        return None

    norm_q = normalize_apostrophes(question.strip())
    if not norm_q:
        return None

    try:
        client = client or get_client()
        col = getattr(settings, "QDRANT_CACHE_COLLECTION", "mezon_semantic_cache")
        ensure_cache_collection(name=col, client=client)

        dense = get_embedder().encode([norm_q])[0][0]
        thresh = threshold if threshold is not None else getattr(settings, "SEMANTIC_CACHE_THRESHOLD", 0.94)
        on_date_str = on_date.isoformat() if on_date else ""

        must_conditions = [
            models.FieldCondition(key="lang", match=models.MatchValue(value=lang)),
            models.FieldCondition(key="effort", match=models.MatchValue(value=effort)),
            models.FieldCondition(key="on_date", match=models.MatchValue(value=on_date_str)),
        ]
        flt = models.Filter(must=must_conditions)

        res = client.query_points(
            collection_name=col,
            query=dense,
            query_filter=flt,
            score_threshold=thresh,
            limit=1,
            with_payload=True,
        )

        if not res.points:
            return None

        hit = res.points[0]
        p = hit.payload or {}

        # Hit count statistikasini yangilash
        try:
            client.set_payload(
                collection_name=col,
                payload={"hit_count": p.get("hit_count", 0) + 1},
                points=[hit.id],
            )
        except Exception:
            pass

        return {
            "aspects": p.get("aspects", []),
            "sources": p.get("sources", []),
            "answer": p.get("answer", ""),
            "verification": p.get("verification", {"ok": True, "citations": [], "quotes_checked": 0, "issues": []}),
            "usage": p.get("usage", {}),
            "similarity": round(float(hit.score), 4),
            "cached": True,
        }
    except Exception as e:
        logger.warning("Semantik keshni o'qishda xatolik: %s", e)
        return None


def set_cached_answer(question: str, lang: str, effort: str, aspects: list[dict],
                      sources: list[dict], answer: str, verification: dict,
                      usage: dict | None = None, on_date: date | None = None,
                      client: QdrantClient | None = None) -> bool:
    """Tekshiruvdan muvaffaqiyatli o'tgan to'liq javobni semantik keshga saqlaydi."""
    if not getattr(settings, "SEMANTIC_CACHE_ENABLED", True):
        return False

    norm_q = normalize_apostrophes(question.strip())
    if not norm_q or not answer:
        return False

    if verification and not verification.get("ok", True):
        return False

    try:
        client = client or get_client()
        col = getattr(settings, "QDRANT_CACHE_COLLECTION", "mezon_semantic_cache")
        ensure_cache_collection(name=col, client=client)

        dense = get_embedder().encode([norm_q])[0][0]
        on_date_str = on_date.isoformat() if on_date else ""

        key = f"{lang}:{effort}:{on_date_str}:{norm_q.lower()}"
        point_id = str(uuid.uuid5(CACHE_NAMESPACE, key))

        payload = {
            "question": norm_q,
            "lang": lang,
            "effort": effort,
            "on_date": on_date_str,
            "aspects": aspects,
            "sources": sources,
            "answer": answer,
            "verification": verification,
            "usage": usage or {},
            "created_at": time.time(),
            "hit_count": 0,
        }

        client.upsert(
            collection_name=col,
            points=[models.PointStruct(id=point_id, vector=dense, payload=payload)],
        )
        return True
    except Exception as e:
        logger.warning("Semantik keshga yozishda xatolik: %s", e)
        return False


def clear_semantic_cache(client: QdrantClient | None = None) -> bool:
    """Barcha semantik kesh yozuvlarini tozalaydi (masalan, qonunlar yangilanganda)."""
    try:
        client = client or get_client()
        col = getattr(settings, "QDRANT_CACHE_COLLECTION", "mezon_semantic_cache")
        if client.collection_exists(col):
            client.delete_collection(col)
        ensure_cache_collection(name=col, client=client)
        return True
    except Exception as e:
        logger.error("Semantik keshni tozalashda xatolik: %s", e)
        return False

