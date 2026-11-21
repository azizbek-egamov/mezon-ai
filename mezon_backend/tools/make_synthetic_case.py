"""Sintetik jinoyat ishi (PDF) va javoblar kaliti (JSON) — hujjat tahlili zanjirini sinash uchun.

Barcha shaxslar, raqamlar va voqealar TO'QIMA. Ichiga ataylab ziddiyatlar va protsessual muammolar qo'yilgan;
ular `answer_key.json` da varaq raqamlari bilan yoziladi (varaqlar generatsiya paytida avtomatik aniqlanadi).

    .venv/Scripts/python tools/make_synthetic_case.py  ->  fixtures/cases/case_01/{case_01.pdf, answer_key.json}
"""
import json
from pathlib import Path

from fpdf import FPDF

OUT = Path(__file__).resolve().parent.parent / "fixtures" / "cases" / "case_01"
CASE_NO = "№ 2026/0457"
FONT_DIR = Path("C:/Windows/Fonts")

# ---------------------------------------------------------------- hujjatlar
# Abzas: matn yoki (matn, fakt_belgisi). Belgili abzas qaysi varaqqa tushgani kalitga yoziladi.

INVESTIGATOR = "Toshkent shahar Sergeli tumani IIB Tergov boʻlimi katta tergovchisi, adliya kapitani N.Sh. Yusupov"

