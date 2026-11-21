"""
Lex.uz Qonun Hujjatlari ID va Metadatalarini yig'uvchi (Scraper).
Texnologiya: Python, requests, BeautifulSoup4.
"""

import sys
import re
import json
import time
import argparse
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional

# Windows konsolida UTF-8 bilan ishlash
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

BASE_URL = "https://lex.uz"

FORM_IDS = {
    "qonun": "3968",      # Faqat O'zbekiston Respublikasi Qonunlari (~1,586 ta)
    "kodeks": "3964",     # Kodekslar (~28 ta)
    "farmon": "3973",     # Prezident farmonlari
    "qaror": "3972",      # Qarorlar
    "nat": "",            # Barcha milliy qonunchilik hujjatlari (~28,450 ta)
    "unique": "UNIQUE"    # Yagona qidiruv - Lex.uz dagi mutlaqo barcha hujjatlar (~57,950 ta)
}


class LexScraper:
    def __init__(self, doc_type: str = "qonun", lang: str = "4", delay: float = 0.5):
        """
        :param doc_type: 'qonun', 'kodeks', 'farmon', 'qaror', 'nat', 'unique'
        :param lang: '4' (O'zbekcha lotin), '3' (O'zbekcha kirill), '1' (Ruscha), '' (Barchasi)
        :param delay: So'rovlar orasidagi kutish vaqti (soniya)
        """
        self.doc_type = doc_type.lower()
        self.form_id = FORM_IDS.get(self.doc_type, "")
        self.lang = lang
        self.delay = delay
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'uz,ru;q=0.9,en;q=0.8'
        })

    def _get_start_url(self) -> str:
        if self.doc_type == "unique":
            params = []
            if self.lang:
                params.append(f"lang={self.lang}")
            query_string = "&".join(params)
            return f"{BASE_URL}/uz/search/unique{('?' + query_string) if query_string else ''}"

        params = []
        if self.lang:
            params.append(f"lang={self.lang}")
        if self.form_id:
            params.append(f"form_id={self.form_id}")
        query_string = "&".join(params)
        return f"{BASE_URL}/uz/search/nat{('?' + query_string) if query_string else ''}"

    def _extract_aspnet_fields(self, soup: BeautifulSoup) -> Dict[str, str]:
        fields = {}
        for inp in soup.select('input[type="hidden"]'):
            name = inp.get('name')
            val = inp.get('value', '')
            if name:
                fields[name] = val
        return fields

    def _parse_row(self, row) -> Optional[Dict]:
        link_el = row.select_one('a.lx_link[href*="/uz/docs/"]')
        if not link_el:
            return None
        
        href = link_el.get('href', '')
        match = re.search(r'/uz/docs/(-?\d+)', href)
        if not match:
            return None
        doc_id = match.group(1)

        title = link_el.get_text(strip=True)
        badge = row.select_one('.badge')
        badge_text = badge.get_text(strip=True) if badge else ""

        doc_type_name = ""
        act_date = ""
        act_number = ""
        if badge_text:
            parts = [p.strip() for p in badge_text.split(',')]
            if len(parts) >= 1:
                doc_type_name = parts[0]
            if len(parts) >= 2:
                date_match = re.search(r'(\d{2}\.\d{2}\.\d{4})', parts[1])
                if date_match:
                    act_date = date_match.group(1)
                num_match = re.search(r'(?:yildagi\s+)?([^\s,]+-son)', parts[1])
                if num_match:
                    act_number = num_match.group(1)

        status_icon = row.select_one('.lx_act_state i')
        is_active = status_icon and ("status_code_y" in status_icon.get('class', []))

        return {
            "id": doc_id,
            "title": title,
            "act_type": doc_type_name,
            "act_number": act_number,
            "act_date": act_date,
            "status": "kuchda" if is_active else "kuchini_yoqotgan",
            "url": f"{BASE_URL}/uz/docs/{doc_id}",
            "passport_url": f"{BASE_URL}/uz/doc-passport/{doc_id}",
            "pdf_url": f"{BASE_URL}/uz/pdfs/{doc_id}",
            "word_url": f"{BASE_URL}/uz/docs/{doc_id}?type=doc"
        }

    def _extract_page_docs(self, soup: BeautifulSoup) -> List[Dict]:
        results = []
        rows = soup.select('tr.dd-table__main-item')
        for row in rows:
            doc = self._parse_row(row)
            if doc:
                results.append(doc)
        return results

    def _get_total_count(self, soup: BeautifulSoup) -> Optional[int]:
        title_el = soup.select_one('.refind__result-export__title')
        if title_el:
            m = re.search(r'(\d[\d\s]*\d)\s*hujjat\s+topildi', title_el.get_text())
            if m:
                return int(m.group(1).replace(' ', ''))
        return None

    def _save_json(self, docs: List[Dict], filepath: str):
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(docs, f, ensure_ascii=False, indent=2)

    def scrape(self, max_pages: Optional[int] = None, output_file: str = "lex_documents.json"):
        start_url = self._get_start_url()
        print(f"[*] Boshlang'ich URL: {start_url}")
        print(f"[*] Hujjat turi: '{self.doc_type}' | Til: '{self.lang or 'Hammasi'}'")

        all_docs = []
        seen_ids = set()

        # 1-sahifani yuklab olish
        resp = self.session.get(start_url, timeout=20)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, 'html.parser')

        total_docs = self._get_total_count(soup)
        if total_docs is not None:
            print(f"[i] Jami topilgan hujjatlar soni: {total_docs:,} ta")
        else:
            print("[!] Jami soni aniqlanmadi, sahifalar bo'ylab qidirilmoqda...")

        page = 1
        try:
            while True:
                docs = self._extract_page_docs(soup)
                for d in docs:
                    if d['id'] not in seen_ids:
                        seen_ids.add(d['id'])
                        all_docs.append(d)

                print(f"  [+] Sahifa {page:4d}: {len(docs)} ta hujjat o'qildi (Jami: {len(all_docs)})")

                # Har 20 sahifada faylga oraliq saqlash (checkpoint)
                if page % 20 == 0:
                    self._save_json(all_docs, output_file)

                if max_pages and page >= max_pages:
                    print(f"[i] Belgilangan chegara sahifaga ({max_pages}) yetildi.")
                    break

                # Keyingi sahifa bormi tekshirish
                next_btn = soup.select_one('#ucFoundActsControl_LinkButton1')
                if not next_btn:
                    print("[i] Keyingi sahifa tugmasi topilmadi. Oxirgi sahifaga yetildi.")
                    break

                # ASP.NET WebForms postback
                form_data = self._extract_aspnet_fields(soup)
                form_data['__EVENTTARGET'] = 'ucFoundActsControl$LinkButton1'
                form_data['__EVENTARGUMENT'] = ''

                time.sleep(self.delay)
                page += 1

                try:
                    post_resp = self.session.post(start_url, data=form_data, timeout=20)
                    post_resp.raise_for_status()
                    soup = BeautifulSoup(post_resp.text, 'html.parser')
                except Exception as e:
                    print(f"[!] {page}-sahifani yuklashda xatolik: {e}")
                    time.sleep(2)
                    try:
                        post_resp = self.session.post(start_url, data=form_data, timeout=30)
                        soup = BeautifulSoup(post_resp.text, 'html.parser')
                    except Exception as retry_e:
                        print(f"[X] Qayta urinishda ham xatolik: {retry_e}. To'xtatildi.")
                        break

        except KeyboardInterrupt:
            print("\n[!] Foydalanuvchi tomonidan to'xtatildi. Yig'ilgan ma'lumotlar saqlanmoqda...")

        print(f"\n[✓] Parsing yakunlandi! Jami yig'ilgan noyob hujjatlar: {len(all_docs)} ta.")
        self._save_json(all_docs, output_file)
        print(f"[✓] Natijalar '{output_file}' fayliga muvaffaqiyatli saqlandi.")
        return all_docs


def main():
    parser = argparse.ArgumentParser(description="Lex.uz qonun hujjatlari ID larini yig'ish dasturi")
    parser.add_argument("--type", choices=["qonun", "kodeks", "farmon", "qaror", "nat", "unique"], default="unique",
                        help="Hujjat turi: unique (57950 ta - barcha hujjatlar), qonun (1586 ta - faqat qonunlar), nat (28450 ta - milliy qonunchilik)")
    parser.add_argument("--lang", default="", help="Til kodi: 4=O'zbekcha(lotin), 3=Kirill, 1=Ruscha, ''=barchasi (default: bo'sh - barcha tillar)")
    parser.add_argument("--pages", type=int, default=None, help="Maksimal tekshiriladigan sahifalar soni (test uchun)")
    parser.add_argument("--output", default="lex_all_documents.json", help="Chiqariladigan JSON fayli")
    parser.add_argument("--delay", type=float, default=0.5, help="So'rovlar orasidagi kutish (sekund)")

    args = parser.parse_args()

    scraper = LexScraper(doc_type=args.type, lang=args.lang, delay=args.delay)
    scraper.scrape(max_pages=args.pages, output_file=args.output)


if __name__ == "__main__":
    main()
