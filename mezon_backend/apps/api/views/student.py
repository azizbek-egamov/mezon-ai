"""Talabalar ekotizimi API ko'rinishlari (`/api/v1/student/*`).
1. Kazuslar ustaxonasi (IRAC analizatori va kazuslar banki)
2. Yuridik taqdimotlar generatori (.pptx)
3. Qonunlar qiyosiy taqqoslagichi (Diff - ZERO API COST)
4. Huquqiy test va imtihon trenajyori (Quiz - ZERO API COST)
"""
from django.http import HttpResponse
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.student.models import StudentCaseBank, StudentCaseSubmission, StudentLegalGlossary
from apps.student.services.calculator import calculate_court_fee, calculate_deadline
from apps.student.services.case_solver import solve_legal_case
from apps.student.services.diff_comparator import compare_legal_texts
from apps.student.services.moot_court import simulate_moot_court
from apps.student.services.presentation_builder import build_pptx_presentation, generate_presentation_outline
from apps.student.services.quiz_engine import evaluate_quiz_submission, get_quiz_questions
from apps.student.services.thesis_builder import build_thesis_roadmap

from .. import serializers as s
from .common import error


class CaseBankListView(generics.ListAPIView):
    """Tayyor namunaviy kazuslar banki ro'yxati."""
    serializer_class = s.StudentCaseBankSerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = StudentCaseBank.objects.filter(is_active=True)
        category = self.request.query_params.get("category")
        difficulty = self.request.query_params.get("difficulty")
        if category and category != "ALL":
            qs = qs.filter(category=category)
        if difficulty and difficulty != "ALL":
            qs = qs.filter(difficulty=difficulty)
        return qs

    @extend_schema(
        parameters=[
            OpenApiParameter("category", str, description="CIVIL, CRIMINAL, LABOR, ADMINISTRATIVE..."),
            OpenApiParameter("difficulty", str, description="EASY, MEDIUM, HARD"),
        ],
        responses={200: s.StudentCaseBankSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CaseBankDetailView(generics.RetrieveAPIView):
    """Namunaviy kazus tafsiloti."""
    serializer_class = s.StudentCaseBankSerializer
    permission_classes = [permissions.AllowAny]
    queryset = StudentCaseBank.objects.filter(is_active=True)


class CaseSolveView(APIView):
    """Kazusni IRAC uslubida tahlil qilish va yechish."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=s.CaseSolveRequestSerializer,
        responses={200: dict},
    )
    def post(self, request):
        ser = s.CaseSolveRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        facts = data.get("facts", "")
        task_question = data.get("task_question", "")
        student_answer = data.get("student_answer", "")
        case_bank_id = data.get("case_bank_id")
        lang = data.get("lang", "lat")

        user = request.user if request.user.is_authenticated else None

        try:
            result = solve_legal_case(
                facts=facts,
                task_question=task_question,
                student_answer=student_answer,
                case_bank_id=case_bank_id,
                user=user,
                lang=lang,
            )
            return Response(result)
        except ValueError as e:
            return error(str(e), status=400)
        except Exception as e:
            return error(f"Tahlil jarayonida xatolik yuz berdi: {e}", status=500)


class CaseSubmissionListView(generics.ListAPIView):
    """Foydalanuvchining shaxsiy kazus yechimlari tarixi."""
    serializer_class = s.StudentCaseSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentCaseSubmission.objects.filter(user=self.request.user)


class CaseSubmissionDetailView(generics.RetrieveAPIView):
    """Foydalanuvchining shaxsiy kazus yechimi tafsiloti."""
    serializer_class = s.StudentCaseSubmissionSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return StudentCaseSubmission.objects.filter(user=self.request.user)


class PresentationGenerateView(APIView):
    """Yuridik taqdimot (.pptx) generatsiya qilish."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=s.PresentationGenerateRequestSerializer,
        responses={200: dict},
    )
    def post(self, request):
        ser = s.PresentationGenerateRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        topic = data["topic"]
        slide_count = data.get("slide_count", 5)
        author_name = data.get("author_name") or (request.user.full_name if request.user.is_authenticated else "Mezon Talabasi")
        download = data.get("download", False)

        try:
            outline = generate_presentation_outline(topic=topic, slide_count=slide_count)

            if download:
                pptx_bytes = build_pptx_presentation(outline, author_name=author_name)
                response = HttpResponse(
                    pptx_bytes,
                    content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
                )
                safe_filename = "Mezon_Taqdimot.pptx"
                response["Content-Disposition"] = f'attachment; filename="{safe_filename}"'
                response["Content-Length"] = len(pptx_bytes)
                return response

            return Response({
                "topic": topic,
                "author_name": author_name,
                "outline": outline,
            })
        except Exception as e:
            return error(f"Taqdimot tayyorlashda xatolik: {e}", status=500)


class LegalDiffView(APIView):
    """Yuridik matnlarni qiyosiy taqqoslash (ZERO API COST)."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=s.LegalDiffRequestSerializer,
        responses={200: dict},
    )
    def post(self, request):
        ser = s.LegalDiffRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        text_a = ser.validated_data.get("text_a", "")
        text_b = ser.validated_data.get("text_b", "")

        result = compare_legal_texts(text_a, text_b)
        return Response(result)


class QuizQuestionsView(APIView):
    """Lokal test savollarini olish (ZERO API COST)."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter("category", str, description="CIVIL, LABOR, CRIMINAL..."),
            OpenApiParameter("limit", int, description="Nechta savol (default 10)"),
        ],
        responses={200: dict},
    )
    def get(self, request):
        category = request.query_params.get("category")
        try:
            limit = int(request.query_params.get("limit", 10))
        except ValueError:
            limit = 10

        questions = get_quiz_questions(category=category, limit=limit)
        return Response({"questions": questions, "total": len(questions)})


