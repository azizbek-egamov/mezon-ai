"""Interfeys tilini tanlash (TZ §5.4): kirgan foydalanuvchining profilidagi til > cookie > brauzer tili > sukut."""
from django.conf import settings
from django.middleware.locale import LocaleMiddleware
from django.utils import translation


class UserLocaleMiddleware(LocaleMiddleware):
    """AuthenticationMiddleware dan keyin turishi kerak (request.user kerak)."""

    def process_request(self, request):
        user = getattr(request, "user", None)
        lang = getattr(user, "language", "") if user is not None and user.is_authenticated else ""
        if lang and lang in dict(settings.LANGUAGES):
            translation.activate(lang)
            request.LANGUAGE_CODE = translation.get_language()
            return
        super().process_request(request)
