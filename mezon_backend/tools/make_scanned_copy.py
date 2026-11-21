"""Matnli PDF dan "skaner nusxa" yasash — OCR ni sinash uchun (matn qatlamisiz, faqat rasm).

Har bir sahifa 150 DPI da rasmga aylantiriladi, kulrang, ±1.2° qiyshiqlik, shovqin, biroz xiralik va JPEG siqish
qo'shiladi (oddiy ofis skaneri kabi).

    .venv/Scripts/python tools/make_scanned_copy.py fixtures/cases/case_01/case_01.pdf fixtures/cases/case_01/case_01_scan.pdf
"""
import io
import random
import sys

import numpy as np
import pypdfium2 as pdfium
from PIL import Image, ImageFilter

DPI = 150


def scan_like(img: Image.Image, rng: random.Random) -> Image.Image:
    img = img.convert("L")
    img = img.rotate(rng.uniform(-1.2, 1.2), resample=Image.BICUBIC, expand=False, fillcolor=255)
    img = img.filter(ImageFilter.GaussianBlur(radius=0.6))
    arr = np.asarray(img, dtype=np.float32)
    arr = arr * rng.uniform(0.92, 0.98) + np.random.default_rng(rng.randint(0, 10_000)).normal(0, 9, arr.shape)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    buf = io.BytesIO()
    img.save(buf, "JPEG", quality=60)  # skanerlarning JPEG artefaktlari
    return Image.open(io.BytesIO(buf.getvalue()))


def main(src: str, dst: str) -> None:
    rng = random.Random(42)  # takrorlanadigan natija
    pdf = pdfium.PdfDocument(src)
    pages = [scan_like(pdf[i].render(scale=DPI / 72).to_pil(), rng) for i in range(len(pdf))]
    pages[0].save(dst, "PDF", resolution=DPI, save_all=True, append_images=pages[1:])
    print(f"{dst}: {len(pages)} varaq (faqat rasm, {DPI} DPI)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2])
