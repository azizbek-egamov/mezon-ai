"""Yurxizmat.uz dagi barcha 966 ta hujjatni to'liq yuklab oluvchi skript.
- oz (lotin), uz (kirill) va mavjud bo'lsa ru (rus) tillarini yuklaydi.
- Yuklangan fayllarni data/yurxizmat/raw/{id}.json ko'rinishida saqlaydi.
- Resume (to'xtab qolsa qolgan joyidan davom etish) qo'llab-quvvatlanadi.
- ThreadPoolExecutor bilan xavfsiz va tezkor yuklaydi.
"""
import concurrent.futures
import json
import logging
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("yurxizmat_downloader")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "yurxizmat"
CATALOG_FILE = DATA_DIR / "catalog.json"
RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36"
}

def fetch_doc_lang(url: str, lang: str) -> tuple[str, str]:
    """Qaytaradi: (html_matni, yakuniy_url). Agar redirect bo'lsa yoki xato bo'lsa aniqlaydi."""
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=15) as resp:
            final_url = resp.geturl()
            # Rus tilida sahifa yo'q bo'lsa bosh sahifa /uz yoki /oz ga redirect qiladi
            if lang == "ru" and not f"/ru/document/" in final_url:
                return "", final_url
            html = resp.read().decode("utf-8", errors="ignore")
            return html, final_url
    except urllib.error.HTTPError as e:
        if e.code in (404, 500):
            return "", str(e)
        raise
    except Exception as e:
        logger.debug("Fetch xatosi %s: %s", url, e)
        return "", str(e)

def process_document(item: dict) -> bool:
    doc_id = item["id"]
    out_file = RAW_DIR / f"{doc_id}.json"
    
    # Agar allaqachon yuklangan bo'lsa o'tkazib yuborish
    if out_file.exists():
        return True
        
    url_oz = item.get("url_oz") or f"https://yurxizmat.uz/oz/document/{doc_id}"
    url_uz = item.get("url_uz") or f"https://yurxizmat.uz/uz/document/{doc_id}"
    url_ru = item.get("url_ru") or f"https://yurxizmat.uz/ru/document/{doc_id}"
    
    html_oz, final_oz = fetch_doc_lang(url_oz, "oz")
    time.sleep(0.05)
    html_uz, final_uz = fetch_doc_lang(url_uz, "uz")
    time.sleep(0.05)
    html_ru, final_ru = fetch_doc_lang(url_ru, "ru")
    
    # Kamida bitta tilda (oz yoki uz) muvaffaqiyatli yuklangan bo'lishi kerak
    if not html_oz and not html_uz:
        logger.warning("Hujjat #%s yuklanmadi (oz: %s, uz: %s)", doc_id, final_oz, final_uz)
        return False
        
    doc_data = {
        "id": doc_id,
        "title": item["title"],
        "url_oz": url_oz,
        "url_uz": url_uz,
        "url_ru": url_ru,
        "has_oz": bool(html_oz),
        "has_uz": bool(html_uz),
        "has_ru": bool(html_ru),
        "html_oz": html_oz,
        "html_uz": html_uz,
        "html_ru": html_ru,
        "fetched_at": time.time(),
    }
    
    # Atomik yozish
    tmp_file = out_file.with_suffix(".tmp")
    with open(tmp_file, "w", encoding="utf-8") as f:
        json.dump(doc_data, f, ensure_ascii=False)
    tmp_file.replace(out_file)
    
    return True

def download_all(workers: int = 5):
    if not CATALOG_FILE.exists():
        logger.error("Katalog fayli topilmadi: %s. Avval crawl_yurxizmat_catalog.py ni ishga tushiring.", CATALOG_FILE)
        return
        
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)
        
    total = len(catalog)
    logger.info("Jami yuklanishi kerak bo'lgan hujjatlar: %s ta", total)
    
    already_done = len(list(RAW_DIR.glob("*.json")))
    logger.info("Allaqachon yuklangan: %s ta", already_done)
    
    t0 = time.time()
    completed = already_done
    errors = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as executor:
        future_to_doc = {executor.submit(process_document, doc): doc for doc in catalog}
        
        for future in concurrent.futures.as_completed(future_to_doc):
            doc = future_to_doc[future]
            try:
                ok = future.result()
                if ok:
                    completed += 1
                else:
                    errors += 1
            except Exception as e:
                logger.error("Xato hujjat #%s da: %s", doc["id"], e)
                errors += 1
                
            if completed % 25 == 0 or completed == total:
                elapsed = time.time() - t0
                rate = completed / elapsed if elapsed > 0 else 0
                logger.info("Progress: %s/%s hujjat yuklandi (%d%%, %.1f doc/s, xatolar: %s)",
                            completed, total, int(completed * 100 / total), rate, errors)
                
    logger.info("YUKLASH TUGADI! Jami yuklandi: %s ta, Xatolar: %s ta", completed, errors)

if __name__ == "__main__":
    download_all(workers=6)

