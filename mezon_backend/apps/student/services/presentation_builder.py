"""Yuridik taqdimotlar generatori (python-pptx).
Mezon Klassik dizayn tizimida (To'q ko'k #1F3A5F, Oltin #C5A059, nafis tipografika).
O'zbekiston qonunchiligi asosida professional slaydlar to'plamini (.pptx) shakllantiradi.
"""
import io
import json
import logging
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

from apps.rag.llm import get_llm

logger = logging.getLogger(__name__)

# Mezon Klassik ranglar palitrasi
NAVY = RGBColor(0x1F, 0x3A, 0x5F)
NAVY_DARK = RGBColor(0x14, 0x26, 0x3E)
GOLD = RGBColor(0xC5, 0xA0, 0x59)
GOLD_LIGHT = RGBColor(0xE2, 0xC7, 0x7E)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
OFF_WHITE = RGBColor(0xF8, 0xF9, 0xFB)
INK = RGBColor(0x1E, 0x29, 0x3B)
MUTED = RGBColor(0x64, 0x74, 0x8B)
CARD_BG = RGBColor(0xFF, 0xFF, 0xFF)
CARD_BORDER = RGBColor(0xE2, 0xE8, 0xF0)


def generate_presentation_outline(topic: str, slide_count: int = 6, language: str = "uz") -> dict:
    """Gemini orqali yuridik mavzu bo'yicha strukturaviy slaydlar rejasini yaratadi."""
    system = (
        "Siz O'zbekiston Respublikasi huquqi bo'yicha yetuk professor va taqdimotlar mutaxassisisiz. "
        "Foydalanuvchi taqdim etgan yuridik mavzu bo'yicha seminar, ma'ruza yoki konferensiya uchun "
        "chiroyli, professional, qonun moddalariga asoslangan slaydlar rejasini JSON formatida tuzing.\n"
        "Talablar:\n"
        "1. Slaydlar soni: ko'rsatilgan miqdorda (masalan 5-7 ta).\n"
        "2. Har bir slaydda sarlavha (title), asosiy tushunchalar (key_points: 3-4 ta qisqa va lo'nda fikr), "
        "tegishli qonun moddasi (law_reference: masalan 'FK 354-modda') va amaliy ahamiyati (practical_tip).\n"
        "3. Til: o'zbek tili (lotin yozuvi).\n"
        "Javobni FAQAT JSON formatida quyidagi sxemada qaytaring:\n"
        "{\n"
        '  "topic_title": "Mavzu sarlavhasi",\n'
        '  "subtitle": "Kichik sarlavha va maqsad",\n'
        '  "slides": [\n'
        '    {\n'
        '      "slide_number": 1,\n'
        '      "type": "title",\n'
        '      "title": "Mavzu sarlavhasi",\n'
        '      "subtitle": "Yuridik tahlil va amaliyot",\n'
        '      "points": []\n'
        '    },\n'
        '    {\n'
        '      "slide_number": 2,\n'
        '      "type": "agenda",\n'
        '      "title": "Mundarija va reja",\n'
        '      "points": ["1. Asosiy tushunchalar", "2. Qonuniy asoslar", "3. Sud amaliyoti", "4. Xulosa"]\n'
        '    },\n'
        '    {\n'
        '      "slide_number": 3,\n'
        '      "type": "content",\n'
        '      "title": "Slayd sarlavhasi",\n'
        '      "law_reference": "Qonun nomi va moddasi",\n'
        '      "points": ["Fikr 1", "Fikr 2", "Fikr 3"],\n'
        '      "practical_tip": "Amaliy tavsiya yoki sud tajribasi"\n'
        '    },\n'
        '    {\n'
        '      "slide_number": 6,\n'
        '      "type": "conclusion",\n'
        '      "title": "Xulosa va takliflar",\n'
        '      "points": ["Xulosa 1", "Xulosa 2", "Xulosa 3"]\n'
        '    }\n'
        '  ]\n'
        "}"
    )

    user_prompt = f"Yuridik mavzu: {topic}. Slaydlar soni: {slide_count} ta."

    try:
        llm = get_llm()
        data = llm.chat_json(system=system, user=user_prompt)
        if isinstance(data, dict) and "slides" in data:
            return data
    except Exception as e:
        logger.warning("LLM presentation generation outline fallback: %s", e)

    # Fallback outline agar LLM javob bermasa
    return {
        "topic_title": topic,
        "subtitle": "Oʻzbekiston Respublikasi qonunchiligi asosida yuridik sharh",
        "slides": [
            {
                "slide_number": 1,
                "type": "title",
                "title": topic,
                "subtitle": "Oʻzbekiston Respublikasi qonunchiligi tahlili",
                "points": [],
            },
            {
                "slide_number": 2,
                "type": "agenda",
                "title": "Mavzu rejasi va tuzilishi",
                "points": [
                    "Mavzuning huquqiy mohiyati va dolzarbligi",
                    "Normativ-huquqiy baza va asosiy moddalar",
                    "Huquqni qoʻllash amaliyotidagi muammolar",
                    "Yakuniy xulosalar va takliflar",
                ],
            },
            {
                "slide_number": 3,
                "type": "content",
                "title": "Huquqiy asoslar va tushunchalar",
                "law_reference": "Amaldagi Kodeks va qonun normalari",
                "points": [
                    "Huquqiy munosabat ishtirokchilarining huquq va majburiyatlari",
                    "Shartnoma yoki huquqiy harakatning haqiqiylik shartlari",
                    "Qonunda belgilangan maxsus talablar va cheklovlar",
                ],
                "practical_tip": "Hujjatlarni tuzishda qonun talablariga qatʼiy rioya qilish noqonuniylik xavfini oldini oladi.",
            },
            {
                "slide_number": 4,
                "type": "content",
                "title": "Sud amaliyoti va nizolarni hal qilish",
                "law_reference": "Oliy sud Plenumi tushuntirishlari",
                "points": [
                    "Sudlarda eng koʻp uchraydigan nizo toifalari",
                    "Isbotlash vositalari va dalillarni taqdim etish mezonlari",
                    "Daʼvo muddatlarini hisoblash tartibi",
                ],
                "practical_tip": "Sudga murojaat qilishdan oldin pretenziya tartibiga rioya qilish muhim.",
            },
            {
                "slide_number": 5,
                "type": "conclusion",
                "title": "Yakuniy xulosalar",
                "points": [
                    "Qonunchilik normalarini toʻgʻri qoʻllash barqarorlik garovidir",
                    "Ishtirokchilarning huquqiy kafolatlari toʻliq taʼminlanishi shart",
                    "Eʼtiboringiz uchun rahmat!",
                ],
            },
        ],
    }


