"""/api/v1/billing/* — joriy tarif va sarf, faol tariflar ro'yxati (TZ §8.1)."""
from drf_spectacular.utils import extend_schema
from rest_framework import generics
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.billing import quota
from apps.billing.models import Plan

from .. import serializers as s


class UsageView(APIView):
    @extend_schema(responses=s.UsageSerializer, tags=["billing"])
    def get(self, request):
        summary = quota.usage_summary(request.user)
        plan, sub = summary["plan"], summary["subscription"]
        return Response({
            "plan": plan.code, "plan_name": plan.display_name, "max_pages": summary["max_pages"],
            "unlimited": summary["exempt"], "expires_at": sub.expires_at if sub else None,
            "usage": [{"kind": r.get("kind"), "scope": r.get("scope"), "label": str(r["label"]),
                       "used": r["used"], "limit": r["limit"]} for r in summary["rows"]],
        })


class PlanListView(generics.ListAPIView):
    """Tariflar sahifasi uchun (kirmagan foydalanuvchiga ham ochiq)."""
    serializer_class = s.PlanSerializer
    permission_classes = [AllowAny]
    pagination_class = None

    def get_queryset(self):
        quota.free_plan()   # bazada FREE bo'lmasa yaratiladi (quota bilan bir xil)
        return Plan.objects.filter(is_active=True)

    @extend_schema(tags=["billing"])
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)
