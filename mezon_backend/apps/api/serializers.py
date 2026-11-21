"""API v1 serializerlari. Validatsiya iloji boricha mavjud Django formalari va servislarda (bitta manba) —
serializerlar asosan javob shakli va OpenAPI sxemasi uchun."""
from django.conf import settings
from django.utils.translation import gettext as _
from rest_framework import serializers

from apps.accounts.models import Role, User
from apps.billing.models import Plan
from apps.cases.case_types import CASE_TYPES
from apps.cases.models import CaseRun
from apps.doc_builder.models import DocumentTemplate
from apps.i18n.codes import TZ_TO_DJANGO, to_tz_code
from apps.student.models import (
    StudentCaseBank, StudentCaseSubmission, StudentQuizQuestion,
    StudentLegalGlossary, LawCategory, DifficultyLevel
)

# OpenAPI enum nomlari uchun (settings.SPECTACULAR_SETTINGS["ENUM_NAME_OVERRIDES"])
REGISTER_ROLE_CHOICES = [
    (Role.LAWYER, Role.LAWYER.label),
    (Role.STUDENT, Role.STUDENT.label),
    (Role.CLIENT, Role.CLIENT.label),
]
CASE_CATEGORY_CHOICES = [(code, t.label) for code, t in CASE_TYPES.items()]


def language_code(value: str) -> str | None:
    """'uz-Latn' (TZ) yoki 'uz-latn' (Django) -> Django kodi; noma'lum — None."""
    code = TZ_TO_DJANGO.get(value, value)
    return code if code in dict(settings.LANGUAGES) else None


# --- auth -------------------------------------------------------------------------------------------------------

class UserSerializer(serializers.ModelSerializer):
    role_label = serializers.CharField(source="get_role_display", read_only=True)
    language_tz = serializers.SerializerMethodField(help_text="TZ kodi: uz-Latn | uz-Latn-2026 | uz-Cyrl | ru | kaa | en")

    class Meta:
        model = User
        fields = ["id", "phone_number", "full_name", "role", "role_label", "advocate_license_no",
                  "university", "study_level", "student_id_no", "language",
                  "language_tz", "is_staff", "date_joined"]
        read_only_fields = ["id", "phone_number", "role", "is_staff", "date_joined"]

    def get_language_tz(self, user) -> str:
        return to_tz_code(user.language)

    def validate_language(self, value):
        code = language_code(value)
        if code is None:
            raise serializers.ValidationError(_("Nomaʼlum til"))
        return code

    def validate_full_name(self, value):
        value = value.strip()
        if not value:
            raise serializers.ValidationError(_("F.I.Sh. boʻsh boʻlmasin"))
        return value


class LoginSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    password = serializers.CharField(style={"input_type": "password"})
    cookie = serializers.BooleanField(default=False, help_text=(
        "true — refresh token HttpOnly cookie da (veb SPA), javob tanasida bo'lmaydi; false — tanada (mobil)"))


class RegisterSerializer(serializers.Serializer):
    phone_number = serializers.CharField()
    full_name = serializers.CharField()
    role = serializers.ChoiceField(choices=REGISTER_ROLE_CHOICES)
    advocate_license_no = serializers.CharField(required=False, allow_blank=True)
    university = serializers.CharField(required=False, allow_blank=True)
    study_level = serializers.CharField(required=False, allow_blank=True)
    student_id_no = serializers.CharField(required=False, allow_blank=True)
    password1 = serializers.CharField()
    password2 = serializers.CharField()
    consent = serializers.BooleanField(help_text="Shaxsiy ma'lumotlarni qayta ishlashga rozilik (O'RQ-547)")
    cookie = serializers.BooleanField(default=False)


class TokenPairSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField(required=False, help_text="cookie=false bo'lsa")
    user = UserSerializer()


class RefreshSerializer(serializers.Serializer):
    refresh = serializers.CharField(required=False, help_text="Bo'sh — HttpOnly cookie dan olinadi")


