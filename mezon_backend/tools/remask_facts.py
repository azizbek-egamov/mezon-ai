"""Veb hisobotdagi (niqobi ochilgan) faktlarni qayta niqoblab, faqat faktlardan iborat oraliq hisobot yozadi —
`analyze_case --from-report` tahlil va huquqiy bosqichni faktlarni qayta ajratmasdan (pulsiz) takrorlay oladi.

    .venv/Scripts/python tools/remask_facts.py <ish.pdf> <web_report.json> <chiqish.json>
"""
import json
import os
import sys
from pathlib import Path

import django

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
django.setup()

from apps.cases.pdf_text import read_pdf_pages
from apps.cases.pii import PiiVault

sys.stdout.reconfigure(encoding="utf-8")
pdf_path, report_path, out_path = sys.argv[-3:]
report = json.load(open(report_path, encoding="utf-8"))
pages = read_pdf_pages(pdf_path)
vault = PiiVault()
vault.learn_names([p.text for p in pages])  # pipeline bilan bir xil tartib — tokenlar mos keladi
masked_text = "\n".join(vault.mask(p.text) for p in pages)

facts = [{**f, **{k: vault.mask(f[k]) for k in ("summary", "quote", "source")}} for f in report["facts"]]
lost = [f["id"] for f in facts if f["verified"] and " ".join(f["quote"].split()) not in " ".join(masked_text.split())]
out = {"pdf": pdf_path, "pages": report["pages"], "pii_counts": vault.counters, "errors": [], "facts": facts,
       "findings": []}
Path(out_path).write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"{len(facts)} fakt niqoblandi, tokenlar: {vault.counters}; niqoblangan matnda aynan topilmagan iqtiboslar: "
      f"{len(lost)} {lost[:10]}")
