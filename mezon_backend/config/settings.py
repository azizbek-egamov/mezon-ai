"""MEZON AI — Django sozlamalari. Qiymatlar .env dan olinadi (.env.example ga qarang)."""
import hashlib
import os
import sys
from datetime import timedelta
from pathlib import Path

import dj_database_url
from dotenv import dotenv_values, load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-only-insecure-key")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
if not DEBUG and (SECRET_KEY.startswith("dev-") or len(SECRET_KEY) < 50):
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured("Production (DJANGO_DEBUG=0): .env da kuchli DJANGO_SECRET_KEY (>= 50 belgi) kerak.")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "corsheaders",
    "apps.i18n",
    "apps.accounts",
    "apps.billing",
    "apps.lex_corpus",
    "apps.rag",
    "apps.cases",
    "apps.doc_builder",
    "apps.student",
    "apps.api",
    "apps.ops",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",   # /static/ (Django admin + veb/admin SPA build) — production da
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.i18n.middleware.UserLocaleMiddleware",   # profil tili > cookie > brauzer tili (TZ §5.4)
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {"context_processors": [
            "django.template.context_processors.request",
            "django.contrib.auth.context_processors.auth",
            "django.contrib.messages.context_processors.messages",
            "apps.i18n.context.i18n",
        ]},
    },
]
WSGI_APPLICATION = "config.wsgi.application"

DATA_DIR = Path(os.environ.get("MEZON_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

# Docker/PostgreSQL o'rnatilguncha SQLite; o'tish uchun DATABASE_URL=postgres://... kifoya.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{(DATA_DIR / 'dev.sqlite3').as_posix()}", conn_max_age=600
    )
}

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# Foydalanuvchilar: telefon raqami bilan kirish (apps.accounts).
AUTH_USER_MODEL = "accounts.User"
LOGIN_URL = "/accounts/login/"
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
     "OPTIONS": {"user_attributes": ("phone_number", "full_name")}},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 8}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]
SESSION_COOKIE_AGE = 14 * 24 * 3600
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_SECURE = CSRF_COOKIE_SECURE = not DEBUG
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("DJANGO_CSRF_TRUSTED_ORIGINS", "").split(",") if o]

