"""Hujjat bloklarini DOCX va PDF ga chizish (ish hisoboti va shablonli hujjatlar uchun umumiy).

Bloklar formatdan mustaqil: ikkala fayl bir xil mazmunda chiqadi. Rasmiy hujjat talablari (TZ §5.1):
Times New Roman, asosiy matn 14 pt, hoshiyalar: chap 3 sm, o'ng 1.5 sm, yuqori/past 2 sm.
Fayllar xotirada yaratiladi — diskka yozilmaydi.

Blok turlari:
  title  — markazda, katta qalin (hisobot sarlavhasi)
  center — markazda, qalin (hujjat nomi: "DAʼVO ARIZASI")
  right  — o'ngga tekislangan (kimga / kimdan rekvizitlari)
  h1, h2 — bo'lim sarlavhalari
  p      — oddiy abzats (eni bo'yicha tekislangan)
  bullet — ro'yxat bandi (kichik, 12/11 pt — hisobotdagi manbalar)
  item   — hujjat matnidagi sanab o'tish bandi ("– ...", 14 pt)
  meta   — kichik kursiv izoh
  warn   — ogohlantirish (qalin, to'q qizil)
  sign   — imzo qatori: "chap matn | o'ng matn"
  space  — bo'sh qator
"""
import io
from dataclasses import dataclass
from pathlib import Path

from django.conf import settings


@dataclass
class Block:
    kind: str
    text: str = ""

    @property
    def sign_left(self) -> str:
        return self.text.partition("|")[0].strip()

    @property
    def sign_right(self) -> str:
        return self.text.partition("|")[2].strip()


def to_docx(blocks: list[Block]) -> bytes:
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_TAB_ALIGNMENT
    from docx.shared import Cm, Pt, RGBColor

    doc = Document()
    for section in doc.sections:
        section.left_margin, section.right_margin = Cm(3), Cm(1.5)
        section.top_margin = section.bottom_margin = Cm(2)
    normal = doc.styles["Normal"]
    normal.font.name, normal.font.size = "Times New Roman", Pt(14)
    for style in ("Title", "Heading 1", "Heading 2", "List Bullet"):
        doc.styles[style].font.name = "Times New Roman"
        doc.styles[style].font.color.rgb = RGBColor(0, 0, 0)
    text_width = doc.sections[0].page_width - doc.sections[0].left_margin - doc.sections[0].right_margin
    for blk in blocks:
        if blk.kind == "title":
            doc.add_paragraph(blk.text, style="Title").alignment = WD_ALIGN_PARAGRAPH.CENTER
        elif blk.kind == "center":
            p = doc.add_paragraph()
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.add_run(blk.text).bold = True
        elif blk.kind == "right":
            p = doc.add_paragraph(blk.text)
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
            p.paragraph_format.space_after = Pt(0)
        elif blk.kind == "h1":
            doc.add_heading(blk.text, level=1)
        elif blk.kind == "h2":
            doc.add_heading(blk.text, level=2)
        elif blk.kind == "bullet":
            p = doc.add_paragraph(blk.text, style="List Bullet")
            p.runs[0].font.size = Pt(12)
        elif blk.kind == "item":
            p = doc.add_paragraph(blk.text, style="List Bullet")
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        elif blk.kind == "meta":
            run = doc.add_paragraph().add_run(blk.text)
            run.italic, run.font.size = True, Pt(12)
        elif blk.kind == "warn":
            run = doc.add_paragraph().add_run(blk.text)
            run.bold, run.font.size, run.font.color.rgb = True, Pt(12), RGBColor(0x9A, 0x34, 0x12)
        elif blk.kind == "sign":
            p = doc.add_paragraph()
            p.paragraph_format.tab_stops.add_tab_stop(text_width, WD_TAB_ALIGNMENT.RIGHT)
            p.add_run(f"{blk.sign_left}\t{blk.sign_right}")
        elif blk.kind == "space":
            doc.add_paragraph()
        else:
            p = doc.add_paragraph(blk.text)
            p.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            p.paragraph_format.first_line_indent = Cm(1.25)
    out = io.BytesIO()
    doc.save(out)
    return out.getvalue()


def to_pdf(blocks: list[Block]) -> bytes:
    from fpdf import FPDF

    font_dir = Path(settings.EXPORT_FONT_DIR)
    pdf = FPDF(format="A4")
    pdf.set_margins(left=30, top=20, right=15)
    pdf.set_auto_page_break(auto=True, margin=20)
    for style, name in (("", "times.ttf"), ("B", "timesbd.ttf"), ("I", "timesi.ttf")):
        pdf.add_font("TNR", style, str(font_dir / name))
    pdf.add_page()
    width = pdf.w - pdf.l_margin - pdf.r_margin

    def cell(text, size, style="", align="L", h=None):
        pdf.set_font("TNR", style, size)
        pdf.multi_cell(width, h or size * 0.5, text, align=align, new_x="LMARGIN", new_y="NEXT")

    def paragraph(text, first_line_indent=0.0, indent=0.0, bullet=""):
        # Eni bo'yicha tekislash + birinchi qator chekinishi (multi_cell buni bilmaydi).
        pdf.set_font("TNR", "", 14)
        with pdf.text_columns(text_align="J", l_margin=pdf.l_margin, r_margin=pdf.r_margin) as cols:
            with cols.paragraph(first_line_indent=first_line_indent, indent=indent, bullet_string=bullet,
                                line_height=1.15) as par:
                par.write(text)

    for blk in blocks:
        if blk.kind == "title":
            cell(blk.text, 18, "B", "C", 9)
            pdf.ln(2)
        elif blk.kind == "center":
            pdf.ln(2)
            cell(blk.text, 14, "B", "C", 7)
            pdf.ln(1)
        elif blk.kind == "right":
            cell(blk.text, 14, "", "R", 6.5)
            continue
        elif blk.kind in ("h1", "h2"):
            pdf.ln(3)
            cell(blk.text, 15 if blk.kind == "h1" else 13, "B", h=7)
        elif blk.kind == "bullet":
            cell("• " + blk.text, 11, h=5.5)
        elif blk.kind == "meta":
            cell(blk.text, 11, "I", h=5.5)
        elif blk.kind == "warn":
            pdf.set_text_color(0x9A, 0x34, 0x12)
            cell(blk.text, 11, "B", h=5.5)
            pdf.set_text_color(0, 0, 0)
        elif blk.kind == "sign":
            pdf.set_font("TNR", "", 14)
            pdf.cell(width / 2, 7, blk.sign_left)
            pdf.cell(width / 2, 7, blk.sign_right, align="R", new_x="LMARGIN", new_y="NEXT")
        elif blk.kind == "space":
            pdf.ln(6)
            continue
        elif blk.kind == "item":
            paragraph(blk.text, indent=7, bullet="–")
        else:
            paragraph(blk.text, first_line_indent=12.5)
        pdf.ln(1)
    return bytes(pdf.output())
