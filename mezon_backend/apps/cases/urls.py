from django.urls import path

from . import views

urlpatterns = [
    path("cases/", views.case_list, name="case_list"),
    path("cases/upload", views.case_upload, name="case_upload"),
    path("cases/<uuid:run_id>/", views.case_detail, name="case_detail"),
    path("cases/<uuid:run_id>/confirm", views.case_confirm, name="case_confirm"),
    path("cases/<uuid:run_id>/export.<str:fmt>", views.case_export, name="case_export"),
    path("api/cases/<uuid:run_id>/confirmation", views.api_confirmation, name="case_confirmation"),
    path("cases/<uuid:run_id>/delete", views.case_delete, name="case_delete"),
    path("cases/<uuid:run_id>/retry", views.case_retry, name="case_retry"),
    path("cases/<uuid:run_id>/pdf", views.case_pdf, name="case_pdf"),
    path("api/cases/<uuid:run_id>", views.api_status, name="case_status"),
    path("api/cases/<uuid:run_id>/report", views.api_report, name="case_report"),
]
