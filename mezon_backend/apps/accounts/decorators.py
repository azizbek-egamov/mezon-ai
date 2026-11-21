from functools import wraps

from django.http import JsonResponse
from django.utils.translation import gettext as _


def api_login_required(view):
    """API uchun: kirmagan foydalanuvchiga login sahifasiga yo'naltirish o'rniga 401 JSON."""
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({"error": _("Avval tizimga kiring")}, status=401)
        return view(request, *args, **kwargs)
    return wrapper