DOCS = [
    {
        "title": "JINOYAT ISHI " + CASE_NO,
        "paras": [
            "Rustamov Jasur Baxtiyorovichni Oʻzbekiston Respublikasi Jinoyat kodeksining 168-moddasi uchinchi qismi "
            "“a” bandi bilan ayblash toʻgʻrisida.",
            "Ish qoʻzgʻatilgan sana: 2026-yil 14-mart.",
            "Tergov organi: Toshkent shahar Sergeli tumani Ichki ishlar boʻlimi Tergov boʻlimi.",
            "1-tom. Varaqlar soni: ushbu tomda raqamlangan.",
            "Ish materiallari roʻyxati: ariza; jinoyat ishini qoʻzgʻatish toʻgʻrisidagi qaror; jabrlanuvchining "
            "soʻroq bayonnomasi; tintuv bayonnomasi; gumon qilinuvchini ushlab turish bayonnomasi; gumon qilinuvchining "
            "soʻroq bayonnomasi; guvohlarning soʻroq bayonnomalari; bank koʻchirmasi; tilxat; ekspertiza tayinlash "
            "toʻgʻrisidagi qaror; ekspertiza xulosasi; ehtiyot chorasini qoʻllash toʻgʻrisidagi ajrim; ayblanuvchi "
            "tariqasida ishda ishtirok etishga jalb qilish toʻgʻrisidagi qaror; ekspertiza tayinlash toʻgʻrisidagi "
            "qaror bilan tanishtirish bayonnomasi; ayblov xulosasi.",
        ],
    },
    {
        "title": "ARIZA",
        "paras": [
            "Sergeli tumani IIB boshligʻiga Toshkent shahar, Sergeli tumani, Quyosh mahallasi, 14-uy, 27-xonadonda "
            "yashovchi fuqaro Qodirova Malika Anvarovnadan (JSHSHIR 41503881230051, tel. +998 90 123-45-67)",
            ("Men 2026-yil 3-mart kuni soat 14:00 larda Sergeli avtomobil bozorida Jasur ismli shaxs bilan uchrashdim. "
             "U oʻzini oq rangli Chevrolet Cobalt (davlat raqami 01 A 777 BC) avtomobilining egasi deb tanishtirdi va "
             "avtomobilni 85 000 000 (sakson besh million) soʻmga sotishga rozi boʻldi.", "victim_meeting_14"),
            ("Kelishuvga koʻra men oʻsha kuni, yaʼni 2026-yil 3-mart kuni, 85 000 000 soʻmni uning bank kartasiga "
             "oʻtkazib berdim.", "victim_transfer_date_0303"),
            "Pulni olgach, Jasur avtomobilni ikki kundan keyin rasmiylashtirib beraman, deb vaʼda berdi. Shundan beri u "
            "telefonga javob bermayapti, avtomobil ham, pul ham qaytarilmadi. Keyin bilsam, bu avtomobil boshqa shaxsga "
            "tegishli ekan.",
            "Sizdan Jasur ismli shaxsni aniqlab, qonuniy chora koʻrishingizni va menga yetkazilgan 85 000 000 soʻm "
            "zararni undirib berishingizni soʻrayman. Yolgʻon xabar berganlik uchun javobgarlik haqida ogohlantirildim.",
            "Sana: 2026-yil 12-mart. Imzo: M.A. Qodirova",
        ],
    },
    {
        "title": "JINOYAT ISHINI QOʻZGʻATISH TOʻGʻRISIDA QAROR",
        "paras": [
            "Toshkent shahri, 2026-yil 14-mart.",
            INVESTIGATOR + " fuqaro M.A. Qodirovaning 2026-yil 12-martdagi arizasini koʻrib chiqib,",
            "ANIQLADI: 2026-yil 3-mart kuni Sergeli avtomobil bozorida nomaʼlum shaxs fuqaro M.A. Qodirovani aldab, "
            "avtomobil sotish bahonasida undan 85 000 000 soʻm pul mablagʻini qoʻlga kiritgan. Qilmishda Oʻzbekiston "
            "Respublikasi Jinoyat kodeksining 168-moddasida nazarda tutilgan jinoyat alomatlari mavjud.",
            "Bayon etilganlarga asosan, Oʻzbekiston Respublikasi Jinoyat-protsessual kodeksining tegishli moddalariga "
            "amal qilib,",
            "QAROR QILDI: 1. Jinoyat kodeksining 168-moddasi uchinchi qismi “a” bandi alomatlari boʻyicha jinoyat ishi "
            "qoʻzgʻatilsin va oʻz ish yuritishimga qabul qilinsin. 2. Qaror nusxasi tuman prokuroriga yuborilsin. "
            "3. Ariza beruvchi qaror toʻgʻrisida xabardor qilinsin.",
            "Tergovchi: N.Sh. Yusupov",
        ],
    },
    {
        "title": "JABRLANUVCHINI SOʻROQ QILISH BAYONNOMASI",
        "paras": [
            "Toshkent shahri, 2026-yil 15-mart. Soʻroq boshlandi: 10:05. Soʻroq tugadi: 11:40.",
            INVESTIGATOR + " Sergeli tumani IIB binosidagi 214-xonada jabrlanuvchi tariqasida quyidagi shaxsni soʻroq qildi:",
            "Familiyasi, ismi, otasining ismi: Qodirova Malika Anvarovna. Tugʻilgan sanasi: 1988-yil 7-avgust. "
            "Manzili: Toshkent shahar, Sergeli tumani, Quyosh mahallasi, 14-uy, 27-xonadon. Ish joyi: “Sergeli-Savdo” MChJ, "
            "buxgalter. JSHSHIR: 41503881230051.",
            "Jabrlanuvchiga Jinoyat-protsessual kodeksida nazarda tutilgan huquq va majburiyatlari tushuntirildi, bila "
            "turib yolgʻon koʻrsatma berganlik uchun Jinoyat kodeksining 238-moddasi boʻyicha javobgarlik haqida ogohlantirildi. "
            "Soʻroq oʻzbek tilida olib borildi, jabrlanuvchi tarjimonga muhtoj emasligini bildirdi.",
            "Mazmunan quyidagilarni koʻrsatdi:",
            "2026-yil fevral oyining oxirida “OLX” saytida oq rangli Chevrolet Cobalt avtomobilini sotish haqidagi "
            "eʼlonni koʻrdim. Eʼlondagi telefon raqami orqali Jasur ismli yigit bilan bogʻlandim. U avtomobilni "
            "Sergeli avtomobil bozorida koʻrsatishini aytdi.",
            ("2026-yil 3-mart kuni soat 14:00 da dugonam Hasanova Dilnoza bilan birga Sergeli avtomobil bozoriga bordim. "
             "Jasur bizni bozor darvozasi oldida kutib oldi va oq rangli Chevrolet Cobalt avtomobilini koʻrsatdi. Avtomobil "
             "yaxshi holatda edi, davlat raqami 01 A 777 BC edi.", "victim_meeting_14_interrogation"),
            ("Narx 85 000 000 soʻm deb kelishdik. Jasur pulni naqd emas, kartaga oʻtkazishni soʻradi. Men shu kuning "
             "oʻzida, uchrashuvdan keyin, 85 000 000 soʻmni “Humo” kartamdan u aytgan kartaga oʻtkazdim.",
             "victim_amount_85"),
            "Savol: Pul oʻtkazilganini tasdiqlovchi hujjatingiz bormi? Javob: Ha, bank ilovasidagi chekni va bankdan "
            "olingan koʻchirmani taqdim etaman.",
            "Savol: Jasurga biror hujjat, tilxat yoki ishonchnoma berganmisiz yoki undan olganmisiz? Javob: Yoʻq, hech "
            "qanday tilxat yozmaganman va imzolamaganman. Jasur ham menga hech narsa bermadi.",
            ("Savol: Tilxatda “58 000 000 soʻm oldim” deb yozilgan boʻlsa, unga nima deysiz? Javob: Bunday tilxatni "
             "bilmayman, men 58 000 000 emas, aynan 85 000 000 soʻm oʻtkazganman.", "victim_denies_receipt"),
            "Savol: Uchrashuvda yana kim bor edi? Javob: Dugonam Hasanova Dilnoza va bozordagi qorovul yonimizdan "
            "oʻtib turdi, uning ismini bilmayman.",
            "Bir necha kun oʻtib Jasur telefonni koʻtarmay qoʻydi. Keyin bilsam, 01 A 777 BC raqamli avtomobil boshqa "
            "shaxsga tegishli ekan va u avtomobilni hech kimga sotmoqchi boʻlmagan. Menga 85 000 000 soʻm moddiy zarar "
            "yetkazildi, uni toʻliq undirib berishni soʻrayman. Shuningdek, maʼnaviy zararni ham qoplashni soʻrayman.",
            "Bayonnoma men tomonimdan oʻqib chiqildi, koʻrsatmalarim toʻgʻri yozilgan, eʼtirozim yoʻq.",
            "Jabrlanuvchi: M.A. Qodirova. Tergovchi: N.Sh. Yusupov.",
        ],
    },
    {
        "title": "TINTUV BAYONNOMASI",
        "paras": [
            "Toshkent shahri, 2026-yil 18-mart. Tintuv boshlandi: 07:40. Tintuv tugadi: 08:50.",
            INVESTIGATOR + " xolislar I.T. Rahimov va B.B. Tojiyev ishtirokida, gumon qilinuvchi Rustamov Jasur "
            "Baxtiyorovichning Toshkent shahar, Chilonzor tumani, Bunyodkor shoh koʻchasi, 45-uy, 12-xonadondagi "
            "yashash joyida tintuv oʻtkazdi.",
            "Tintuvdan oldin gumon qilinuvchiga tintuv oʻtkazish toʻgʻrisidagi qaror eʼlon qilindi va ishga aloqador "
            "buyumlarni ixtiyoriy topshirish taklif qilindi. Gumon qilinuvchi ishga aloqador buyumlar yoʻqligini bildirdi.",
            "Tintuv natijasida quyidagilar topildi va olib qoʻyildi: 1) “Samsung Galaxy A54” rusumli mobil telefon; "
            "2) “Humo” bank kartasi, egasi “JASUR RUSTAMOV”; 3) qoʻlda yozilgan tilxat, mazmuni: “Men, Qodirova Malika "
            "Anvarovna, avtomobil uchun 58 000 000 soʻm toʻladim, daʼvoim yoʻq”, imzo va sana 03.03.2026 qoʻyilgan.",
            ("Olib qoʻyilgan buyumlar qadoqlanib, muhrlandi. Tilxat gumon qilinuvchining soʻzlariga koʻra, "
             "jabrlanuvchi tomonidan oʻz qoʻli bilan yozilgan.", "search_receipt_found"),
            "Tintuv vaqtida eʼtirozlar va arizalar kelib tushmadi.",
            "Xolislar: I.T. Rahimov, B.B. Tojiyev. Gumon qilinuvchi: J.B. Rustamov. Tergovchi: N.Sh. Yusupov.",
        ],
    },
    {
        "title": "GUMON QILINUVCHINI USHLAB TURISH BAYONNOMASI",
        "paras": [
            "Toshkent shahri, 2026-yil 18-mart.",
            ("Gumon qilinuvchi Rustamov Jasur Baxtiyorovich 2026-yil 18-mart kuni soat 09:30 da Sergeli tumani IIB "
             "binosida ushlab turildi.", "detention_start"),
            "Ushlab turish asoslari: jabrlanuvchi va guvoh gumon qilinuvchini jinoyat sodir etgan shaxs sifatida "
            "bevosita koʻrsatdi; gumon qilinuvchining yashash joyida jinoyat izlari topildi.",
            "Gumon qilinuvchiga ushlab turish asoslari, himoyachiga ega boʻlish, koʻrsatma berishdan bosh tortish va "
            "boshqa huquqlari tushuntirildi. Ushlab turilganligi haqida uning onasi R.K. Rustamovaga soat 10:15 da "
            "telefon orqali xabar qilindi.",
            "Gumon qilinuvchi: Rustamov Jasur Baxtiyorovich, 1991-yil 12-mayda tugʻilgan, JSHSHIR 31205910450027, "
            "yashash joyi: Toshkent shahar, Chilonzor tumani, Bunyodkor shoh koʻchasi, 45-uy, 12-xonadon, vaqtincha ishsiz.",
            "Gumon qilinuvchining arizasi: “Men aybsizman, pulni avtomobil uchun oldim, keyin vositachi orqali "
            "qaytarmoqchi edim. Himoyachi soʻrayman.”",
            "Gumon qilinuvchi: J.B. Rustamov. Himoyachi: advokat S.M. Abdullayev (2026-yil 18-mart, 11:20 dan "
            "ishtirok etmoqda). Tergovchi: N.Sh. Yusupov.",
        ],
    },
    {
        "title": "GUMON QILINUVCHINI SOʻROQ QILISH BAYONNOMASI",
        "paras": [
            "Toshkent shahri, 2026-yil 18-mart. Soʻroq boshlandi: 11:30. Soʻroq tugadi: 13:10.",
            INVESTIGATOR + " himoyachi advokat S.M. Abdullayev ishtirokida gumon qilinuvchi Rustamov Jasur "
            "Baxtiyorovichni soʻroq qildi.",
            "Gumon qilinuvchiga Jinoyat-protsessual kodeksida nazarda tutilgan huquqlari, shu jumladan koʻrsatma "
            "berishdan bosh tortish huquqi tushuntirildi. U koʻrsatma berishga rozi ekanligini bildirdi.",
            "Mazmunan quyidagilarni koʻrsatdi:",
            "2026-yil fevral oyida tanishim Otabek menga oʻzining kulrang Chevrolet Cobalt avtomobilini sotishda "
            "yordam berishni soʻradi va men “OLX” saytiga eʼlon joylashtirdim. Avtomobil menga tegishli emas edi, "
            "lekin egasi rozi edi, deb hisoblayman.",
            ("2026-yil 3-mart kuni men ertalabdan Samarqand shahrida edim, onamning qarindoshlarinikida boʻldim. "
             "Toshkentga “Afrosiyob” poyezdida qaytdim va soat 18:00 dan keyin yetib keldim. Shu sababli kunduzi soat "
             "14:00 da Sergeli bozorida boʻlishim mumkin emas.", "accused_alibi_samarkand"),
            ("Malika opa bilan kechqurun, soat 19:00 dan keyin Sergeli bozori yonida uchrashdik. Men koʻrsatgan avtomobil "
             "kulrang Chevrolet Cobalt edi, oq emas.", "accused_car_grey"),
            ("Malika opa menga avtomobil uchun 58 000 000 soʻm toʻladi, 85 000 000 emas. Shu haqda u oʻz qoʻli bilan "
             "tilxat yozib berdi va imzoladi. Tilxat uyimdan tintuvda olindi.", "accused_amount_58"),
            "Savol: Pul qaysi kartaga oʻtkazildi? Javob: Mening “Humo” kartamga. Pulning bir qismini Otabekka naqd "
            "berdim, qolganini qarzlarimni toʻlashga ishlatdim.",
            "Savol: Otabekning toʻliq ismi va manzili? Javob: Familiyasini bilmayman, telefon raqami oʻchiq.",
            "Savol: Nima uchun jabrlanuvchiga avtomobilni topshirmadingiz? Javob: Otabek avtomobilni bermay qoʻydi. "
            "Men pulni qaytarmoqchi edim, lekin ulgurmadim.",
            "Bayonnoma men tomonimdan oʻqib chiqildi, toʻgʻri yozilgan.",
            "Gumon qilinuvchi: J.B. Rustamov. Himoyachi: S.M. Abdullayev. Tergovchi: N.Sh. Yusupov.",
        ],
    },
    {
        "title": "GUVOHNI SOʻROQ QILISH BAYONNOMASI",
        "paras": [
            "Toshkent shahri, 2026-yil 16-mart. Soʻroq boshlandi: 15:00. Soʻroq tugadi: 15:55.",
            INVESTIGATOR + " guvoh tariqasida Hasanova Dilnoza Botirovnani soʻroq qildi. Tugʻilgan sanasi: "
            "1990-yil 22-yanvar. Manzili: Toshkent shahar, Yangihayot tumani, Navroʻz koʻchasi, 8-uy. "
            "JSHSHIR: 42201900560034.",
            "Guvohga huquq va majburiyatlari tushuntirildi, bila turib yolgʻon koʻrsatma berganlik va koʻrsatma "
            "berishdan bosh tortganlik uchun Jinoyat kodeksining 238 va 240-moddalari boʻyicha javobgarlik haqida "
            "ogohlantirildi.",
            "Mazmunan quyidagilarni koʻrsatdi:",
            ("Dugonam Malika Qodirova menga avtomobil sotib olmoqchi ekanini aytdi va birga borishni soʻradi. Biz "
             "2026-yil 3-mart kuni ishdan keyin, kechqurun soat 19:30 larda Sergeli avtomobil bozoriga bordik.",
             "witness1_meeting_1930"),
            ("Jasur ismli yigit bizga oq rangli Chevrolet Cobalt avtomobilini koʻrsatdi. Avtomobil oq rangda ekanini "
             "aniq eslayman, chunki Malika aynan oq rang xohlagan edi.", "witness1_car_white"),
            "Malika bozordayoq telefon orqali Jasurga pul oʻtkazdi. Qancha summa oʻtkazganini aniq koʻrmadim, lekin "
            "Malika menga 85 million soʻm toʻlaganini aytdi.",
            "Savol: Malika Jasurga biror tilxat yozib berdimi? Javob: Men koʻrgan vaqtda hech qanday tilxat yozilmadi.",
            "Bayonnoma men tomonimdan oʻqib chiqildi, koʻrsatmalarim toʻgʻri yozilgan.",
            "Guvoh: D.B. Hasanova. Tergovchi: N.Sh. Yusupov.",
        ],
    },
    {
        "title": "ГУВОҲНИ СЎРОҚ ҚИЛИШ БАЁННОМАСИ",
        "paras": [
            "Тошкент шаҳри, 2026 йил 17 март. Сўроқ бошланди: 09:10. Сўроқ тугади: 09:50.",
            "Тошкент шаҳар Сергели тумани ИИБ Тергов бўлими катта терговчиси, адлия капитани Н.Ш. Юсупов гувоҳ "
            "тариқасида Эргашев Шуҳрат Комиловични сўроқ қилди. Туғилган санаси: 1967 йил 3 октябр. Иш жойи: "
            "Сергели автомобиль бозори, қоровул. ЖШШИР: 30310670120018.",
            "Гувоҳга ҳуқуқ ва мажбуриятлари тушунтирилди, била туриб ёлғон кўрсатма берганлик учун жавобгарлик "
            "ҳақида огоҳлантирилди.",
            "Мазмунан қуйидагиларни кўрсатди:",
            ("2026 йил 3 март куни мен кундузги навбатда, соат 08:00 дан 20:00 гача ишладим. Тушдан кейин, соат 14:00 "
             "атрофида бозор дарвозаси олдида бир йигит икки аёлга кумушранг Chevrolet Cobalt автомобилини кўрсатаётганини "
             "кўрдим.", "witness2_time_14_silver"),
            "Савол: Йигитни таний оласизми? Жавоб: Юзини яхши эслайман, кўрсатилса таний оламан.",
            "Савол: Автомобилнинг давлат рақамини эслайсизми? Жавоб: Йўқ, рақамига эътибор бермадим.",
            "Савол: Кечқурун, соат 19:00 дан кейин уларни яна кўрдингизми? Жавоб: Йўқ, кечқурун уларни кўрмадим.",
            "Баённома мен томонимдан ўқиб чиқилди, тўғри ёзилган.",
            "Гувоҳ: Ш.К. Эргашев. Терговчи: Н.Ш. Юсупов.",
        ],
    },
    {
        "title": "BANK KOʻCHIRMASI",
        "paras": [
            "“Agrobank” ATB Sergeli filiali. Karta egasi: QODIROVA MALIKA. Karta: 9860 **** **** 4417 (Humo).",
            "Davr: 2026-yil 1-martdan 10-martgacha.",
            "01.03.2026 09:14 | Kirim | Ish haqi “Sergeli-Savdo” MChJ | +7 450 000,00 soʻm",
            "02.03.2026 18:40 | Chiqim | “Korzinka” supermarketi | −312 400,00 soʻm",
            "03.03.2026 12:05 | Chiqim | “Uzum Market” | −149 000,00 soʻm",
            ("04.03.2026 10:12 | Chiqim | P2P oʻtkazma, qabul qiluvchi karta 9860 **** **** 2093, egasi “JASUR RUSTAMOV” | "
             "−85 000 000,00 soʻm", "bank_transfer_0403"),
            "04.03.2026 10:12 | Chiqim | P2P oʻtkazma komissiyasi | −425 000,00 soʻm",
            "06.03.2026 13:30 | Chiqim | “Mediapark” | −2 199 000,00 soʻm",
            "08.03.2026 11:02 | Kirim | Depozitdan oʻtkazma | +500 000,00 soʻm",
            "Davr boshidagi qoldiq: 81 264 300,00 soʻm. Davr oxiridagi qoldiq: 1 128 900,00 soʻm.",
            "Koʻchirma bank tizimidan avtomatik shakllantirilgan. Filial operatsionisti: G.R. Nazarova. Muhr.",
        ],
    },
    {
        "title": "EKSPERTIZA TAYINLASH TOʻGʻRISIDA QAROR",
        "paras": [
            "Toshkent shahri, 2026-yil 20-mart.",
            INVESTIGATOR + " jinoyat ishi materiallarini oʻrganib,",
            "ANIQLADI: 2026-yil 18-martda oʻtkazilgan tintuv vaqtida gumon qilinuvchi J.B. Rustamovning uyidan "
            "M.A. Qodirova nomidan yozilgan, 58 000 000 soʻm toʻlangani haqidagi tilxat olib qoʻyilgan. Jabrlanuvchi "
            "tilxatni yozmaganini bildirgan. Tilxatdagi qoʻlyozma matn va imzo kim tomonidan bajarilganini aniqlash "
            "uchun maxsus bilim talab etiladi.",
            ("QAROR QILDI: 1. Qoʻlyozma va imzo ekspertizasi tayinlansin, uni oʻtkazish Respublika sud ekspertizasi "
             "markaziga topshirilsin. 2. Ekspert oldiga quyidagi savollar qoʻyilsin: tilxatdagi matn va imzo "
             "M.A. Qodirova tomonidan bajarilganmi? 3. Ekspert ixtiyoriga tilxat asli va M.A. Qodirovaning erkin "
             "namunalari yuborilsin.", "expertise_ordered_2003"),
            "Tergovchi: N.Sh. Yusupov.",
        ],
    },
    {
        "title": "ЗАКЛЮЧЕНИЕ ЭКСПЕРТА",
        "paras": [
            "Республиканский центр судебной экспертизы. Почерковедческая экспертиза № 1184. г. Ташкент, 31 марта 2026 года.",
            "Эксперт: А.Р. Каримов, стаж экспертной работы 12 лет. Об ответственности за дачу заведомо ложного заключения "
            "предупреждён.",
            "Основание: постановление следователя СО ОВД Сергелийского района г. Ташкента Н.Ш. Юсупова от 20.03.2026.",
            "Вопрос: Выполнены ли рукописный текст и подпись в расписке от 03.03.2026 Кодировой Маликой Анваровной?",
            "Исследование: представлены оригинал расписки и свободные образцы почерка и подписи М.А. Кодировой "
            "(12 листов). Выявлены совпадающие общие признаки почерка (выработанность, наклон, размер) и ряд частных "
            "признаков в начертании букв «М», «д», «я». Различающиеся признаки малочисленны и объясняются необычными "
            "условиями письма.",
            ("ВЫВОД: Рукописный текст расписки от 03.03.2026, вероятно, выполнен Кодировой Маликой Анваровной. Подпись "
             "от имени М.А. Кодировой, вероятно, выполнена самой Кодировой М.А. Решить вопрос в категорической форме "
             "не представилось возможным ввиду краткости подписи.", "expert_probable_victim"),
            "Эксперт: А.Р. Каримов. Печать.",
        ],
    },
    {
        "title": "EHTIYOT CHORASINI QOʻLLASH TOʻGʻRISIDA AJRIM",
        "paras": [
            "Sergeli tumanlararo jinoyat ishlari boʻyicha sudi. Toshkent shahri, 2026-yil 21-mart, soat 11:00.",
            "Sudya D.A. Mirzayev, prokuror yordamchisi K.O. Tursunov, gumon qilinuvchi J.B. Rustamov va himoyachi "
            "S.M. Abdullayev ishtirokida tergovchining qamoqqa olish tarzidagi ehtiyot chorasini qoʻllash toʻgʻrisidagi "
            "iltimosnomasini koʻrib chiqdi.",
            ("Himoyachi gumon qilinuvchi 2026-yil 18-mart soat 09:30 dan buyon ushlab turilganini, ushlab turish "
             "muddati uzaytirilmaganini va iltimosnoma sudga kechiktirib kiritilganini bildirdi.", "court_defense_objection"),
            "Sud tergovchining iltimosnomasi asosli deb hisobladi: gumon qilinuvchi doimiy ish joyiga ega emas, "
            "jabrlanuvchiga yetkazilgan zarar qoplanmagan, u tergovdan yashirinishi mumkin.",
            ("AJRIM QILDI: Rustamov Jasur Baxtiyorovichga nisbatan qamoqqa olish tarzidagi ehtiyot chorasi "
             "qoʻllanilsin, muddat 2026-yil 18-martdan hisoblansin.", "custody_order_2103_1100"),
            "Ajrim ustidan yuqori turuvchi sudga shikoyat berilishi yoki protest keltirilishi mumkin.",
            "Sudya: D.A. Mirzayev.",
        ],
    },
    {
        "title": "AYBLANUVCHI TARIQASIDA ISHDA ISHTIROK ETISHGA JALB QILISH TOʻGʻRISIDA QAROR",
        "paras": [
            "Toshkent shahri, 2026-yil 25-mart.",
            INVESTIGATOR + " jinoyat ishi materiallarini oʻrganib,",
            "ANIQLADI: Rustamov Jasur Baxtiyorovich 2026-yil 3-mart kuni soat 14:00 larda Sergeli avtomobil bozorida "
            "oʻziga tegishli boʻlmagan oq rangli Chevrolet Cobalt avtomobilini sotish bahonasida M.A. Qodirovani "
            "aldab, undan 85 000 000 soʻm pul mablagʻini oʻz kartasiga oʻtkazdirib, koʻp miqdorda firibgarlik sodir etgan.",
            "QAROR QILDI: Rustamov Jasur Baxtiyorovich Jinoyat kodeksining 168-moddasi uchinchi qismi “a” bandi bilan "
            "ayblanuvchi tariqasida ishda ishtirok etishga jalb qilinsin. Ayblov himoyachi ishtirokida eʼlon qilinsin.",
            "Ayblov eʼlon qilindi: 2026-yil 25-mart, 15:20. Ayblanuvchi: J.B. Rustamov (“aybimni tan olmayman”). "
            "Himoyachi: S.M. Abdullayev. Tergovchi: N.Sh. Yusupov.",
        ],
    },
    {
        "title": "EKSPERTIZA TAYINLASH TOʻGʻRISIDAGI QAROR BILAN TANISHTIRISH BAYONNOMASI",
        "paras": [
            "Toshkent shahri, 2026-yil 2-aprel.",
            ("Ayblanuvchi J.B. Rustamov va uning himoyachisi S.M. Abdullayev 2026-yil 20-martdagi qoʻlyozma va imzo "
             "ekspertizasini tayinlash toʻgʻrisidagi qaror bilan 2026-yil 2-aprel kuni tanishtirildi. Shu kuni "
             "2026-yil 31-martdagi ekspert xulosasi bilan ham tanishtirildi.", "expertise_familiarization_0204"),
            "Himoyachining arizasi: “Ekspertiza tayinlash toʻgʻrisidagi qaror bilan ekspertiza oʻtkazilib boʻlgandan keyin "
            "tanishtirildik. Biz ekspert oldiga qoʻshimcha savollar qoʻyish va boshqa ekspert muassasasini tanlash "
            "huquqidan mahrum boʻldik. Takroriy ekspertiza tayinlashni soʻraymiz.”",
            "Tergovchining qarori: ariza ish materiallariga qoʻshilsin.",
            "Ayblanuvchi: J.B. Rustamov. Himoyachi: S.M. Abdullayev. Tergovchi: N.Sh. Yusupov.",
        ],
    },
    {
        "title": "AYBLOV XULOSASI",
        "paras": [
            "Jinoyat ishi " + CASE_NO + " boʻyicha Rustamov Jasur Baxtiyorovichni Oʻzbekiston Respublikasi Jinoyat "
            "kodeksining 168-moddasi uchinchi qismi “a” bandi bilan ayblash toʻgʻrisida.",
            "Ayblanuvchi haqida maʼlumot: Rustamov Jasur Baxtiyorovich, 1991-yil 12-mayda Toshkent shahrida tugʻilgan, "
            "oʻzbek, oʻrta maxsus maʼlumotli, uylanmagan, vaqtincha ishsiz, ilgari sudlanmagan.",
            ("Dastlabki tergov bilan aniqlandi: ayblanuvchi J.B. Rustamov 2026-yil 3-mart kuni soat 14:00 da Sergeli "
             "avtomobil bozorida oʻziga tegishli boʻlmagan oq rangli Chevrolet Cobalt (01 A 777 BC) avtomobilini sotish "
             "bahonasida jabrlanuvchi M.A. Qodirovani aldab, uning “Humo” kartasidan shu kuni oʻz kartasiga "
             "85 000 000 soʻm pul mablagʻini oʻtkazdirib olgan.", "indictment_0303_14_85"),
            "Ayblanuvchining aybi quyidagi dalillar bilan tasdiqlanadi: jabrlanuvchi M.A. Qodirovaning arizasi va "
            "koʻrsatmalari; guvoh D.B. Hasanovaning koʻrsatmalari; guvoh Sh.K. Ergashevning koʻrsatmalari; bank koʻchirmasi; "
            "tintuv bayonnomasi.",
            ("Ayblanuvchining 58 000 000 soʻm olgani haqidagi tilxat soxta ekanligi qoʻlyozma ekspertizasi xulosasi bilan "
             "tasdiqlangan, shu sababli uning bu boradagi koʻrsatmalari himoya vositasi sifatida baholanadi.",
             "indictment_expert_misread"),
            "Ayblanuvchining 2026-yil 3-mart kuni Samarqand shahrida boʻlgani haqidagi koʻrsatmalari tekshirilib, oʻz "
            "tasdigʻini topmadi.",
            "Yengillashtiruvchi holatlar: ilgari sudlanmagan. Ogʻirlashtiruvchi holatlar: aniqlanmadi.",
            "Jabrlanuvchiga yetkazilgan 85 000 000 soʻm moddiy zarar qoplanmagan. Fuqaroviy daʼvo qoʻzgʻatilgan.",
            "Yuqoridagilarga asosan jinoyat ishi sudga yuborish uchun prokurorga taqdim etilsin.",
            "Ayblov xulosasi tuzildi: 2026-yil 10-aprel. Tergovchi: N.Sh. Yusupov.",
        ],
    },
]