def build_pptx_presentation(outline: dict, author_name: str = "Mezon Talaba") -> bytes:
    """Strukturaviy rejadan chiroyli 16:9 Mezon Klassik formatdagi .pptx yaratadi."""
    prs = Presentation()
    # 16:9 o'lcham (13.333 x 7.5 inches)
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    blank_layout = prs.slide_layouts[6]

    topic_title = outline.get("topic_title", "Yuridik Taqdimot")
    subtitle = outline.get("subtitle", "")
    slides = outline.get("slides", [])

    for s in slides:
        stype = s.get("type", "content")
        slide = prs.slides.add_slide(blank_layout)

        if stype == "title":
            _render_title_slide(slide, s.get("title", topic_title), s.get("subtitle", subtitle), author_name)
        elif stype == "agenda":
            _render_agenda_slide(slide, s.get("title", "Reja"), s.get("points", []))
        elif stype == "conclusion":
            _render_conclusion_slide(slide, s.get("title", "Xulosa"), s.get("points", []))
        else:
            _render_content_slide(
                slide,
                s.get("title", ""),
                s.get("points", []),
                s.get("law_reference", ""),
                s.get("practical_tip", "")
            )

    buf = io.BytesIO()
    prs.save(buf)
    return buf.getvalue()


def _render_title_slide(slide, title: str, subtitle: str, author_name: str):
    # Fon: To'q ko'k to'rtburchak
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY
    bg.line.fill.background()

    # Oltin bezak chizig'i
    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.5), Inches(1.5), Inches(1.2), Inches(0.08))
    accent.fill.solid()
    accent.fill.fore_color.rgb = GOLD
    accent.line.fill.background()

    # Brend belgisi / Label
    brand_box = slide.shapes.add_textbox(Inches(1.5), Inches(1.8), Inches(10), Inches(0.5))
    tf_b = brand_box.text_frame
    tf_b.word_wrap = True
    p_b = tf_b.paragraphs[0]
    p_b.text = "MEZON • HUQUQIY TAHLIL VA AKADEMIYA"
    p_b.font.size = Pt(12)
    p_b.font.bold = True
    p_b.font.color.rgb = GOLD_LIGHT
    p_b.font.name = "Georgia"

    # Asosiy sarlavha
    tbox = slide.shapes.add_textbox(Inches(1.5), Inches(2.4), Inches(10.5), Inches(2.2))
    tf = tbox.text_frame
    tf.word_wrap = True
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(36)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = "Georgia"

    # Kichik sarlavha
    if subtitle:
        sbox = slide.shapes.add_textbox(Inches(1.5), Inches(4.7), Inches(10.5), Inches(1.0))
        tf_s = sbox.text_frame
        tf_s.word_wrap = True
        p_s = tf_s.paragraphs[0]
        p_s.text = subtitle
        p_s.font.size = Pt(18)
        p_s.font.color.rgb = RGBColor(0xDF, 0xE7, 0xF2)
        p_s.font.name = "Calibri"

    # Muallif va sana
    footer_box = slide.shapes.add_textbox(Inches(1.5), Inches(6.2), Inches(10.5), Inches(0.6))
    tf_f = footer_box.text_frame
    p_f = tf_f.paragraphs[0]
    p_f.text = f"Tayyorladi: {author_name} | Oʻzbekiston Respublikasi Qonunchiligi"
    p_f.font.size = Pt(13)
    p_f.font.color.rgb = RGBColor(0xA5, 0xB4, 0xCB)
    p_f.font.name = "Calibri"