class AccessSerializer(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField(required=False, help_text="Yangi (rotatsiya); cookie rejimida tanada bo'lmaydi")


class LanguageSerializer(serializers.Serializer):
    language = serializers.CharField(help_text="uz-latn | uz-latn-2026 | uz-cyrl | ru | kaa | en (TZ kodlari ham qabul qilinadi)")

    def validate_language(self, value):
        code = language_code(value)
        if code is None:
            raise serializers.ValidationError(_("Nomaʼlum til"))
        return code


class DetailSerializer(serializers.Serializer):
    detail = serializers.CharField()
    code = serializers.CharField(required=False)


# --- cases ------------------------------------------------------------------------------------------------------

class CaseSerializer(serializers.ModelSerializer):
    status_label = serializers.CharField(source="get_status_display", read_only=True)
    category_label = serializers.SerializerMethodField()
    confirmed_at = serializers.DateTimeField(source="lawyer_confirmed_at", read_only=True)
    has_pdf = serializers.SerializerMethodField()
    cost_usd = serializers.FloatField(read_only=True)

    class Meta:
        model = CaseRun
        fields = ["id", "title", "created_at", "category", "category_label", "status", "status_label", "stage",
                  "progress", "pages", "zero_retention", "error", "cost_usd", "confirmed_at", "has_pdf"]
        read_only_fields = fields

    def get_category_label(self, run) -> str:
        t = CASE_TYPES.get(run.category)
        return str(t.label) if t else run.category

    def get_has_pdf(self, run) -> bool:
        return bool(run.pdf_path)


class CaseSourceSerializer(serializers.Serializer):
    name = serializers.CharField()
    kind = serializers.CharField(help_text="pdf | docx | image")
    first_page = serializers.IntegerField()
    last_page = serializers.IntegerField()


class CaseDetailSerializer(CaseSerializer):
    sources = CaseSourceSerializer(many=True, read_only=True, help_text="Yuklangan fayllar va ularning varaqlari")

    class Meta(CaseSerializer.Meta):
        fields = CaseSerializer.Meta.fields + ["sources"]
        read_only_fields = fields


class CaseUploadSerializer(serializers.Serializer):
    files = serializers.ListField(child=serializers.FileField(), help_text="PDF, DOCX, JPG, PNG — bitta PDF ga birlashtiriladi")
    category = serializers.ChoiceField(choices=CASE_CATEGORY_CHOICES, required=False)
    title = serializers.CharField(required=False, allow_blank=True, max_length=255)
    zero_retention = serializers.BooleanField(default=False)


class CaseTypeSerializer(serializers.Serializer):
    code = serializers.CharField()
    label = serializers.CharField()


class CaseOptionsSerializer(serializers.Serializer):
    case_types = CaseTypeSerializer(many=True)
    max_files = serializers.IntegerField()
    max_mb = serializers.IntegerField()
    max_pages = serializers.IntegerField(help_text="Foydalanuvchi tarifi boʻyicha maksimal varaq (FREE=15, PRO=150)")
    server_max_pages = serializers.IntegerField(required=False, help_text="Server texnik chegarasi (200)")
    plan_code = serializers.CharField(required=False, allow_null=True)
    plan_name = serializers.CharField(required=False, allow_null=True)
    unlimited = serializers.BooleanField(required=False)
    cases_remaining = serializers.IntegerField(required=False, allow_null=True)
    cases_exhausted = serializers.BooleanField(required=False)


class ConfirmSerializer(serializers.Serializer):
    acknowledged = serializers.BooleanField(help_text="\"Asosiy dalillar va qonun moddalari bilan tanishdim\" (TZ §12)")


# --- chat -------------------------------------------------------------------------------------------------------

class AskSerializer(serializers.Serializer):
    question = serializers.CharField(max_length=2000)
    lang = serializers.CharField(default="uz-Latn", help_text="Javob tili: uz-Latn | uz-Cyrl | ru | kaa | en")
    effort = serializers.ChoiceField(choices=["low", "medium", "high"], default="medium")
    on_date = serializers.DateField(required=False, allow_null=True, help_text="Voqea sanasi (o'sha sanadagi tahrir)")


# --- templates --------------------------------------------------------------------------------------------------

CATEGORY_TRANSLATIONS: dict[str, dict[str, str]] = {
    "CONTRACTS": {
        "uz-Latn": "Shartnomalar",
        "uz-Cyrl": "Шартномалар",
        "ru": "Договоры",
    },
    "STATEMENTS": {
        "uz-Latn": "Arizalar",
        "uz-Cyrl": "Аризалар",
        "ru": "Заявления",
    },
    "PERSONAL": {
        "uz-Latn": "Shaxsiy tarkibga oid hujjatlar",
        "uz-Cyrl": "Шахсий таркибга оид ҳужжатлар",
        "ru": "Документы по личному составу",
    },
    "NOTARIAL": {
        "uz-Latn": "Notarial tasdiqlanadigan hujjatlar",
        "uz-Cyrl": "Нотариал тасдиқланадиган ҳужжатлар",
        "ru": "Нотариально удостоверяемые документы",
    },
    "COURT": {
        "uz-Latn": "Sudga oid hujjatlar",
        "uz-Cyrl": "Судга оид ҳужжатлар",
        "ru": "Судебные документы",
    },
    "CORPORATE": {
        "uz-Latn": "Korporativ hujjatlar",
        "uz-Cyrl": "Корпоратив ҳужжатлар",
        "ru": "Корпоративные документы",
    },
}


class TemplateSerializer(serializers.ModelSerializer):
    category_label = serializers.SerializerMethodField()
    is_approved = serializers.SerializerMethodField(help_text="Joriy versiyani yurist-moderator tasdiqlaganmi")
    title = serializers.SerializerMethodField()
    subcategory = serializers.SerializerMethodField()
    available_languages = serializers.JSONField(read_only=True)

    class Meta:
        model = DocumentTemplate
        fields = [
            "id", "doc_id", "title", "title_translations", "category", "category_label",
            "subcategory", "subcategory_slug", "subcategory_translations", "available_languages",
            "language", "description", "version", "is_approved"
        ]
        read_only_fields = fields

    def get_is_approved(self, template) -> bool:
        return template.approved_at is not None

    def get_category_label(self, template) -> str:
        lang = self.context.get("lang")
        if not lang and "request" in self.context:
            lang = self.context["request"].query_params.get("lang") or getattr(self.context["request"], "LANGUAGE_CODE", None)
        norm = (lang or "uz-Latn").lower()
        key = "uz-Cyrl" if "cyrl" in norm else ("ru" if "ru" in norm else "uz-Latn")
        trans = CATEGORY_TRANSLATIONS.get(template.category, {})
        return trans.get(key) or template.get_category_display()

    def get_title(self, template) -> str:
        lang = self.context.get("lang")
        if not lang and "request" in self.context:
            lang = self.context["request"].query_params.get("lang") or getattr(self.context["request"], "LANGUAGE_CODE", None)
        return template.title_for(lang)

    def get_subcategory(self, template) -> str:
        lang = self.context.get("lang")
        if not lang and "request" in self.context:
            lang = self.context["request"].query_params.get("lang") or getattr(self.context["request"], "LANGUAGE_CODE", None)
        return template.subcategory_for(lang)


class TemplateDetailSerializer(TemplateSerializer):
    legal_basis = serializers.SerializerMethodField()
    form_schema = serializers.SerializerMethodField()

    class Meta(TemplateSerializer.Meta):
        fields = TemplateSerializer.Meta.fields + ["form_schema", "legal_basis"]
        read_only_fields = fields

    def get_legal_basis(self, template) -> list[str]:
        return [line.strip() for line in template.legal_basis.splitlines() if line.strip()]

    def get_form_schema(self, template) -> list[dict]:
        lang = self.context.get("lang")
        if not lang and "request" in self.context:
            lang = self.context["request"].query_params.get("lang")
        variant = template.variant_for(lang)
        return variant.get("form_schema") or template.form_schema


class TemplateValuesSerializer(serializers.Serializer):
    values = serializers.DictField(help_text="Forma maydonlari: {nom: qiymat}; sana — YYYY-MM-DD")
    lang = serializers.CharField(required=False, default="uz-Latn", help_text="Hujjat tuzish tili (uz-Latn, uz-Cyrl, ru)")


class BlockSerializer(serializers.Serializer):
    kind = serializers.CharField(help_text="right | center | h2 | item | sign | p | space | meta")
    text = serializers.CharField(allow_blank=True)


class PreviewSerializer(serializers.Serializer):
    blocks = BlockSerializer(many=True)


# --- billing ----------------------------------------------------------------------------------------------------

class PlanSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="display_name", read_only=True)
    price_uzs = serializers.DecimalField(max_digits=12, decimal_places=2, coerce_to_string=False, allow_null=True,
                                         read_only=True)

    class Meta:
        model = Plan
        fields = ["code", "name", "price_uzs", "duration_days", "daily_case_limit", "monthly_case_limit",
                  "lifetime_case_limit", "max_pages_per_case", "daily_chat_limit", "lifetime_chat_limit",
                  "daily_template_limit", "lifetime_template_limit", "watermark", "priority_queue"]
        read_only_fields = fields


