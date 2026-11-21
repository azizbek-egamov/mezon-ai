"""Ish hujjatlarini qabul qilish: bir nechta fayl (PDF, DOCX, JPG/PNG) -> bitta PDF (9-bosqich).

Tahlil zanjiri, sahifa ko'rsatkichi ("varaq" tugmalari) va shifrlangan saqlash bitta PDF ga tayanadi, shuning uchun
yuklangan fayllar yuklash paytida ketma-ket bitta PDF ga birlashtiriladi; varaq raqamlari fayllar bo'ylab davom
etadi. Har bir faylning varaqlar oralig'i `sources` da saqlanadi.

  PDF   — sahifalar o'z holicha (matn qatlami bor/yo'qligi keyin pdf_text da aniqlanadi);
  JPG/PNG — bitta sahifa, matn qatlamisiz (OCR qiladi); telefon rasmining EXIF yo'nalishi qo'llanadi;
  DOCX  — abzats va jadval matni TNR 14 bilan matn qatlamli PDF ga chiziladi (OCR kerak emas). Hujjat ichidagi
          rasmlar, sarlavha/pastlik va izohlar olinmaydi — `warnings` da aytiladi.
"""
import io
from dataclasses import dataclass, field
from pathlib import PurePath

from django.utils.translation import gettext as _
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

IMAGE_EXTS = {".jpg", ".jpeg", ".png"}
ACCEPTED_EXTS = {".pdf", ".docx"} | IMAGE_EXTS
MAX_IMAGE_PIXELS = 60_000_000   # ~ 7750 x 7750; undan kattasi rad etiladi (xotira)
IMAGE_PDF_DPI = 200


class IntakeError(ValueError):
    """Foydalanuvchiga ko'rsatiladigan xato matni."""


@dataclass
class SourceFile:
    name: str
    kind: str            # pdf | docx | image
    first_page: int
    last_page: int

    def to_dict(self) -> dict:
        return {"name": self.name, "kind": self.kind, "first_page": self.first_page, "last_page": self.last_page}


@dataclass
class Intake:
    pdf: bytes
    pages: int
    sources: list[SourceFile] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _pdf_pages(data: bytes, name: str) -> list:
    try:
        reader = PdfReader(io.BytesIO(data))
        encrypted = reader.is_encrypted
        pages = [] if encrypted else list(reader.pages)
    except (PdfReadError, ValueError, OSError):
        raise IntakeError(_("%(name)s: PDF faylni oʻqib boʻlmadi") % {"name": name}) from None
    if encrypted:
        raise IntakeError(_("%(name)s: PDF parol bilan himoyalangan") % {"name": name})
    return pages


def _image_to_pdf(data: bytes, name: str) -> bytes:
    from PIL import Image, ImageOps, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(data)) as raw:
            if raw.width * raw.height > MAX_IMAGE_PIXELS:
                raise IntakeError(_("%(name)s: rasm juda katta (%(w)s×%(h)s)") % {"name": name, "w": raw.width, "h": raw.height})
            img = ImageOps.exif_transpose(raw).convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise IntakeError(_("%(name)s: rasmni oʻqib boʻlmadi") % {"name": name}) from None
    out = io.BytesIO()
    img.save(out, "PDF", resolution=IMAGE_PDF_DPI)
    return out.getvalue()


def _docx_blocks(data: bytes, name: str):
    """DOCX matni (abzatslar va jadvallar hujjatdagi tartibda) -> doc_builder Block lari; (bloklar, ogohlantirishlar)."""
    from docx import Document
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    from apps.doc_builder.writers import Block

    try:
        doc = Document(io.BytesIO(data))
    except Exception:  # python-docx turli xatolarni (zipfile, KeyError, ...) tashlaydi
        raise IntakeError(_("%(name)s: DOCX faylni oʻqib boʻlmadi") % {"name": name}) from None
    blocks, warnings = [], []
    for child in doc.element.body.iterchildren():
        tag = child.tag.rsplit("}", 1)[-1]
        if tag == "p":
            text = Paragraph(child, doc).text.strip()
            if text:
                blocks.append(Block("p", text))
        elif tag == "tbl":
            for row in Table(child, doc).rows:
                cells = []
                for cell in row.cells:
                    if not cells or cell.text != cells[-1]:  # birlashtirilgan katakchalar takrorlanmasin
                        cells.append(cell.text.strip().replace("\n", " "))
                line = " | ".join(c for c in cells if c)
                if line:
                    blocks.append(Block("bullet", line))
    if not blocks:
        raise IntakeError(_("%(name)s: DOCX da matn topilmadi") % {"name": name})
    return blocks, warnings


