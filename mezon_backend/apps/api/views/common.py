"""API view lari uchun umumiy yordamchilar: xato javoblari, Django forma xatolari, no-store."""
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.cases.services import CaseError
from apps.i18n.errors import localize_django_error


def error(detail: str, status: int = 400, code: str = "invalid") -> Response:
    """Xato javobining yagona shakli: {"detail": "...", "code": "..."}. 429 (tarif limiti) — mijoz /billing ga yo'naltiradi."""
    return Response({"detail": str(detail), "code": code}, status=status)


def case_error(e: CaseError) -> Response:
    return error(e.message, e.status, e.code)


def raise_form_errors(form) -> None:
    """Django forma xatolari -> DRF ValidationError ({maydon: [xabar]}, umumiy xatolar — non_field_errors)."""
    errors = {("non_field_errors" if field == "__all__" else field):
              [localize_django_error(item) for item in messages]
              for field, messages in form.errors.as_data().items()}
    raise ValidationError(errors)


def no_store(response):
    """Hisobot, PDF, eksport va tokenlar keshlanmasin."""
    response["Cache-Control"] = "private, no-store"
    return response
