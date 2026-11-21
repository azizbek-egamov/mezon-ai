"""Parolni taxmin qilishdan himoya (HTML kirish sahifasi va API uchun umumiy).

15 daqiqada bitta raqamga 5 ta, bitta IP dan 20 ta muvaffaqiyatsiz urinishdan keyin kirish vaqtincha yopiladi
(kesh orqali; production da Redis).
"""
import ipaddress

from django.conf import settings
from django.core.cache import caches

LOCK_SECONDS = 15 * 60
MAX_FAILS_PER_PHONE = 5
MAX_FAILS_PER_IP = 20


LOCAL_PROXIES = ("127.0.0.1", "::1")


def client_ip(request) -> str:
    """Mijoz IP manzili. Cloudflare Tunnel orqasida har so'rov 127.0.0.1 (cloudflared) dan keladi — haqiqiy IP
    settings.CLIENT_IP_HEADER (CF-Connecting-IP) da. Sarlavhaga faqat lokal proksidan kelganda ishoniladi:
    to'g'ridan-to'g'ri ulangan mijoz uni soxtalashtira olmasin."""
    remote = request.META.get("REMOTE_ADDR", "")
    header = settings.CLIENT_IP_HEADER
    if header and remote in LOCAL_PROXIES:
        forwarded = request.META.get(header, "").strip()
        try:
            return str(ipaddress.ip_address(forwarded))
        except ValueError:
            pass  # sarlavha yo'q yoki noto'g'ri — lokal so'rov (masalan, holat tekshiruvi)
    return remote


def _cache():
    """Hisoblagichlar alohida "security" keshida (LLM natijalari keshi ularni tasodifan o'chirmasin)."""
    return caches["security"]


def _fail_keys(request, phone: str) -> list[tuple[str, int]]:
    keys = [(f"login_fail:ip:{client_ip(request)}", MAX_FAILS_PER_IP)]
    if phone:
        keys.append((f"login_fail:phone:{phone}", MAX_FAILS_PER_PHONE))
    return keys


def is_locked(request, phone: str) -> bool:
    cache = _cache()
    return any(cache.get(key, 0) >= limit for key, limit in _fail_keys(request, phone))


def record_fail(request, phone: str) -> None:
    cache = _cache()
    for key, _ in _fail_keys(request, phone):
        if not cache.add(key, 1, LOCK_SECONDS):
            try:
                cache.incr(key)
            except ValueError:  # kalit shu orada muddati tugab o'chgan
                cache.set(key, 1, LOCK_SECONDS)


def clear_phone(phone: str) -> None:
    """Muvaffaqiyatli kirish: raqam bo'yicha hisob nolga (IP hisobi qoladi)."""
    if phone:
        _cache().delete(f"login_fail:phone:{phone}")
