"""Test uchun production URL tuzilmasi (LEGACY_UI = False): API + SPA."""
from config.urls import base_patterns, spa_patterns

urlpatterns = base_patterns + spa_patterns
