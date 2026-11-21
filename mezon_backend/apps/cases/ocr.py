"""Skaner qilingan (matn qatlamisiz) sahifalar uchun OCR: RapidOCR (PaddleOCR PP-OCRv5 modellari, ONNX, CPU).

PaddleOCR ning o'zi (paddlepaddle) Python 3.14 uchun chiqarilmagan, RapidOCR esa xuddi shu modellarni onnxruntime
orqali ishlatadi. CPU da ishlaydi — GPU (LLM, embedding) bilan to'qnashmaydi.

Tanlash: avval lotin modeli; ishonch past yoki matnda kirill ko'p bo'lsa — kirill modeli ham, yaxshirog'i olinadi.
Kirill modelining lug'atida o'zbekcha ў қ ғ ҳ yo'q — ular у к г х bo'lib chiqadi; `cyr_fix` ularni lex.uz
lug'ati bo'yicha tiklaydi (ismlar tiklanmaydi — sahifa baribir ogohlantirish bilan belgilanadi).
Qiyshiq skaner (telefon bilan olingan rasm) o'qishdan oldin to'g'rilanadi (`deskew`).
Qo'lyozma va muhr ustidagi matnni yomon o'qiydi.
"""
import logging
import re
import threading
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
from django.conf import settings

from apps.lex_corpus.normalize import normalize_apostrophes
from apps.rag.llm import get_llm

from .cyr_fix import fix_uzbek_cyrillic

logger = logging.getLogger(__name__)

DPI = 200
LATIN_ACCEPT = 0.95       # lotin modeli shu ishonchdan yuqori bo'lsa, kirill sinab ko'rilmaydi
UPSIDE_DOWN_CHECK = 0.75  # bundan past ishonch — sahifa 180° aylantirib qayta o'qiladi
_lock = threading.Lock()  # onnxruntime sessiyalari — bitta oqimda

LEGAL_VISION_SYSTEM_PROMPT = (
    "Sen O'zbekiston sud va tergov hujjatlarini so'zma-so'z ko'chiruvchi professional yuridik transkriptorsan.\n"
    "Vazifang — taqdim etilgan rasmdagi barcha matnlarni (bosma matn, qo'lyozma, jadvallar, muhrlar) "
    "100% ASLIDAGIDEK BIRGA-BIR ko'chirish.\n\n"
    "QAT'IY QOIDALAR:\n"
    "1. O'zingdan bitta ham so'z qo'shma, tahrir qilma, gap tuzilishini o'zgartirma va qisqartirma.\n"
    "2. Rasmdagi matn qaysi tilda va alifboda bo'lsa, aynan o'sha alifboda yoz:\n"
    "   - O'zbek kirill alifbosi (ў, қ, ғ, ҳ) aynan rasmda yozilganidek qolsin.\n"
    "   - O'zbek lotin alifbosi (oʻ, gʻ, sh, ch, tutuq belgisi) aynan rasmda yozilganidek qolsin.\n"
    "3. Qo'lda yozilgan barcha yozuvlarni (tergovchi yoki fuqaroning qo'lyozmasi) [QO'LYOZMA: ...] blokiga ol.\n"
    "4. Muhr va shtamplarni [MUHR: ... yozuvlari] deb alohida ko'rsat.\n"
    "5. Jadvallarni toza Markdown jadval ko'rinishida ifodala.\n"
    "6. Agar biror so'zni dog' yoki xiralik sabab mutlaqo o'qib bo'lmasa, taxmin qilma, [o'qib bo'lmadi] deb yoz."
)


@dataclass
class OcrResult:
    text: str
    confidence: float     # qatorlar ishonchining o'rtachasi (0..1)
    script: str           # "latin" | "cyrillic"
    warning: str = ""
    engine: str = "rapidocr"  # "rapidocr" | "gemini_vision"
    has_handwriting: bool = False
    stamps: list[str] = field(default_factory=list)
    cost_usd: float = 0.0


