from django.contrib import admin
from .models import StudentCaseBank, StudentCaseSubmission, StudentQuizQuestion


@admin.register(StudentCaseBank)
class StudentCaseBankAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "category", "difficulty", "is_active", "created_at")
    list_filter = ("category", "difficulty", "is_active")
    search_fields = ("title", "facts", "task_question")


@admin.register(StudentCaseSubmission)
class StudentCaseSubmissionAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "title", "score", "created_at")
    list_filter = ("created_at",)
    search_fields = ("title", "facts", "student_answer", "user__phone_number")


@admin.register(StudentQuizQuestion)
class StudentQuizQuestionAdmin(admin.ModelAdmin):
    list_display = ("id", "category", "correct_option", "law_reference", "is_active")
    list_filter = ("category", "is_active")
    search_fields = ("question_text", "law_reference", "explanation")

