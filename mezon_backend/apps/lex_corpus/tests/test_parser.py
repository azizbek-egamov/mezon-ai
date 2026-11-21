from django.test import SimpleTestCase

from apps.lex_corpus.parser import edition_label_date, parse_document


def elem(kind: str, elem_id: str, inner: str = "") -> str:
    return (f'<div class="{kind} lx_elem"><div class="lx_elem2"><div class="lx_elem3">'
            f'<span>Hujjatga taklif yuborish</span></div></div><div id="{elem_id}">{inner}</div></div>')


HTML = "".join([
    '<div id="lx_var_t">'
    '<div class="dropdown-menu__item lx_date_link">30.12.2026</div>'
    '<div class="dropdown-menu__item lx_date_selected stopProp">15.10.2026 01</div>'
    '<div class="dropdown-menu__item lx_date_link">15.10.2026</div></div>',
    elem("ACT_TITLE", "-1", "OʻZBEKISTON RESPUBLIKASINING JINOYAT KODEKSI"),
    elem("TEXT_HEADER_DEFAULT", "-2", "MAXSUS QISM"),
    elem("TEXT_HEADER_DEFAULT", "-3", "UCHINCHI BOʻLIM IQTISODIYOT SOHASIDAGI JINOYATLAR"),
    elem("TEXT_HEADER_DEFAULT", "-4", "X bob. Oʻzgalar mulkini talon-toroj qilish"),
    elem("CLAUSE_DEFAULT", "-10", "168-modda. Firibgarlik"),
    elem("BY_DEFAULT", "-11"),
    elem("ACT_TEXT", "-12"),
    elem("ACT_TEXT", "-13", "Firibgarlik, yaʼni aldash —"),
    elem("ACT_TEXT", "-14", "jarima bilan jazolanadi."),
    elem("ACT_TEXT", "-15"),
    elem("ACT_TEXT", "-16", "Firibgarlik:"),
    elem("ACT_TEXT", "-17", "a) ancha miqdorda —"),
    elem("CLAUSE_DEFAULT", "-20", '168<sup>1</sup>-modda. Yangi modda'),
    elem("CLAUSE_DEFAULT", "-21"),  # bo'sh sarlavha moddani yopmasligi kerak
    elem("ACT_TEXT", "-22", 'Ushbu Kodeksning <a href="/uz/docs/-111453#-10">168</a>-moddasi.'),
])


INLINE_HTML = "".join([
    elem("ACT_FORM", "-1", "Oʻzbekiston Respublikasining Qonuni"),
    elem("ACT_TITLE", "-2", "Ayrim qonun hujjatlariga oʻzgartishlar kiritish toʻgʻrisida"),
    elem("GRIF_PARLAMENT", "-3", "Qonunchilik palatasi tomonidan qabul qilingan"),
    elem("ACT_TEXT", "-4", "1-modda. Ushbu Qonunning maqsadi"),
    elem("ACT_TEXT", "-5", "Maqsad — tartibga solish."),
    elem("ACT_TEXT", "-6", "2-modda. Jinoyat kodeksiga quyidagi oʻzgartish kiritilsin:"),
    elem("ACT_TEXT", "-7", "“168-modda. Firibgarlik"),  # iqtibos ichidagi modda yangi birlik emas
    elem("ACT_TEXT", "-71", "19-modda uchinchi qismi chiqarilsin."),  # havola, yangi modda emas
    elem("ACT_TEXT", "-72", "3-modda. Ushbu Qonun rasmiy eʼlon qilingan kundan eʼtiboran kuchga kiradi"),
    elem("SIGNATURE", "-8", "Oʻzbekiston Respublikasining Prezidenti"),
])

BAND_HTML = "".join([
    elem("ACCEPTING_BODY", "-1", "Oʻzbekiston Respublikasi Oliy sudi plenumining"),
    elem("ACT_TEXT", "-2", "Sud amaliyotini umumlashtirib, Plenum qaror qiladi:"),
    elem("ACT_TEXT", "-3", "1. Sudlarning eʼtibori qaratilsin."),
    elem("ACT_TEXT", "-4", "Shunga koʻra, sudlar talab qilishi lozim."),
    elem("ACT_TEXT", "-5", "2. Daʼvoni taʼminlash choralari."),
])

WHOLE_HTML = "".join([
    elem("ACT_TITLE", "-1", "Konvensiyani ratifikatsiya qilish toʻgʻrisida"),
    elem("ACT_TEXT", "-2", "Konvensiya ratifikatsiya qilinsin."),
])


