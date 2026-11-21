"""Jarayon ichidagi umumiy qulflar."""
import threading
from contextlib import contextmanager

# GPU modellari (embedding, reranker) va ichki Qdrant bir vaqtda bitta qidiruvni bajaradi:
# chat so'rovlari va fondagi ish tahlili shu qulfni birga ishlatadi.
SEARCH_LOCK = threading.Lock()

# Navbatda kutish chegarasi: cheksiz kutgan so'rovlar butun server oqimlarini (waitress threads) band qilmasin.
SEARCH_WAIT_SECONDS = 60


class SearchBusy(Exception):
    """Qidiruv navbati uzoq band — so'rov rad etiladi (503), oqim bo'shatiladi."""


@contextmanager
def search_slot(timeout: float = SEARCH_WAIT_SECONDS):
    if not SEARCH_LOCK.acquire(timeout=timeout):
        raise SearchBusy
    try:
        yield
    finally:
        SEARCH_LOCK.release()