# Qo'shimcha hujjatlar: ro'yxatdagi qaysi hujjatdan KEYIN joylashishi bilan.
EXTRA_DOCS = [
    ("JINOYAT ISHINI QOʻZGʻATISH TOʻGʻRISIDA QAROR", {
        "title": "JABRLANUVCHI VA FUQAROVIY DAʼVOGAR DEB TOPISH TOʻGʻRISIDA QAROR",
        "paras": [
            "Toshkent shahri, 2026-yil 15-mart.",
            INVESTIGATOR + " jinoyat ishi materiallarini oʻrganib, fuqaro M.A. Qodirovaga jinoyat natijasida "
            "85 000 000 soʻm miqdorida mulkiy zarar yetkazilganini va u zararni undirish haqida ariza berganini aniqladi.",
            "QAROR QILDI: 1. Qodirova Malika Anvarovna jinoyat ishi boʻyicha jabrlanuvchi deb topilsin. 2. U fuqaroviy "
            "daʼvogar deb topilsin, daʼvo summasi 85 000 000 soʻm. 3. Jabrlanuvchiga va fuqaroviy daʼvogarga "
            "Jinoyat-protsessual kodeksida nazarda tutilgan huquqlar tushuntirilsin.",
            "Qaror bilan tanishdim, huquqlarim tushuntirildi: M.A. Qodirova. Tergovchi: N.Sh. Yusupov.",
        ],
    }),
    ("ГУВОҲНИ СЎРОҚ ҚИЛИШ БАЁННОМАСИ", {
        "title": "TANIB OLISH UCHUN KOʻRSATISH BAYONNOMASI",
        "paras": [
            "Toshkent shahri, 2026-yil 19-mart. Boshlandi: 14:00. Tugadi: 14:20.",
            INVESTIGATOR + " guvoh Sh.K. Ergashevga tanib olish uchun shaxsni koʻrsatdi.",
            ("Tanib olish fotosurat boʻyicha oʻtkazildi: guvohga tergovchining mobil telefonidagi bitta fotosurat — "
             "gumon qilinuvchi J.B. Rustamovning surati koʻrsatildi. Boshqa shaxslarning fotosuratlari koʻrsatilmadi.",
             "identification_single_photo"),
            "Guvoh Sh.K. Ergashev: “Ha, bu yigit 3-mart kuni bozor darvozasi oldida ikki ayolga avtomobil "
            "koʻrsatgan yigit. Uni yuzidan taniyman.”",
            "Xolislar: A.A. Qosimov, F.F. Nurmatov. Guvoh: Sh.K. Ergashev. Tergovchi: N.Sh. Yusupov.",
        ],
    }),
    ("GUMON QILINUVCHINI SOʻROQ QILISH BAYONNOMASI", {
        "title": "QAMOQQA OLISH TARZIDAGI EHTIYOT CHORASINI QOʻLLASH TOʻGʻRISIDA ILTIMOSNOMA",
        "paras": [
            "Sergeli tumanlararo jinoyat ishlari boʻyicha sudiga. Toshkent shahri, 2026-yil 20-mart.",
            INVESTIGATOR + " Jinoyat kodeksining 168-moddasi uchinchi qismi “a” bandi bilan qoʻzgʻatilgan jinoyat ishi "
            "boʻyicha gumon qilinuvchi J.B. Rustamovga nisbatan qamoqqa olish tarzidagi ehtiyot chorasini qoʻllashni soʻraydi.",
            "Asoslar: gumon qilinuvchi ogʻir jinoyat sodir etishda gumon qilinmoqda, doimiy ish joyi yoʻq, jabrlanuvchiga "
            "yetkazilgan zararni qoplamagan, ozodlikda qolsa tergovdan yashirinishi va guvohlarga taʼsir oʻtkazishi mumkin.",
            ("Iltimosnoma sudga 2026-yil 20-mart kuni soat 17:45 da kiritildi.", "custody_motion_2003_1745"),
            "Ilova: jinoyat ishi materiallari, 1-tom. Tergovchi: N.Sh. Yusupov. Kelishildi: tuman prokurori oʻrinbosari.",
        ],
    }),
    ("EHTIYOT CHORASINI QOʻLLASH TOʻGʻRISIDA AJRIM", {
        "title": "HIMOYACHINING SHIKOYATI",
        "paras": [
            "Sergeli tumani prokuroriga advokat S.M. Abdullayevdan (Toshkent shahar advokatlar hayʼati, 1-son "
            "advokatlik byurosi, guvohnoma № 04217).",
            ("Himoyam ostidagi J.B. Rustamov 2026-yil 18-mart soat 09:30 da ushlab turilgan. Qamoqqa olish toʻgʻrisidagi "
             "iltimosnoma sudga faqat 20-mart soat 17:45 da kiritilgan, sud ajrimi 21-mart soat 11:00 da chiqarilgan. "
             "Ushlab turish muddati uzaytirilmagan. Shu tariqa himoyam ostidagi shaxs qonunda belgilangan muddatdan ortiq "
             "ozodlikdan mahrum qilingan.", "defense_complaint_detention"),
            "Shuningdek, guvoh Sh.K. Ergashevga tanib olish uchun faqat bitta fotosurat koʻrsatilgan, bu tanib olish "
            "natijasini ishonchsiz qiladi.",
            "Soʻrayman: ushlab turish muddati buzilishi yuzasidan prokuror tekshiruvi oʻtkazilsin, tanib olish "
            "bayonnomasi maqbul boʻlmagan dalil deb topilsin.",
            "Sana: 2026-yil 22-mart. Advokat: S.M. Abdullayev.",
        ],
    }),
    ("AYBLANUVCHI TARIQASIDA ISHDA ISHTIROK ETISHGA JALB QILISH TOʻGʻRISIDA QAROR", {
        "title": "AYBLANUVCHINI SOʻROQ QILISH BAYONNOMASI",
        "paras": [
            "Toshkent shahri, 2026-yil 25-mart. Soʻroq boshlandi: 15:30. Soʻroq tugadi: 16:45.",
            INVESTIGATOR + " himoyachi S.M. Abdullayev ishtirokida ayblanuvchi J.B. Rustamovni soʻroq qildi. "
            "Ayblanuvchiga ayblov mazmuni va huquqlari tushuntirildi.",
            "Ayblanuvchi aybini tan olmasligini va avvalgi koʻrsatmalarini tasdiqlashini bildirdi. Mazmunan qoʻshimcha "
            "qilib quyidagilarni koʻrsatdi:",
            ("2026-yil 3-mart kuni Samarqanddan Toshkentga “Afrosiyob” poyezdida qaytganman, chiptani “Oʻzbekiston temir "
             "yoʻllari” saytidan oʻz pasportim bilan sotib olganman. Bu maʼlumotni tekshirishni soʻrayman. Shuningdek, "
             "telefonim (+998 93 555-12-90) oʻsha kuni qayerda boʻlganini aniqlashni soʻrayman.", "accused_requests_check"),
            "Otabekning telefon raqami +998 97 444-08-08 edi, hozir oʻchiq. U Yunusobod tumanida yashaydi, deb eshitganman.",
            "Malika opa bilan uchrashganda u menga 58 000 000 soʻm toʻladi va tilxatni oʻz qoʻli bilan yozdi. Qolgan "
            "27 000 000 soʻm haqida hech qanday gap boʻlmagan.",
            "Bayonnoma oʻqib chiqildi, toʻgʻri yozilgan. Ayblanuvchi: J.B. Rustamov. Himoyachi: S.M. Abdullayev. "
            "Tergovchi: N.Sh. Yusupov.",
        ],
    }),
    ("AYBLANUVCHINI SOʻROQ QILISH BAYONNOMASI", {
        "title": "MULKNI XATLASH BAYONNOMASI",
        "paras": [
            "Toshkent shahri, 2026-yil 26-mart.",
            INVESTIGATOR + " fuqaroviy daʼvoni taʼminlash maqsadida ayblanuvchi J.B. Rustamovga tegishli mol-mulkni xatladi.",
            "Xatlandi: 1) “Samsung Galaxy A54” mobil telefoni (tintuvda olib qoʻyilgan), taxminiy qiymati 3 500 000 soʻm; "
            "2) “Humo” kartasi 9860 **** **** 2093 dagi qoldiq — 1 240 000 soʻm.",
            "Boshqa mol-mulk aniqlanmadi. Ayblanuvchining onasi R.K. Rustamovaga tegishli xonadon xatlanmadi.",
            "Ayblanuvchi: J.B. Rustamov. Xolislar: I.T. Rahimov, B.B. Tojiyev. Tergovchi: N.Sh. Yusupov.",
        ],
    }),
    ("MULKNI XATLASH BAYONNOMASI", {
        "title": "YUZLASHTIRISH BAYONNOMASI",
        "paras": [
            "Toshkent shahri, 2026-yil 27-mart. Boshlandi: 10:00. Tugadi: 11:35.",
            INVESTIGATOR + " jabrlanuvchi M.A. Qodirova va ayblanuvchi J.B. Rustamov (himoyachi S.M. Abdullayev "
            "ishtirokida) koʻrsatmalaridagi jiddiy ziddiyatlarni bartaraf etish maqsadida ular oʻrtasida yuzlashtirish oʻtkazdi.",
            "Yuzlashtirishga chaqirilganlar bir-birlarini tanishlarini va oʻzaro adovatlari yoʻqligini bildirdilar.",
            "Savol jabrlanuvchiga: Rustamov bilan qachon, qayerda uchrashgansiz? Javob: 2026-yil 3-mart kuni Sergeli "
            "avtomobil bozorida.",
            ("Savol jabrlanuvchiga: Uchrashuv soat nechada boʻlgan? Javob: Tushdan keyin edi, aniq vaqtini hozir "
             "eslolmayman. Ilgari soat 14:00 deb aytgan edim, lekin adashgan boʻlishim mumkin, kech kirmagan edi.",
             "confrontation_victim_unsure_time"),
            "Savol ayblanuvchiga: Jabrlanuvchining koʻrsatmasini tasdiqlaysizmi? Javob: Yoʻq. Biz kechqurun, soat "
            "19:00 dan keyin uchrashdik, men kunduzi Samarqandda edim.",
            ("Savol jabrlanuvchiga: Qancha pul oʻtkazgansiz? Javob: 85 000 000 soʻm. Savol ayblanuvchiga: Javob: "
             "58 000 000 soʻm oldim, tilxat bor.", "confrontation_amounts"),
            "Savol jabrlanuvchiga: Tilxatni siz yozganmisiz? Javob: Yoʻq, men hech qanday tilxat yozmaganman.",
            "Savol ayblanuvchiga: Koʻrsatgan avtomobilingiz qanday rangda edi? Javob: Kulrang. Jabrlanuvchi: Oq edi.",
            "Har bir ishtirokchi oʻz koʻrsatmasida qoldi. Bayonnoma oʻqib chiqildi.",
            "Jabrlanuvchi: M.A. Qodirova. Ayblanuvchi: J.B. Rustamov. Himoyachi: S.M. Abdullayev. Tergovchi: N.Sh. Yusupov.",
        ],
    }),
    ("YUZLASHTIRISH BAYONNOMASI", {
        "title": "“UCELL” MOBIL ALOQA OPERATORINING JAVOB XATI",
        "paras": [
            "Sergeli tumani IIB Tergov boʻlimiga. 2026-yil 28-mart, № 02-11/877.",
            "Sizning 2026-yil 26-martdagi soʻrovingizga asosan +998 93 555-12-90 abonent raqami (abonent: Rustamov Jasur "
            "Baxtiyorovich) boʻyicha 2026-yil 3-mart kungi ulanishlar va tayanch stansiyalar haqida maʼlumot beramiz:",
            "08:10–15:25 — Samarqand shahri, Registon va Siyob tayanch stansiyalari (24 ta ulanish).",
            ("15:40–17:45 — Samarqand–Jizzax–Toshkent temir yoʻli boʻylab tayanch stansiyalar (harakatdagi abonent).",
             "billing_moving"),
            ("13:40, 14:05, 14:32 — kiruvchi va chiquvchi qoʻngʻiroqlar, tayanch stansiya: Samarqand, Siyob.",
             "billing_samarkand_14"),
            ("18:05–23:50 — Toshkent shahri, Chilonzor va Sergeli tumanlari; 19:24 — Sergeli avtomobil bozori hududidagi "
             "tayanch stansiya.", "billing_sergeli_1924"),
            "Maʼlumot faqat tergov ehtiyojlari uchun berildi. Bosh muhandis: O.T. Xolmatov. Muhr.",
        ],
    }),
    ("“UCELL” MOBIL ALOQA OPERATORINING JAVOB XATI", {
        "title": "“OʻZBEKISTON TEMIR YOʻLLARI” AJ JAVOB XATI",
        "paras": [
            "Sergeli tumani IIB Tergov boʻlimiga. 2026-yil 29-mart, № 14/3301.",
            ("Soʻrovingizga javoban maʼlum qilamizki, Rustamov Jasur Baxtiyorovich (pasport AD 2231475) nomiga "
             "2026-yil 3-mart kuni Samarqand — Toshkent yoʻnalishidagi 766-“Afrosiyob” poyezdiga 4-vagon, 18-oʻrin chiptasi "
             "sotilgan. Poyezd Samarqanddan soat 15:40 da joʻnab, Toshkentga soat 17:50 da yetib kelgan. Chipta "
             "qoʻllanilgan (yoʻlovchi poyezdga chiqqanda roʻyxatdan oʻtgan).", "train_ticket"),
            "Bosh mutaxassis: S.N. Rasulova. Muhr.",
        ],
    }),
    ("“OʻZBEKISTON TEMIR YOʻLLARI” AJ JAVOB XATI", {
        "title": "GUVOHNI SOʻROQ QILISH BAYONNOMASI (AVTOMOBIL EGASI)",
        "paras": [
            "Fargʻona shahri, 2026-yil 30-mart. Soʻroq topshiriq boʻyicha Fargʻona shahar IIB tergovchisi "
            "B.U. Ahmedov tomonidan oʻtkazildi. Boshlandi: 11:00. Tugadi: 11:40.",
            "Guvoh: Sobirov Anvar Ilhomovich, 1979-yil 14-aprelda tugʻilgan, Fargʻona shahri, Mustaqillik koʻchasi, "
            "112-uy. JSHSHIR: 31404790330041. Javobgarlik haqida ogohlantirildi.",
            ("Men oq rangli Chevrolet Cobalt (davlat raqami 01 A 777 BC) avtomobilining egasiman. Avtomobilni hech qachon "
             "sotuvga qoʻymaganman, “OLX” saytida eʼlon bermaganman. 2026-yil 3-mart kuni kun boʻyi Fargʻonada edim, "
             "avtomobil ham Fargʻonada, mening uyim oldida turgan.", "owner_car_in_fergana"),
            "Rustamov Jasur va Otabek ismli shaxslarni tanimayman. Avtomobilimning davlat raqami qanday qilib bu ishda "
            "tilga olinganini bilmayman.",
            "Bayonnoma oʻqib chiqildi. Guvoh: A.I. Sobirov. Tergovchi: B.U. Ahmedov.",
        ],
    }),
    ("GUVOHNI SOʻROQ QILISH BAYONNOMASI (AVTOMOBIL EGASI)", {
        "title": "SUDLANGANLIK TOʻGʻRISIDA MAʼLUMOTNOMA",
        "paras": [
            "Oʻzbekiston Respublikasi IIV Axborot-tahlil markazi. 2026-yil 30-mart.",
            "Rustamov Jasur Baxtiyorovich, 1991-yil 12-mayda tugʻilgan: sudlanganligi haqida maʼlumot yoʻq. "
            "Maʼmuriy javobgarlikka tortilganlik: 2024-yil 11-noyabrda yoʻl harakati qoidalarini buzgani uchun "
            "jarima (toʻlangan).",
        ],
    }),
    ("SUDLANGANLIK TOʻGʻRISIDA MAʼLUMOTNOMA", {
        "title": "MAHALLA FUQAROLAR YIGʻINI TAVSIFNOMASI",
        "paras": [
            "Chilonzor tumani “Bunyodkor” mahalla fuqarolar yigʻini. 2026-yil 31-mart.",
            "Rustamov Jasur Baxtiyorovich mahallamizda onasi bilan birga yashaydi. Qoʻshnilar bilan munosabati yaxshi, "
            "mahalla tadbirlarida qatnashadi. Jamoat tartibini buzgani haqida shikoyatlar kelib tushmagan. Soʻnggi "
            "bir yilda doimiy ishi yoʻq, vaqtincha avtomobil savdosida vositachilik qilib keladi.",
            "Rais: Q.M. Yoʻldoshev. Muhr.",
        ],
    }),
    ("EKSPERTIZA TAYINLASH TOʻGʻRISIDAGI QAROR BILAN TANISHTIRISH BAYONNOMASI", {
        "title": "JINOYAT ISHI MATERIALLARI BILAN TANISHTIRISH BAYONNOMASI",
        "paras": [
            "Toshkent shahri, 2026-yil 8-aprel.",
            INVESTIGATOR + " dastlabki tergov tugaganini maʼlum qilib, ayblanuvchi J.B. Rustamov va himoyachi "
            "S.M. Abdullayevni jinoyat ishining barcha materiallari bilan tanishtirdi (1-tom).",
            ("Himoyachining iltimosnomasi: “Ishdagi “Ucell” va “Oʻzbekiston temir yoʻllari” javob xatlari ayblanuvchi "
             "3-mart kuni soat 15:40 gacha Samarqandda boʻlganini va kechqurun 19:24 da Sergeli bozori hududida boʻlganini "
             "tasdiqlaydi. Bu jabrlanuvchining dugonasi D.B. Hasanovaning koʻrsatmasiga mos keladi. Ayblovdagi “soat 14:00” "
             "vaqti va 85 000 000 soʻm summasi qayta koʻrib chiqilsin, takroriy qoʻlyozma ekspertizasi tayinlansin.”",
             "defense_motion_alibi"),
            ("Tergovchining qarori: iltimosnoma rad etilsin, chunki ish boʻyicha toʻplangan dalillar yetarli.",
             "investigator_rejects_motion"),
            "Ayblanuvchi: J.B. Rustamov. Himoyachi: S.M. Abdullayev. Tergovchi: N.Sh. Yusupov.",
        ],
    }),
]


