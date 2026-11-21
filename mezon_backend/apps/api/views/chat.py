"""/api/v1/chat/ask — iqtibosli huquqiy javob, Server-Sent Events oqimi (HTML chat bilan bir xil hodisalar).

Hodisalar: aspects, sources, delta (ko'p marta), verification, done; xato bo'lsa — error va oqim tugaydi.
Validatsiya xatosi (400) va tarif limiti (429) — oddiy JSON: {"detail", "code"}.
DIQQAT: har bir so'rov Claude API ni chaqiradi (pullik) va savol kvotasini band qiladi.
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework.views import APIView

from apps.billing import quota
from apps.rag.views import AskError, answer_response, parse_ask

from .. import serializers as s
from ..throttling import ClientIpScopedRateThrottle
from .common import error


class AskView(APIView):
    throttle_classes = [ClientIpScopedRateThrottle]
    throttle_scope = "ask"

    @extend_schema(request=s.AskSerializer, responses={
        (200, "text/event-stream"): OpenApiResponse(OpenApiTypes.STR, description="SSE oqimi"),
        400: s.DetailSerializer, 429: s.DetailSerializer}, tags=["chat"])
    def post(self, request):
        try:
            question, lang, effort, on_date = parse_ask(request.data)
        except AskError as e:
            return error(str(e), 400, "invalid")
        decision = quota.reserve_chat(request.user)   # tarif: kunlik/umrbod savol limiti (TZ §8.1)
        if not decision.ok:
            return error(decision.message, 429, f"quota_{decision.code}")
        return answer_response(question, lang, effort, on_date, request.user)
