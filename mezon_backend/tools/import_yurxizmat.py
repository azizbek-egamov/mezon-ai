"""Yurxizmat.uz dagi barcha hujjatlarni metismenu toifa va bo'limlari bilan import qilish.
6 ta asosiy toifa va 31 ta aniq bo'lim (subcategory) bo'yicha ajratadi.
"""
import json
import logging
import os
import re
import sys
import uuid
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from apps.doc_builder.models import Category, DocumentTemplate, validate_schema, template_variables, ENGINE
from apps.i18n.translit import lat_to_cyr

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("yurxizmat_importer")

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "yurxizmat"
RAW_DIR = DATA_DIR / "raw"
MAPPING_FILE = DATA_DIR / "full_doc_mapping.json"
NAMESPACE = uuid.uuid5(uuid.NAMESPACE_DNS, "yurxizmat.uz")

CODE_TO_CATEGORY = {
    "contracts": Category.CONTRACTS,
    "statements": Category.STATEMENTS,
    "personal": Category.PERSONAL,
    "notarial": Category.NOTARIAL,
    "court": Category.COURT,
    "corporate": Category.CORPORATE,
    "other": Category.OTHER,
}

RU_SUBCAT_MAP = {
    "for-juridical-contracts": "Договоры для юридических лиц",
    "real-estate-contracts": "Договоры по недвижимости",
    "contracts-for-auto": "Договоры по автотранспорту",
    "services-contract": "Договоры купли-продажи и оказания услуг",
    "other-types-of-contracts": "Другие виды договоров",
    "agreements": "Соглашения",
    "deals": "Сделки",
    "power-of-attorneys": "Доверенности",
    "applications-for-legal": "Заявления для юридических лиц",
    "applications-for-individuals": "Заявления для физических лиц",
    "for-kids": "Заявления по детям",
    "petitions": "Ходатайства",
    "personal-applications": "Заявления по личному составу",
    "notifications": "Уведомления",
    "commands": "Приказы",
    "acts": "Акты",
    "personal-agreements": "Соглашения и договоры по личному составу",
    "other-documents": "Другие документы",
    "notarial-applications": "Нотариальные заявления",
    "wills": "Завещания",
    "notarial-credentials": "Нотариальные доверенности",
    "notarial-contracts": "Нотариальные договоры",
    "court-claims": "Исковые заявления",
    "court-applications": "Судебные заявления",
    "corporate-protocols": "Протоколы",
    "appeals-cassation-complaints": "Апелляционные и кассационные жалобы",
    "court-petitions": "Судебные ходатайства",
    "corporate-demands": "Претензии и требования",
    "corporate-u": "Уставы",
    "corporate-acts": "Акты и протоколы",
    "corporate-other-documents": "Другие корпоративные документы",
}

def clean_var_name(label: str, fallback_id: str) -> str:
    text = label.lower().strip()
    text = re.sub(r"[ʻʼ'ʻ`]", "", text)
    text = re.sub(r"[^\w\s]", " ", text)
    words = text.split()[:4]
    base = "_".join(words)
    base = re.sub(r"[^a-z0-9_]", "", base)
    if not base or not base[0].isalpha():
        base = "f"
    else:
        base = base[:32].rstrip("_")
    return f"{base}_{fallback_id}"