def _insert_extra_docs():
    for after_title, doc in EXTRA_DOCS:
        idx = max(i for i, d in enumerate(DOCS) if d["title"] == after_title)
        DOCS.insert(idx + 1, doc)


_insert_extra_docs()

# ---------------------------------------------------------------- javoblar kaliti

KEY_CONTRADICTIONS = [
    {"id": "C1", "topic": "Toʻlangan summa", "facts": ["victim_amount_85", "accused_amount_58", "search_receipt_found"],
     "note": "Jabrlanuvchi 85 000 000 soʻm deydi; ayblanuvchi va tilxat — 58 000 000 soʻm. Bank koʻchirmasida 85 000 000."},
    {"id": "C2", "topic": "Uchrashuv vaqti", "facts": ["victim_meeting_14_interrogation", "witness1_meeting_1930",
                                                        "witness2_time_14_silver", "accused_alibi_samarkand"],
     "note": "Jabrlanuvchi va qorovul 14:00 deydi; jabrlanuvchining dugonasi (guvoh) va ayblanuvchi — kechqurun 19:00–19:30."},
    {"id": "C3", "topic": "Pul oʻtkazilgan sana", "facts": ["victim_transfer_date_0303", "bank_transfer_0403"],
     "note": "Jabrlanuvchi va ayblov xulosasi 3-mart deydi; bank koʻchirmasida 04.03.2026 10:12."},
    {"id": "C4", "topic": "Avtomobil rangi", "facts": ["witness1_car_white", "accused_car_grey", "witness2_time_14_silver"],
     "note": "Jabrlanuvchi va guvoh Hasanova — oq; ayblanuvchi — kulrang; qorovul — kumushrang."},
    {"id": "C5", "topic": "Ekspertiza xulosasi ayblov xulosasida notoʻgʻri bayon qilingan",
     "facts": ["expert_probable_victim", "indictment_expert_misread"],
     "note": "Ekspert: tilxat matni va imzo EHTIMOL jabrlanuvchiga tegishli (ayblanuvchi versiyasini qoʻllaydi); "
             "ayblov xulosasi: tilxat soxtaligi tasdiqlangan."},
    {"id": "C6", "topic": "Ayblanuvchining soat 14:00 dagi joylashuvi",
     "facts": ["indictment_0303_14_85", "billing_samarkand_14", "train_ticket", "billing_sergeli_1924"],
     "note": "Ayblov: 14:00 da Sergeli bozorida. Billing: 13:40–14:32 Samarqandda; poyezd 15:40 da Samarqanddan joʻnagan; "
             "19:24 da Sergeli bozori hududida — kechki uchrashuv versiyasiga mos."},
    {"id": "C7", "topic": "Koʻrsatilgan avtomobil", "facts": ["victim_meeting_14_interrogation", "owner_car_in_fergana"],
     "note": "Jabrlanuvchi 01 A 777 BC raqamli oq Cobaltni koʻrgan deydi; uning egasi avtomobil 3-mart kuni Fargʻonada "
             "boʻlganini koʻrsatgan."},
    {"id": "C8", "topic": "Jabrlanuvchi uchrashuv vaqtini aniq eslamasligi",
     "facts": ["victim_meeting_14_interrogation", "confrontation_victim_unsure_time"],
     "note": "Soʻroqda “14:00”; yuzlashtirishda “aniq eslolmayman, adashgan boʻlishim mumkin”."},
]