class UsageRowSerializer(serializers.Serializer):
    kind = serializers.CharField(required=False, help_text="case | chat | template")
    scope = serializers.CharField(required=False, help_text="daily | monthly | lifetime")
    label = serializers.CharField()
    used = serializers.IntegerField()
    limit = serializers.IntegerField()


class UsageSerializer(serializers.Serializer):
    plan = serializers.CharField()
    plan_name = serializers.CharField()
    max_pages = serializers.IntegerField()
    unlimited = serializers.BooleanField()
    expires_at = serializers.DateTimeField(allow_null=True)
    usage = UsageRowSerializer(many=True)


# --- laws -------------------------------------------------------------------------------------------------------

class LawDocumentSerializer(serializers.Serializer):
    id = serializers.IntegerField(source="abs_id")
    title = serializers.CharField()
    doc_type = serializers.CharField()
    doc_type_label = serializers.CharField()
    official_number = serializers.CharField()
    adoption_date = serializers.DateField(allow_null=True)
    status = serializers.CharField()
    status_label = serializers.CharField()
    lex_url = serializers.CharField()
    languages = serializers.ListField(child=serializers.CharField(), help_text="Bazadagi matn tillari: lat | cyr | ru")


class ArticleRefSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    unit_type = serializers.CharField()
    article_number = serializers.CharField()
    label = serializers.CharField()
    section_path = serializers.CharField()


