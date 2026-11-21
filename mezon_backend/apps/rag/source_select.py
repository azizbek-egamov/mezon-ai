"""Yakuniy manbalarni LLM bilan tanlash (LLM-rerank).

bge-reranker o'zbekcha huquqiy matnlarda beqaror: masalan, mast haydovchi savolida JK 266 ("transport
harakati xavfsizligi qoidalarini buzish") dense+sparse da 3-o'rinda, reranker esa uni tushirib yuboradi.
Kuchli LLM qonunchilikni biladi: unga har bir yo'nalishdan nomzodlar (sarlavha + qisqa parcha) beriladi,
u javob uchun kerak bo'lganlarini tartib bilan tanlaydi. Natija keshlanadi; LLM ishlamasa — None.
"""
import hashlib
import logging

from django.core.cache import cache

from .llm import get_llm, task_model

logger = logging.getLogger(__name__)

SNIPPET_CHARS = 220

SYSTEM = """Sen Oʻzbekiston qonunchiligini chuqur biladigan yuristsan.
Senga foydalanuvchi savoli va lex.uz dan topilgan NOMZOD MANBALAR roʻyxati beriladi (id | yoʻnalish | hujjat | modda | parcha).
Savolga toʻliq va aniq javob berish uchun KERAK boʻlgan manbalarni tanla:
- har bir yoʻnalish qamrab olinsin; asosiy (javobgarlik belgilovchi) moddalar birinchi;
- javobgarlik moddasi (kodeks) + uni tushuntiruvchi Plenum bandi juftligi foydali;
- savolga aloqasi yoʻq, takrorlanuvchi yoki faqat chetdan tegib oʻtadigan manbalarni tanlama.
Faqat roʻyxatdagi id larni ishlat. Muhimlik tartibida qaytar. Faqat JSON."""

SCHEMA = {
    "type": "object",
    "properties": {"selected": {"type": "array", "items": {"type": "string"}}},
    "required": ["selected"],
    "additionalProperties": False,
}


def select_sources(question: str, candidates: list, limit: int) -> list | None:
    """candidates — SearchHit lar (topic bilan). Tanlangan SearchHit lar ro'yxati yoki None (LLM ishlamasa)."""
    if not candidates:
        return []
    ids = {f"C{i}": h for i, h in enumerate(candidates, 1)}
    lines = [
        f"{cid} | {h.topic} | {h.doc_title} | {h.label} | {' '.join(h.text.split())[:SNIPPET_CHARS]}"
        for cid, h in ids.items()
    ]
    user = (f"Savol: {question}\n\nKoʻpi bilan {limit} ta manba tanla.\n\nNOMZODLAR:\n" + "\n".join(lines))
    llm = get_llm()
    model = task_model("select")
    key = "select:" + hashlib.sha256(f"{llm.name}:{model or llm.model}:{SYSTEM}:{user}".encode()).hexdigest()[:32]
    selected = cache.get(key)
    if selected is None:
        try:
            data = llm.chat_json(SYSTEM, user, schema=SCHEMA, effort="low", model=model)
        except Exception as e:
            logger.warning("Manbalarni LLM bilan tanlash ishlamadi: %s", e)
            return None
        selected = [c for c in data.get("selected", []) if isinstance(c, str)] if isinstance(data, dict) else []
        cache.set(key, selected)
    out, used = [], set()
    for cid in selected:
        if cid in ids and cid not in used:
            used.add(cid)
            out.append(ids[cid])
        if len(out) == limit:
            break
    return out or None
