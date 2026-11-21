"""Qdrant kolleksiyasi: nomlangan vektorlar `dense` (bge-m3, 1024, cosine) + `sparse` (bge-m3 leksik og'irliklar)."""
from functools import lru_cache

from django.conf import settings
from qdrant_client import QdrantClient, models

DENSE = "dense"
SPARSE = "sparse"


@lru_cache(maxsize=1)
def get_client() -> QdrantClient:
    if settings.QDRANT_URL:
        return QdrantClient(url=settings.QDRANT_URL)
    settings.QDRANT_PATH.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(settings.QDRANT_PATH))  # ichki rejim (server shart emas)


def ensure_collection(recreate: bool = False, name: str | None = None, client: QdrantClient | None = None) -> str:
    """Server rejimida vektorlar, HNSW grafi, sparse indeks va payload diskda (mmap) — RAM da faqat
    ishlatilayotgan sahifalar turadi. Scalar quantization (INT8) orqali xotira 4 barobar tejaladi."""
    client, name = client or get_client(), name or settings.QDRANT_COLLECTION
    if recreate and client.collection_exists(name):
        client.delete_collection(name)
    if not client.collection_exists(name):
        client.create_collection(
            name,
            vectors_config={DENSE: models.VectorParams(size=1024, distance=models.Distance.COSINE, on_disk=True)},
            sparse_vectors_config={SPARSE: models.SparseVectorParams(index=models.SparseIndexParams(on_disk=True))},
            hnsw_config=models.HnswConfigDiff(on_disk=True),
            quantization_config=models.ScalarQuantization(
                scalar=models.ScalarQuantizationConfig(
                    type=models.ScalarType.INT8,
                    quantile=0.99,
                    always_ram=True,
                )
            ),
            on_disk_payload=True,
        )
    for field, schema in [("document_id", models.PayloadSchemaType.INTEGER),
                          ("article_id", models.PayloadSchemaType.INTEGER),
                          ("article_number", models.PayloadSchemaType.KEYWORD),
                          ("lang", models.PayloadSchemaType.KEYWORD),
                          ("doc_type", models.PayloadSchemaType.KEYWORD),
                          ("is_amending", models.PayloadSchemaType.BOOL)]:
        try:
            client.create_payload_index(name, field, schema)
        except Exception:
            pass
    return name


def to_sparse(weights: dict[int, float]) -> models.SparseVector:
    items = sorted(weights.items())
    return models.SparseVector(indices=[k for k, _ in items], values=[v for _, v in items])


def build_filter(document_ids: list[int] | None = None, doc_types: list[str] | None = None,
                 exclude_amending: bool = False) -> models.Filter | None:
    """Qidiruv doirasi: document_ids YOKI doc_types (masalan, "JPK, JK yoki istalgan Plenum qarori")."""
    should = []
    if document_ids:
        should.append(models.FieldCondition(key="document_id", match=models.MatchAny(any=document_ids)))
    if doc_types:
        should.append(models.FieldCondition(key="doc_type", match=models.MatchAny(any=doc_types)))
    must = []
    if exclude_amending:
        must.append(models.FieldCondition(key="is_amending", match=models.MatchValue(value=False)))
    if not should and not must:
        return None
    return models.Filter(should=should or None, must=must or None)
