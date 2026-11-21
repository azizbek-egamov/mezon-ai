"""Yurxizmat.uz metismenu dagi barcha 6 ta toifa va 31 ta bo'limni aylanib,
har bir hujjat qaysi asosiy toifa va qaysi bo'limga tegishli ekanligini xaritalash (mapping).
Natija: mezon_backend/data/yurxizmat/category_tree.json da saqlanadi.
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
logger = logging.getLogger("cat_mapper")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "yurxizmat"
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUT_FILE = DATA_DIR / "category_tree.json"

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

def fetch(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="ignore")

def extract_tree_structure():
    logger.info("Metismenu daraxtini o'qish boshlandi...")
    html = fetch("https://yurxizmat.uz/oz/categories")
    soup = BeautifulSoup(html, "html.parser")
    
    menu = soup.select_one("ul.metismenu.sidebarMenu")
    if not menu:
        raise RuntimeError("Metismenu topilmadi!")
        
    tree = []
    
    for li in menu.find_all("li", recursive=False):
        top_a = li.find("a")
        if not top_a:
            continue
        top_name = top_a.get_text(strip=True)
        top_href = top_a.get("href", "")
        top_slug = top_href.rstrip("/").split("/")[-1]
        
        sub_items = []
        sub_ul = li.find("ul")
        if sub_ul:
            for sub_li in sub_ul.find_all("li", recursive=False):
                sub_a = sub_li.find("a")
                if not sub_a:
                    continue
                sub_name = sub_a.get_text(strip=True)
                sub_href = sub_a.get("href", "")
                sub_slug = sub_href.rstrip("/").split("/")[-1]
                sub_items.append({
                    "name": sub_name,
                    "slug": sub_slug,
                    "href": sub_href,
                    "url": f"https://yurxizmat.uz{sub_href}" if sub_href.startswith("/") else sub_href
                })
                
        tree.append({
            "name": top_name,
            "slug": top_slug,
            "href": top_href,
            "subcategories": sub_items
        })
        
    logger.info("Jami %s ta asosiy toifa va %s ta ichki bo'lim topildi.",
                len(tree), sum(len(t["subcategories"]) for t in tree))
    return tree

def crawl_subcategories_and_map_docs(tree):
    doc_to_cat = {} # doc_id -> {top_name, top_slug, sub_name, sub_slug}
    
    for top in tree:
        top_name = top["name"]
        top_slug = top["slug"]
        for sub in top["subcategories"]:
            sub_name = sub["name"]
            sub_slug = sub["slug"]
            sub_url = sub["url"]
            
            page = 1
            sub_doc_count = 0
            while True:
                url = f"{sub_url}?page={page}"
                logger.info("Yuklanmoqda: [%s > %s] sahifa %s", top_name, sub_name, page)
                try:
                    html = fetch(url)
                except Exception as e:
                    logger.warning("Xato [%s]: %s", url, e)
                    break
                    
                soup = BeautifulSoup(html, "html.parser")
                docs = soup.select("a[href*='/document/']")
                if not docs:
                    break
                    
                for a in docs:
                    href = a.get("href", "")
                    m = re.search(r"/document/(\d+)", href)
                    if m:
                        doc_id = int(m.group(1))
                        sub_doc_count += 1
                        if doc_id not in doc_to_cat:
                            doc_to_cat[doc_id] = {
                                "doc_id": doc_id,
                                "top_category": top_name,
                                "top_slug": top_slug,
                                "subcategory": sub_name,
                                "sub_slug": sub_slug,
                            }
                            
                next_btn = soup.select_one(".pagination .next:not(.disabled) a, a[rel='next']")
                if not next_btn and page >= 4:
                    break
                page += 1
                if page > 30: # safety
                    break
                time.sleep(0.15)
                
            logger.info("Bo'lim [%s > %s]: %s ta hujjat xaritalandi", top_name, sub_name, sub_doc_count)
            
    logger.info("XARITALASH TUGADI! Jami xaritalangan hujjatlar: %s ta", len(doc_to_cat))
    
    result = {
        "tree": tree,
        "doc_mappings": doc_to_cat
    }
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    logger.info("Saqlandi: %s", OUT_FILE)
    return result

if __name__ == "__main__":
    tree = extract_tree_structure()
    crawl_subcategories_and_map_docs(tree)