class StructureTests(SimpleTestCase):
    def test_inline_articles(self):
        doc = parse_document(INLINE_HTML)
        self.assertEqual(doc.structure, "INLINE")
        a1, a2, a3 = doc.articles
        self.assertEqual((a1.number, a1.heading, a1.text), ("1", "Ushbu Qonunning maqsadi", "Maqsad — tartibga solish."))
        self.assertEqual(a2.heading, "")
        self.assertEqual(a2.text, "2-modda. Jinoyat kodeksiga quyidagi oʻzgartish kiritilsin:\n“168-modda. Firibgarlik"
                                  "\n19-modda uchinchi qismi chiqarilsin.")
        self.assertEqual((a3.number, a3.heading, a3.text),
                         ("3", "", "Ushbu Qonun rasmiy eʼlon qilingan kundan eʼtiboran kuchga kiradi"))

    def test_inline_articles_russian(self):
        html = "".join([
            elem("ACT_TITLE", "-2", "О внесении изменений в некоторые законодательные акты"),
            elem("ACT_TEXT", "-4", "Статья 1. Цель настоящего Закона"),
            elem("ACT_TEXT", "-5", "Цель — регулирование."),
            elem("ACT_TEXT", "-6", "Статья 2. Внести в Уголовный кодекс следующие изменения:"),
            elem("ACT_TEXT", "-7", "Статью 19 дополнить частью."),
            elem("ACT_TEXT", "-8", "Статья 3. Настоящий Закон вступает в силу со дня опубликования"),
        ])
        doc = parse_document(html)
        self.assertEqual(doc.structure, "INLINE")
        self.assertEqual([(a.number, a.heading) for a in doc.articles],
                         [("1", "Цель настоящего Закона"), ("2", ""), ("3", "")])
        self.assertEqual(doc.articles[1].text, "Статья 2. Внести в Уголовный кодекс следующие изменения:\n"
                                               "Статью 19 дополнить частью.")

    def test_plenum_bands(self):
        doc = parse_document(BAND_HTML)
        self.assertEqual(doc.structure, "BAND")
        self.assertEqual([(a.unit_type, a.number) for a in doc.articles], [("PREAMBLE", ""), ("BAND", "1"), ("BAND", "2")])
        self.assertEqual(doc.articles[1].text, "1. Sudlarning eʼtibori qaratilsin.\nShunga koʻra, sudlar talab qilishi lozim.")

    def test_whole_document(self):
        doc = parse_document(WHOLE_HTML)
        self.assertEqual(doc.structure, "WHOLE")
        self.assertEqual([(a.unit_type, a.text) for a in doc.articles], [("WHOLE", "Konvensiya ratifikatsiya qilinsin.")])


class ParserTests(SimpleTestCase):
    def setUp(self):
        self.doc = parse_document(HTML)

    def test_title_and_editions(self):
        self.assertEqual(self.doc.title, "OʻZBEKISTON RESPUBLIKASINING JINOYAT KODEKSI")
        self.assertEqual(self.doc.current_edition, "15.10.2026 01")
        self.assertEqual(self.doc.editions, ["30.12.2026", "15.10.2026 01", "15.10.2026"])
        self.assertEqual(str(edition_label_date("15.10.2026 01")), "2026-10-15")

    def test_articles_and_parts(self):
        a168, a1681 = self.doc.articles
        self.assertEqual((a168.number, a168.heading, a168.elem_id), ("168", "Firibgarlik", "-10"))
        self.assertEqual(a168.section_path, ["MAXSUS QISM", "UCHINCHI BOʻLIM IQTISODIYOT SOHASIDAGI JINOYATLAR",
                                             "X bob. Oʻzgalar mulkini talon-toroj qilish"])
        self.assertEqual([p["n"] for p in a168.parts], [1, 2])
        self.assertEqual([x["elem_id"] for x in a168.parts[0]["paragraphs"]], ["-13", "-14"])
        self.assertEqual(a168.parts[1]["text"], "Firibgarlik:\na) ancha miqdorda —")

    def test_superscript_article_and_empty_clause(self):
        a = self.doc.articles[1]
        self.assertEqual(a.number, "168¹")
        self.assertEqual(len(a.parts), 1)
        self.assertEqual(a.parts[0]["text"], "Ushbu Kodeksning 168-moddasi.")
