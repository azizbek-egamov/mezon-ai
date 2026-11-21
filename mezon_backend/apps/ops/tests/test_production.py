"""Production tarmoq (17-bosqich): proksi orqasida IP, holat tekshiruvi, SPA tarqatish, production sozlamalari."""
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.lockout import client_ip
from apps.api.throttling import ClientIpScopedRateThrottle

PASSWORD = "Kuchli-parol-77"
CF = "HTTP_CF_CONNECTING_IP"


@override_settings(CLIENT_IP_HEADER=CF)
class ClientIpTests(SimpleTestCase):
    def ip(self, remote, **headers):
        return client_ip(RequestFactory().get("/", REMOTE_ADDR=remote, **headers))

    def test_header_trusted_only_from_local_proxy(self):
        self.assertEqual(self.ip("127.0.0.1", **{CF: "203.0.113.7"}), "203.0.113.7")
        self.assertEqual(self.ip("::1", **{CF: "2001:db8::1"}), "2001:db8::1")
        # to'g'ridan-to'g'ri ulangan mijoz sarlavhani soxtalashtira olmaydi
        self.assertEqual(self.ip("198.51.100.9", **{CF: "203.0.113.7"}), "198.51.100.9")

    def test_missing_or_invalid_header_falls_back(self):
        self.assertEqual(self.ip("127.0.0.1"), "127.0.0.1")
        self.assertEqual(self.ip("127.0.0.1", **{CF: "1.2.3.4, 5.6.7.8"}), "127.0.0.1")
        self.assertEqual(self.ip("127.0.0.1", **{CF: "<script>"}), "127.0.0.1")

    @override_settings(CLIENT_IP_HEADER="")
    def test_disabled_in_dev(self):
        self.assertEqual(self.ip("127.0.0.1", **{CF: "203.0.113.7"}), "127.0.0.1")

    def test_register_throttle_uses_real_ip(self):
        request = RequestFactory().post("/", REMOTE_ADDR="127.0.0.1", **{CF: "203.0.113.7"})
        self.assertEqual(ClientIpScopedRateThrottle().get_ident(request), "203.0.113.7")
        # DRF ning o'zi X-Forwarded-For ga ishonardi — bizda e'tiborsiz
        request = RequestFactory().post("/", REMOTE_ADDR="198.51.100.9", HTTP_X_FORWARDED_FOR="10.0.0.1")
        self.assertEqual(ClientIpScopedRateThrottle().get_ident(request), "198.51.100.9")


@override_settings(CLIENT_IP_HEADER=CF)
class TunnelLoginTests(TestCase):
    def setUp(self):
        cache.clear()
        self.user = get_user_model().objects.create_user("+998901112233", PASSWORD, role="LAWYER")

    def login(self, ip, phone="90 111 22 33", password=PASSWORD):
        return APIClient(REMOTE_ADDR="127.0.0.1", **{CF: ip}).post(
            "/api/v1/auth/login", {"phone_number": phone, "password": password}, format="json")

    def test_login_records_real_ip(self):
        self.assertEqual(self.login("203.0.113.7").status_code, 200)
        self.user.refresh_from_db()
        self.assertEqual(self.user.last_login_ip, "203.0.113.7")

    def test_ip_lockout_is_per_real_client(self):
        # tunnel orqasida hamma 127.0.0.1 — bitta hujumchi butun xizmatni yopib qo'ymasligi kerak
        for i in range(20):
            self.login("203.0.113.7", phone=f"90 000 00 {i:02d}", password="notogri")
        self.assertEqual(self.login("203.0.113.7").status_code, 429)
        self.assertEqual(self.login("198.51.100.20").status_code, 200)


class HealthTests(TestCase):
    @override_settings(QDRANT_URL="")
    def test_ok(self):
        resp = Client().get("/api/v1/health")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json(), {"status": "ok", "database": True, "search": True})

    @override_settings(QDRANT_URL="http://127.0.0.1:9")
    def test_search_down_is_degraded(self):
        with self.assertLogs("django.request", "ERROR"):  # 5xx jurnalga yoziladi (monitoring uchun)
            resp = Client().get("/api/v1/health")
        self.assertEqual(resp.status_code, 503)
        self.assertEqual(resp.json()["search"], False)

    @override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r"^api/v1/health$"], QDRANT_URL="",
                       SECURE_PROXY_SSL_HEADER=("HTTP_X_FORWARDED_PROTO", "https"))
    def test_health_exempt_from_https_redirect(self):
        client = Client()
        self.assertEqual(client.get("/api/v1/health").status_code, 200)        # lokal tekshiruv HTTP da
        self.assertEqual(client.get("/api/v1/auth/me").status_code, 301)        # qolgani — HTTPS ga
        self.assertEqual(client.get("/api/v1/auth/me", headers={"X-Forwarded-Proto": "https"}).status_code, 401)


