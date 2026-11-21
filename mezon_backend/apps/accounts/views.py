"""Kirish, ro'yxatdan o'tish, chiqish (HTML). Parolni taxmin qilishdan himoya — lockout.py."""
from django.contrib.auth import login, logout
from django.shortcuts import redirect, render
from django.utils.translation import gettext
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_http_methods, require_POST

from . import lockout
from .audit import remember_login_ip
from .forms import LoginForm, RegisterForm
from .models import normalize_phone


def _safe_next(request) -> str:
    target = request.POST.get("next") or request.GET.get("next") or "/cases/"
    if url_has_allowed_host_and_scheme(target, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return target
    return "/cases/"


@require_http_methods(["GET", "POST"])
def login_view(request):
    if request.user.is_authenticated:
        return redirect(_safe_next(request))
    form = LoginForm(request, data=request.POST or None)
    error = ""
    if request.method == "POST":
        try:
            phone = normalize_phone(request.POST.get("phone_number", ""))
        except Exception:
            phone = ""
        if lockout.is_locked(request, phone):
            error = gettext("Juda koʻp notoʻgʻri urinish. 15 daqiqadan keyin qayta urinib koʻring.")
        elif form.is_valid():
            lockout.clear_phone(phone)
            remember_login_ip(request, form.user)
            login(request, form.user)
            return redirect(_safe_next(request))
        else:
            lockout.record_fail(request, phone)
    return render(request, "accounts/login.html", {"form": form, "error": error, "next": _safe_next(request)},
                  status=429 if error else 200)


@require_http_methods(["GET", "POST"])
def register_view(request):
    if request.user.is_authenticated:
        return redirect("/cases/")
    form = RegisterForm(data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        remember_login_ip(request, user, registered=True)
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("/cases/")
    return render(request, "accounts/register.html", {"form": form})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("/accounts/login/")
