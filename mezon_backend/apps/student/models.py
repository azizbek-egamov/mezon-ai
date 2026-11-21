from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _


class LawCategory(models.TextChoices):
    CIVIL = "CIVIL", _("Fuqarolik huquqi")
    CRIMINAL = "CRIMINAL", _("Jinoyat huquqi")
    LABOR = "LABOR", _("Mehnat huquqi")
    ADMINISTRATIVE = "ADMINISTRATIVE", _("Maʼmuriy huquq")
    FAMILY = "FAMILY", _("Oila huquqi")
    BUSINESS = "BUSINESS", _("Tadbirkorlik (Iqtisodiy) huquqi")
    CONSTITUTIONAL = "CONSTITUTIONAL", _("Konstitutsiyaviy huquq")


class DifficultyLevel(models.TextChoices):
    EASY = "EASY", _("Boshlangʻich (1-2 kurs)")
    MEDIUM = "MEDIUM", _("Oʻrta (3-4 kurs)")
    HARD = "HARD", _("Murakkab (Magistratura / Sud)")


class StudentCaseBank(models.Model):
    """Tayyor o'quv kazuslari banki (TDYU va OTMlar o'quv dasturi asosida)."""
    title = models.CharField(max_length=255, verbose_name=_("Kazus mavzusi"))
    category = models.CharField(max_length=32, choices=LawCategory.choices, default=LawCategory.CIVIL)
    difficulty = models.CharField(max_length=16, choices=DifficultyLevel.choices, default=DifficultyLevel.MEDIUM)
    facts = models.TextField(verbose_name=_("Kazus holati (faktlar)"))
    task_question = models.TextField(verbose_name=_("Hal qilinishi lozim boʻlgan savol"))
    relevant_laws = models.JSONField(default=list, blank=True, verbose_name=_("Tegishli qonun moddalari"))
    reference_solution = models.JSONField(default=dict, blank=True, verbose_name=_("Namunaviy IRAC yechimi"))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_case_bank"
        ordering = ["category", "id"]
        verbose_name = _("Kazuslar banki")
        verbose_name_plural = _("Kazuslar banki")

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"


class StudentCaseSubmission(models.Model):
    """Talabaning yechgan yoki tahlil qildirgan kazuslari tarixi."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="case_submissions")
    case_bank = models.ForeignKey(StudentCaseBank, null=True, blank=True, on_delete=models.SET_NULL)
    title = models.CharField(max_length=255, verbose_name=_("Kazus sarlavhasi"))
    facts = models.TextField(verbose_name=_("Kazus faktlari"))
    student_answer = models.TextField(blank=True, verbose_name=_("Talaba taklif qilgan yechim"))
    irac_solution = models.JSONField(default=dict, blank=True, verbose_name=_("AI / IRAC tahlili"))
    score = models.IntegerField(null=True, blank=True, verbose_name=_("Baholash (0-100)"))
    feedback = models.TextField(blank=True, verbose_name=_("Taqriz va kamchiliklar"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_case_submissions"
        ordering = ["-created_at"]
        verbose_name = _("Talaba kazus yechimi")
        verbose_name_plural = _("Talaba kazus yechimlari")

    def __str__(self):
        return f"{self.user} - {self.title} ({self.created_at.strftime('%Y-%m-%d')})"


class StudentQuizQuestion(models.Model):
    """Lokal test savollari (Davlat imtihonlari va advokatura tayyorgarligi, ZERO API COST)."""
    category = models.CharField(max_length=32, choices=LawCategory.choices, default=LawCategory.CIVIL)
    question_text = models.TextField(verbose_name=_("Savol matni"))
    options = models.JSONField(default=list, verbose_name=_("Variantlar"))  # [{"key": "A", "text": "..."}, ...]
    correct_option = models.CharField(max_length=4, verbose_name=_("Toʻgʻri variant"))  # "A", "B", "C", "D"
    explanation = models.TextField(blank=True, verbose_name=_("Qonuniy izoh"))
    law_reference = models.CharField(max_length=255, blank=True, verbose_name=_("Qonun moddasi"))
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_quiz_questions"
        ordering = ["category", "id"]
        verbose_name = _("Yuridik test savoli")
        verbose_name_plural = _("Yuridik test savollari")

    def __str__(self):
        return f"[{self.get_category_display()}] {self.question_text[:60]}..."


class StudentLegalGlossary(models.Model):
    """Yuridik atamalar, rim huquqi va lotincha iboralar lug'ati (ZERO API COST)."""
    term = models.CharField(max_length=255, verbose_name=_("Atama / Iboraning nomi"))
    latin_term = models.CharField(max_length=255, blank=True, verbose_name=_("Lotincha yozilishi"))
    category = models.CharField(max_length=32, choices=LawCategory.choices, default=LawCategory.CIVIL)
    is_roman_latin = models.BooleanField(default=False, verbose_name=_("Rim huquqi / Lotincha aforizm"))
    definition = models.TextField(verbose_name=_("Mazmuni va huquqiy taʼrifi"))
    legal_source = models.CharField(max_length=255, blank=True, verbose_name=_("Qonuniy asosi"))
    example_usage = models.TextField(blank=True, verbose_name=_("Qoʻllanish misoli"))
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "student_legal_glossary"
        ordering = ["term"]
        verbose_name = _("Yuridik atama")
        verbose_name_plural = _("Yuridik lugʻat")

    def __str__(self):
        return self.term