def _render_agenda_slide(slide, title: str, points: list[str]):
    _render_slide_base(slide, title, "Taqdimot rejasi va asosiy bosqichlar")

    top_start = 2.4
    for i, pt in enumerate(points):
        y = Inches(top_start + (i * 1.1))

        # Raqam doirasi (Gold)
        num_circle = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.5), y, Inches(0.8), Inches(0.8))
        num_circle.fill.solid()
        num_circle.fill.fore_color.rgb = GOLD
        num_circle.line.fill.background()
        tf_c = num_circle.text_frame
        p_c = tf_c.paragraphs[0]
        p_c.alignment = PP_ALIGN.CENTER
        p_c.text = f"0{i+1}"
        p_c.font.size = Pt(18)
        p_c.font.bold = True
        p_c.font.color.rgb = WHITE
        p_c.font.name = "Georgia"

        # Matn kartochkasi
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(2.5), y, Inches(9.3), Inches(0.8))
        card.fill.solid()
        card.fill.fore_color.rgb = WHITE
        card.line.color.rgb = CARD_BORDER
        card.line.width = Pt(1)
        tf_card = card.text_frame
        tf_card.vertical_anchor = MSO_ANCHOR.MIDDLE
        p_text = tf_card.paragraphs[0]
        p_text.text = f"   {pt}"
        p_text.font.size = Pt(16)
        p_text.font.bold = True
        p_text.font.color.rgb = INK
        p_text.font.name = "Calibri"


def _render_content_slide(slide, title: str, points: list[str], law_ref: str, practical_tip: str):
    _render_slide_base(slide, title)

    # Chap tomon kartochkasi: Asosiy fikrlar va tahlil
    card_w = Inches(7.0) if law_ref or practical_tip else Inches(10.3)
    card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(1.5), Inches(2.2), card_w, Inches(4.5))
    card.fill.solid()
    card.fill.fore_color.rgb = WHITE
    card.line.color.rgb = CARD_BORDER
    card.line.width = Pt(1)

    tf = card.text_frame
    tf.word_wrap = True
    tf.margin_left = Inches(0.4)
    tf.margin_top = Inches(0.4)
    tf.margin_right = Inches(0.4)

    for i, pt in enumerate(points):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.text = f"•  {pt}"
        p.font.size = Pt(15)
        p.font.color.rgb = INK
        p.font.name = "Calibri"
        p.space_after = Pt(14)

    # O'ng tomon kartochkasi: Qonun moddasi va Amaliy tavsiya
    if law_ref or practical_tip:
        right_x = Inches(8.8)
        right_w = Inches(3.0)

        if law_ref:
            law_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, right_x, Inches(2.2), right_w, Inches(2.0))
            law_box.fill.solid()
            law_box.fill.fore_color.rgb = RGBColor(0xFA, 0xF5, 0xEA)
            law_box.line.color.rgb = GOLD
            law_box.line.width = Pt(1.5)

            tf_l = law_box.text_frame
            tf_l.word_wrap = True
            tf_l.margin_left = Inches(0.25)
            tf_l.margin_top = Inches(0.25)

            p_lh = tf_l.paragraphs[0]
            p_lh.text = "Qonuniy havola:"
            p_lh.font.size = Pt(12)
            p_lh.font.bold = True
            p_lh.font.color.rgb = GOLD
            p_lh.space_after = Pt(6)

            p_lt = tf_l.add_paragraph()
            p_lt.text = law_ref
            p_lt.font.size = Pt(14)
            p_lt.font.bold = True
            p_lt.font.color.rgb = NAVY

        if practical_tip:
            tip_y = Inches(4.5) if law_ref else Inches(2.2)
            tip_h = Inches(2.2) if law_ref else Inches(4.5)

            tip_box = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, right_x, tip_y, right_w, tip_h)
            tip_box.fill.solid()
            tip_box.fill.fore_color.rgb = RGBColor(0xEE, 0xF4, 0xFB)
            tip_box.line.color.rgb = NAVY
            tip_box.line.width = Pt(1.5)

            tf_t = tip_box.text_frame
            tf_t.word_wrap = True
            tf_t.margin_left = Inches(0.25)
            tf_t.margin_top = Inches(0.25)

            p_th = tf_t.paragraphs[0]
            p_th.text = "Amaliy ahamiyati:"
            p_th.font.size = Pt(12)
            p_th.font.bold = True
            p_th.font.color.rgb = NAVY
            p_th.space_after = Pt(6)

            p_tt = tf_t.add_paragraph()
            p_tt.text = practical_tip
            p_tt.font.size = Pt(13)
            p_tt.font.color.rgb = INK