def parse_html(html: str, id_to_var_override: dict | None = None) -> tuple[str, list[dict], str, dict]:
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.find("h1") or soup.find("title")
    title = title_el.get_text(strip=True) if title_el else ""
    
    form_tabs = soup.select(".document-form .document-tab")
    fields = []
    id_to_var = {} if id_to_var_override is None else dict(id_to_var_override)
    
    for tab in form_tabs:
        for li in tab.find_all("li"):
            label_el = li.find("label")
            label_text = label_el.get_text(strip=True) if label_el else ""
            inp = li.find(["input", "select", "textarea"])
            if not inp:
                continue
                
            raw_id = inp.get("id", "")
            num_match = re.search(r"\d+", raw_id)
            if not num_match:
                continue
            num_id = num_match.group(0)
            
            tag_name = inp.name
            inp_type = inp.get("type", tag_name)
            
            m_type = "text"
            if tag_name == "textarea":
                m_type = "textarea"
            elif tag_name == "select":
                m_type = "select"
            elif "date" in inp.get("class", []) or "datepicker" in raw_id or inp_type == "date" or "sana" in label_text.lower():
                m_type = "date"
            elif inp_type == "number" or any(w in label_text.lower() for w in ["summa", "narx", "miqdor", "so'm", "to'lov"]):
                m_type = "money"
            elif "telefon" in label_text.lower() or "tel" in label_text.lower():
                m_type = "phone"
            elif "jshshir" in label_text.lower() or "pnfl" in label_text.lower():
                m_type = "jshshir"
                
            options = []
            if tag_name == "select":
                options = [opt.get_text(strip=True) for opt in inp.find_all("option") if opt.get_text(strip=True) and opt.get_text(strip=True) != "—"]
                if not options:
                    m_type = "text"
                    
            if num_id not in id_to_var:
                id_to_var[num_id] = clean_var_name(label_text, num_id)
            var_name = id_to_var[num_id]
            
            fields.append({
                "name": var_name,
                "label": label_text or f"Maydon {num_id}",
                "type": m_type,
                "required": True,
                "options": options if m_type == "select" else None,
            })
            
    preview = soup.find("div", class_="html-preview") or soup.find("div", class_="document-view-scroll")
    if not preview:
        return title, fields, "", id_to_var
        
    for span in preview.find_all(class_=lambda c: c and "structure-" in c):
        classes = span.get("class", [])
        span_id = None
        for c in classes:
            m = re.match(r"structure-(\d+)", c)
            if m:
                span_id = m.group(1)
                break
        if span_id and span_id in id_to_var:
            var = id_to_var[span_id]
            span.replace_with(f"{{{{ {var} }}}}")
        else:
            span.replace_with(span.get_text(strip=True))
            
    lines = []
    for elem in preview.children:
        if isinstance(elem, NavigableString):
            txt = str(elem).strip()
            if txt:
                lines.append(txt)
            continue
            
        if elem.name == "style":
            continue
            
        if elem.name == "table":
            rows = elem.find_all("tr")
            for tr in rows:
                cols = [td.get_text(" ", strip=True) for td in tr.find_all(["td", "th"])]
                cols = [c for c in cols if c]
                if len(cols) == 2:
                    lines.append(f"~ {cols[0]} | {cols[1]}")
                elif len(cols) == 3:
                    lines.append(f"{cols[0]}    {cols[1]}    {cols[2]}")
                elif len(cols) == 1:
                    lines.append(cols[0])
            lines.append("")
            continue
            
        if elem.name in ("h1", "h2", "h3"):
            txt = elem.get_text(" ", strip=True)
            if txt:
                lines.append(f"## {txt}")
                lines.append("")
            continue
            
        if elem.name == "p":
            txt = elem.get_text(" ", strip=True)
            if not txt or txt == " ":
                lines.append("")
                continue
                
            style = elem.get("style", "").lower()
            align = elem.get("align", "").lower()
            is_center = "text-align: center" in style or align == "center"
            is_right = "text-align: right" in style or align == "right"
            
            if is_center and len(txt) < 80:
                lines.append(f"## {txt}")
                lines.append("")
            elif is_right:
                lines.append(f">> {txt}")
            elif re.match(r"^\d+\.\s+[A-ZА-Я]", txt):
                lines.append(f"### {txt}")
            else:
                lines.append(txt)
                
    body_text = "\n".join(lines)
    body_text = re.sub(r"\n{3,}", "\n\n", body_text).strip()
    return title, fields, body_text, id_to_var

