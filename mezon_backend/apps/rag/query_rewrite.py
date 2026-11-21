"""Foydalanuvchi savolini rasmiy huquqiy atamalardagi qidiruv so'rovlariga o'girish (Legal Researcher bosqichi).

Odamlar "mansabdor pul olsa" deydi, qonunda esa "pora olish" yozilgan — embedding bu farqni yaxshi
yopmaydi (diag_search natijasi), LLM esa yopadi. Namunalar sinov to'plamidagi savollardan farqli tanlangan.
Natijalar keshlanadi: bir xil savol qayta pul va vaqt sarflamaydi.
"""
import hashlib
import logging

from django.core.cache import cache

from .llm import get_llm, task_model

logger = logging.getLogger(__name__)

SYSTEM = """Sen Oʻzbekiston qonunchiligini biladigan yurist yordamchisisan.
Foydalanuvchi savolini lex.uz dagi qonun matnlarida ishlatiladigan RASMIY HUQUQIY ATAMALARGA oʻgir.
2-3 ta qisqa qidiruv soʻrovi tuz (har biri 3-8 soʻz, oʻzbek lotin yozuvida).
Birinchi soʻrov — huquqbuzarlik yoki huquqiy institutning rasmiy nomi; qolganlari — sinonim atamalar.
Modda raqamini oʻylab topma. Faqat JSON qaytar: {"queries": ["...", "..."]}

Namunalar:
Savol: qarzni qaytarmayapti nima qilsam boʻladi
{"queries": ["qarz shartnomasi boʻyicha majburiyatni bajarmaslik", "qarz summasini undirish", "majburiyatni lozim darajada bajarmaganlik uchun javobgarlik"]}
Savol: qoʻshnim mening yerimni egallab oldi
{"queries": ["yer uchastkasini oʻzboshimchalik bilan egallash", "yer uchastkasiga boʻlgan huquqni himoya qilish"]}
Savol: ijarachi uy haqini toʻlamayapti
{"queries": ["mulk ijarasi shartnomasi ijara haqi", "ijara shartnomasini bekor qilish"]}"""

SCHEMA = {
    "type": "object",
    "properties": {"queries": {"type": "array", "items": {"type": "string"}}},
    "required": ["queries"],
    "additionalProperties": False,
}


def _cache_key(question: str, system: str = SYSTEM, extra: str = "", task: str = "rewrite") -> str:
    llm = get_llm()
    model = task_model(task) or llm.model
    digest = hashlib.sha256(f"{llm.name}:{model}:{system}:{extra}:{question}".encode()).hexdigest()[:32]
    return f"rewrite:{digest}"


# ---------- Ko'p yo'nalishli reja: murakkab savol bir nechta huquq sohasiga tegadi ----------

PLAN_SYSTEM = """Sen Oʻzbekiston qonunchiligini biladigan yurist yordamchisisan.
Foydalanuvchi savolini tahlil qil va javob berish uchun qaysi HUQUQIY YOʻNALISHLAR kerakligini aniqla
(masalan: jinoiy javobgarlik, maʼmuriy javobgarlik, zararni qoplash, mehnat munosabatlari, oilaviy munosabatlar,
mulk huquqi, soliq majburiyatlari, protsessual tartib — tergov, sud, shikoyat, konstitutsiyaviy huquqlar).
Oddiy savolga 1 ta yoʻnalish yetadi; vaziyat bir necha sohaga tegsa — har birini alohida yoz, eng muhimi birinchi.
Har bir yoʻnalish uchun:
  topic — qisqa nom (oʻzbek lotin, 2-6 soʻz);
  queries — lex.uz dagi qonun matnlarida ishlatiladigan RASMIY HUQUQIY ATAMALARDA 2-3 ta qidiruv soʻrovi (har biri 3-8 soʻz).
Modda raqamini oʻylab topma.
legal — savol huquq, qonun, sud, jazo, shartnoma, mehnat, soliq, oila, mulk kabi huquqiy masalaga tegsa true.
Huquqqa umuman aloqasi yoʻq suhbat (salomlashuv, "sen kimsan", "nima qila olasan", ob-havo, matematika, hazil va h.k.)
boʻlsa — legal=false va aspects=[]. Shubha boʻlsa legal=true qil (huquqiy savolni rad etma).
Faqat JSON qaytar."""

PLAN_SCHEMA = {
    "type": "object",
    "properties": {
        "legal": {"type": "boolean"},
        "aspects": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {"topic": {"type": "string"}, "queries": {"type": "array", "items": {"type": "string"}}},
                "required": ["topic", "queries"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["legal", "aspects"],
    "additionalProperties": False,
}


def plan_aspects(question: str, max_aspects: int = 4) -> list[dict]:
    """[{"topic": "...", "queries": [...]}] — eng muhimi birinchi. LLM ishlamasa: bitta yo'nalish, asl savol bilan.
    Savol huquqqa aloqador emas (suhbat, "nima qila olasan") bo'lsa — BO'SH ro'yxat: lex.uz da qidirilmaydi."""
    fallback = [{"topic": "Asosiy savol", "queries": [question]}]
    key = _cache_key(question, PLAN_SYSTEM, extra=str(max_aspects), task="plan")
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        data = get_llm().chat_json(PLAN_SYSTEM, f"Koʻpi bilan {max_aspects} ta yoʻnalish.\nSavol: {question}",
                                   schema=PLAN_SCHEMA, effort="low", model=task_model("plan"))
    except Exception as e:
        logger.warning("Yo'nalishlarni aniqlash ishlamadi: %s", e)
        return fallback
    if isinstance(data, dict) and data.get("legal") is False:
        cache.set(key, [])
        return []
    aspects = []
    for a in (data.get("aspects", []) if isinstance(data, dict) else [])[:max_aspects]:
        queries = [q.strip() for q in a.get("queries", []) if isinstance(q, str) and q.strip()][:3]
        if queries:
            aspects.append({"topic": str(a.get("topic", "")).strip() or queries[0], "queries": queries})
    aspects = aspects or fallback
    cache.set(key, aspects)
    return aspects


def rewrite_query(question: str) -> list[str]:
    key = _cache_key(question)
    cached = cache.get(key)
    if cached is not None:
        return cached
    try:
        data = get_llm().chat_json(SYSTEM, f"Savol: {question}", schema=SCHEMA, effort="low", model=task_model("rewrite"))
    except Exception as e:
        logger.warning("So'rovni o'girish ishlamadi: %s", e)
        return []  # LLM ishlamasa qidiruv asl savol bilan davom etadi
    queries = data.get("queries", []) if isinstance(data, dict) else []
    result = [q.strip() for q in queries if isinstance(q, str) and q.strip()][:3]
    cache.set(key, result)
    return result
