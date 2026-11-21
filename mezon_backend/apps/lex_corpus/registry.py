"""lex.uz dagi yangi va o'zgargan hujjatlar ro'yxati: RSS lenta va reyestr qidiruvining birinchi sahifalari.

Yozuvlar `import_registry.build_documents` qabul qiladigan shaklda: id, title, act_type, act_number, act_date, status.
Reyestr qidiruvi (/uz/search/unique) eng yangi hujjatdan boshlanadi; keyingi sahifa — ASP.NET postback
(lex-uz-dagi-qonunlar/lex_scraper.py dagi usul).
"""
import re
import time
import xml.etree.ElementTree as ET
from datetime import date, datetime

from bs4 import BeautifulSoup
from django.conf import settings

from .lexuz_client import LexUzClient

SEARCH_URL = "/uz/search/unique"
NEXT_BUTTON = "ucFoundActsControl$LinkButton1"


def _date(text: str) -> date | None:
    m = re.search(r"(\d{2}\.\d{2}\.\d{4})", text or "")
    try:
        return datetime.strptime(m.group(1), "%d.%m.%Y").date() if m else None
    except ValueError:
        return None


def parse_rss(xml_text: str) -> list[dict]:
    """RSS: <item><title>…</title><link>/uz/docs/8554315</link><description>Turi рег. № … Qabul qilingan sana
    23.10.2026. Kuchga kirish sanasi 25.01.2027</description></item>"""
    rows = []
    for item in ET.fromstring(xml_text.lstrip("﻿").encode("utf-8")).iter("item"):
        link = item.findtext("link") or ""
        m = re.search(r"/docs/(-?\d+)", link)
        if not m:
            continue
        desc = item.findtext("description") or ""
        act_type = re.split(r"\s+рег\.|\.\s*Qabul qilingan sana", desc)[0].strip()
        number = re.search(r"(\S+-son)", desc)  # "рег. № МЮ 3960" — ro'yxatga olish raqami, hujjat raqami emas
        adopted = re.search(r"Qabul qilingan sana\s*(\d{2}\.\d{2}\.\d{4})", desc)
        effective = re.search(r"Kuchga kirish sanasi\s*(\d{2}\.\d{2}\.\d{4})", desc)
        rows.append({"id": m.group(1), "title": (item.findtext("title") or "").strip(), "act_type": act_type,
                     "act_number": number.group(1).strip() if number else "",
                     "act_date": adopted.group(1) if adopted else "", "status": "kuchda",
                     "effective_from": _date(effective.group(1)) if effective else None})
    return rows


def _parse_row(row) -> dict | None:
    link = row.select_one('a.lx_link[href*="/uz/docs/"]')
    m = re.search(r"/uz/docs/(-?\d+)", link.get("href", "")) if link else None
    if not m:
        return None
    badge = row.select_one(".badge")
    parts = [p.strip() for p in (badge.get_text(strip=True) if badge else "").split(",")]
    number = re.search(r"(?:yildagi\s+)?([^\s,]+-son)", parts[1]) if len(parts) > 1 else None
    adopted = _date(parts[1]) if len(parts) > 1 else None
    icon = row.select_one(".lx_act_state i")
    active = bool(icon and "status_code_y" in icon.get("class", []))
    return {"id": m.group(1), "title": link.get_text(strip=True), "act_type": parts[0] if parts else "",
            "act_number": number.group(1) if number else "",
            "act_date": adopted.strftime("%d.%m.%Y") if adopted else "",
            "status": "kuchda" if active else "kuchini_yoqotgan"}


def fetch_recent(client: LexUzClient, since: date, max_pages: int = 30) -> list[dict]:
    """Reyestrning birinchi sahifalari: sahifadagi barcha sanali hujjatlar `since` dan eski bo'lguncha."""
    url = settings.LEX_BASE_URL + SEARCH_URL
    session = client.session
    resp = session.get(url, timeout=60)
    resp.raise_for_status()
    rows: list[dict] = []
    for page in range(1, max_pages + 1):
        soup = BeautifulSoup(resp.text, "lxml")
        page_rows = [r for r in (_parse_row(tr) for tr in soup.select("tr.dd-table__main-item")) if r]
        rows.extend(page_rows)
        dates = [_date(r["act_date"]) for r in page_rows if r["act_date"]]
        if not page_rows or (dates and max(dates) < since) or not soup.select_one("#ucFoundActsControl_LinkButton1"):
            break
        form = {i.get("name"): i.get("value", "") for i in soup.select('input[type="hidden"]') if i.get("name")}
        form.update({"__EVENTTARGET": NEXT_BUTTON, "__EVENTARGUMENT": ""})
        time.sleep(client.delay)
        resp = session.post(url, data=form, timeout=60)
        resp.raise_for_status()
    return rows


def fetch_rss(client: LexUzClient) -> list[dict]:
    resp = client.session.get(settings.LEX_BASE_URL + "/uz/rss", timeout=60)
    resp.raise_for_status()
    resp.encoding = "utf-8"
    return parse_rss(resp.text)


def linked_documents(html: str) -> set[int]:
    """Hujjat sahifasidagi boshqa hujjatlarga havolalar (o'zgartirish kirituvchi hujjat — o'zgartirilgan hujjatga)."""
    return {abs(int(i)) for i in re.findall(r"/(?:uz|ru|oz|en)/docs/(-?\d+)", html)}