def _render_conclusion_slide(slide, title: str, points: list[str]):
    # To'q ko'k yakuniy fon
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = NAVY_DARK
    bg.line.fill.background()

    # Oltin chiziq
    accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(1.5), Inches(1.5), Inches(1.2), Inches(0.08))
    accent.fill.solid()
    accent.fill.fore_color.rgb = GOLD
    accent.line.fill.background()

    # Sarlavha
    tbox = slide.shapes.add_textbox(Inches(1.5), Inches(1.8), Inches(10.5), Inches(1.2))
    tf = tbox.text_frame
    p = tf.paragraphs[0]
    p.text = title
    p.font.size = Pt(32)
    p.font.bold = True
    p.font.color.rgb = WHITE
    p.font.name = "Georgia"

    # Fikrlar
    cbox = slide.shapes.add_textbox(Inches(1.5), Inches(3.2), Inches(10.5), Inches(3.0))
    tfc = cbox.text_frame
    tfc.word_wrap = True

    for i, pt in enumerate(points):
        p = tfc.paragraphs[0] if i == 0 else tfc.add_paragraph()
        p.text = f"✓  {pt}"
        p.font.size = Pt(18)
        p.font.color.rgb = RGBColor(0xFA, 0xFA, 0xFA)
        p.space_after = Pt(14)


def _render_slide_base(slide, title: str, category_label: str = "Huquqiy sharh"):
    # Fon: och kulrang/oq
    bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg.fill.solid()
    bg.fill.fore_color.rgb = OFF_WHITE
    bg.line.fill.background()

    # Yuqori ko'k chiziq
    top_line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.1))
    top_line.fill.solid()
    top_line.fill.fore_color.rgb = NAVY
    top_line.line.fill.background()

    # Sarlavha qismi
    tbox = slide.shapes.add_textbox(Inches(1.5), Inches(0.6), Inches(10.3), Inches(1.2))
    tf = tbox.text_frame
    tf.word_wrap = True

    p_sub = tf.paragraphs[0]
    p_sub.text = category_label.upper()
    p_sub.font.size = Pt(11)
    p_sub.font.bold = True
    p_sub.font.color.rgb = GOLD
    p_sub.font.name = "Georgia"

    p_title = tf.add_paragraph()
    p_title.text = title
    p_title.font.size = Pt(26)
    p_title.font.bold = True
    p_title.font.color.rgb = NAVY
    p_title.font.name = "Georgia"

    # Pastki qism: footer
    fbox = slide.shapes.add_textbox(Inches(1.5), Inches(6.9), Inches(10.3), Inches(0.4))
    tff = fbox.text_frame
    pf = tff.paragraphs[0]
    pf.text = "Mezon • Oʻzbekiston qonunchiligi axborot-tahlil tizimi"
    pf.font.size = Pt(10)
    pf.font.color.rgb = MUTED

