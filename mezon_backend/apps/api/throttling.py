"""So'rovlar chastotasi cheklovi. DRF o'zi X-Forwarded-For ni oladi (mijoz soxtalashtira oladi) — biz esa
Cloudflare Tunnel orqasidagi haqiqiy IP ni (`accounts.lockout.client_ip`) ishlatamiz.

Registratsiyada oddiy ``10/hour`` yo'q: qisqa burst oshsa 3 daqiqadan boshlanadigan progressiv tanaffus beriladi.
Takroriy buzilishlar shu oy ichida tanaffusni uzaytiradi, yangi kalendar oyida daraja avtomatik nolga tushadi.
"""
import math
import time
from datetime import datetime
from zoneinfo import ZoneInfo

from django.conf import settings
from django.core.cache import caches
from rest_framework.throttling import BaseThrottle
from rest_framework.throttling import ScopedRateThrottle

from apps.accounts.lockout import client_ip


class ClientIpScopedRateThrottle(ScopedRateThrottle):
    # LLM natijalari keshi throttle tarixini tasodifan o'chirmasin (settings.CACHES["security"])
    cache = caches["security"]

    def get_ident(self, request):
        return client_ip(request._request if hasattr(request, "_request") else request)


class ProgressiveRegisterThrottle(BaseThrottle):
    """IP bo'yicha registratsiya burst himoyasi: 5/min, so'ng 3m, 5m, 10m...; har oy boshidan qayta."""

    cache = caches["security"]
    cache_ttl = 35 * 24 * 3600

    def __init__(self):
        self.wait_seconds = 0

    @staticmethod
    def _request(request):
        return request._request if hasattr(request, "_request") else request

    def _key(self, request, now: float) -> str:
        month = datetime.fromtimestamp(now, tz=ZoneInfo(settings.TIME_ZONE)).strftime("%Y%m")
        return f"register_progressive:{month}:{client_ip(self._request(request))}"

    def allow_request(self, request, view) -> bool:
        now = time.time()
        key = self._key(request, now)
        state = self.cache.get(key) or {"hits": [], "level": 0, "blocked_until": 0.0}

        blocked_until = float(state.get("blocked_until", 0))
        if blocked_until > now:
            self.wait_seconds = max(1, math.ceil(blocked_until - now))
            return False

        window = settings.REGISTER_THROTTLE_WINDOW_SECONDS
        hits = [float(hit) for hit in state.get("hits", []) if float(hit) > now - window]
        burst = settings.REGISTER_THROTTLE_BURST
        cooldowns = settings.REGISTER_THROTTLE_COOLDOWNS
        if len(hits) >= burst:
            level = max(0, int(state.get("level", 0)))
            cooldown = cooldowns[min(level, len(cooldowns) - 1)]
            self.wait_seconds = cooldown
            self.cache.set(key, {"hits": [], "level": level + 1, "blocked_until": now + cooldown}, self.cache_ttl)
            return False

        hits.append(now)
        state.update(hits=hits, blocked_until=0.0)
        self.cache.set(key, state, self.cache_ttl)
        return True

    def wait(self) -> int:
        return self.wait_seconds
