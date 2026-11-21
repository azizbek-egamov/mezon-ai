from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path

from . import spa

base_patterns = [
    *([path(settings.DJANGO_ADMIN_PATH, admin.site.urls)] if settings.DJANGO_ADMIN_PATH else []),
    path("api/v1/", include("apps.api.urls")),
]

# Eski Django shablon sahifalari (dev; SPA to'liq o'rnini bosgach o'chiriladi)
legacy_patterns = [
    path("", include("apps.i18n.urls")),
    path("", include("apps.accounts.urls")),
    path("", include("apps.billing.urls")),
    path("", include("apps.cases.urls")),
    path("", include("apps.doc_builder.urls")),
    path("", include("apps.rag.urls")),
]

# Production: veb SPA (/) va admin SPA (/panel/); /api/ va /static/ ga tegmaydi
spa_patterns = [
    re_path(r"^panel(?:/(?P<path>.*))?$", spa.panel, name="spa_panel"),
    re_path(r"^(?!api/|static/)(?P<path>.*)$", spa.web, name="spa_web"),
]

urlpatterns = base_patterns + (legacy_patterns if settings.LEGACY_UI else spa_patterns)
