"""API v1 marshrutlari (`/api/v1/`). Sxema: /api/v1/schema/ (OpenAPI 3), hujjat: /api/v1/docs/ (Swagger UI)."""
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from .views import admin, auth, billing, cases, chat, laws, meta, student, templates

urlpatterns = [
    path("auth/login", auth.LoginView.as_view(), name="api_login"),
    path("auth/register", auth.RegisterView.as_view(), name="api_register"),
    path("auth/refresh", auth.RefreshView.as_view(), name="api_refresh"),
    path("auth/logout", auth.LogoutView.as_view(), name="api_logout"),
    path("auth/me", auth.MeView.as_view(), name="api_me"),
    path("auth/language", auth.LanguageView.as_view(), name="api_language"),

    path("cases/", cases.CaseListView.as_view(), name="api_cases"),
    path("cases/options", cases.CaseOptionsView.as_view(), name="api_case_options"),
    path("cases/<uuid:run_id>", cases.CaseDetailView.as_view(), name="api_case"),
    path("cases/<uuid:run_id>/report", cases.CaseReportView.as_view(), name="api_case_report"),
    path("cases/<uuid:run_id>/pdf", cases.CasePdfView.as_view(), name="api_case_pdf"),
    path("cases/<uuid:run_id>/confirmation", cases.CaseConfirmationView.as_view(), name="api_case_confirmation"),
    path("cases/<uuid:run_id>/export/<str:fmt>", cases.CaseExportView.as_view(), name="api_case_export"),
    path("cases/<uuid:run_id>/retry", cases.CaseRetryView.as_view(), name="api_case_retry"),

    path("chat/ask", chat.AskView.as_view(), name="api_ask"),

    path("templates/", templates.TemplateListView.as_view(), name="api_templates"),
    path("templates/<uuid:template_id>", templates.TemplateDetailView.as_view(), name="api_template"),
    path("templates/<uuid:template_id>/preview", templates.TemplatePreviewView.as_view(), name="api_template_preview"),
    path("templates/<uuid:template_id>/render/<str:fmt>", templates.TemplateRenderView.as_view(),
         name="api_template_render"),

    path("billing/usage", billing.UsageView.as_view(), name="api_usage"),
    path("billing/plans", billing.PlanListView.as_view(), name="api_plans"),

    path("laws/documents", laws.LawDocumentListView.as_view(), name="api_law_documents"),
    path("laws/documents/<int:doc_id>", laws.LawDocumentDetailView.as_view(), name="api_law_document"),
    path("laws/articles/<int:article_id>", laws.ArticleView.as_view(), name="api_law_article"),
    path("laws/search", laws.LawSearchView.as_view(), name="api_law_search"),

    # Talabalar ekotizimi (Student Academy)
    path("student/cases/bank", student.CaseBankListView.as_view(), name="api_student_case_bank"),
    path("student/cases/bank/<int:pk>", student.CaseBankDetailView.as_view(), name="api_student_case_bank_detail"),
    path("student/cases/solve", student.CaseSolveView.as_view(), name="api_student_case_solve"),
    path("student/cases/history", student.CaseSubmissionListView.as_view(), name="api_student_case_history"),
    path("student/cases/history/<int:pk>", student.CaseSubmissionDetailView.as_view(), name="api_student_case_history_detail"),
    path("student/presentations/generate", student.PresentationGenerateView.as_view(), name="api_student_presentation_generate"),
    path("student/diff", student.LegalDiffView.as_view(), name="api_student_diff"),
    path("student/quiz/questions", student.QuizQuestionsView.as_view(), name="api_student_quiz_questions"),
    path("student/quiz/submit", student.QuizSubmitView.as_view(), name="api_student_quiz_submit"),
    path("student/glossary", student.GlossaryListView.as_view(), name="api_student_glossary"),
    path("student/calculator/court-fee", student.CourtFeeCalculatorView.as_view(), name="api_student_calculator_court_fee"),
    path("student/calculator/procedural-deadline", student.ProceduralDeadlineView.as_view(), name="api_student_calculator_deadline"),
    path("student/moot-court/simulate", student.MootCourtSimulateView.as_view(), name="api_student_moot_court_simulate"),
    path("student/thesis/roadmap", student.ThesisRoadmapView.as_view(), name="api_student_thesis_roadmap"),

    path("i18n/languages", meta.LanguagesView.as_view(), name="api_languages"),
    path("health", meta.HealthView.as_view(), name="api_health"),

    # Admin panel (MODERATOR / SUPERADMIN)
    path("admin/me", admin.StaffMeView.as_view(), name="admin_me"),
    path("admin/dashboard", admin.DashboardView.as_view(), name="admin_dashboard"),
    path("admin/users/", admin.UserListView.as_view(), name="admin_users"),
    path("admin/users/<uuid:user_id>", admin.UserDetailView.as_view(), name="admin_user"),
    path("admin/users/<uuid:user_id>/subscriptions", admin.UserGrantView.as_view(), name="admin_user_grant"),
    path("admin/subscriptions/", admin.SubscriptionListView.as_view(), name="admin_subscriptions"),
    path("admin/subscriptions/<int:sub_id>/cancel", admin.SubscriptionCancelView.as_view(), name="admin_subscription_cancel"),
    path("admin/plans/", admin.PlanListView.as_view(), name="admin_plans"),
    path("admin/plans/<int:plan_id>", admin.PlanDetailView.as_view(), name="admin_plan"),
    path("admin/payments/", admin.PaymentListView.as_view(), name="admin_payments"),
    path("admin/payments/<int:payment_id>/mark-paid", admin.PaymentMarkPaidView.as_view(), name="admin_payment_paid"),
    path("admin/payments/<int:payment_id>/cancel", admin.PaymentCancelView.as_view(), name="admin_payment_cancel"),
    path("admin/costs", admin.CostsView.as_view(), name="admin_costs"),
    path("admin/antifraud", admin.AntiFraudView.as_view(), name="admin_antifraud"),
    path("admin/sync/", admin.SyncListView.as_view(), name="admin_sync"),
    path("admin/sync/start", admin.SyncStartView.as_view(), name="admin_sync_start"),
    path("admin/templates/", admin.AdminTemplateListView.as_view(), name="admin_templates"),
    path("admin/templates/<uuid:template_id>", admin.AdminTemplateDetailView.as_view(), name="admin_template"),
    path("admin/templates/<uuid:template_id>/approve", admin.AdminTemplateApproveView.as_view(), name="admin_template_approve"),
    path("admin/templates/<uuid:template_id>/preview", admin.AdminTemplatePreviewView.as_view(), name="admin_template_preview"),
    path("admin/audit/", admin.AuditListView.as_view(), name="admin_audit"),

    path("schema/", SpectacularAPIView.as_view(), name="api_schema"),
    path("docs/", SpectacularSwaggerView.as_view(url_name="api_schema"), name="api_docs"),
]
