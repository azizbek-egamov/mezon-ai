from django.conf import settings
from django.http import HttpResponseRedirect
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST


@require_POST
def set_language(request):
    """POST language=<kod>&next=<yo'l>: profilga (kirgan bo'lsa) va cookie ga yozadi."""
    code = request.POST.get("language", "")
    target = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    if not url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        target = "/"
    response = HttpResponseRedirect(target)
    if code in dict(settings.LANGUAGES):
        if request.user.is_authenticated and request.user.language != code:
            request.user.language = code
            request.user.save(update_fields=["language"])
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, code, max_age=365 * 24 * 3600, samesite="Lax",
                            secure=settings.SESSION_COOKIE_SECURE)
    return response
