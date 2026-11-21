"""Ish fayllarini diskda shifrlab saqlash (TZ §5.3 advokatlik siri).

Yuklangan PDF va tayyor hisobot (unda F.I.Sh. va boshqa shaxsiy ma'lumotlar ochiq) `.enc` fayllarda Fernet
(AES-128-CBC + HMAC-SHA256) bilan shifrlanadi. Kalit(lar) — MEZON_DATA_KEYS (vergul bilan; birinchisi bilan
shifrlanadi, qolganlari faqat eski fayllarni ochish uchun — kalitni almashtirish shu orqali). Dev rejimida kalit
berilmasa, DATA_DIR/secret/data.key avtomatik yaratiladi; production da (DEBUG=0) kalit majburiy.

`.enc` bilan tugamagan yo'llar — shifrlashdan oldingi eski fayllar, ular o'qiladi (`encrypt_case_files` buyrug'i
ularni shifrlaydi).
"""
import os
import tempfile
from contextlib import contextmanager
from functools import lru_cache
from pathlib import Path

from cryptography.fernet import Fernet, MultiFernet
from django.conf import settings
from django.core.exceptions import ImproperlyConfigured

SUFFIX = ".enc"


def _dev_key_file() -> Path:
    path = settings.DATA_DIR / "secret" / "data.key"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(Fernet.generate_key())
    return path


@lru_cache(maxsize=1)
def _fernet() -> MultiFernet:
    keys = [k.strip() for k in settings.DATA_KEYS if k.strip()]
    if not keys:
        if not settings.DEBUG:
            raise ImproperlyConfigured("MEZON_DATA_KEYS berilmagan — ish fayllarini shifrlab bo'lmaydi")
        keys = [_dev_key_file().read_text().strip()]
    return MultiFernet([Fernet(k) for k in keys])


def write_encrypted(path: str | Path, data: bytes) -> str:
    path = Path(path)
    if path.suffix != SUFFIX:
        path = path.with_name(path.name + SUFFIX)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_bytes(_fernet().encrypt(data))
    os.replace(tmp, path)  # yarim yozilgan fayl qolmasin
    return str(path)


def read_file(path: str | Path) -> bytes:
    raw = Path(path).read_bytes()
    return _fernet().decrypt(raw) if str(path).endswith(SUFFIX) else raw


def is_managed(path: str | Path) -> bool:
    """Faqat DATA_DIR ichidagi fayllar bizniki (import qilingan ishlar repodagi fixture PDF ga ishora qilishi mumkin)."""
    return bool(path) and Path(path).resolve().is_relative_to(Path(settings.DATA_DIR).resolve())


def delete_file(path: str | Path) -> None:
    if is_managed(path):
        Path(path).unlink(missing_ok=True)


@contextmanager
def decrypted_copy(path: str | Path):
    """OCR/PDF kutubxonalari fayl yo'lini talab qiladi: vaqtinchalik ochiq nusxa, ish tugashi bilan o'chiriladi."""
    if not str(path).endswith(SUFFIX):
        yield str(path)
        return
    fd, tmp = tempfile.mkstemp(suffix=".pdf", prefix="mezon_")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(read_file(path))
        yield tmp
    finally:
        Path(tmp).unlink(missing_ok=True)
