"""Interfeys tillari (TZ §5.4, 10-bosqich): til tanlash, kataloglar, transliteratsiya, chat da javob tili."""
import json
import os
import re
from unittest import mock

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import translation

from apps.i18n import catalog
from apps.i18n.codes import to_django_code, to_tz_code
from apps.i18n.translit import cyr_to_lat, lat_to_cyr, lat_to_new_latn, new_latn_to_lat
from apps.lex_corpus.models import corpus_lang

def js_catalog(js: str) -> dict:
    """/jsi18n/ javobidagi `const newcatalog = {...}` ni lug'atga aylantiradi."""
    return json.loads(re.search(r"const newcatalog = (\{.*?\n  \});", js, re.S).group(1))


LOGIN_TITLE = {"uz-latn": "Kirish", "uz-latn-2026": "Kiriş", "uz-cyrl": "Кириш", "ru": "Вход", "en": "Log in", "kaa": "Кириў"}


class TranslitTests(SimpleTestCase):
    def test_latin_to_new_latn(self):
        cases = {
            "Oʻzbekiston Respublikasi": "Özbekiston Respublikasi",
            "gʻalaba, koʻl, shahar, choy": "ğalaba, köl, şahar, çoy",
            "SHARTNOMA VA CHORAKLAR": "ŞARTNOMA VA ÇORAKLAR",
            "Shartnoma va choraklar": "Şartnoma va çoraklar",
            "Kirish": "Kiriş",
            "Roʻyxatdan oʻtish": "Röyxatdan ötiş",
            "Isʼhoq, sanʼat, aʼlo": "Isʼhoq, sanʼat, aʼlo",
            "Fayl: %(name)s, {{count}} ta koʻring": "Fayl: %(name)s, {{count}} ta köring",
            "Oʻzbekcha": "Özbekça",
        }
        for lat, new_lat in cases.items():
            self.assertEqual(lat_to_new_latn(lat), new_lat, lat)
            self.assertEqual(new_latn_to_lat(new_lat), lat, new_lat)
    def test_latin_to_cyrillic(self):
        cases = {
            "Oʻzbekiston Respublikasi": "Ўзбекистон Республикаси",
            "gʻoya, yoʻl, yoz, yulduz, yangi": "ғоя, йўл, ёз, юлдуз, янги",
            "shartnoma, choraklar, ish": "шартнома, чораклар, иш",
            "eʼlon, sunʼiy, ekspertiza": "эълон, сунъий, экспертиза",
            "Konstitutsiya, protsessual": "Конституция, процессуал",
            "Sentabr, oktabr, yanvar": "Сентябр, октябр, январ",
            "168-modda. Firibgarlik": "168-модда. Фирибгарлик",
            "SHARTNOMA": "ШАРТНОМА",
            "Toshkent shahar, qonun, hujjat": "Тошкент шаҳар, қонун, ҳужжат",
        }
        for lat, cyr in cases.items():
            self.assertEqual(lat_to_cyr(lat), cyr, lat)

    def test_cyrillic_to_latin(self):
        cases = {
            "Ўзбекистон Республикаси": "Oʻzbekiston Respublikasi",
            "ғоя, йўл, ёз, юлдуз, янги": "gʻoya, yoʻl, yoz, yulduz, yangi",
            "эълон, сунъий": "eʼlon, sunʼiy",
            "Тошкент шаҳар": "Toshkent shahar",
            "ЎЗБЕКИСТОН ИШ": "OʻZBEKISTON ISH",
            "ер, мактаб": "yer, maktab",
        }
        for cyr, lat in cases.items():
            self.assertEqual(cyr_to_lat(cyr), lat, cyr)

    def test_other_characters_untouched(self):
        text = "№ 12, 15.10.2026 — (3-qism) «iqtibos»"
        self.assertEqual(cyr_to_lat(lat_to_cyr(text)).replace("«", "«"), text.replace("iqtibos", "iqtibos"))
        self.assertIn("№ 12, 15.10.2026 — (3-", lat_to_cyr(text))

    def test_roundtrip_on_legal_sentence(self):
        text = "Firibgarlik, yaʼni aldash yoki ishonchni suiisteʼmol qilish yoʻli bilan oʻzganing mulkini egallash"
        self.assertEqual(cyr_to_lat(lat_to_cyr(text)), text)


class CodesTests(SimpleTestCase):
    def test_code_mapping(self):
        self.assertEqual([to_django_code(c) for c in ("uz-Latn", "uz-Latn-2026", "uz-Cyrl", "ru", "kaa", "en", "xx")],
                         ["uz-latn", "uz-latn-2026", "uz-cyrl", "ru", "kaa", "en", "uz-latn"])
        self.assertEqual(to_tz_code("uz-latn-2026"), "uz-Latn-2026")
        self.assertEqual(to_tz_code("uz-cyrl"), "uz-Cyrl")
        self.assertEqual([corpus_lang(c) for c in ("uz-Latn", "uz-Latn-2026", "uz-Cyrl", "ru", "kaa", "en")],
                         ["lat", "lat", "cyr", "ru", "lat", "lat"])


