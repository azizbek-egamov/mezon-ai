"""Skaner/PDF ni o'qib niqoblaydi va kalitdagi PII qiymatlari (raqamlar, ismlar) LLM ga ketadigan matnda qolgan-qolmaganini tekshiradi."""
import json
import os
import re
import sys
from pathlib import Path
from types import SimpleNamespace

import django

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.cases.pdf_text import read_pdf_pages
from apps.cases.pii import PiiVault, match_key

sys.stdout.reconfigure(encoding="utf-8")
pdf_path, key_path = sys.argv[-2:]
key = json.load(open(key_path, encoding="utf-8"))
pages = read_pdf_pages(pdf_path)
vault = PiiVault()
vault.learn_names([p.text for p in pages])
masked = "\n".join(vault.mask(p.text) for p in pages)
digits = re.sub(r"[\s()+*-]", "", masked)
leaks = [v for v in key["pii_values"] if re.sub(r"\D", "", v) and re.sub(r"\D", "", v) in digits]
words = {match_key(w) for w in re.findall(r"\w+", masked)}
name_leaks = [n for n in key["pii_names"] if match_key(n.split()[0]) in words]
print("raqamli sizish:", leaks or 0)
print("ism sizishi:", name_leaks or 0)
print("tokenlar:", vault.counters)
