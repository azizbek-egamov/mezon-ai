"""`.po` kataloglarini frontend (veb, admin, mobil) uchun i18next JSON ga eksport qilish.

    manage.py i18n_export_json [--out ../frontend/packages/i18n/locales]

Har bir til — `<TZ kodi>.json` (uz-Latn.json, uz-Cyrl.json, ru.json, kaa.json, en.json): tekis lug'at {kalit: matn},
kalit — o'zbek lotin manba matni (msgid). i18next sozlamasi: `keySeparator: false, nsSeparator: false`.
Django o'rinbosarlari `%(n)s` i18next ko'rinishiga `{{n}}` o'tkaziladi (kalitda ham, matnda ham); ko'plik shakllari —
`kalit_one` / `kalit_other`. Manba tilda kalit = matn. Tarjimasiz yoki obsolete yozuvlar chiqarilmaydi
(i18next kalitning o'zini — o'zbek lotin matnni ko'rsatadi). Qo'shimcha: `languages.json` — tillar ro'yxati.
Yangi matn qo'shilganda: `i18n_sync`, tarjima, keyin shu buyruq.
"""
import json
import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from apps.i18n.catalog import SOURCE_LANG, load_po
from apps.i18n.codes import to_tz_code

PLACEHOLDER_RE = re.compile(r"%\((\w+)\)s")


def to_i18next(text: str) -> str:
    return PLACEHOLDER_RE.sub(r"{{\1}}", text)


def export_catalog(lang: str) -> dict[str, str]:
    source = lang == SOURCE_LANG
    out: dict[str, str] = {}
    for entry in load_po(lang):
        if entry.obsolete or "fuzzy" in entry.flags:
            continue
        key = to_i18next(entry.msgid)
        if entry.msgid_plural:
            forms = ([entry.msgid, entry.msgid_plural] if source
                     else [entry.msgstr_plural.get(0, ""), entry.msgstr_plural.get(1, "")])
            for suffix, text in zip(("_one", "_other"), forms):
                if text:
                    out[key + suffix] = to_i18next(text)
        elif source or entry.msgstr:
            out[key] = to_i18next(entry.msgid if source else entry.msgstr)
    return dict(sorted(out.items()))


class Command(BaseCommand):
    help = "Tarjima kataloglarini (.po) frontend uchun i18next JSON ga eksport qiladi"

    def add_arguments(self, parser):
        parser.add_argument("--out", default=str(Path(settings.BASE_DIR).parent / "frontend" / "packages" / "i18n"
                                                 / "locales"), help="Chiqish papkasi")

    def handle(self, *args, out, **options):
        out_dir = Path(out)
        out_dir.mkdir(parents=True, exist_ok=True)
        for lang, _name in settings.LANGUAGES:
            catalog = export_catalog(lang)
            path = out_dir / f"{to_tz_code(lang)}.json"
            path.write_text(json.dumps(catalog, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
            self.stdout.write(f"{to_tz_code(lang):8} {len(catalog):4} ta matn -> {path}")
        languages = [{"code": to_tz_code(code), "django_code": code, "name": name} for code, name in settings.LANGUAGES]
        (out_dir / "languages.json").write_text(json.dumps(languages, ensure_ascii=False, indent=1) + "\n",
                                                encoding="utf-8")
