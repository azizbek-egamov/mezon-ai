"""drf-spectacular: bizning JWT sinfimiz uchun xavfsizlik sxemasi (Bearer)."""
from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme


class MezonJWTScheme(SimpleJWTScheme):
    target_class = "apps.api.authentication.JWTAuthentication"