# Production tarmoq (17-bosqich): Cloudflare Tunnel -> waitress (tools/serve.py, faqat 127.0.0.1). HTTPS Cloudflare da
# tugaydi, ichkarida HTTP; sxema X-Forwarded-Proto dan, mijoz IP — CF-Connecting-IP dan olinadi. Bu sarlavhalarga
# faqat server tashqaridan ko'rinmagani (127.0.0.1 da tinglagani) uchun ishonish mumkin.
# Haqiqiy IP sarlavhasi (META kaliti), faqat so'rov 127.0.0.1/::1 dan (cloudflared) kelganda o'qiladi; bo'sh — REMOTE_ADDR.
CLIENT_IP_HEADER = os.environ.get("MEZON_CLIENT_IP_HEADER", "" if DEBUG else "HTTP_CF_CONNECTING_IP")
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = os.environ.get("DJANGO_SSL_REDIRECT", "1") == "1"
    SECURE_REDIRECT_EXEMPT = [r"^api/v1/health$"]   # lokal holat tekshiruvi (tools/prod.ps1) HTTP da
    # HSTS: brauzer domenni faqat HTTPS da ochadi. Avval qisqa muddat; hammasi barqaror bo'lgach 31536000 (1 yil).
    SECURE_HSTS_SECONDS = int(os.environ.get("DJANGO_HSTS_SECONDS", "86400"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = os.environ.get("DJANGO_HSTS_SUBDOMAINS", "0") == "1"
    SECURE_CROSS_ORIGIN_OPENER_POLICY = "same-origin"
    # W005/W021: subdomenlar va preload — domen egasining qarori (DJANGO_HSTS_SUBDOMAINS), sukut bo'yicha yoqilmaydi
    SILENCED_SYSTEM_CHECKS = ["security.W005", "security.W021"]

# SPA sahifalari uchun Content-Security-Policy (config/spa.py): enforce | report (faqat brauzer konsoliga) | off
CSP_MODE = os.environ.get("MEZON_CSP", "off" if DEBUG else "enforce")

# Eski Django shablon sahifalari (vaqtinchalik). Production da o'chiq: o'rniga veb SPA (/) va admin SPA (/panel/).
LEGACY_UI = os.environ.get("MEZON_LEGACY_UI", "1" if DEBUG else "0") == "1"
# Django admin: dev da /admin/; production da faqat DJANGO_ADMIN_PATH (masalan "boshqaruv-x7k2/") berilsa ulanadi —
# unda kirish urinishlariga lockout yo'q, shuning uchun sukut bo'yicha yopiq (xodimlar uchun React admin /panel/ bor).
DJANGO_ADMIN_PATH = os.environ.get("DJANGO_ADMIN_PATH", "admin/" if DEBUG else "")

# API v1 (apps/api): DRF + JWT. Faqat token autentifikatsiya — sessiya/CSRF yo'q (eski HTML sahifalar sessiyada qoladi).
REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": ["apps.api.authentication.JWTAuthentication"],
    "DEFAULT_PERMISSION_CLASSES": ["rest_framework.permissions.IsAuthenticated"],
    "DEFAULT_RENDERER_CLASSES": ["rest_framework.renderers.JSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser", "rest_framework.parsers.MultiPartParser"],
    "DEFAULT_CONTENT_NEGOTIATION_CLASS": "apps.api.negotiation.LenientNegotiation",
    "DEFAULT_PAGINATION_CLASS": "rest_framework.pagination.PageNumberPagination",
    "PAGE_SIZE": 20,
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "EXCEPTION_HANDLER": "apps.api.exceptions.exception_handler",
    "DEFAULT_THROTTLE_RATES": {
        # GPU/LLM ni band qiluvchi yo'llar: kvotadan tashqari tezlik chegarasi (foydalanuvchi bo'yicha)
        "ask": os.environ.get("API_ASK_RATE", "20/min"),
        "laws_search": os.environ.get("API_LAWS_SEARCH_RATE", "30/min"),
    },
}
# Registratsiya: bir IP qisqa vaqtda ko'p so'rov yuborsa progressiv tanaffus. Har yangi kalendar oyida daraja
# avtomatik yana birinchi qiymatga (3 daqiqa) tushadi (`api.throttling.ProgressiveRegisterThrottle`).
REGISTER_THROTTLE_BURST = int(os.environ.get("API_REGISTER_BURST", "5"))
REGISTER_THROTTLE_WINDOW_SECONDS = int(os.environ.get("API_REGISTER_WINDOW_SECONDS", "60"))
REGISTER_THROTTLE_COOLDOWNS = tuple(int(v.strip()) for v in os.environ.get(
    "API_REGISTER_COOLDOWNS", "180,300,600,1200,2400,3600,10800,43200,86400"
).split(",") if v.strip())
SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=int(os.environ.get("JWT_ACCESS_MINUTES", "15"))),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=int(os.environ.get("JWT_REFRESH_DAYS", "14"))),
    "ROTATE_REFRESH_TOKENS": True,        # har yangilashda yangi refresh, eskisi qora ro'yxatga
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    # SECRET_KEY dan hosil qilingan alohida kalit (HS256 uchun >= 32 bayt; boshqa imzolar bilan aralashmaydi)
    "SIGNING_KEY": hashlib.sha256(f"mezon-jwt:{SECRET_KEY}".encode()).hexdigest(),
    "AUTH_HEADER_TYPES": ("Bearer",),
}
# Veb SPA: refresh token HttpOnly cookie da (JS ko'rmaydi); mobil ilova uni javob tanasida oladi.
JWT_REFRESH_COOKIE = "mezon_refresh"
JWT_REFRESH_COOKIE_PATH = "/api/v1/auth/"

# CORS: dev da Vite proxy ishlatiladi (kerak emas); production da veb/admin domenlari .env dan.
CORS_ALLOWED_ORIGINS = [o for o in os.environ.get("DJANGO_CORS_ORIGINS", "").split(",") if o]
CORS_ALLOW_CREDENTIALS = True
CORS_URLS_REGEX = r"^/api/.*$"
CORS_EXPOSE_HEADERS = ["Content-Disposition"]

