from django.apps import AppConfig


class ApiConfig(AppConfig):
    name = "apps.api"
    verbose_name = "API v1"

    def ready(self):
        from . import schema  # noqa: F401  (OpenAPI kengaytmasini ro'yxatga olish)