@lru_cache(maxsize=2)
def _engine(lang: str):
    from rapidocr import LangRec, ModelType, OCRVersion, RapidOCR  # og'ir import — faqat OCR kerak bo'lganda

    # Global.use_cls=False: qator yo'nalishi modeli (Xitoy matni uchun o'rgatilgan) qiyshiq lotin qatorlarini 180°
    # aylantirib, axlat matnga aylantirardi — case_01 skanerida to'liq kenglikdagi qatorlar yo'qolgan (CER 9% -> pastga).
    # To'liq teskari sahifa ocr_image da butun sahifani aylantirib qayta o'qish bilan hal qilinadi.
    return RapidOCR(params={"Rec.lang_type": LangRec(lang), "Rec.ocr_version": OCRVersion.PPOCRV5,
                            "Rec.model_type": ModelType.MOBILE, "Global.log_level": "warning",
                            "Global.use_cls": False})


def _lines(result) -> tuple[str, float]:
    """Qutilarni o'qish tartibida (yuqoridan pastga, chapdan o'ngga) qatorlarga yig'adi."""
    if not result.txts:
        return "", 0.0
    items = []
    for box, txt, score in zip(result.boxes, result.txts, result.scores):
        ys, xs = [p[1] for p in box], [p[0] for p in box]
        items.append((min(ys), max(ys), min(xs), txt, score))
    items.sort(key=lambda t: (t[0], t[2]))
    lines: list[list] = []
    for top, bottom, left, txt, _ in items:
        mid = (top + bottom) / 2
        if lines and abs(mid - lines[-1][0]) < (bottom - top) * 0.6:
            lines[-1][1].append((left, txt))
        else:
            lines.append([mid, [(left, txt)]])
    text = "\n".join(" ".join(t for _, t in sorted(parts)) for _, parts in lines)
    return text, float(np.mean(result.scores))


def _cyrillic_share(text: str) -> float:
    letters = re.findall(r"[A-Za-zА-Яа-яЁё]", text)
    return sum(1 for c in letters if "Ѐ" <= c <= "ӿ") / max(1, len(letters))


MAX_SKEW = 12.0           # shu burchakdan (daraja) katta qiyshiqlik izlanmaydi
MIN_SKEW = 0.4            # bundan kichik burchak to'g'rilanmaydi (interpolyatsiya matnni xiralashtirmasin)
SKEW_SIDE = 900           # burchak kichraytirilgan nusxada izlanadi (tezlik uchun)