SPECTACULAR_SETTINGS = {
    "TITLE": "MEZON AI API",
    "DESCRIPTION": "Veb, admin va mobil ilova uchun JSON API (TZ v2.1). Autentifikatsiya: `Authorization: Bearer <access>`.",
    "VERSION": "1.0.0",
    "SCHEMA_PATH_PREFIX": r"/api/v1",
    "SERVE_INCLUDE_SCHEMA": False,
    # Sxema va Swagger UI: dev da ochiq, production da faqat xodimlar
    "SERVE_PERMISSIONS": ["rest_framework.permissions.AllowAny" if DEBUG else "rest_framework.permissions.IsAdminUser"],
    "COMPONENT_SPLIT_REQUEST": True,
    "ENUM_NAME_OVERRIDES": {"CaseCategoryEnum": "apps.api.serializers.CASE_CATEGORY_CHOICES",
                            "TemplateCategoryEnum": "apps.doc_builder.models.Category",
                            "UserRoleEnum": "apps.accounts.models.Role",
                            "RegisterRoleEnum": "apps.api.serializers.REGISTER_ROLE_CHOICES",
                            "CaseStatusEnum": "apps.cases.models.CaseRun.Status",
                            "PaymentStatusEnum": "apps.billing.models.Payment.Status",
                            "SubscriptionStatusEnum": "apps.billing.models.Subscription.Status",
                            "SyncStatusEnum": "apps.lex_corpus.models.SyncRun.Status",
                            "LawCategoryEnum": "apps.student.models.LawCategory"},
}
# Interfeys tillari (TZ §5.4): uz-Latn, uz-Cyrl, ru, kaa, en. Manba matnlar — oʻzbek lotin; kataloglar locale/ da
# (apps/i18n/catalog.py, `manage.py i18n_sync`). Django da bu kodlar yo'q — EXTRA_LANG_INFO bilan qo'shiladi.
LANGUAGE_CODE = "uz-latn"
LANGUAGES = [
    ("uz-latn", "Oʻzbekcha"),
    ("uz-latn-2026", "Özbekça (2026)"),
    ("uz-cyrl", "Ўзбекча"),
    ("ru", "Русский"),
    ("kaa", "Қарақалпақша"),
    ("en", "English"),
]
EXTRA_LANG_INFO = {
    "uz-latn": {"bidi": False, "code": "uz-latn", "name": "Uzbek (Latin)", "name_local": "Oʻzbekcha"},
    "uz-latn-2026": {"bidi": False, "code": "uz-latn-2026", "name": "Uzbek (Latin 2026)", "name_local": "Özbekça (2026)"},
    "uz-cyrl": {"bidi": False, "code": "uz-cyrl", "name": "Uzbek (Cyrillic)", "name_local": "Ўзбекча"},
    "kaa": {"bidi": False, "code": "kaa", "name": "Karakalpak", "name_local": "Қарақалпақша"},
}
from django.conf import locale as _locale  # noqa: E402

_locale.LANG_INFO.update(EXTRA_LANG_INFO)
LOCALE_PATHS = [BASE_DIR / "locale"]
TIME_ZONE = "Asia/Tashkent"
USE_I18N = True
USE_TZ = True
STATIC_URL = "static/"
STATIC_ROOT = Path(os.environ.get("DJANGO_STATIC_ROOT", BASE_DIR / "staticfiles"))  # `manage.py collectstatic`
# Veb va admin SPA build natijalari (`npm run build`): /static/web/ va /static/panel/ ostida (Vite `base`).
FRONTEND_DIR = Path(os.environ.get("MEZON_FRONTEND_DIR", BASE_DIR.parent / "frontend"))
SPA_BUILDS = {"web": FRONTEND_DIR / "apps" / "web" / "dist", "panel": FRONTEND_DIR / "apps" / "admin" / "dist"}
STATICFILES_DIRS = [(prefix, path) for prefix, path in SPA_BUILDS.items() if path.is_dir()]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Production: gzip/brotli nusxalar oldindan tayyorlanadi; Vite fayl nomlari o'zi xeshlangan (manifest shart emas)
    "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage" if DEBUG
                    else "whitenoise.storage.CompressedStaticFilesStorage"},
}
# Vite xeshlangan fayllari (assets/index-AbC123xy.js) o'zgarmaydi — brauzer 1 yil keshlaydi
WHITENOISE_IMMUTABLE_FILE_TEST = r"^.+/assets/.+-[A-Za-z0-9_-]{8}\.\w+$"