KEY_PROCEDURAL = [
    {"id": "P1", "topic": "Ushlab turish muddati", "facts": ["detention_start", "custody_order_2103_1100", "court_defense_objection"],
     "note": "18.03.2026 09:30 da ushlab turilgan, qamoqqa olish toʻgʻrisidagi ajrim 21.03.2026 11:00 — taxminan 73,5 soat; "
             "ishda muddatni uzaytirish toʻgʻrisidagi qaror yoʻq. Ushlab turish muddati (JPK: 48 soat) buzilgan boʻlishi mumkin."},
    {"id": "P2", "topic": "Ekspertiza tayinlash qarori bilan kech tanishtirish",
     "facts": ["expertise_ordered_2003", "expert_probable_victim", "expertise_familiarization_0204"],
     "note": "Qaror 20.03.2026, xulosa 31.03.2026, tanishtirish 02.04.2026 — ekspertizadan keyin. Ayblanuvchi savol qoʻyish, "
             "ekspert muassasasini tanlash huquqlaridan foydalana olmagan."},
    {"id": "P3", "topic": "Alibini tasdiqlovchi dalillar inobatga olinmagan",
     "facts": ["accused_alibi_samarkand", "billing_samarkand_14", "train_ticket", "defense_motion_alibi",
               "investigator_rejects_motion"],
     "note": "Billing va temir yoʻl javobi ayblanuvchi 14:00 da Samarqandda boʻlganini koʻrsatadi; ayblov xulosasi esa alibi "
             "“tasdiqlanmadi” deydi, himoyachining iltimosnomasi asoslantirilmay rad etilgan."},
    {"id": "P4", "topic": "Tanib olish bitta fotosurat bilan oʻtkazilgan",
     "facts": ["identification_single_photo", "defense_complaint_detention"],
     "note": "Guvohga faqat ayblanuvchining bitta fotosurati koʻrsatilgan — tanib olish tartibi buzilgan boʻlishi mumkin, "
             "natija ishonchsiz."},
]