class LawDocumentDetailSerializer(LawDocumentSerializer):
    edition = serializers.CharField(help_text="Joriy tahrir yorlig'i")
    articles = ArticleRefSerializer(many=True)


class ArticlePartSerializer(serializers.Serializer):
    n = serializers.CharField(allow_blank=True)
    text = serializers.CharField()


class ArticleSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    document_id = serializers.IntegerField()
    doc_title = serializers.CharField()
    lang = serializers.CharField(help_text="Qaytarilgan matn tili (so'ralgan tilda bo'lmasa — asosiy til)")
    unit_type = serializers.CharField()
    article_number = serializers.CharField()
    label = serializers.CharField()
    section_path = serializers.CharField()
    text = serializers.CharField()
    parts = ArticlePartSerializer(many=True)
    edition = serializers.CharField()
    is_current = serializers.BooleanField()
    valid_from = serializers.DateField(allow_null=True)
    valid_until = serializers.DateField(allow_null=True)
    lex_url = serializers.CharField()


class SearchHitSerializer(serializers.Serializer):
    article_id = serializers.IntegerField()
    document_id = serializers.IntegerField()
    doc_title = serializers.CharField()
    label = serializers.CharField()
    text = serializers.CharField()
    lex_url = serializers.CharField()
    edition = serializers.CharField()
    exact = serializers.BooleanField()
    score = serializers.FloatField()


# --- i18n -------------------------------------------------------------------------------------------------------

class LanguageInfoSerializer(serializers.Serializer):
    code = serializers.CharField(help_text="Django kodi (uz-latn)")
    tz_code = serializers.CharField(help_text="TZ kodi (uz-Latn)")
    name = serializers.CharField(help_text="O'z yozuvidagi nomi")


class HealthSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=["ok", "degraded"])
    database = serializers.BooleanField()
    search = serializers.BooleanField(help_text="Qdrant server (QDRANT_URL) javob beryaptimi")


# --- student (Talabalar ekotizimi) -------------------------------------------------------------------------------

class StudentCaseBankSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)
    difficulty_label = serializers.CharField(source="get_difficulty_display", read_only=True)

    class Meta:
        model = StudentCaseBank
        fields = [
            "id", "title", "category", "category_label", "difficulty", "difficulty_label",
            "facts", "task_question", "relevant_laws", "reference_solution", "created_at"
        ]


class StudentCaseSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentCaseSubmission
        fields = [
            "id", "case_bank", "title", "facts", "student_answer",
            "irac_solution", "score", "feedback", "created_at"
        ]
        read_only_fields = ["id", "irac_solution", "score", "feedback", "created_at"]


class CaseSolveRequestSerializer(serializers.Serializer):
    facts = serializers.CharField(required=False, allow_blank=True)
    task_question = serializers.CharField(required=False, allow_blank=True)
    student_answer = serializers.CharField(required=False, allow_blank=True)
    case_bank_id = serializers.IntegerField(required=False, allow_null=True)
    lang = serializers.CharField(default="lat")


class PresentationGenerateRequestSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=500)
    slide_count = serializers.IntegerField(default=5, min_value=3, max_value=12)
    author_name = serializers.CharField(required=False, default="Mezon Huquqshunos Talabasi")
    download = serializers.BooleanField(default=False)


class LegalDiffRequestSerializer(serializers.Serializer):
    text_a = serializers.CharField(allow_blank=True)
    text_b = serializers.CharField(allow_blank=True)


class QuizQuestionSerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = StudentQuizQuestion
        fields = ["id", "category", "category_label", "question_text", "options", "law_reference"]


class QuizAnswerItemSerializer(serializers.Serializer):
    question_id = serializers.IntegerField()
    selected_option = serializers.CharField(max_length=4)


class QuizSubmitRequestSerializer(serializers.Serializer):
    answers = QuizAnswerItemSerializer(many=True)


class StudentLegalGlossarySerializer(serializers.ModelSerializer):
    category_label = serializers.CharField(source="get_category_display", read_only=True)

    class Meta:
        model = StudentLegalGlossary
        fields = [
            "id", "term", "latin_term", "category", "category_label",
            "is_roman_latin", "definition", "legal_source", "example_usage"
        ]


class CourtFeeCalculateRequestSerializer(serializers.Serializer):
    court_type = serializers.ChoiceField(choices=["CIVIL", "ECONOMIC", "ADMINISTRATIVE"])
    claim_type = serializers.ChoiceField(choices=["PROPERTY", "NON_PROPERTY", "DIVORCE", "ORDER", "CONTRACT_DISPUTE"])
    claim_amount = serializers.FloatField(required=False, default=0.0)
    is_repeated_divorce = serializers.BooleanField(required=False, default=False)
    stage = serializers.ChoiceField(choices=["FIRST_INSTANCE", "APPEAL_CASSATION"], required=False, default="FIRST_INSTANCE")


class ProceduralDeadlineRequestSerializer(serializers.Serializer):
    procedure = serializers.ChoiceField(choices=[
        "CIVIL_APPEAL", "CIVIL_CASSATION", "CIVIL_SUPERVISORY",
        "ECONOMIC_APPEAL", "ECONOMIC_CASSATION",
        "ADMIN_APPEAL", "ADMIN_CLAIM",
        "CRIMINAL_APPEAL", "CRIMINAL_CASSATION"
    ])
    start_date = serializers.DateField()


class MootCourtRequestSerializer(serializers.Serializer):
    case_facts = serializers.CharField()
    claim_dispute = serializers.CharField(required=False, allow_blank=True, default="")
    lang = serializers.CharField(default="lat")


class ThesisRoadmapRequestSerializer(serializers.Serializer):
    topic = serializers.CharField(max_length=500)
    work_type = serializers.ChoiceField(choices=["COURSEWORK", "THESIS_BACHELOR", "MASTER_DISSERTATION"], default="COURSEWORK")
    lang = serializers.CharField(default="lat")