class CatalogTests(SimpleTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.found = catalog.extract_messages()

    def test_all_languages_fully_translated_and_placeholders_match(self):
        for lang, _ in settings.LANGUAGES:
            po = catalog.load_po(lang)
            live = {e.msgid: e for e in po if not e.obsolete}
            missing = [m for m in self.found if m not in live]
            self.assertEqual(missing, [], f"{lang}: kataloglar eskirgan — manage.py i18n_sync")
            if lang == catalog.SOURCE_LANG:
                continue
            empty = [m for m in self.found if not live[m].msgstr]
            self.assertEqual(empty, [], f"{lang}: tarjima qilinmagan matnlar")
            for msgid in self.found:
                self.assertEqual(sorted(catalog.PLACEHOLDER_RE.findall(msgid)),
                                 sorted(catalog.PLACEHOLDER_RE.findall(live[msgid].msgstr)), f"{lang}: {msgid[:50]}")

    def test_extracts_template_python_and_js_strings(self):
        for msgid in ("Kirish",                                            # {% trans %}
                      "moderator tasdiqlagan · v%(v)s",                    # {% blocktrans trimmed with %}
                      "Qidirilmoqda…",                                     # JS gettext("...")
                      "%(n)s varaq",                                       # JS gettext + interpolate
                      "Telefon raqami yoki parol notoʻgʻri",               # Python gettext
                      "Fuqaro"):                                           # gettext_lazy
            self.assertIn(msgid, self.found)

    def test_cyrillic_catalog_is_transliteration_with_placeholders_intact(self):
        self.assertEqual(catalog.transliterate_msgstr("%(n)s ta manba topildi"), "%(n)s та манба топилди")

    def test_compiled_catalogs_exist(self):
        for lang, _ in settings.LANGUAGES:
            self.assertTrue(catalog.po_path(lang).with_suffix(".mo").exists(), lang)


class LanguageSelectionTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("+998901112233", "Kuchli-parol-77", full_name="Test Advokat")

    def login_title(self, **headers):
        html = self.client.get("/accounts/login/", **headers).content.decode()
        return re.search(r"<h2>(.*?)</h2>", html).group(1)

    def test_default_is_uzbek_latin(self):
        self.assertEqual(self.login_title(), "Kirish")

    def test_browser_language_header(self):
        self.assertEqual(self.login_title(HTTP_ACCEPT_LANGUAGE="ru,en;q=0.5"), LOGIN_TITLE["ru"])
        self.assertEqual(self.login_title(HTTP_ACCEPT_LANGUAGE="uz-Cyrl"), LOGIN_TITLE["uz-cyrl"])
        self.assertEqual(self.login_title(HTTP_ACCEPT_LANGUAGE="uz"), "Kirish")   # umumiy "uz" -> lotin

    def test_set_language_for_anonymous_sets_cookie(self):
        resp = self.client.post("/i18n/set/", {"language": "en", "next": "/accounts/login/"})
        self.assertEqual((resp.status_code, resp["Location"]), (302, "/accounts/login/"))
        self.assertEqual(resp.cookies[settings.LANGUAGE_COOKIE_NAME].value, "en")
        self.assertEqual(self.login_title(), LOGIN_TITLE["en"])

    def test_set_language_saves_to_profile_and_overrides_cookie_and_header(self):
        self.client.force_login(self.user)
        self.client.post("/i18n/set/", {"language": "kaa"})
        self.user.refresh_from_db()
        self.assertEqual(self.user.language, "kaa")
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        html = self.client.get("/cases/", HTTP_ACCEPT_LANGUAGE="ru").content.decode()
        self.assertIn('<html lang="kaa">', html)
        self.assertIn("Ис таллаўы", html)             # profil tili cookie va brauzer tilidan ustun
        self.assertEqual(self.client.get("/cases/")["Content-Language"], "kaa")

    def test_invalid_language_and_open_redirect_rejected(self):
        resp = self.client.post("/i18n/set/", {"language": "xx", "next": "https://evil.example/"})
        self.assertEqual(resp["Location"], "/")
        self.assertNotIn(settings.LANGUAGE_COOKIE_NAME, resp.cookies)
        self.assertEqual(self.client.get("/i18n/set/").status_code, 405)

    def test_switcher_lists_all_languages(self):
        html = self.client.get("/accounts/login/").content.decode()
        for code, name in settings.LANGUAGES:
            self.assertIn(f'<option value="{code}"', html)
            self.assertIn(name, html)

    def test_role_labels_and_form_errors_are_translated(self):
        self.client.force_login(self.user)
        html = self.client.get("/cases/").content.decode()
        self.assertIn("Fuqaro", html)                        # foydalanuvchi roli (lotin: manba matn)
        self.client.post("/i18n/set/", {"language": "ru"})
        html = self.client.get("/cases/").content.decode()
        self.assertIn("Гражданин", html)
        self.assertIn("Анализ дела", html)

    def test_jsi18n_catalog_in_active_language(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "ru"
        js = self.client.get("/jsi18n/").content.decode()
        self.assertEqual(js_catalog(js)["Qidirilmoqda…"], "Идёт поиск…")
        self.assertIn("globals.interpolate", js)
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "uz-cyrl"
        self.assertEqual(js_catalog(self.client.get("/jsi18n/").content.decode())["Qidirilmoqda…"], "Қидирилмоқда…")


@override_settings(BILLING_ENFORCED=False)   # kvotalar alohida sinaladi (apps/billing/tests)
class ChatLanguageTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user("+998901112233", "Kuchli-parol-77", full_name="Test Advokat")
        self.client.force_login(self.user)

    def test_answer_language_select_defaults_to_ui_language(self):
        self.client.post("/i18n/set/", {"language": "uz-cyrl"})
        html = self.client.get("/").content.decode()
        self.assertRegex(html, r'<option value="uz-Cyrl" selected>Ўзбекча</option>')
        self.assertIn('<option value="kaa">Қарақалпақша</option>', html)
        self.assertEqual(js_catalog(self.client.get("/jsi18n/").content.decode())["%(n)s varaq"], "%(n)s варақ")

    def test_search_gets_corpus_language_and_messages_follow_ui_language(self):
        self.client.post("/i18n/set/", {"language": "ru"})
        with mock.patch("apps.rag.views.search_aspects", return_value=([], [{"topic": "t", "queries": ["q"]}])) as search:
            resp = self.client.post("/api/ask", json.dumps({"question": "Что за мошенничество?", "lang": "ru"}),
                                    content_type="application/json")
            body = b"".join(resp.streaming_content).decode()
        self.assertEqual(search.call_args.kwargs["lang"], "ru")
        self.assertIn("Подходящие статьи закона не найдены.", body)   # xabar interfeys tilida
        with mock.patch("apps.rag.views.search_aspects", return_value=([], [{"topic": "t", "queries": ["q"]}])) as search:
            self.client.post("/api/ask", json.dumps({"question": "x?", "lang": "kaa"}), content_type="application/json").streaming_content
            list(self.client.post("/api/ask", json.dumps({"question": "x?", "lang": "uz-Cyrl"}),
                                  content_type="application/json").streaming_content)
        self.assertEqual(search.call_args.kwargs["lang"], "cyr")

    def test_verification_messages_are_translated(self):
        from apps.rag.answer import verify_answer

        with translation.override("ru"):
            report = verify_answer("Ответ без ссылок.", [])
        self.assertEqual(report.issues[0].detail, "В ответе нет ни одной ссылки на источник [M#]")


class ExportJsonTests(SimpleTestCase):
    """manage.py i18n_export_json: .po -> frontend uchun i18next JSON."""

    def test_placeholders_and_languages(self):
        import tempfile
        from pathlib import Path

        from django.core.management import call_command

        from apps.i18n.management.commands.i18n_export_json import export_catalog, to_i18next

        self.assertEqual(to_i18next("Jami %(n)s ta, %(mb)s MB"), "Jami {{n}} ta, {{mb}} MB")
        source = export_catalog("uz-latn")
        self.assertEqual(source["Fayl tanlang"], "Fayl tanlang")           # manba tilda kalit = matn
        ru = export_catalog("ru")
        self.assertEqual(ru["Fayl tanlang"], "Выберите файл")
        self.assertTrue(all("%(" not in k and "%(" not in v for k, v in ru.items()))
        with tempfile.TemporaryDirectory() as out:
            call_command("i18n_export_json", out=out, stdout=open(os.devnull, "w"))
            files = sorted(p.name for p in Path(out).iterdir())
            self.assertEqual(files, ["en.json", "kaa.json", "languages.json", "ru.json", "uz-Cyrl.json", "uz-Latn-2026.json", "uz-Latn.json"])
            self.assertEqual(json.loads((Path(out) / "kaa.json").read_text(encoding="utf-8")), export_catalog("kaa"))


class FrontendExtractionTests(SimpleTestCase):
    """Frontend (React) matnlari ham .po ga tushadi: t("...") va i18next o'rinbosarlari."""

    def test_extract_frontend(self):
        import tempfile
        from pathlib import Path

        src = ('const a = t("Fayllar jami {{mb}} MB", { mb });\n'
               "const b = t('Bir {{ n }} marta');\n"
               'alert("emas"); i18n.t("bu ham emas"); format(t(`Shablon`));\n'
               "const c = t(`Dinamik ${x}`);\n")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "Page.tsx"
            path.write_text(src, encoding="utf-8")
            found = {}
            catalog.extract_frontend(path, "apps/web/Page.tsx", found)
        self.assertEqual(sorted(found), ["Bir %(n)s marta", "Fayllar jami %(mb)s MB", "Shablon"])
        self.assertEqual(found["Bir %(n)s marta"].places, ["apps/web/Page.tsx:2"])