# Kesh (dev: fayl; production: Redis). LLM so'rov o'girish natijalari shu yerda saqlanadi.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.filebased.FileBasedCache",
        "LOCATION": str(DATA_DIR / "cache"),
        "TIMEOUT": 30 * 24 * 3600,
        # Sukut MAX_ENTRIES=300 va har to'lishda tasodifiy 1/3 yozuv o'chadi — LLM natijalari uchun juda kichik
        "OPTIONS": {"MAX_ENTRIES": 50_000, "CULL_FREQUENCY": 10},
    },
    # Xavfsizlik hisoblagichlari (kirish urinishlari, throttle): LLM natijalari bu keshni to'ldirib, tasodifiy
    # "cull" bilan hisoblagichlarni o'chira olmasin. Atomik incr — jarayon ichida; production da Redis (bir nechta jarayon).
    "security": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "mezon-security",
        "OPTIONS": {"MAX_ENTRIES": 200_000, "CULL_FREQUENCY": 10},
    },
}
# Testlar dev keshini (pullik LLM natijalari) o'qimasin va `cache.clear()` bilan o'chirib yubormasin.
# Ikkala nom ham bitta xotira omboriga qaraydi (LOCATION yo'q) — testdagi `cache.clear()` hisoblagichlarni ham tozalaydi.
if sys.argv[1:2] == ["test"]:
    CACHES = {name: {"BACKEND": "django.core.cache.backends.locmem.LocMemCache"} for name in ("default", "security")}

# lex.uz
LEX_BASE_URL = "https://lex.uz"
LEX_CACHE_DIR = DATA_DIR / "lex_cache"
LEX_REQUEST_DELAY = float(os.environ.get("LEX_REQUEST_DELAY", "1.0"))
LEX_REGISTRY_JSON = Path(os.environ.get(
    "LEX_REGISTRY_JSON", BASE_DIR.parent / "lex-uz-dagi-qonunlar" / "barcha_57950_hujjat.json"
))

# Qdrant: QDRANT_URL bo'lmasa — ichki (serversiz) rejim, DATA_DIR/qdrant da.
QDRANT_URL = os.environ.get("QDRANT_URL", "")
QDRANT_PATH = DATA_DIR / "qdrant"
QDRANT_COLLECTION = os.environ.get("QDRANT_COLLECTION", "lex_articles")
QDRANT_CACHE_COLLECTION = os.environ.get("QDRANT_CACHE_COLLECTION", "mezon_semantic_cache")
SEMANTIC_CACHE_ENABLED = (
    False if sys.argv[1:2] == ["test"]
    else (os.environ.get("SEMANTIC_CACHE_ENABLED", "1") == "1")
)
SEMANTIC_CACHE_THRESHOLD = float(os.environ.get("SEMANTIC_CACHE_THRESHOLD", "0.94"))

# Embedding va reranker modellari (lokal; GPU bo'lsa fp16). *-fp16 papkalar — asl .bin modellarning fp16 safetensors
# nusxasi (natijalar bir xil): .bin yuklanganda RAM da ~1 GB qoldiq qolardi, safetensors bilan qolmaydi.
EMBEDDING_MODEL_PATH = os.environ.get("EMBEDDING_MODEL_PATH", "E:/models/bge-m3-fp16")
RERANKER_MODEL_PATH = os.environ.get("RERANKER_MODEL_PATH", "E:/models/bge-reranker-v2-m3-fp16")
EMBEDDING_DEVICE = os.environ.get("EMBEDDING_DEVICE", "")  # bo'sh = cuda bo'lsa cuda, aks holda cpu
CHUNK_MAX_TOKENS = int(os.environ.get("CHUNK_MAX_TOKENS", "512"))