class SpaTests(TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        for app in ("web", "panel"):
            (self.root / app).mkdir()
            (self.root / app / "index.html").write_text(f"<html>{app}</html>", encoding="utf-8")
        override = override_settings(ROOT_URLCONF="apps.ops.tests.urls_production", STATIC_ROOT=self.root)
        override.enable()
        self.addCleanup(override.disable)

    def test_routes(self):
        client = Client()
        for path, app in (("/", "web"), ("/cases/abc", "web"), ("/accounts/login/", "web"),
                          ("/panel", "panel"), ("/panel/", "panel"), ("/panel/users/5", "panel")):
            resp = client.get(path)
            self.assertEqual(resp.status_code, 200, path)
            self.assertEqual(resp.content.decode(), f"<html>{app}</html>", path)
            self.assertEqual(resp["Cache-Control"], "no-cache")
        self.assertEqual(client.get("/api/v1/yoq").status_code, 404)       # API yo'li SPA ga tushmaydi
        self.assertEqual(client.get("/static/yoq.js").status_code, 404)
        self.assertEqual(client.post("/cases").status_code, 405)
        self.assertEqual(client.get("/api/v1/i18n/languages").status_code, 200)

    @override_settings(CSP_MODE="enforce")
    def test_csp_header_with_inline_script_hash(self):
        script = "\ntry{document.documentElement.dataset.theme='light'}\ncatch(e){}\n"
        # Windows da yig'ilgan index.html — CRLF; brauzer xeshni LF bilan hisoblaydi
        (self.root / "web" / "index.html").write_bytes(
            f'<html><script>{script}</script><script type="module" src="/a.js"></script></html>'
            .replace("\n", "\r\n").encode("utf-8"))
        resp = Client().get("/")
        csp = resp["Content-Security-Policy"]
        digest = base64.b64encode(hashlib.sha256(script.encode()).digest()).decode()
        self.assertIn(f"script-src 'self' 'sha256-{digest}'", csp)
        self.assertNotIn("unsafe-eval", csp)
        self.assertIn("connect-src 'self'", csp)
        self.assertIn("frame-ancestors 'none'", csp)
        with override_settings(CSP_MODE="report"):
            self.assertIn("Content-Security-Policy-Report-Only", Client().get("/"))
        with override_settings(CSP_MODE="off"):
            self.assertNotIn("Content-Security-Policy", Client().get("/"))

    def test_missing_build(self):
        (self.root / "panel" / "index.html").unlink()
        with self.assertLogs("django.request", "ERROR"):
            resp = Client().get("/panel/")
        self.assertEqual(resp.status_code, 503)
        self.assertIn("npm run build", resp.content.decode())


class ProductionSettingsTests(SimpleTestCase):
    """Sozlamalar DJANGO_DEBUG=0 bilan alohida jarayonda yuklanadi (.env dagi qiymatlar ustidan)."""

    def run_python(self, code, **env):
        # Windows konsol kodi tizim tiliga qarab cp1251 bo'lishi mumkin; capture_output esa quyida UTF-8 o'qiydi.
        full = {**os.environ, "PYTHONIOENCODING": "utf-8", "DJANGO_SETTINGS_MODULE": "config.settings",
                "DJANGO_DEBUG": "0", **env}
        return subprocess.run([sys.executable, "-c", code], cwd=settings.BASE_DIR, env=full, capture_output=True,
                              text=True, encoding="utf-8", timeout=120)

    def test_admin_closed_and_csp_enforced_by_default(self):
        code = "from django.conf import settings; print(repr(settings.DJANGO_ADMIN_PATH), settings.CSP_MODE)"
        env = {k: v for k, v in {**os.environ, "DJANGO_SETTINGS_MODULE": "config.settings", "DJANGO_DEBUG": "0",
                                 "DJANGO_SECRET_KEY": "x" * 60}.items() if k not in ("DJANGO_ADMIN_PATH", "MEZON_CSP")}
        proc = subprocess.run([sys.executable, "-c", code], cwd=settings.BASE_DIR, env=env, capture_output=True,
                              text=True, encoding="utf-8", timeout=120)
        self.assertEqual(proc.stdout.strip(), "'' enforce", proc.stderr)

    def test_weak_secret_key_refused(self):
        proc = self.run_python("import config.settings", DJANGO_SECRET_KEY="dev-only-insecure-key")
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn("DJANGO_SECRET_KEY", proc.stderr)

    def test_production_values_and_deploy_check(self):
        code = (
            "import json, django; django.setup(); from django.conf import settings as s; "
            "from django.core.management import call_command; call_command('check', deploy=True, fail_level='WARNING'); "
            "print(json.dumps({'legacy': s.LEGACY_UI, 'proxy': list(s.SECURE_PROXY_SSL_HEADER), 'hsts': s.SECURE_HSTS_SECONDS, "
            "'ip': s.CLIENT_IP_HEADER, 'cookie': s.SESSION_COOKIE_SECURE, 'debug': s.DEBUG, "
            "'storage': s.STORAGES['staticfiles']['BACKEND']}))")
        proc = self.run_python(code, DJANGO_SECRET_KEY="x" * 30 + "Kuchli-Production-Kaliti-0123456789",
                               DJANGO_ALLOWED_HOSTS="mezon.example.uz")
        self.assertEqual(proc.returncode, 0, proc.stderr)
        values = json.loads(proc.stdout.strip().splitlines()[-1])
        self.assertEqual(values, {"legacy": False, "proxy": ["HTTP_X_FORWARDED_PROTO", "https"], "hsts": 86400,
                                  "ip": CF, "cookie": True, "debug": False,
                                  "storage": "whitenoise.storage.CompressedStaticFilesStorage"})
