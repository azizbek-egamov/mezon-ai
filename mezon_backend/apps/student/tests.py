import datetime
from django.test import TestCase
from rest_framework.test import APIClient
from apps.student.models import StudentCaseBank, StudentQuizQuestion, StudentLegalGlossary, LawCategory, DifficultyLevel
from apps.student.services.calculator import calculate_court_fee, calculate_deadline
from apps.student.services.diff_comparator import compare_legal_texts
from apps.student.services.quiz_engine import evaluate_quiz_submission


class StudentServicesTestCase(TestCase):
    def test_calculate_court_fee_civil_property(self):
        # 100,000,000 UZS civil property claim -> 4% = 4,000,000 UZS
        res = calculate_court_fee(
            court_type="CIVIL",
            claim_type="PROPERTY",
            claim_amount=100000000.0,
        )
        self.assertEqual(res["court_fee_uzs"], 4000000.0)
        self.assertIn("O'RQ-600", res["legal_basis"])

    def test_calculate_court_fee_economic_property(self):
        # 50,000,000 UZS economic claim -> 2% = 1,000,000 UZS
        res = calculate_court_fee(
            court_type="ECONOMIC",
            claim_type="PROPERTY",
            claim_amount=50000000.0,
        )
        self.assertEqual(res["court_fee_uzs"], 1000000.0)

    def test_calculate_procedural_deadline(self):
        # CIVIL_APPEAL from 2026-01-01 -> 1 month -> 2026-02-01 (Sunday) -> next working day: 2026-02-02 (Monday)
        start = datetime.date(2026, 1, 1)
        res = calculate_deadline(start_date=start, procedure="CIVIL_APPEAL")
        self.assertEqual(res["deadline_date"], "2026-02-02")
        self.assertIn("FPK 385", res["rule_description"])

    def test_diff_comparator(self):
        old_text = "Fuqarolik huquqi bo'yicha shartnoma buzildi."
        new_text = "Fuqarolik huquqi bo'yicha shartnoma bekor qilindi va zarar undirildi."
        res = compare_legal_texts(old_text, new_text)
        self.assertGreater(res["stats"]["added_words"], 0)
        self.assertGreater(res["stats"]["deleted_words"], 0)
        self.assertIn("diff_segments", res)

    def test_quiz_evaluator(self):
        q = StudentQuizQuestion.objects.create(
            category=LawCategory.CIVIL,
            question_text="Umumiy da'vo muddati necha yil?",
            options=[
                {"key": "A", "text": "1 yil"},
                {"key": "B", "text": "3 yil"},
            ],
            correct_option="B",
            explanation="FK 150-modda",
            law_reference="FK 150-m",
        )
        eval_res = evaluate_quiz_submission([{"question_id": q.id, "selected_option": "B"}])
        self.assertEqual(eval_res["percentage"], 100.0)
        self.assertEqual(eval_res["correct_count"], 1)


class StudentAPITestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.case = StudentCaseBank.objects.create(
            title="Ijara nizosi",
            category=LawCategory.CIVIL,
            difficulty=DifficultyLevel.EASY,
            facts="Ijara shartnomasi tuzilgan.",
            task_question="Nizo qanday hal qilinadi?",
        )
        self.glossary = StudentLegalGlossary.objects.create(
            term="Pacta sunt servanda",
            latin_term="Pacta sunt servanda",
            category=LawCategory.CIVIL,
            is_roman_latin=True,
            definition="Shartnomalar bajarilishi shart.",
            legal_source="FK 236-m",
        )

    def test_case_bank_list(self):
        response = self.client.get("/api/v1/student/cases/bank")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)

    def test_glossary_list(self):
        response = self.client.get("/api/v1/student/glossary?q=pacta")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.data), 1)
        self.assertEqual(response.data[0]["latin_term"], "Pacta sunt servanda")

    def test_court_fee_calculator_endpoint(self):
        payload = {
            "court_type": "CIVIL",
            "claim_type": "PROPERTY",
            "claim_amount": 20000000,
        }
        response = self.client.post("/api/v1/student/calculator/court-fee", data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["court_fee_uzs"], 800000.0)

    def test_deadline_calculator_endpoint(self):
        payload = {
            "procedure": "CIVIL_APPEAL",
            "start_date": "2026-05-01",
        }
        response = self.client.post("/api/v1/student/calculator/procedural-deadline", data=payload, format="json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["deadline_date"], "2026-06-01")
