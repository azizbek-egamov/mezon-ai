"""JWT autentifikatsiya + foydalanuvchi profilidagi interfeys tili.

UserLocaleMiddleware sessiyadagi foydalanuvchini ko'radi; token bilan kelgan foydalanuvchi esa faqat DRF view ichida
aniqlanadi — shuning uchun profil tili (TZ §5.4: profil > cookie > Accept-Language) shu yerda yoqiladi va
xabarlar (xatolar, kvota matnlari, SSE) foydalanuvchi tilida qaytadi.
"""
from django.conf import settings
from django.utils import translation
from rest_framework_simplejwt.authentication import JWTAuthentication as BaseJWTAuthentication


class JWTAuthentication(BaseJWTAuthentication):
    def authenticate(self, request):
        result = super().authenticate(request)
        if result is not None:
            lang = getattr(result[0], "language", "")
            if lang in dict(settings.LANGUAGES):
                translation.activate(lang)
                request._request.LANGUAGE_CODE = lang
        return result
