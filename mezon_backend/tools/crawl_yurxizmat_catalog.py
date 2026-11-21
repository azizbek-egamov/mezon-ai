"""Yurxizmat.uz katalogini to'liq yuklab olish skripti.
Barcha kategoriyalar va 49 ta sahifadagi 960+ hujjat havolalarini yig'adi.
Natija: mezon_backend/data/yurxizmat/catalog.json da saqlanadi.
"""
import json
import logging
import re
import sys
import time
import urllib.request
from pathlib import Path
from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("yurxizmat_catalog")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "yurxizmat"
DATA_DIR.mkdir(parents=True, exist_ok=True)
CATALOG_FILE = DATA_DIR / "catalog.json"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
}

def fetch_url(url: str, retries: int = 3, delay: float = 1.0) -> str:
    for attempt in range(1, retries + 1):
        try:
            req = urllib.request.Request(url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=15) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as e:
            logger.warning("Ulanish xatosi (%s/%s) [%s]: %s", attempt, retries, url, e)
            if attempt == retries:
                raise
            time.sleep(delay * attempt)
    return ""

def collect_catalog() -> list[dict]:
    logger.info("Yurxizmat katalogini yig'ish boshlandi...")
    page = 1
    docs_by_id = {}
    
    while True:
        url = f"https://yurxizmat.uz/oz/categories?page={page}"
        logger.info("Sahifa yuklanmoqda: %s", url)
        try:
            html = fetch_url(url)
        except Exception as e:
            logger.error("Sahifani yuklab bo'lmadi: %s, xato: %s", url, e)
            break
            
        soup = BeautifulSoup(html, "html.parser")
        doc_links = soup.select("a[href*='/document/']")
        if not doc_links:
            logger.info("Sahifada hujjat topilmadi. Yuklash tugadi (sahifa %s).", page)
            break
            
        found_in_page = 0
        for a in doc_links:
            href = a.get("href", "")
            m = re.search(r"/document/(\d+)", href)
            if not m:
                continue
            doc_id = int(m.group(1))
            title = a.get_text(strip=True)
            if doc_id not in docs_by_id:
                docs_by_id[doc_id] = {
                    "id": doc_id,
                    "title": title,
                    "url_oz": f"https://yurxizmat.uz/oz/document/{doc_id}",
                    "url_uz": f"https://yurxizmat.uz/uz/document/{doc_id}",
                    "url_ru": f"https://yurxizmat.uz/ru/document/{doc_id}",
                    "page": page,
                }
                found_in_page += 1
                
        logger.info("Sahifa %s: %s ta yangi hujjat topildi (Jami: %s ta)", page, found_in_page, len(docs_by_id))
        
        # Check next button
        next_btn = soup.select_one(".pagination .next:not(.disabled) a, a[rel='next']")
        if not next_btn and page >= 4:
            # Let's double check if there's any active page > current
            active_p = soup.select_one(".pagination li.active, .pagination .active")
            active_num = int(active_p.get_text(strip=True)) if active_p and active_p.get_text(strip=True).isdigit() else page
            if active_num < page:
                break
                
        page += 1
        if page > 60:  # safety limit
            break
        time.sleep(0.3)
        
    catalog = sorted(docs_by_id.values(), key=lambda d: d["id"], reverse=True)
    with open(CATALOG_FILE, "w", encoding="utf-8") as f:
        json.dump(catalog, f, ensure_ascii=False, indent=2)
    logger.info("Katalog saqlandi: %s (%s ta hujjat)", CATALOG_FILE, len(catalog))
    return catalog

if __name__ == "__main__":
    collect_catalog()

