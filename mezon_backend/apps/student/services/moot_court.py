"""Sud Simulyatsiyasi (Moot Court & Argumentlar xaritasi).
Talabalar sud jarayoni mashg'ulotlari uchun 3 tomonlama tahlil:
  1. Da'vogar (Ayblov/Advokat) pozitsiyasi va sud nutqi
  2. Javobgar (Himoya) pozitsiyasi va qarshi vajlar
  3. Sudya pozitsiyasi va isbotlash majburiyati taqsimoti
"""
import logging
from apps.rag.llm import get_llm
from apps.rag.search import search

logger = logging.getLogger(__name__)


def simulate_moot_court(case_facts: str, claim_dispute: str = "", lang: str = "lat") -> dict:
    case_facts = case_facts.strip()
    claim_dispute = claim_dispute.strip()

    if not case_facts:
        raise ValueError("Kazus yoki nizo faktlari kiritilishi shart.")

    # 1. Qdrant orqali tegishli kodeks moddalarini lokal qidirish (ZERO AI COST)
    search_query = f"{case_facts[:300]} {claim_dispute[:150]}"
    try:
        hits = search(query=search_query, limit=5, lang=lang)
    except Exception as e:
        logger.warning("Qdrant search error in moot_court: %s", e)
        hits = []

    retrieved_articles = []
    articles_context = []
    for h in hits:
        retrieved_articles.append({
            "article_id": h.article_id,
            "document_id": h.document_id,
            "doc_title": h.doc_title,
            "label": h.label,
            "lex_url": h.lex_url,
            "score": round(h.score, 3),
        })
        articles_context.append(f"[{h.doc_title} - {h.label}]\n{h.text}")

    articles_text = "\n\n---\n\n".join(articles_context) if articles_context else "Lokal qidiruvda moddalar topilmadi."

    system_prompt = (
        "Siz tajribali Oliy sud sudyasi va TDYU Sud simulyatsiyasi (Moot Court) bo'yicha etakchi professorsiz. "
        "Foydalanuvchi taqdim etgan yuridik ish yoki kazus bo'yicha sud majlisi uchun professional "
        "3 tomonlama argumentlar xaritasini (Da'vogar, Javobgar, Sudya) tuzib bering.\n"
        "Faqat O'zbekiston Respublikasining amaldagi qonunchiligi (FK, JK, MK, FPK, IPK, MSIYK) normalariga tayaning.\n\n"
        "Javobni FAQAT JSON formatida quyidagi sxemada qaytaring:\n"
        "{\n"
        '  "case_title": "Nizo sarlavhasi",\n'
        '  "legal_domain": "Fuqarolik / Iqtisodiy / Mehnat / Jinoyat / Maʼmuriy",\n'
        '  "plaintiff": {\n'
        '    "title": "Daʼvogar (yoki Prokuror/Jabrlanuvchi) pozitsiyasi",\n'
        '    "demands": ["Asosiy daʼvo talablari (2-3 ta)"],\n'
        '    "legal_basis": ["Qonun moddalari va asoslar"],\n'
        '    "key_evidence": ["Sudga taqdim etilishi lozim boʻlgan dalillar"],\n'
        '    "opening_speech": "Sudda soʻzlanadigan taʼsirli va savodli kirish nutqi matni (1-2 xatboshi)"\n'
        '  },\n'
        '  "defendant": {\n'
        '    "title": "Javobgar (Himoyachi) pozitsiyasi",\n'
        '    "counter_arguments": ["Daʼvoga qarshi asosiy vajlar va eʼtirozlar"],\n'
        '    "procedural_defenses": ["Protsessual himoya vositalari (muddat, dalilning nomaqbulligi)"],\n'
        '    "counter_claim_possible": "Qarshi daʼvo kiritish asosi bor/yoʻqligi",\n'
        '    "defense_speech": "Javobgar himoya nutqi matni (1-2 xatboshi)"\n'
        '  },\n'
        '  "judge": {\n'
        '    "title": "Sudya tahlili va ehtimoliy yechim",\n'
        '    "burden_of_proof": "Kim nimani isbotlashi shartligi (isbotlash majburiyati taqsimoti)",\n'
        '    "key_decision_factors": ["Sud qarori uchun hal qiluvchi 2-3 ta omil"],\n'
        '    "probable_verdict": "Qonuniy va adolatli sud qarori xulosasi (qanoatlantirish yoki rad etish)"\n'
        '  }\n'
        "}"
    )

    user_message = f"""KAZUS FAKTLARI VA NIZO:
{case_facts}

QO'SHIMCHA SAVOL / DA'VO TALABI:
{claim_dispute or "Da'vogar va javobgar o'rtasidagi nizoni sudda ko'rish uchun to'liq tahlil qiling."}

BAZADAN TOPILGAN TEGISHLI MODDALAR:
{articles_text}
"""

    llm = get_llm()
    try:
        data = llm.chat_json(system=system_prompt, user=user_message)
        if isinstance(data, dict):
            data["retrieved_articles"] = retrieved_articles
            return data
    except Exception as e:
        logger.error("Moot court simulation error: %s", e)

    return {
        "case_title": "Sud simulyatsiyasi",
        "legal_domain": "Fuqarolik huquqi",
        "plaintiff": {
            "title": "Daʼvogar pozitsiyasi",
            "demands": ["Zararni qoplash va huquqlarni tiklash"],
            "legal_basis": ["FK tegishli moddalari"],
            "key_evidence": ["Shartnoma, yozishmalar, toʻlov hujjatlari"],
            "opening_speech": "Hurmatli sud! Daʼvomiz amaldagi qonunchilikka toʻliq mos boʻlib, qanoatlantirilishini soʻraymiz.",
        },
        "defendant": {
            "title": "Javobgar pozitsiyasi",
            "counter_arguments": ["Daʼvogarning talablari asossiz"],
            "procedural_defenses": ["Daʼvo muddatining oʻtganligi"],
            "counter_claim_possible": "Mavjud emas",
            "defense_speech": "Hurmatli sud! Daʼvogarning daʼvosi asossiz boʻlganligi sababli uni rad etishingizni soʻraymiz.",
        },
        "judge": {
            "title": "Sudya tahlili",
            "burden_of_proof": "Daʼvogar oʻz talablarini, javobgar eʼtirozlarini isbotlashi shart.",
            "key_decision_factors": ["Moddiy huquq normalariga rioya qilinganligi"],
            "probable_verdict": "Taqdim etilgan dalillar asosida qaror qabul qilinadi.",
        },
        "retrieved_articles": retrieved_articles,
    }

