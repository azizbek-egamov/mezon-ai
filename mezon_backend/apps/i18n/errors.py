"""Django va DRF standart validatsiya xatolarini loyiha kataloglari orqali tarjima qilish.

Django/DRF o'zbek lotin, o'zbek kirill va qoraqalpoq tillari uchun to'liq katalog bermaydi.
Shu sabab ularning standart inglizcha xabarlarini bevosita mijozga uzatmaymiz: barqaror
``code`` qiymatidan loyiha xabariga o'tamiz. Ilova o'zi yozgan xabarlar esa o'zgartirilmaydi.
"""
from django.core.exceptions import ValidationError as DjangoValidationError
from django.utils.translation import gettext as _
from rest_framework.exceptions import ErrorDetail


def _limit(params: dict | None) -> object:
    params = params or {}
    return params.get("limit_value", params.get("max_length", params.get("min_length", "")))


def message_for_code(code: str | None, params: dict | None = None) -> str | None:
    """Standart validator kodi uchun joriy interfeys tilidagi xabar."""
    code = code or ""
    if code == "password_too_short":
        return _("Parol juda qisqa. U kamida %(min_length)s ta belgidan iborat boʻlishi kerak.") % {
            "min_length": (params or {}).get("min_length", 8)
        }
    if code == "password_too_common":
        return _("Bu parol juda koʻp ishlatiladi. Murakkabroq parol tanlang.")
    if code == "password_entirely_numeric":
        return _("Parol faqat raqamlardan iborat boʻlmasin.")
    if code == "password_too_similar":
        return _("Parol shaxsiy maʼlumotlaringizga juda oʻxshash.")

    if code in {"required", "blank"}:
        return _("Bu maydonni toʻldiring.")
    if code == "null":
        return _("Bu maydon boʻsh qiymat qabul qilmaydi.")
    if code in {"invalid_choice", "does_not_exist"}:
        return _("Tanlangan qiymat ruxsat etilmagan.")
    if code == "max_length":
        limit = _limit(params)
        return (_("Koʻpi bilan %(limit)s ta belgi kiriting.") % {"limit": limit}
                if limit != "" else _("Kiritilgan matn juda uzun."))
    if code == "min_length":
        limit = _limit(params)
        return (_("Kamida %(limit)s ta belgi kiriting.") % {"limit": limit}
                if limit != "" else _("Kiritilgan matn juda qisqa."))
    if code == "max_value":
        limit = _limit(params)
        return (_("Qiymat %(limit)s dan oshmasin.") % {"limit": limit}
                if limit != "" else _("Qiymat ruxsat etilgan chegaradan oshib ketgan."))
    if code == "min_value":
        limit = _limit(params)
        return (_("Qiymat kamida %(limit)s boʻlsin.") % {"limit": limit}
                if limit != "" else _("Qiymat ruxsat etilgan chegaradan past."))
    if code in {"unique", "unique_for_date", "unique_for_month", "unique_for_year"}:
        return _("Bu qiymat allaqachon mavjud.")
    if code == "not_a_list":
        return _("Roʻyxat yuborilishi kerak.")
    if code == "not_a_dict":
        return _("Obyekt yuborilishi kerak.")
    if code == "empty":
        return _("Roʻyxat boʻsh boʻlmasin.")
    if code in {"invalid_image", "no_name", "empty_file", "max_size"}:
        return _("Fayl notoʻgʻri yoki oʻqib boʻlmaydi.")
    if code in {"date", "datetime", "time", "decimal", "max_digits", "max_decimal_places",
                "max_whole_digits", "incorrect_type"}:
        return _("Qiymat formati notoʻgʻri.")
    return None


_ENGLISH_DEFAULT_PREFIXES = (
    "ensure this", "a valid", "not a valid", "invalid ", "enter a valid",
    "date has wrong format", "datetime has wrong format", "time has wrong format", "the submitted",
    "no file was submitted", "expected a ", "incorrect type", "select a valid choice",
    "unable to log in", "authentication credentials",
)


def _looks_like_english_default(message: str) -> bool:
    value = message.strip().lower()
    return value.startswith(_ENGLISH_DEFAULT_PREFIXES) or value in {
        "invalid input.", "invalid value.", "invalid data.", "malformed request.",
    }


def localize_django_error(error: DjangoValidationError) -> str:
    """Bitta Django ValidationError bargini tarjima qiladi."""
    mapped = message_for_code(getattr(error, "code", None), getattr(error, "params", None))
    if mapped is not None:
        return mapped
    message = str(getattr(error, "message", error))
    if _looks_like_english_default(message):
        return _("Qiymat formati notoʻgʻri.")
    return message


def localize_error_detail(detail: ErrorDetail) -> str:
    """DRF ErrorDetail ni tarjima qiladi, ilovaning tayyor tarjimasini saqlaydi."""
    message = str(detail)
    mapped = message_for_code(getattr(detail, "code", None))
    if mapped is not None:
        return mapped
    if _looks_like_english_default(message):
        return _("Qiymat formati notoʻgʻri.")
    return message


def localize_error_data(value):
    """DRF javobidagi ichma-ich xato tuzilmasini tarjima qiladi."""
    if isinstance(value, ErrorDetail):
        return localize_error_detail(value)
    if isinstance(value, dict):
        return {key: localize_error_data(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [localize_error_data(item) for item in value]
    return value
