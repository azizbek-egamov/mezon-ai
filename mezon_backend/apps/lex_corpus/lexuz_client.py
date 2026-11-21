"""lex.uz dan hujjat sahifalarini yuklash (diskda keshlanadi, so'rovlar orasida kechikish bilan)."""
import hashlib
import time
from pathlib import Path
from urllib.parse import quote

import requests
from django.conf import settings

USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) MEZON-AI corpus bot"


class LexUzClient:
    def __init__(self, cache_dir: Path | None = None, delay: float | None = None):
        self.cache_dir = Path(cache_dir or settings.LEX_CACHE_DIR)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.delay = settings.LEX_REQUEST_DELAY if delay is None else delay
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "uz,ru;q=0.8"})
        self._last_request = 0.0

    @staticmethod
    def document_url(lex_id: str, edition_label: str | None = None) -> str:
        """edition_label — lex.uz ONDATE qiymati ('15.10.2026' yoki '15.10.2026 01')."""
        url = f"{settings.LEX_BASE_URL}/uz/docs/{lex_id}"
        return f"{url}?ONDATE={quote(edition_label)}" if edition_label else url

    def _cache_path(self, lex_id: str, edition_label: str | None) -> Path:
        suffix = "_" + edition_label.replace(".", "").replace(" ", "_") if edition_label else "_current"
        return self.cache_dir / f"{lex_id}{suffix}.html"

    def get_document_html(self, lex_id: str, edition_label: str | None = None, refresh: bool = False) -> str:
        path = self._cache_path(lex_id, edition_label)
        if path.exists() and not refresh:
            return path.read_text(encoding="utf-8")
        wait = self.delay - (time.monotonic() - self._last_request)
        if wait > 0:
            time.sleep(wait)
        resp = self.session.get(self.document_url(lex_id, edition_label), timeout=60)
        self._last_request = time.monotonic()
        resp.raise_for_status()
        resp.encoding = "utf-8"
        self.write_cache(path, resp.text)
        return resp.text

    @staticmethod
    def write_cache(path: Path, text: str) -> None:
        """Atomik yozish: yarim yozilgan fayl keshda qolmasin."""
        tmp = path.with_name(path.name + ".part")
        tmp.write_text(text, encoding="utf-8")
        tmp.replace(path)

    def restore_cache(self, lex_id: str, text: str | None, edition_label: str | None = None) -> None:
        """Yaroqsiz javob keshga yozilgan bo'lsa — oldingi (yaxshi) nusxani qaytaradi (`None` bo'lsa faylni o'chiradi)."""
        path = self._cache_path(lex_id, edition_label)
        if text is None:
            path.unlink(missing_ok=True)
        else:
            self.write_cache(path, text)


def content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()
