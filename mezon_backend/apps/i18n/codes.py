"""Til kodlari: TZ (§5.4) kodlari <-> Django kodlari. TZ: uz-Latn, uz-Latn-2026, uz-Cyrl, ru, kaa, en; Django kichik harfda."""
TZ_TO_DJANGO = {
    "uz-Latn": "uz-latn",
    "uz-Latn-2026": "uz-latn-2026",
    "uz-Cyrl": "uz-cyrl",
    "ru": "ru",
    "kaa": "kaa",
    "en": "en",
}
DJANGO_TO_TZ = {v: k for k, v in TZ_TO_DJANGO.items()}


def to_tz_code(django_code: str) -> str:
    return DJANGO_TO_TZ.get(django_code, "uz-Latn")


def to_django_code(tz_code: str) -> str:
    return TZ_TO_DJANGO.get(tz_code, "uz-latn")
