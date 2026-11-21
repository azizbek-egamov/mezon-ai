"""/api/v1/auth/* — JWT bilan kirish (veb, admin, mobil uchun bir xil).

Token: access (15 daq) `Authorization: Bearer` sarlavhasida; refresh (14 kun, har yangilashda rotatsiya, eskisi
qora ro'yxatda). Veb SPA `cookie: true` yuboradi — refresh HttpOnly cookie da (`/api/v1/auth/` yo'li, SameSite=Strict),
mobil — javob tanasida (expo-secure-store da saqlanadi).
Parolni taxmin qilishdan himoya — HTML kirish sahifasi bilan umumiy (`accounts/lockout.py`).
"""
from django.conf import settings
from django.contrib.auth.models import update_last_login
from django.utils.translation import gettext as _
from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.exceptions import APIException
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts import lockout
from apps.accounts.audit import remember_login_ip
from apps.accounts.forms import LoginForm, RegisterForm
from apps.accounts.models import normalize_phone

from .. import serializers as s
from ..throttling import ProgressiveRegisterThrottle
from .common import error, no_store, raise_form_errors


def _set_refresh_cookie(response, refresh: str) -> None:
    response.set_cookie(
        settings.JWT_REFRESH_COOKIE, refresh, httponly=True, samesite="Strict", path=settings.JWT_REFRESH_COOKIE_PATH,
        secure=settings.SESSION_COOKIE_SECURE,
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()))


def _delete_refresh_cookie(response) -> None:
    response.delete_cookie(settings.JWT_REFRESH_COOKIE, path=settings.JWT_REFRESH_COOKIE_PATH, samesite="Strict")


def _token_response(user, cookie: bool, status_code: int = 200) -> Response:
    refresh = RefreshToken.for_user(user)
    update_last_login(None, user)
    body = {"access": str(refresh.access_token), "user": s.UserSerializer(user).data}
    if not cookie:
        body["refresh"] = str(refresh)
    response = no_store(Response(body, status=status_code))
    if cookie:
        _set_refresh_cookie(response, str(refresh))
    return response


def _flag(data, name: str) -> bool:
    return str(data.get(name, "")).lower() in ("1", "true", "on", "yes")


class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=s.LoginSerializer, responses={200: s.TokenPairSerializer, 400: OpenApiResponse(
        description="Telefon yoki parol noto'g'ri"), 429: s.DetailSerializer}, tags=["auth"])
    def post(self, request):
        data = request.data
        try:
            phone = normalize_phone(str(data.get("phone_number", "")))
        except Exception:
            phone = ""
        if lockout.is_locked(request._request, phone):
            return error(_("Juda koʻp notoʻgʻri urinish. 15 daqiqadan keyin qayta urinib koʻring."), 429, "locked")
        form = LoginForm(request._request, data={"phone_number": data.get("phone_number", ""),
                                                 "password": data.get("password", "")})
        if not form.is_valid():
            lockout.record_fail(request._request, phone)
            raise_form_errors(form)
        lockout.clear_phone(phone)
        remember_login_ip(request._request, form.user)
        return _token_response(form.user, _flag(data, "cookie"))


class RegisterView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ProgressiveRegisterThrottle]

    @extend_schema(request=s.RegisterSerializer, responses={201: s.TokenPairSerializer}, tags=["auth"])
    def post(self, request):
        data = request.data
        form = RegisterForm(data={k: data.get(k, "") for k in (
            "phone_number", "full_name", "role", "advocate_license_no",
            "university", "study_level", "student_id_no",
            "password1", "password2")}
            | {"consent": _flag(data, "consent")})
        if not form.is_valid():
            raise_form_errors(form)
        user = form.save()
        remember_login_ip(request._request, user, registered=True)
        return _token_response(user, _flag(data, "cookie"), status.HTTP_201_CREATED)


class RefreshView(APIView):
    """Yangi access (va rotatsiya qilingan refresh). Refresh tanada bo'lmasa — HttpOnly cookie dan."""
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=s.RefreshSerializer, responses={200: s.AccessSerializer, 401: s.DetailSerializer},
                   tags=["auth"])
    def post(self, request):
        from_cookie = not request.data.get("refresh")
        token = request.COOKIES.get(settings.JWT_REFRESH_COOKIE, "") if from_cookie else request.data["refresh"]
        serializer = TokenRefreshSerializer(data={"refresh": token})
        try:
            serializer.is_valid(raise_exception=True)
        except (APIException, TokenError):   # yaroqsiz, muddati o'tgan, qora ro'yxatdagi yoki foydalanuvchi faolsiz
            response = error(_("Sessiya muddati tugagan. Qaytadan kiring."), 401, "token_invalid")
            if from_cookie:
                _delete_refresh_cookie(response)
            return response
        body = dict(serializer.validated_data)
        response = no_store(Response({"access": body["access"]} if from_cookie else body))
        if from_cookie and "refresh" in body:
            _set_refresh_cookie(response, body["refresh"])
        return response


class LogoutView(APIView):
    """Refresh token qora ro'yxatga qo'shiladi (access o'z muddati tugaguncha amal qiladi — 15 daq)."""
    permission_classes = [AllowAny]
    authentication_classes = []

    @extend_schema(request=s.RefreshSerializer, responses={204: None}, tags=["auth"])
    def post(self, request):
        token = request.data.get("refresh") or request.COOKIES.get(settings.JWT_REFRESH_COOKIE, "")
        if token:
            try:
                RefreshToken(token).blacklist()
            except TokenError:
                pass   # muddati o'tgan yoki allaqachon bekor qilingan — natija bir xil
        response = Response(status=status.HTTP_204_NO_CONTENT)
        _delete_refresh_cookie(response)
        return response


class MeView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses=s.UserSerializer, tags=["auth"])
    def get(self, request):
        return no_store(Response(s.UserSerializer(request.user).data))

    @extend_schema(request=s.UserSerializer, responses=s.UserSerializer, tags=["auth"],
                   description="O'zgartirish mumkin: full_name, advocate_license_no, language")
    def patch(self, request):
        serializer = s.UserSerializer(request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return no_store(Response(serializer.data))


class LanguageView(APIView):
    """Interfeys tili: kirgan bo'lsa — profilga, har holda `django_language` cookie ga (HTML sahifalar bilan umumiy)."""
    permission_classes = [AllowAny]

    @extend_schema(request=s.LanguageSerializer, responses=s.LanguageSerializer, tags=["auth"])
    def post(self, request):
        serializer = s.LanguageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        code = serializer.validated_data["language"]
        if request.user.is_authenticated and request.user.language != code:
            request.user.language = code
            request.user.save(update_fields=["language"])
        response = Response({"language": code})
        response.set_cookie(settings.LANGUAGE_COOKIE_NAME, code, max_age=365 * 24 * 3600, samesite="Lax",
                            secure=settings.SESSION_COOKIE_SECURE)
        return response