class QuizSubmitView(APIView):
    """Test javoblarini tekshirish va baholash (ZERO API COST)."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=s.QuizSubmitRequestSerializer,
        responses={200: dict},
    )
    def post(self, request):
        ser = s.QuizSubmitRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        answers = ser.validated_data.get("answers", [])
        result = evaluate_quiz_submission(answers)
        return Response(result)


class GlossaryListView(generics.ListAPIView):
    """Yuridik atamalar, rim huquqi va lotincha iboralar glossariysi (ZERO API COST)."""
    serializer_class = s.StudentLegalGlossarySerializer
    permission_classes = [permissions.AllowAny]
    pagination_class = None

    def get_queryset(self):
        qs = StudentLegalGlossary.objects.all()
        q = self.request.query_params.get("q", "").strip()
        category = self.request.query_params.get("category")
        is_roman_latin = self.request.query_params.get("is_roman_latin")

        if q:
            from django.db.models import Q
            qs = qs.filter(Q(term__icontains=q) | Q(latin_term__icontains=q) | Q(definition__icontains=q))
        if category and category != "ALL":
            qs = qs.filter(category=category)
        if is_roman_latin in ["true", "1", "True"]:
            qs = qs.filter(is_roman_latin=True)
        return qs

    @extend_schema(
        parameters=[
            OpenApiParameter("q", str, description="Qidiruv so'zi"),
            OpenApiParameter("category", str, description="CIVIL, CRIMINAL, etc."),
            OpenApiParameter("is_roman_latin", bool, description="Faqat rim/lotin iboralari"),
        ],
        responses={200: s.StudentLegalGlossarySerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class CourtFeeCalculatorView(APIView):
    """Davlat boji kalkulyatori (O'RQ-600 qonuni asosida, ZERO API COST)."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=s.CourtFeeCalculateRequestSerializer,
        responses={200: dict},
    )
    def post(self, request):
        ser = s.CourtFeeCalculateRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        result = calculate_court_fee(
            court_type=data["court_type"],
            claim_type=data["claim_type"],
            claim_amount=data.get("claim_amount", 0.0),
            is_repeated_divorce=data.get("is_repeated_divorce", False),
            stage=data.get("stage", "FIRST_INSTANCE"),
        )
        return Response(result)


class ProceduralDeadlineView(APIView):
    """Protsessual muddatlar kalkulyatori (FPK, IPK, MSIYK, JPK asosida, ZERO API COST)."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=s.ProceduralDeadlineRequestSerializer,
        responses={200: dict},
    )
    def post(self, request):
        ser = s.ProceduralDeadlineRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        result = calculate_deadline(
            start_date=data["start_date"],
            procedure=data["procedure"],
        )
        return Response(result)


class MootCourtSimulateView(APIView):
    """Sud simulyatsiyasi (Moot Court & 3 tomonlama argumentlar xaritasi)."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=s.MootCourtRequestSerializer,
        responses={200: dict},
    )
    def post(self, request):
        ser = s.MootCourtRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        try:
            result = simulate_moot_court(
                case_facts=data["case_facts"],
                claim_dispute=data.get("claim_dispute", ""),
                lang=data.get("lang", "lat"),
            )
            return Response(result)
        except ValueError as e:
            return error(str(e), status=400)
        except Exception as e:
            return error(f"Sud simulyatsiyasida xatolik: {e}", status=500)


class ThesisRoadmapView(APIView):
    """Kurs ishi va BMI (Bitiruv malakaviy ishi) tadqiqot rejasi konstruktori."""
    permission_classes = [permissions.AllowAny]

    @extend_schema(
        request=s.ThesisRoadmapRequestSerializer,
        responses={200: dict},
    )
    def post(self, request):
        ser = s.ThesisRoadmapRequestSerializer(data=request.data)
        if not ser.is_valid():
            return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

        data = ser.validated_data
        try:
            result = build_thesis_roadmap(
                topic=data["topic"],
                work_type=data.get("work_type", "COURSEWORK"),
                lang=data.get("lang", "lat"),
            )
            return Response(result)
        except ValueError as e:
            return error(str(e), status=400)
        except Exception as e:
            return error(f"Reja tuzishda xatolik: {e}", status=500)


