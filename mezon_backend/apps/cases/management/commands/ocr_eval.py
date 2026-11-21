"""OCR sifatini o'lchash: skaner nusxani OCR qilib, asl matnli PDF bilan sahifama-sahifa solishtiradi (CER).

    python manage.py ocr_eval fixtures/cases/case_01/case_01_scan.pdf --reference fixtures/cases/case_01/case_01.pdf

CER = Levenshtein masofasi / asl matn uzunligi (bo'shliqlar va apostroflar normallashtirilgandan keyin).
"CER*" — o'zbek kirill harflari (ў қ ғ ҳ ↔ у к г х) farqi hisobga olinmagan holda: model lug'atidagi ma'lum
cheklovni boshqa xatolardan ajratish uchun.
"""
import re
import time

from django.core.management.base import BaseCommand

from apps.cases.pdf_text import read_pdf_pages
from apps.lex_corpus.normalize import normalize_apostrophes

UZ_CYR_FOLD = str.maketrans("ўқғҳЎҚҒҲ", "укгхУКГХ")


def normalize(text: str) -> str:
    text = normalize_apostrophes(text).replace("“", '"').replace("”", '"').replace("«", '"').replace("»", '"')
    return re.sub(r"\s+", " ", text).strip()


def levenshtein(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return prev[-1]


class Command(BaseCommand):
    help = "OCR sifatini asl matn bilan solishtiradi (CER)"

    def add_arguments(self, parser):
        parser.add_argument("scan")
        parser.add_argument("--reference", required=True)

    def handle(self, *args, scan, reference, **opts):
        t0 = time.monotonic()
        ocr_pages = read_pdf_pages(scan)
        seconds = time.monotonic() - t0
        ref_pages = read_pdf_pages(reference, ocr=False)
        total_err = total_err_fold = total_len = 0
        for o, r in zip(ocr_pages, ref_pages):
            hyp, ref = normalize(o.text), normalize(r.text)
            err = levenshtein(hyp, ref)
            err_fold = levenshtein(hyp.translate(UZ_CYR_FOLD), ref.translate(UZ_CYR_FOLD))
            total_err, total_err_fold, total_len = total_err + err, total_err_fold + err_fold, total_len + len(ref)
            flag = " ⚠ past ishonch" if o.low_quality else ""
            self.stdout.write(f"{o.number:>3}-v  {o.source:<4} ishonch {o.ocr_confidence or 0:.3f}  "
                              f"CER {err / max(1, len(ref)):6.2%}  CER* {err_fold / max(1, len(ref)):6.2%}{flag}"
                              f"{'  | ' + o.ocr_warning if o.ocr_warning else ''}")
        self.stdout.write(f"\nJami: CER {total_err / total_len:.2%} | CER* (ў қ ғ ҳ hisobsiz) {total_err_fold / total_len:.2%} | "
                          f"OCR {seconds:.0f} s ({seconds / len(ocr_pages):.1f} s/varaq)")
