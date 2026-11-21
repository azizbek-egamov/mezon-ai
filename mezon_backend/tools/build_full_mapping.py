"""Barcha 966 ta hujjat uchun 100% to'liq toifa va bo'lim xaritasini shakllantirish skripti.
Natija: mezon_backend/data/yurxizmat/full_doc_mapping.json
"""
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "yurxizmat"
CATALOG_FILE = DATA_DIR / "catalog.json"
TREE_FILE = DATA_DIR / "category_tree.json"
OUT_FILE = DATA_DIR / "full_doc_mapping.json"

CATEGORY_CODE_MAP = {
    "contracts": "contracts",
    "statements": "statements",
    "personal-documents": "personal",
    "notarial": "notarial",
    "court": "court",
    "corporate-documents": "corporate"
}

CATEGORY_NAMES = {
    "contracts": "Shartnomalar",
    "statements": "Arizalar",
    "personal": "Shaxsiy tarkibga oid hujjatlar",
    "notarial": "Notarial tasdiqlanadigan hujjatlar",
    "court": "Sudga oid hujjatlar",
    "corporate": "Korporativ hujjatlar"
}

def build_full_mapping():
    with open(CATALOG_FILE, "r", encoding="utf-8") as f:
        catalog = json.load(f)
    with open(TREE_FILE, "r", encoding="utf-8") as f:
        tree_data = json.load(f)
        
    doc_mappings = tree_data.get("doc_mappings", {})
    
    full_map = {}
    
    for item in catalog:
        doc_id = item["id"]
        title = item["title"]
        str_id = str(doc_id)
        
        if str_id in doc_mappings or doc_id in doc_mappings:
            m = doc_mappings.get(str_id) or doc_mappings.get(doc_id)
            top_slug = m["top_slug"]
            top_code = CATEGORY_CODE_MAP.get(top_slug, "other")
            full_map[doc_id] = {
                "doc_id": doc_id,
                "title": title,
                "category_code": top_code,
                "category_name": CATEGORY_NAMES.get(top_code, m["top_category"]),
                "subcategory_name": m["subcategory"],
                "subcategory_slug": m["sub_slug"]
            }
        else:
            # Fallback for remaining items by title heuristics to match exact metismenu sections
            t = title.lower()
            if "shartnoma" in t or "oldi-sotdi" in t or "ijara" in t:
                top_code = "contracts"
                sub_name = "Boshqa turdagi shartnomalar"
                sub_slug = "other-types-of-contracts"
                if "avto" in t or "transport" in t:
                    sub_name = "Avtotransportlarga oid shartnomalar"
                    sub_slug = "contracts-for-auto"
                elif "uy-joy" in t or "mol-mulk" in t or "ko'chmas" in t or "noturar" in t:
                    sub_name = "Ko‘chmas mulkka oid shartnomalar"
                    sub_slug = "real-estate-contracts"
            elif "daʼvo" in t or "da'vo" in t or "sud" in t:
                top_code = "court"
                sub_name = "Daʼvo arizalar"
                sub_slug = "court-claims"
            elif "iltimosnoma" in t:
                top_code = "court"
                sub_name = "Iltimosnomalar"
                sub_slug = "court-petitions"
            elif "shikoyat" in t or "kassatsiya" in t or "appelyatsiya" in t:
                top_code = "court"
                sub_name = "Appelyatsiya, kassatsiya shikoyatlari"
                sub_slug = "appeals-cassation-complaints"
            elif "buyruq" in t or "mehnat" in t:
                top_code = "personal"
                sub_name = "Buyruqlar"
                sub_slug = "commands"
            elif "ishonchnoma" in t:
                top_code = "notarial"
                sub_name = "Ishonchnomalar"
                sub_slug = "notarial-credentials"
            elif "vasiyatnoma" in t:
                top_code = "notarial"
                sub_name = "Vasiyatnomalar"
                sub_slug = "wills"
            elif "talabnoma" in t or "ustav" in t:
                top_code = "corporate"
                sub_name = "Talabnomalar" if "talabnoma" in t else "Ustavlar"
                sub_slug = "corporate-demands" if "talabnoma" in t else "corporate-u"
            elif "farzand" in t or "bola" in t or "nikoh" in t:
                top_code = "statements"
                sub_name = "Bolalarga oid arizalar"
                sub_slug = "for-kids"
            else:
                top_code = "statements"
                sub_name = "Jismoniy shaxslarga oid arizalar"
                sub_slug = "applications-for-individuals"
                
            full_map[doc_id] = {
                "doc_id": doc_id,
                "title": title,
                "category_code": top_code,
                "category_name": CATEGORY_NAMES.get(top_code, "Boshqa"),
                "subcategory_name": sub_name,
                "subcategory_slug": sub_slug
            }
            
    print(f"Total mapped: {len(full_map)} / {len(catalog)}")
    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(full_map, f, ensure_ascii=False, indent=2)
    print(f"Saved: {OUT_FILE}")

if __name__ == "__main__":
    build_full_mapping()

