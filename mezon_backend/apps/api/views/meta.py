"""Ochiq meta so'rovlar: /api/v1/i18n/languages (til almashtirgichi uchun) va /api/v1/health (holat tekshiruvi)."""
import requests
from django.conf import settings
from django.db import connection
from drf_spectacular.utils import extend_schema
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.i18n.codes import to_tz_code

from .. import serializers as s


class LanguagesView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses=s.LanguageInfoSerializer(many=True), tags=["i18n"])
    def get(self, request):
        return Response([{"code": code, "tz_code": to_tz_code(code), "name": name} for code, name in settings.LANGUAGES])


class HealthView(APIView):
    """Holat tekshiruvi (tools/prod.ps1, tashqi monitoring): baza va qidiruv serveri. Ichki tafsilot qaytarilmaydi."""
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(responses=s.HealthSerializer, tags=["meta"])
    def get(self, request):
        checks = {"database": _database_ok(), "search": _search_ok()}
        ok = all(checks.values())
        return Response({"status": "ok" if ok else "degraded", **checks}, status=200 if ok else 503)


def _database_ok() -> bool:
    try:
        connection.ensure_connection()
        return True
    except Exception:
        return False


def _search_ok() -> bool:
    if not settings.QDRANT_URL:  # ichki (serversiz) rejim — alohida tekshiriladigan server yo'q
        return True
    try:
        return requests.get(settings.QDRANT_URL.rstrip("/") + "/readyz", timeout=2).ok
    except requests.RequestException:
        return False
