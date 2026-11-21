import sys, time
import numpy as np, pypdfium2 as pdfium
from rapidocr import RapidOCR, LangRec, OCRVersion, ModelType
sys.stdout.reconfigure(encoding="utf-8")
eng = {}
for lang in (LangRec.LATIN, LangRec.CYRILLIC):
    eng[lang.value] = RapidOCR(params={"Rec.lang_type": lang, "Rec.ocr_version": OCRVersion.PPOCRV5,
                                        "Rec.model_type": ModelType.MOBILE, "Global.log_level": "warning"})
pdf = pdfium.PdfDocument("E:/mezon/mezon_backend/fixtures/cases/case_01/case_01_scan.pdf")
for n in (5, 12, 16):
    img = np.asarray(pdf[n - 1].render(scale=200 / 72).to_pil().convert("RGB"))
    for name, e in eng.items():
        t = time.monotonic(); r = e(img); dt = time.monotonic() - t
        sc = float(np.mean(r.scores)) if r.scores else 0
        print(f"--- {n}-varaq {name}: {dt:.1f}s, {len(r.txts or [])} qator, ishonch {sc:.3f}")
        print("   ", " | ".join((r.txts or [])[3:8])[:300])