def import_all():
    with open(MAPPING_FILE, "r", encoding="utf-8") as f:
        mapping_data = json.load(f)
        
    files = list(RAW_DIR.glob("*.json"))
    logger.info("Import boshlandi: %s ta fayl, metismenu xaritasi yuklandi.", len(files))
    
    total_saved = 0
    errors = 0
    
    for idx, p in enumerate(files, 1):
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        doc_id = data["id"]
        meta = mapping_data.get(str(doc_id)) or mapping_data.get(doc_id)
        if not meta:
            logger.warning("Doc #%s uchun metismenu xaritasi topilmadi", doc_id)
            continue
            
        cat_code = meta["category_code"]
        category = CODE_TO_CATEGORY.get(cat_code, Category.OTHER)
        subcat_oz = meta["subcategory_name"]
        subcat_slug = meta["subcategory_slug"]
        subcat_uz = lat_to_cyr(subcat_oz)
        subcat_ru = RU_SUBCAT_MAP.get(subcat_slug, subcat_oz)
        
        # 1. oz (uz-Latn)
        html_oz = data.get("html_oz", "")
        id_to_var = {}
        if html_oz:
            try:
                title_oz, fields_oz, body_oz, id_to_var = parse_html(html_oz)
                if fields_oz and body_oz:
                    schema_oz = [{"name": f["name"], "label": f["label"], "type": f["type"], "required": True,
                                  **({"options": f["options"]} if f["options"] else {})} for f in fields_oz]
                    validate_schema(schema_oz)
                    ENGINE.from_string(body_oz)
                    
                    uid_oz = uuid.uuid5(NAMESPACE, f"{doc_id}:uz-Latn")
                    DocumentTemplate.objects.update_or_create(
                        id=uid_oz,
                        defaults={
                            "title": title_oz[:255] or data["title"][:255],
                            "category": category,
                            "subcategory": subcat_oz,
                            "subcategory_slug": subcat_slug,
                            "language": "uz-Latn",
                            "description": f"Yurxizmat.uz: {meta['category_name']} > {subcat_oz}.",
                            "form_schema": schema_oz,
                            "body": body_oz,
                            "is_published": True,
                            "version": 1,
                        }
                    )
                    total_saved += 1
            except Exception as e:
                logger.debug("Doc %s [uz-Latn] xato: %s", doc_id, e)
                errors += 1
                
        # 2. uz (uz-Cyrl)
        html_uz = data.get("html_uz", "")
        if html_uz and id_to_var:
            try:
                title_uz, fields_uz, body_uz, _ = parse_html(html_uz, id_to_var_override=id_to_var)
                if fields_uz and body_uz:
                    schema_uz = [{"name": f["name"], "label": f["label"], "type": f["type"], "required": True,
                                  **({"options": f["options"]} if f["options"] else {})} for f in fields_uz]
                    validate_schema(schema_uz)
                    ENGINE.from_string(body_uz)
                    
                    uid_uz = uuid.uuid5(NAMESPACE, f"{doc_id}:uz-Cyrl")
                    DocumentTemplate.objects.update_or_create(
                        id=uid_uz,
                        defaults={
                            "title": title_uz[:255] or title_oz[:255],
                            "category": category,
                            "subcategory": subcat_uz,
                            "subcategory_slug": subcat_slug,
                            "language": "uz-Cyrl",
                            "description": f"Юрхизмат.уз: {lat_to_cyr(meta['category_name'])} > {subcat_uz}.",
                            "form_schema": schema_uz,
                            "body": body_uz,
                            "is_published": True,
                            "version": 1,
                        }
                    )
                    total_saved += 1
            except Exception as e:
                logger.debug("Doc %s [uz-Cyrl] xato: %s", doc_id, e)
                errors += 1
                
        # 3. ru (Russian)
        html_ru = data.get("html_ru", "")
        if html_ru and id_to_var:
            try:
                title_ru, fields_ru, body_ru, _ = parse_html(html_ru, id_to_var_override=id_to_var)
                if fields_ru and body_ru:
                    schema_ru = [{"name": f["name"], "label": f["label"], "type": f["type"], "required": True,
                                  **({"options": f["options"]} if f["options"] else {})} for f in fields_ru]
                    validate_schema(schema_ru)
                    ENGINE.from_string(body_ru)
                    
                    uid_ru = uuid.uuid5(NAMESPACE, f"{doc_id}:ru")
                    DocumentTemplate.objects.update_or_create(
                        id=uid_ru,
                        defaults={
                            "title": title_ru[:255] or title_oz[:255],
                            "category": category,
                            "subcategory": subcat_ru,
                            "subcategory_slug": subcat_slug,
                            "language": "ru",
                            "description": f"Yurxizmat.uz: {subcat_ru}.",
                            "form_schema": schema_ru,
                            "body": body_ru,
                            "is_published": True,
                            "version": 1,
                        }
                    )
                    total_saved += 1
            except Exception as e:
                logger.debug("Doc %s [ru] xato: %s", doc_id, e)
                errors += 1
                
        if idx % 100 == 0 or idx == len(files):
            logger.info("Import progress: %s/%s hujjat qayta ishlandi (Jami saqlangan shablonlar: %s, Xatolar: %s)",
                        idx, len(files), total_saved, errors)
            
    logger.info("IMPORT YAKUNLANDI! Jami saqlangan shablonlar soni: %s ta", total_saved)

if __name__ == "__main__":
    import_all()
