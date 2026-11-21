"""Kazuslar ustaxonasi (Legal Case Solver & Trainer).
O'zbekiston Respublikasi yuridik ta'limi (TDYU va OTMlar) uchun IRAC metodologiyasi:
  1. Issue (Muammo / Huquqiy nizo)
  2. Rule (Qonun normasi va Lex.uz moddalari)
  3. Analysis / Subsumption (Faktlarning qonun bilan tahlili)
  4. Conclusion (Yakuniy sud yoki advokat xulosasi)
  5. Student Assessment (Talaba javobini baholash va taqriz)
"""
import json
import logging
from apps.rag.llm import get_llm
from apps.rag.search import search
from apps.student.models import StudentCaseBank, StudentCaseSubmission

logger = logging.getLogger(__name__)


def solve_legal_case(
    facts: str,
    task_question: str = "",
    student_answer: str = "",
    case_bank_id: int | None = None,
    user=None,
    lang: str = "lat"
) -> dict:
    """Kazusni tahlil qiladi va IRAC yechimini shakllantiradi."""
    facts = facts.strip()
    task_question = task_question.strip()
    student_answer = student_answer.strip()

    case_bank_item = None
    if case_bank_id:
        try:
            case_bank_item = StudentCaseBank.objects.get(id=case_bank_id)
            if not facts:
                facts = case_bank_item.facts
            if not task_question:
                task_question = case_bank_item.task_question
        except StudentCaseBank.DoesNotExist:
            pass

    if not facts:
        raise ValueError("Kazus faktlari kiritilishi shart.")

    # 1. Qdrant orqali tegishli kodeks moddalarini lokal qidirish (ZERO AI API COST)
    search_query = f"{facts[:300]} {task_question[:150]}"
    try:
        hits = search(query=search_query, limit=5, lang=lang)
    except Exception as e:
        logger.warning("Qdrant search error in case_solver: %s", e)
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
        articles_context.append(f"[{h.doc_title} - {h.label}]\n{h.text}\nHavola: {h.lex_url}")

    articles_text = "\n\n---\n\n".join(articles_context) if articles_context else "Lokal qidiruvda moddalar topilmadi."

    # 2. Gemini 3.1 Flash Lite orqali IRAC tahlili
    system_prompt = (
        "Siz O'zbekiston Respublikasi huquqi bo'yicha yetuk professor, sudya va advokatsiz. "
        "Yuridik talabalar uchun berilgan amaliy kazusni xalqaro va milliy IRAC uslubida "
        "(Muammo -> Qoida -> Tahlil -> Xulosa) chuqur, aniq va savodli tahlil qilib bering.\n\n"
        "Qonuniy asos sifatida faqat O'zbekiston Respublikasining amaldagi qonun hujjatlariga "
        "(FK, JK, MK, FPK, JPK, MSIYK, Oliy sud Plenumi qarorlari) tayaning.\n"
        "Quyida qonunchilik bazasidan topilgan tegishli moddalar berilgan, ulardan to'liq foydalaning.\n\n"
        "Javobni FAQAT JSON formatida quyidagi sxemada qaytaring:\n"
        "{\n"
        '  "title": "Kazusning qisqa yuridik mavzusi",\n'
        '  "issue": "1. Asosiy huquqiy nizo: qanday huquqiy munosabat kelib chiqqan va qanday savollar hal etilishi kerak.",\n'
        '  "rules": "2. Qoʻllaniladigan qonun normalari (moddalar raqami, mazmuni va lex.uz havolalari).",\n'
        '  "analysis": "3. Subsumptsiya tahlili: kazusdagi voqelik va faktlarni qonun normalari bilan bogʻlash.",\n'
        '  "conclusion": "4. Yakuniy xulosa: nizo qanday hal qilinishi kerak, sud qanday qaror qabul qilishi lozim.",\n'
        '  "action_steps": ["Taraflar yoki advokat amalga oshirishi kerak boʻlgan 3-4 ta amaliy qadam"],\n'
        '  "student_assessment": {\n'
        '    "evaluated": true/false,\n'
        '    "score": 0-100 (agar talaba oʻz javobini yozgan boʻlsa, baholang; yozmagan boʻlsa null),\n'
        '    "strengths": "Talaba toʻgʻri topgan jihatlar",\n'
        '    "mistakes": "Yoʻl qoʻyilgan xatolar va tushirib qoldirilgan moddalar",\n'
        '    "recommendations": "Talabaga amaliy maslahatlar"\n'
        '  }\n'
        "}"
    )

    user_message = f"""KAZUS FAKTLARI:
{facts}

VAZIFALAR VA SAVOLLAR:
{task_question or "Taraflarning huquqiy holatiga to'liq baho bering va nizoni hal qiling."}

BAZADAN TOPILGAN TEGISHLI MODDALAR:
{articles_text}
"""

    if student_answer:
        user_message += f"\n\nTALABANING TAKLIF QILGAN JAVOBI:\n{student_answer}\n(Iltimos, talabaning javobini xolisona baholab, 0-100 ball qo'ying va kamchiliklarini ko'rsating)."
    else:
        user_message += "\n\n(Talaba o'z javobini kiritmadi, student_assessment.evaluated=false qilib namunaviy yechim bering)."

    llm = get_llm()
    try:
        irac_result = llm.chat_json(system=system_prompt, user=user_message)
    except Exception as e:
        logger.error("LLM case solver error: %s", e)
        # Fallback agar LLM xato bersa
        irac_result = {
            "title": "Kazus tahlili",
            "issue": "Kazus bo'yicha huquqiy munosabatlar va nizolar tahlili talab etiladi.",
            "rules": "O'zbekiston Respublikasi Fuqarolik, Mehnat yoki Jinoyat kodeksi moddalari.",
            "analysis": "Voqelikdagi faktlar qonun hujjatlariga muvofiq baholanishi lozim.",
            "conclusion": "Nizo vakolatli sud yoki huquqni muhofaza qiluvchi organlar tomonidan hal qilinadi.",
            "action_steps": ["Hujjatlar to'plamini shakllantirish", "Sudga da'vo arizasi kiritish"],
            "student_assessment": {"evaluated": False, "score": None, "strengths": "", "mistakes": "", "recommendations": ""},
        }

    irac_result["retrieved_articles"] = retrieved_articles

    # 3. Agar foydalanuvchi tizimga kirgan bo'lsa, tarixga saqlash
    submission = None
    if user and getattr(user, "is_authenticated", False):
        score_val = irac_result.get("student_assessment", {}).get("score")
        feedback_val = (
            f"Kuchli tomonlari: {irac_result.get('student_assessment', {}).get('strengths', '')}\n"
            f"Xatolar: {irac_result.get('student_assessment', {}).get('mistakes', '')}"
        )
        submission = StudentCaseSubmission.objects.create(
            user=user,
            case_bank=case_bank_item,
            title=irac_result.get("title", "Kazus yechimi"),
            facts=facts,
            student_answer=student_answer,
            irac_solution=irac_result,
            score=score_val if isinstance(score_val, int) else None,
            feedback=feedback_val,
        )
        irac_result["submission_id"] = submission.id

    return irac_result

