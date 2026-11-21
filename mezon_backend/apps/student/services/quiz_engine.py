"""Lokal huquqiy test va imtihon trenajyori (ZERO API COST).
TDYU va advokatura litsenziya imtihonlariga tayyorlanish uchun.
"""
from apps.student.models import StudentQuizQuestion, LawCategory


def get_quiz_questions(category: str | None = None, limit: int = 10) -> list[dict]:
    qs = StudentQuizQuestion.objects.filter(is_active=True)
    if category and category != "ALL":
        qs = qs.filter(category=category)

    # Tasodifiy tartibda olish
    questions = qs.order_by("?")[:limit]
    results = []
    for q in questions:
        results.append({
            "id": q.id,
            "category": q.category,
            "category_label": q.get_category_display(),
            "question_text": q.question_text,
            "options": q.options,
            "law_reference": q.law_reference,
        })
    return results


def evaluate_quiz_submission(answers: list[dict]) -> dict:
    """answers: [{"question_id": 1, "selected_option": "B"}, ...]
    Qaytaradi:
      - total_questions
      - correct_count
      - percentage
      - details: har bir savol bo'yicha to'g'ri/noto'g'ri, izoh, qonun moddasi
    """
    q_ids = [a.get("question_id") for a in answers if a.get("question_id")]
    questions_map = {q.id: q for q in StudentQuizQuestion.objects.filter(id__in=q_ids)}

    correct_count = 0
    details = []

    for item in answers:
        qid = item.get("question_id")
        selected = str(item.get("selected_option", "")).strip().upper()
        q = questions_map.get(qid)
        if not q:
            continue

        is_correct = (selected == q.correct_option.strip().upper())
        if is_correct:
            correct_count += 1

        details.append({
            "question_id": q.id,
            "question_text": q.question_text,
            "selected_option": selected,
            "correct_option": q.correct_option,
            "is_correct": is_correct,
            "explanation": q.explanation,
            "law_reference": q.law_reference,
        })

    total = len(details)
    percentage = round((correct_count / total * 100), 1) if total > 0 else 0.0

    return {
        "total_questions": total,
        "correct_count": correct_count,
        "percentage": percentage,
        "passed": percentage >= 70.0,
        "details": details,
    }

