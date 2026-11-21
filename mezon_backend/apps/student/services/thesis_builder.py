"""Kurs ishi va BMI (Bitiruv malakaviy ishi) yo'riqnoma konstruktori.
Talabalarga ilmiy reja, dolzarblik, obyekt, maqsad, vazifalar,
normativ-huquqiy baza va adabiyotlar ro'yxatini tuzib beradi.
"""
import logging
from apps.rag.llm import get_llm
from apps.rag.search import search

logger = logging.getLogger(__name__)


def build_thesis_roadmap(topic: str, work_type: str = "COURSEWORK", lang: str = "lat") -> dict:
    topic = topic.strip()
    if not topic:
        raise ValueError("Mavzu kiritilishi shart.")

    # 1. Qdrant orqali mavzuga oid asosiy qonun va kodekslarni qidirish
    try:
        hits = search(query=topic, limit=6, lang=lang)
    except Exception as e:
        logger.warning("Qdrant search error in thesis_builder: %s", e)
        hits = []

    retrieved_laws = []
    laws_context = []
    for h in hits:
        retrieved_laws.append({
            "doc_title": h.doc_title,
            "label": h.label,
            "lex_url": h.lex_url,
        })
        laws_context.append(f"{h.doc_title} ({h.label}) - {h.lex_url}")

    laws_text = "\n".join(laws_context) if laws_context else "Lokal qonunlar"

    work_type_labels = {
        "COURSEWORK": "Kurs ishi",
        "THESIS": "Bitiruv malakaviy ishi (BMI)",
        "MASTER": "Magistrlik dissertatsiyasi",
    }
    work_label = work_type_labels.get(work_type, "Kurs ishi")

    system_prompt = (
        "Siz O'zbekiston Respublikasi yuridik fanlari doktori, professor va ilmiy rahbarsiz. "
        "Yuridik talabaning tanlagan mavzusi bo'yicha TDYU va Oliy attestatsiya komissiyasi "
        "standartlariga mos keluvchi mukammal ilmiy ish yo'riqnomasini (reja, dolzarblik, "
        "obyekt, maqsad, vazifalar, normativ baza) tuzing.\n\n"
        "Javobni FAQAT JSON formatida quyidagi sxemada qaytaring:\n"
        "{\n"
        '  "topic": "Mavzu nomi",\n'
        '  "work_type": "Kurs ishi / BMI / Magistrlik",\n'
        '  "relevance": "Mavzuning dolzarbligi va bugungi kundagi ilmiy-amaliy ahamiyati (2 xatboshi)",\n'
        '  "object_and_subject": {\n'
        '    "object": "Tadqiqot obyekti",\n'
        '    "subject": "Tadqiqot predmeti"\n'
        '  },\n'
        '  "goal_and_tasks": {\n'
        '    "goal": "Tadqiqotning asosiy maqsadi",\n'
        '    "tasks": ["Vazifa 1", "Vazifa 2", "Vazifa 3", "Vazifa 4"]\n'
        '  },\n'
        '  "outline": [\n'
        '    {\n'
        '      "chapter": "KIRISH",\n'
        '      "description": "Mavzuning dolzarbligi, maqsadi va vazifalari"\n'
        '    },\n'
        '    {\n'
        '      "chapter": "I BOB. [Bob nomi: Nazariy-huquqiy asoslar]",\n'
        '      "sections": ["1.1. Fasl nomi", "1.2. Fasl nomi", "1.3. Fasl nomi"]\n'
        '    },\n'
        '    {\n'
        '      "chapter": "II BOB. [Bob nomi: Huquqni qoʻllash amaliyoti va qonunchilik tahlili]",\n'
        '      "sections": ["2.1. Fasl nomi", "2.2. Fasl nomi", "2.3. Fasl nomi"]\n'
        '    },\n'
        '    {\n'
        '      "chapter": "III BOB. [Bob nomi: Milliy qonunchilikni takomillashtirish va xorijiy tajriba]",\n'
        '      "sections": ["3.1. Xorijiy tajriba tahlili", "3.2. Qonunchilikka takliflar"]\n'
        '    },\n'
        '    {\n'
        '      "chapter": "XULOSA VA TAKLIFLAR",\n'
        '      "description": "Ilmiy xulosalar va amaliy tavsiyalar"\n'
        '    }\n'
        '  ],\n'
        '  "literature_recommendations": [\n'
        '    "Tavsiya etiladigan darslik yoki monografiya 1",\n'
        '    "Tavsiya etiladigan darslik yoki monografiya 2",\n'
        '    "Tavsiya etiladigan ilmiy maqolalar toʻplami"\n'
        '  ]\n'
        "}"
    )

    user_message = f"""ILMIY ISH MAVZUSI: {topic}
ISH TURI: {work_label}

MAVZUGA OID AMALDAGI QONUNCHILIK MODDALARI:
{laws_text}
"""

    llm = get_llm()
    try:
        data = llm.chat_json(system=system_prompt, user=user_message)
        if isinstance(data, dict):
            data["normative_sources"] = retrieved_laws
            return data
    except Exception as e:
        logger.error("Thesis roadmap error: %s", e)

    return {
        "topic": topic,
        "work_type": work_label,
        "relevance": f"{topic} mavzusi Oʻzbekiston Respublikasida sud-huquq islohotlari sharoitida oʻta dolzarbdir.",
        "object_and_subject": {
            "object": "Mavzuga oid ijtimoiy-huquqiy munosabatlar",
            "subject": "Oʻzbekiston Respublikasi qonun hujjatlari va huquqni qoʻllash amaliyoti",
        },
        "goal_and_tasks": {
            "goal": f"{topic} sohasidagi huquqiy munosabatlarni har tomonlama tahlil qilish",
            "tasks": [
                "Nazariy-huquqiy asoslarni ochib berish",
                "Amaldagi qonunchilik normalarini tahlil qilish",
                "Sud amaliyoti va muammolarni aniqlash",
                "Qonunchilikni takomillashtirish boʻyicha takliflar ishlab chiqish",
            ],
        },
        "outline": [
            {"chapter": "KIRISH", "description": "Dolzarblik, maqsad va vazifalar"},
            {"chapter": "I BOB. Nazariy-huquqiy asoslar", "sections": ["1.1. Tushuncha va mohiyat", "1.2. Huquqiy tartibga solish bosqichlari"]},
            {"chapter": "II BOB. Amaliyot va tahlil", "sections": ["2.1. Sud amaliyoti", "2.2. Huquqiy muammolar"]},
            {"chapter": "III BOB. Takomillashtirish", "sections": ["3.1. Xorijiy tajriba", "3.2. Ilmiy xulosalar"]},
            {"chapter": "XULOSA", "description": "Yakuniy xulosalar va takliflar"},
        ],
        "normative_sources": retrieved_laws,
        "literature_recommendations": [
            "Oʻzbekiston Respublikasi Konstitutsiyasi va Kodekslari",
            "TDYU darsliklari va oʻquv qoʻllanmalari",
        ],
    }