def estimate_skew(img: np.ndarray) -> float:
    """Sahifani to'g'rilash uchun burilish burchagi (daraja, soat strelkasiga qarshi musbat; cv2.getRotationMatrix2D
    bilan mos): gorizontal proyeksiya profilining dispersiyasi qatorlar to'g'ri turganda eng katta bo'ladi."""
    import cv2

    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY) if img.ndim == 3 else img
    scale = SKEW_SIDE / max(gray.shape)
    if scale < 1:
        gray = cv2.resize(gray, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
    _, ink = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    if ink.mean() < 1:     # deyarli bo'sh sahifa
        return 0.0
    h, w = ink.shape
    center = (w / 2, h / 2)

    def sharpness(angle: float) -> float:
        rotated = cv2.warpAffine(ink, cv2.getRotationMatrix2D(center, angle, 1.0), (w, h), flags=cv2.INTER_NEAREST)
        return float(np.var(rotated.sum(axis=1, dtype=np.float64)))

    coarse = max(np.arange(-MAX_SKEW, MAX_SKEW + 0.01, 1.0), key=sharpness)
    return float(max(np.arange(coarse - 1.0, coarse + 1.01, 0.1), key=sharpness))


def deskew(img: np.ndarray) -> np.ndarray:
    """Qiyshiq sahifani to'g'rilaydi; burchak MIN_SKEW dan kichik bo'lsa — o'zgarishsiz."""
    import cv2

    angle = estimate_skew(img)
    if abs(angle) < MIN_SKEW:
        return img
    h, w = img.shape[:2]
    matrix = cv2.getRotationMatrix2D((w / 2, h / 2), angle, 1.0)
    return cv2.warpAffine(img, matrix, (w, h), flags=cv2.INTER_CUBIC, borderValue=(255, 255, 255))


def img_to_jpeg_bytes(img: np.ndarray, quality: int = 90) -> bytes:
    """NumPy tasvirni JPEG baytlariga aylantiradi."""
    import cv2

    success, buf = cv2.imencode(".jpg", cv2.cvtColor(img, cv2.COLOR_RGB2BGR) if img.ndim == 3 else img,
                                [cv2.IMWRITE_JPEG_QUALITY, quality])
    if success:
        return buf.tobytes()
    from PIL import Image
    import io

    bio = io.BytesIO()
    Image.fromarray(img).save(bio, format="JPEG", quality=quality)
    return bio.getvalue()


def ocr_image_vision(img: np.ndarray) -> OcrResult:
    """Rasmni Gemini Vision (yoki faol multimodal LLM) orqali transkripsiya qiladi."""
    jpeg_bytes = img_to_jpeg_bytes(img)
    llm = get_llm()
    if not hasattr(llm, "transcribe_image"):
        raise NotImplementedError("LLM provayderida transcribe_image yo'q")
    raw_text, cost = llm.transcribe_image(jpeg_bytes, mime_type="image/jpeg", system=LEGAL_VISION_SYSTEM_PROMPT)
    clean_txt = normalize_apostrophes(raw_text.strip())
    has_hw = bool(re.search(r"\[QO['ʻʼ]LYOZMA:", clean_txt, re.I))
    stamps = re.findall(r"\[MUHR:\s*([^\]]+)\]", clean_txt, re.I)
    cyr_share = _cyrillic_share(clean_txt)
    script = "cyrillic" if cyr_share > 0.5 else "latin"
    return OcrResult(
        text=clean_txt,
        confidence=0.99,
        script=script,
        engine="gemini_vision",
        has_handwriting=has_hw,
        stamps=stamps,
        cost_usd=cost,
    )


def ocr_image_smart(img: np.ndarray, force_vision: bool = False) -> OcrResult:
    """Smart gibrid OCR: deskew qilingan tasvir.
    settings.CASE_VISION_OCR yoqilgan bo'lsa yoki force_vision bo'lsa — Gemini Vision,
    xatoda yoki o'chiq bo'lsa — lokal RapidOCR ga zaxira sifatida o'tadi."""
    img = deskew(img)
    use_vision = force_vision or getattr(settings, "CASE_VISION_OCR", True)
    if use_vision:
        try:
            return ocr_image_vision(img)
        except Exception as e:
            logger.warning("Vision OCR xatosi (%s) — lokal RapidOCR ga o'tilmoqda", e)
    return ocr_image(img)


def ocr_image(img: np.ndarray) -> OcrResult:
    img = deskew(img)
    result = _ocr_upright(img)
    if result.confidence < UPSIDE_DOWN_CHECK:  # sahifa teskari skaner qilingan bo'lishi mumkin
        rotated = _ocr_upright(np.ascontiguousarray(img[::-1, ::-1]))
        if rotated.confidence > result.confidence:
            return rotated
    return result


def _ocr_upright(img: np.ndarray) -> OcrResult:
    with _lock:
        latin_text, latin_conf = _lines(_engine("latin")(img))
        if latin_conf >= LATIN_ACCEPT:
            return OcrResult(normalize_apostrophes(latin_text), latin_conf, "latin")
        cyr_text, cyr_conf = _lines(_engine("cyrillic")(img))
    if cyr_conf > latin_conf and _cyrillic_share(cyr_text) > 0.5:
        warning = ""
        if re.search(r"\b(va|uchun|bilan)\b|[ўқғҳ]", latin_text + cyr_text) or re.search(
                r"\b(ва|учун|билан|йил|куни)\b", cyr_text, re.I):
            cyr_text, fixed = fix_uzbek_cyrillic(cyr_text)
            warning = (f"Oʻzbek kirill matni: ў қ ғ ҳ harflari lugʻat boʻyicha tiklandi ({fixed} soʻz); ismlar va "
                       f"lugʻatda yoʻq soʻzlarda у к г х boʻlib qolgan boʻlishi mumkin")
        return OcrResult(cyr_text, cyr_conf, "cyrillic", warning)
    return OcrResult(normalize_apostrophes(latin_text), latin_conf, "latin")


def render_page(pdf_path: str, index: int):
    import pypdfium2 as pdfium

    pdf = pdfium.PdfDocument(pdf_path)
    try:
        return np.asarray(pdf[index].render(scale=DPI / 72).to_pil().convert("RGB"))
    finally:
        pdf.close()
