from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from apps.accounts.models import Role, normalize_phone

PASSWORD = "Kuchli-parol-77"


class PhoneTests(SimpleTestCase):
    def test_normalize(self):
        for raw in ("+998 (90) 123-45-67", "998901234567", "90 123 45 67"):
            self.assertEqual(normalize_phone(raw), "+998901234567")
        for bad in ("", "12345", "+7 912 345 67 89", "+998 90 123 45 6"):
            with self.assertRaises(ValidationError):
                normalize_phone(bad)


class AuthFlowTests(TestCase):
    def setUp(self):
        cache.clear()
        self.addCleanup(cache.clear)

    def register(self, **over):
        data = {"phone_number": "90 123 45 67", "full_name": "Karimov Anvar Botirovich", "role": "LAWYER",
                "advocate_license_no": "A-123", "password1": PASSWORD, "password2": PASSWORD, "consent": "on"}
        return self.client.post("/accounts/register/", {**data, **over})

    def test_password_fields_have_hold_to_reveal_control(self):
        for url in ("/accounts/login/", "/accounts/register/"):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertContains(response, "Parolni koʻrish uchun bosib turing")
                self.assertContains(response, 'document.querySelectorAll(\'input[type="password"]\')')

    def test_register_logs_in_and_records_consent(self):
        resp = self.register()
        self.assertRedirects(resp, "/cases/", fetch_redirect_response=False)
        user = get_user_model().objects.get()
        self.assertEqual((user.phone_number, user.role), ("+998901234567", Role.LAWYER))
        self.assertIn("pii", user.consents_json)
        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(self.client.get("/cases/").status_code, 200)

    def test_register_validation(self):
        self.assertEqual(self.register(consent="").status_code, 200)            # rozilik majburiy
        self.assertEqual(self.register(password2="boshqa").status_code, 200)   # parollar mos emas
        self.assertEqual(self.register(password1="12345678", password2="12345678").status_code, 200)  # zaif
        self.assertEqual(self.register(role="SUPERADMIN").status_code, 200)    # rolni o'zi tanlay olmaydi
        self.assertEqual(get_user_model().objects.count(), 0)
        self.register()
        self.client.logout()
        resp = self.register(phone_number="+998901234567")                     # takroriy raqam
        self.assertContains(resp, "allaqachon bor")

    def test_login_logout_and_safe_next(self):
        get_user_model().objects.create_user("+998901234567", PASSWORD, full_name="A")
        resp = self.client.post("/accounts/login/", {"phone_number": "901234567", "password": PASSWORD,
                                                     "next": "https://evil.example/"})
        self.assertRedirects(resp, "/cases/", fetch_redirect_response=False)  # tashqi next e'tiborsiz
        self.client.post("/accounts/logout/")
        self.assertEqual(self.client.get("/cases/").status_code, 302)
        resp = self.client.post("/accounts/login/?next=/", {"phone_number": "+998901234567", "password": PASSWORD})
        self.assertRedirects(resp, "/", fetch_redirect_response=False)

    def test_login_is_locked_after_repeated_failures(self):
        get_user_model().objects.create_user("+998901234567", PASSWORD, full_name="A")
        for _ in range(5):
            resp = self.client.post("/accounts/login/", {"phone_number": "+998901234567", "password": "notogri"})
            self.assertContains(resp, "notoʻgʻri")
        resp = self.client.post("/accounts/login/", {"phone_number": "+998901234567", "password": PASSWORD})
        self.assertEqual(resp.status_code, 429)  # to'g'ri parol ham vaqtincha qabul qilinmaydi
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_logout_requires_post(self):
        self.assertEqual(self.client.get("/accounts/logout/").status_code, 405)
