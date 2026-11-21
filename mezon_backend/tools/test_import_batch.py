"""50 ta yuklangan hujjatni sinov tariqasida parse qilib tekshirish skripti."""
import json
import os
import re
import sys
from pathlib import Path
from bs4 import BeautifulSoup, NavigableString

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from apps.doc_builder.models import validate_schema, template_variables, ENGINE

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "yurxizmat" / "raw"

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

def parse_html_to_template(html: str, lang: str):
    soup = BeautifulSoup(html, "html.parser")
    title_el = soup.find("h1") or soup.find("title")
    title = title_el.get_text(strip=True) if title_el else ""
    
    # 1. Parse fields from .document-form
    form_tabs = soup.select(".document-form .document-tab")
    fields = []
    id_to_var = {}
    
    for tab in form_tabs:
        tab_header = tab.find(class_="document-tab-header")
        tab_name = tab_header.get_text(strip=True) if tab_header else ""
        
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
                    
            var_name = clean_var_name(label_text, num_id)
            id_to_var[num_id] = var_name
            
            fields.append({
                "name": var_name,
                "label": label_text or f"Maydon {num_id}",
                "type": m_type,
                "required": True,
                "options": options if m_type == "select" else None,
            })
            
    # 2. Parse body from .html-preview
    preview = soup.find("div", class_="html-preview") or soup.find("div", class_="document-view-scroll")
    if not preview:
        return title, fields, ""
        
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
    return title, fields, body_text

def test_batch():
    files = list(RAW_DIR.glob("*.json"))
    passed = 0
    failed = 0
    
    for p in files:
        with open(p, "r", encoding="utf-8") as f:
            data = json.load(f)
            
        doc_id = data["id"]
        html_oz = data.get("html_oz", "")
        if not html_oz:
            continue
            
        try:
            title, fields, body = parse_html_to_template(html_oz, "oz")
            if not fields or not body:
                print(f"Doc {doc_id}: Empty fields or body!")
                failed += 1
                continue
                
            schema = [{"name": f["name"], "label": f["label"], "type": f["type"], "required": True,
                       **({"options": f["options"]} if f["options"] else {})} for f in fields]
            validate_schema(schema)
            ENGINE.from_string(body)
            
            names = {f["name"] for f in schema}
            vars_in_body = template_variables(body)
            unknown = vars_in_body - names
            if unknown:
                print(f"Doc {doc_id}: Unknown vars {unknown}")
                failed += 1
                continue
                
            passed += 1
        except Exception as e:
            print(f"Doc {doc_id} Error: {e}")
            failed += 1
            
    print(f"\n--- BATCH TEST RESULT: Passed: {passed}/50, Failed: {failed}/50 ---")

if __name__ == "__main__":
    test_batch()
