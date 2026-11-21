from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache, caches
from django.test import TestCase
from rest_framework.test import APIClient
from unittest.mock import patch

PASSWORD = "Kuchli-parol-77"


class AuthApiTests(TestCase):
    def setUp(self):
        cache.clear()   # testlarda xotira keshi (settings), dev keshiga tegmaydi
        caches["security"].clear()
        self.client = APIClient()
        self.user = get_user_model().objects.create_user("+998901112233", PASSWORD, full_name="Test Advokat",
                                                         role="LAWYER")

    def login(self, **over):
        return self.client.post("/api/v1/auth/login", {"phone_number": "90 111 22 33", "password": PASSWORD, **over},
                                format="json")

    def test_login_returns_tokens_in_body_for_mobile(self):
        resp = self.login()
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertTrue(data["access"] and data["refresh"])
        self.assertEqual(data["user"]["phone_number"], "+998901112233")
        self.assertEqual(data["user"]["language_tz"], "uz-Latn")
        self.assertEqual(resp["Cache-Control"], "private, no-store")
        self.assertNotIn(settings.JWT_REFRESH_COOKIE, resp.cookies)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {data['access']}")
        self.assertEqual(self.client.get("/api/v1/auth/me").json()["full_name"], "Test Advokat")

    def test_login_cookie_mode_hides_refresh_from_js(self):
        resp = self.login(cookie=True)
        self.assertNotIn("refresh", resp.json())
        cookie = resp.cookies[settings.JWT_REFRESH_COOKIE]
        self.assertTrue(cookie["httponly"])
        self.assertEqual(cookie["samesite"], "Strict")
        self.assertEqual(cookie["path"], "/api/v1/auth/")
        # refresh tanasiz — cookie dan; yangi cookie (rotatsiya), tanada faqat access
        resp = self.client.post("/api/v1/auth/refresh", {}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(set(resp.json()), {"access"})
        self.assertNotEqual(resp.cookies[settings.JWT_REFRESH_COOKIE].value, cookie.value)

    def test_wrong_password_and_lockout(self):
        resp = self.login(password="notogri")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("non_field_errors", resp.json())
        for _ in range(4):
            self.login(password="notogri")
        resp = self.login()   # to'g'ri parol ham — 15 daqiqa yopiq
        self.assertEqual(resp.status_code, 429)
        self.assertEqual(resp.json()["code"], "locked")

    def test_refresh_rotation_blacklists_old_token(self):
        refresh = self.login().json()["refresh"]
        resp = self.client.post("/api/v1/auth/refresh", {"refresh": refresh}, format="json")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(resp.json()["refresh"])
        again = self.client.post("/api/v1/auth/refresh", {"refresh": refresh}, format="json")
        self.assertEqual(again.status_code, 401)
        self.assertEqual(again.json()["code"], "token_invalid")

    def test_logout_blacklists_refresh(self):
        refresh = self.login().json()["refresh"]
        self.assertEqual(self.client.post("/api/v1/auth/logout", {"refresh": refresh}, format="json").status_code, 204)
        self.assertEqual(self.client.post("/api/v1/auth/refresh", {"refresh": refresh}, format="json").status_code, 401)

    def test_register(self):
        data = {"phone_number": "+998 90 555 66 77", "full_name": "Karimov Anvar", "role": "LAWYER",
                "advocate_license_no": "A-1", "password1": PASSWORD, "password2": PASSWORD}
        resp = self.client.post("/api/v1/auth/register", data, format="json")
        self.assertEqual(resp.status_code, 400)
        self.assertIn("consent", resp.json())          # rozilik majburiy (O'RQ-547)
        resp = self.client.post("/api/v1/auth/register", {**data, "consent": True}, format="json")
        self.assertEqual(resp.status_code, 201)
        user = get_user_model().objects.get(phone_number="+998905556677")
        self.assertIn("pii", user.consents_json)
        self.assertTrue(resp.json()["access"])
        dup = self.client.post("/api/v1/auth/register", {**data, "consent": True}, format="json")
        self.assertIn("phone_number", dup.json())

    def test_registration_password_errors_follow_selected_language(self):
        expected = {
            "uz-latn": [
                "Parol juda qisqa. U kamida 8 ta belgidan iborat boʻlishi kerak.",
                "Bu parol juda koʻp ishlatiladi. Murakkabroq parol tanlang.",
            ],
            "uz-cyrl": [
                "Парол жуда қисқа. У камида 8 та белгидан иборат бўлиши керак.",
                "Бу парол жуда кўп ишлатилади. Мураккаброқ парол танланг.",
            ],
            "ru": [
                "Пароль слишком короткий. Он должен содержать не менее 8 символов.",
                "Этот пароль слишком распространён. Выберите более сложный пароль.",
            ],
            "kaa": [
                "Пароль жүдә қысқа. Ол кеминде 8 белгиден ибарат болыўы керек.",
                "Бул пароль жүдә көп қолланылады. Қурамалырақ пароль таңлаң.",
            ],
            "en": [
                "This password is too short. It must contain at least 8 characters.",
                "This password is too common. Choose a stronger password.",
            ],
        }
        data = {"phone_number": "+998 90 555 66 77", "full_name": "Karimov Anvar", "role": "LAWYER",
                "password1": "abc", "password2": "abc", "consent": True}
        for language, messages in expected.items():
            with self.subTest(language=language):
                response = self.client.post("/api/v1/auth/register", data, format="json",
                                            HTTP_ACCEPT_LANGUAGE=language)
                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.json()["password1"], messages)

    def test_framework_errors_follow_selected_language(self):
        required = self.client.post("/api/v1/auth/language", {}, format="json", HTTP_ACCEPT_LANGUAGE="ru")
        self.assertEqual(required.json()["language"], ["Заполните это поле."])

        malformed = self.client.post("/api/v1/auth/language", data='{"language":',
                                     content_type="application/json", HTTP_ACCEPT_LANGUAGE="ru")
        self.assertEqual(malformed.json(), {"detail": "Неверный формат запроса.", "code": "parse_error"})

        self.user.language = "ru"
        self.user.save(update_fields=["language"])
        token = self.login().json()["access"]
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {token}")
        too_long = self.client.patch("/api/v1/auth/me", {"full_name": "x" * 256}, format="json")
        self.assertEqual(too_long.json()["full_name"], ["Введённый текст слишком длинный."])

        self.client.credentials(HTTP_AUTHORIZATION="Bearer notogri.token")
        invalid_token = self.client.get("/api/v1/auth/me", HTTP_ACCEPT_LANGUAGE="ru")
        self.assertEqual(invalid_token.status_code, 401)
        self.assertEqual(invalid_token.json(),
                         {"detail": "Сессия недействительна. Войдите снова.", "code": "token_not_valid"})

    @patch("apps.api.throttling.time.time")
    def test_register_progressive_throttle_and_monthly_reset(self, now):
        data = {"phone_number": "+998 90 555 66 77", "full_name": "", "role": "LAWYER",
                "password1": "x", "password2": "y", "consent": False}
        # 5 ta tez urinish o'tadi, 6-si birinchi 3 daqiqalik tanaffusni oladi.
        now.return_value = 1_798_761_600.0  # 2027-01-01 UTC
        for _ in range(settings.REGISTER_THROTTLE_BURST):
            self.assertEqual(self.client.post("/api/v1/auth/register", data, format="json").status_code, 400)
        blocked = self.client.post("/api/v1/auth/register", data, format="json")
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked["Retry-After"], "180")
        self.assertIn("3 daqiqadan", blocked.json()["detail"])

        # Tanaffus tugagach yana burst: ikkinchi bosqich 5 daqiqa.
        now.return_value += 181
        for _ in range(settings.REGISTER_THROTTLE_BURST):
            self.assertEqual(self.client.post("/api/v1/auth/register", data, format="json").status_code, 400)
        blocked = self.client.post("/api/v1/auth/register", data, format="json")
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked["Retry-After"], "300")

        # Yangi kalendar oyida eskalatsiya darajasi yo'q: yana 3 daqiqadan boshlanadi.
        now.return_value = 1_801_440_000.0  # 2027-02-01 UTC
        for _ in range(settings.REGISTER_THROTTLE_BURST):
            self.assertEqual(self.client.post("/api/v1/auth/register", data, format="json").status_code, 400)
        blocked = self.client.post("/api/v1/auth/register", data, format="json")
        self.assertEqual(blocked.status_code, 429)
        self.assertEqual(blocked["Retry-After"], "180")

    def test_me_requires_token(self):
        resp = self.client.get("/api/v1/auth/me")
        self.assertEqual(resp.status_code, 401)
        self.assertEqual(resp.json(), {"detail": "Avval tizimga kiring", "code": "not_authenticated"})
        self.client.credentials(HTTP_AUTHORIZATION="Bearer notogri.token")
        self.assertEqual(self.client.get("/api/v1/auth/me").status_code, 401)

    def test_profile_language_applies_to_api_messages(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {self.login().json()['access']}")
        resp = self.client.patch("/api/v1/auth/me", {"language": "ru", "role": "SUPERADMIN"}, format="json")
        self.assertEqual(resp.json()["language"], "ru")
        self.user.refresh_from_db()
        self.assertEqual((self.user.language, self.user.role), ("ru", "LAWYER"))   # rol o'zgarmaydi
        self.assertEqual(self.client.patch("/api/v1/auth/me", {"language": "xx"}, format="json").status_code, 400)
        resp = self.client.post("/api/v1/cases/", {}, format="multipart")
        self.assertEqual(resp.json()["detail"], "Выберите файл")

    def test_language_endpoint_accepts_tz_codes(self):
        resp = self.client.post("/api/v1/auth/language", {"language": "uz-Cyrl"}, format="json")
        self.assertEqual(resp.json(), {"language": "uz-cyrl"})
        self.assertEqual(resp.cookies[settings.LANGUAGE_COOKIE_NAME].value, "uz-cyrl")