# LLM. Anthropic kaliti va manzili umumiy ANTHROPIC_* muhit o'zgaruvchilaridan EMAS, faqat loyihaning
# .env faylidan (yoki MEZON_ANTHROPIC_API_KEY dan) olinadi — boshqa dasturlarning sozlamalari aralashmasin.
_DOTENV = dotenv_values(BASE_DIR / ".env")
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "ollama")
LLM_MODEL = os.environ.get("LLM_MODEL", "claude-opus-5-5")
ANTHROPIC_API_KEY = os.environ.get("MEZON_ANTHROPIC_API_KEY") or _DOTENV.get("ANTHROPIC_API_KEY") or ""
ANTHROPIC_API_URL = "https://api.anthropic.com"
GEMINI_API_KEY = os.environ.get("MEZON_GEMINI_API_KEY") or _DOTENV.get("GEMINI_API_KEY") or ""
GEMINI_API_URL = os.environ.get("GEMINI_API_URL", "https://generativelanguage.googleapis.com")
# Bitta jarayon (server yoki buyruq) uchun xarajat chegarasi, dollar; 0 = cheklovsiz.
LLM_BUDGET_USD = float(os.environ.get("LLM_BUDGET_USD", "0.30"))
# Veb orqali yuklangan bitta ish tahliliga qo'shimcha ajratiladigan chegara (server jarayoni chegarasiga qo'shiladi).
CASE_BUDGET_USD = float(os.environ.get("CASE_BUDGET_USD", "0.50"))
# Zaxira nusxalar (apps/ops, `manage.py backup`): imkon bo'lsa boshqa diskda; nechtasi saqlanadi (disk to'lmasin).
BACKUP_DIR = Path(os.environ.get("MEZON_BACKUP_DIR", BASE_DIR.parent / "backups"))
BACKUP_KEEP = int(os.environ.get("MEZON_BACKUP_KEEP", "7"))
# Ish fayllarini shifrlash kalitlari (apps/cases/storage.py): Fernet kalitlari, vergul bilan, birinchisi joriy.
DATA_KEYS = (os.environ.get("MEZON_DATA_KEYS") or _DOTENV.get("MEZON_DATA_KEYS") or "").split(",")
# DOCX/PDF eksport (apps/cases/export.py): Times New Roman shriftlari (times.ttf, timesbd.ttf, timesi.ttf).
EXPORT_FONT_DIR = os.environ.get("EXPORT_FONT_DIR", "C:/Windows/Fonts")
# Texnik yuqori chegara; tarifdagi "bitta ish hajmi" (apps/billing) undan oshmaydi.
CASE_MAX_PAGES = int(os.environ.get("CASE_MAX_PAGES", "200"))
CASE_MAX_MB = int(os.environ.get("CASE_MAX_MB", "50"))      # barcha yuklangan fayllar yig'indisi
# Tarif kvotalari (TZ §8): False — hamma uchun cheksiz (ichki sinov). Xodim/superadmin doim cheksiz.
BILLING_ENFORCED = os.environ.get("BILLING_ENFORCED", "1") not in ("0", "false", "False", "")
CASE_MAX_FILES = int(os.environ.get("CASE_MAX_FILES", "20"))
# Katta ishda bitta ish chegarasi (CASE_BUDGET_USD) yetmaydi: chegara = max(CASE_BUDGET_USD, varaq soni × shu qiymat).
CASE_BUDGET_PER_PAGE_USD = float(os.environ.get("CASE_BUDGET_PER_PAGE_USD", "0.015"))
# Har bir bosqich uchun model (faqat anthropic provayderida): LLM_MODEL_<BOSQICH>, sukut — LLM_MODEL.
LLM_TASKS = ("rewrite", "plan", "select", "extract", "analysis", "legal", "legal_retry", "answer", "vision_ocr")
LLM_TASK_MODELS = {t: os.environ.get(f"LLM_MODEL_{t.upper()}", LLM_MODEL) for t in LLM_TASKS}
# Skaner va rasm sahifalarini multimodal AI (Gemini Vision) orqali o'qish (1 = yoqilgan, 0 = faqat lokal OCR)
CASE_VISION_OCR = os.environ.get("CASE_VISION_OCR", "1") in ("1", "true", "True", "yes")

# Jurnallar: konsol (dev) + production da data/logs/mezon.log (10 MB x 5 aylanma). Ish tahlili xatolarining
# tafsiloti (worker.user_error) foydalanuvchiga emas, shu yerga yoziladi.
LOG_DIR = DATA_DIR / "logs"
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {"plain": {"format": "%(asctime)s %(levelname)s %(name)s: %(message)s"}},
    "handlers": {"console": {"class": "logging.StreamHandler", "formatter": "plain"}},
    "root": {"handlers": ["console"], "level": "WARNING"},  # kutubxonalar (transformers, httpx) — faqat ogohlantirish
    "loggers": {
        "apps": {"level": "WARNING" if sys.argv[1:2] == ["test"] else os.environ.get("DJANGO_LOG_LEVEL", "INFO")},
        "django.request": {"level": "ERROR"},  # 4xx ogohlantirishlar jurnalni to'ldirmasin
    },
}
if not DEBUG and sys.argv[1:2] != ["test"]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    LOGGING["handlers"]["file"] = {
        "class": "logging.handlers.RotatingFileHandler", "formatter": "plain", "encoding": "utf-8",
        "filename": str(LOG_DIR / "mezon.log"), "maxBytes": 10 * 1024 * 1024, "backupCount": 5,
    }
    LOGGING["root"]["handlers"].append("file")
