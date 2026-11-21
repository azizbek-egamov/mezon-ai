"""GET /billing/ — tarif, limitlar va sarf; GET /api/billing/usage — JSON."""
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.http import require_GET

from apps.accounts.decorators import api_login_required

from . import quota
from .models import Plan


@require_GET
@login_required
def billing_page(request):
    summary = quota.usage_summary(request.user)
    return render(request, "billing/plans.html", {**summary, "plans": Plan.objects.filter(is_active=True)})


@require_GET
@api_login_required
def api_usage(request):
    s = quota.usage_summary(request.user)
    plan, sub = s["plan"], s["subscription"]
    return JsonResponse({
        "plan": plan.code, "plan_name": plan.display_name, "max_pages": s["max_pages"], "unlimited": s["exempt"],
        "expires_at": sub.expires_at.isoformat() if sub and sub.expires_at else None,
        "usage": [{"label": str(r["label"]), "used": r["used"], "limit": r["limit"]} for r in s["rows"]],
    }, json_dumps_params={"ensure_ascii": False})
