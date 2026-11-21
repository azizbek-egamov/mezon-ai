from django.conf import settings
from django.utils import translation

from .codes import to_tz_code


def i18n(request):
    """Shablonlar uchun: til almashtirgichi ro'yxati va joriy til (Django kodi va TZ kodi)."""
    current = translation.get_language() or settings.LANGUAGE_CODE
    return {"ui_languages": settings.LANGUAGES, "ui_language": current, "ui_language_tz": to_tz_code(current)}
