"""Tayyor hisobotni (data/case_runs/*.json yoki /api/cases/<id>/report) javoblar kaliti bilan solishtiradi.

    .venv/Scripts/python tools/compare_report.py <report.json> fixtures/cases/case_01/answer_key.json
"""
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

from apps.cases.management.commands.analyze_case import match_key

sys.stdout.reconfigure(encoding="utf-8")
report_path, key_path = sys.argv[-2:]
report = json.load(open(report_path, encoding="utf-8"))
key = json.load(open(key_path, encoding="utf-8"))

findings = [SimpleNamespace(**{k: f[k] for k in ("kind", "topic", "pages")}) for f in report["findings"]]
rows = match_key(findings, key)
for r in rows:
    print(f"{'✓' if r['found'] else '✗'} {r['id']:<4} {r['topic'][:60]:<60} kalit {r['key_pages']} -> "
          f"{r['finding_pages']} {r['finding'] or ''}"[:220])
print(f"\nKalit: {sum(r['found'] for r in rows)}/{len(rows)} topildi")

facts = report["facts"]
legal = [f.get("legal") or {} for f in report["findings"]]
assessed = [L for L in legal if L.get("verdict")]
print(f"Faktlar: {len(facts)}, iqtibos tasdiqlangan: {sum(f['verified'] for f in facts)}")
print(f"Topilmalar: {len(report['findings'])} (ziddiyat {sum(f['kind'] == 'contradiction' for f in report['findings'])}, "
      f"protsessual {sum(f['kind'] == 'procedural' for f in report['findings'])})")
print(f"Huquqiy baho: {len(assessed)}, tekshiruvdan o'tgan: {sum((L.get('verification') or {}).get('ok', False) for L in assessed)}, "
      f"qayta baholangan: {sum(bool(L.get('retried')) for L in assessed)}")
print(f"OCR varaqlar: {len(report.get('ocr_pages') or [])}, niqoblandi: {report.get('pii_counts')}")
print(f"Xarajat: ${report.get('cost_usd', 0):.3f}, vaqt: {report.get('seconds', 0):.0f} s, xatolar: {report.get('errors')}")