KEY_PII = ["41503881230051", "31205910450027", "42201900560034", "30310670120018", "31404790330041",
           "+998 90 123-45-67", "+998 93 555-12-90", "+998 97 444-08-08", "AD 2231475"]
# Ism-familiyalar (niqoblash sinovi uchun). "Otabek" — familiyasiz, hozirgi niqoblash cheklovi.
KEY_PII_NAMES = ["Qodirova", "Malika", "Rustamov", "Jasur", "Hasanova", "Dilnoza", "Ergashev", "Эргашев",
                 "Шуҳрат", "Sobirov", "Yusupov", "Юсупов", "Abdullayev", "Mirzayev", "Кодиров", "Каримов"]


# ---------------------------------------------------------------- PDF

class CasePDF(FPDF):
    def header(self):
        self.set_font("TNR", "I", 9)
        self.cell(0, 6, f"Jinoyat ishi {CASE_NO} · 1-tom", align="R", new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def footer(self):
        self.set_y(-14)
        self.set_font("TNR", "", 10)
        self.cell(0, 8, f"{self.page_no()}-varaq", align="C")


def build() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    pdf = CasePDF(format="A4")
    pdf.set_margins(25, 18, 15)
    pdf.set_auto_page_break(True, margin=20)
    pdf.add_font("TNR", "", str(FONT_DIR / "times.ttf"))
    pdf.add_font("TNR", "B", str(FONT_DIR / "timesbd.ttf"))
    pdf.add_font("TNR", "I", str(FONT_DIR / "timesi.ttf"))

    fact_pages: dict[str, int] = {}
    documents = []
    for doc in DOCS:
        pdf.add_page()
        start = pdf.page_no()
        pdf.set_font("TNR", "B", 13)
        pdf.multi_cell(0, 7, doc["title"], align="C")
        pdf.ln(4)
        pdf.set_font("TNR", "", 12)
        for para in doc["paras"]:
            text, tag = para if isinstance(para, tuple) else (para, None)
            if tag:
                fact_pages[tag] = pdf.page_no()
            pdf.multi_cell(0, 6.2, text, align="J")
            pdf.ln(2.5)
        documents.append({"title": doc["title"], "pages": [start, pdf.page_no()]})

    pdf_path = OUT / "case_01.pdf"
    pdf.output(str(pdf_path))

    def resolve(items):
        return [{**it, "pages": sorted({fact_pages[f] for f in it["facts"]})} for it in items]

    key = {
        "case": CASE_NO, "synthetic": True, "total_pages": pdf.page_no(),
        "documents": documents,
        "fact_pages": fact_pages,
        "contradictions": resolve(KEY_CONTRADICTIONS),
        "procedural_issues": resolve(KEY_PROCEDURAL),
        "pii_values": KEY_PII,
        "pii_names": KEY_PII_NAMES,
        "timeline": [
            ["2026-03-03", "Uchrashuv va kelishuv (vaqti ziddiyatli: 14:00 yoki 19:00–19:30)"],
            ["2026-03-04 10:12", "85 000 000 soʻm P2P oʻtkazma (bank koʻchirmasi)"],
            ["2026-03-12", "Ariza"], ["2026-03-14", "Jinoyat ishi qoʻzgʻatildi"],
            ["2026-03-18 07:40", "Tintuv"], ["2026-03-18 09:30", "Ushlab turish"],
            ["2026-03-20", "Ekspertiza tayinlandi"], ["2026-03-21 11:00", "Qamoqqa olish ajrimi"],
            ["2026-03-25", "Ayblov eʼlon qilindi"], ["2026-03-31", "Ekspert xulosasi"],
            ["2026-04-02", "Ekspertiza qarori bilan tanishtirish"], ["2026-04-10", "Ayblov xulosasi"],
        ],
    }
    (OUT / "answer_key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{pdf_path} — {pdf.page_no()} varaq; kalit: {len(key['contradictions'])} ziddiyat, "
          f"{len(key['procedural_issues'])} protsessual muammo")


if __name__ == "__main__":
    build()