def _extract_docx_images(data: bytes, doc_name: str) -> list[tuple[str, bytes]]:
    """DOCX ichiga joylangan barcha rasmlarni ajratib oladi."""
    from docx import Document

    try:
        doc = Document(io.BytesIO(data))
    except Exception:
        return []

    images = []
    idx = 1
    for rel in doc.part.rels.values():
        if "image" in getattr(rel, "target_ref", "").lower():
            try:
                blob = rel.target_part.blob
                ext = PurePath(rel.target_ref).suffix.lower() or ".png"
                img_name = f"{PurePath(doc_name).stem}_rasm_{idx}{ext}"
                images.append((img_name, blob))
                idx += 1
            except Exception:
                pass
    return images


def _docx_to_pdf(data: bytes, name: str) -> tuple[bytes, list[str]]:
    from apps.doc_builder.writers import to_pdf

    blocks, warnings = _docx_blocks(data, name)
    return to_pdf(blocks), warnings


def build_case_pdf(files: list[tuple[str, bytes]]) -> Intake:
    """files: [(fayl nomi, mazmuni)] yuklangan tartibda -> bitta PDF, varaqlar soni, fayllar bo'yicha oraliq."""
    if not files:
        raise IntakeError(_("Fayl tanlang"))
    if len(files) == 1 and PurePath(files[0][0]).suffix.lower() == ".pdf":
        name, data = files[0]   # bitta PDF — o'zgarishsiz saqlanadi (qayta yozish formani/xatcho'plarni buzishi mumkin)
        count = len(_pdf_pages(data, name))
        return Intake(pdf=data, pages=count, sources=[SourceFile(PurePath(name).name, "pdf", 1, count)])
    writer = PdfWriter()
    sources: list[SourceFile] = []
    warnings: list[str] = []
    for name, data in files:
        ext = PurePath(name).suffix.lower()
        if ext not in ACCEPTED_EXTS:
            raise IntakeError(_("%(name)s: faqat PDF, DOCX, JPG yoki PNG qabul qilinadi") % {"name": name})
        if ext == ".pdf":
            kind, pages = "pdf", _pdf_pages(data, name)
            first = len(writer.pages) + 1
            for page in pages:
                writer.add_page(page)
            sources.append(SourceFile(PurePath(name).name, kind, first, len(writer.pages)))
        elif ext == ".docx":
            kind = "docx"
            pdf, extra = _docx_to_pdf(data, name)
            warnings += extra
            pages = _pdf_pages(pdf, name)
            first = len(writer.pages) + 1
            for page in pages:
                writer.add_page(page)
            sources.append(SourceFile(PurePath(name).name, kind, first, len(writer.pages)))

            # DOCX ichidagi ichki rasmlarni ham ajratib olib alohida varaq sifatida qo'shamiz
            embedded_images = _extract_docx_images(data, name)
            if embedded_images:
                warnings.append(_("%(name)s: %(n)s ta ichki rasm ajratib olindi va alohida varaq sifatida qoʻshildi") %
                                {"name": name, "n": len(embedded_images)})
                for img_name, img_data in embedded_images:
                    img_first = len(writer.pages) + 1
                    img_pages = _pdf_pages(_image_to_pdf(img_data, img_name), img_name)
                    for ip in img_pages:
                        writer.add_page(ip)
                    sources.append(SourceFile(img_name, "image", img_first, len(writer.pages)))
        else:
            kind, pages = "image", _pdf_pages(_image_to_pdf(data, name), name)
            first = len(writer.pages) + 1
            for page in pages:
                writer.add_page(page)
            sources.append(SourceFile(PurePath(name).name, kind, first, len(writer.pages)))
    out = io.BytesIO()
    writer.write(out)
    return Intake(pdf=out.getvalue(), pages=len(writer.pages), sources=sources, warnings=warnings)
