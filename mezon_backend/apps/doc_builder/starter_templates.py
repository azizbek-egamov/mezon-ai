"""Boshlang'ich shablonlar (namuna). Qonun havolalari 2026-10-26 da bazadagi joriy matn bilan tekshirilgan.
Moderator tasdiqlamaguncha foydalanuvchiga "moderator tasdiqlamagan namuna" belgisi bilan ko'rsatiladi.
`python manage.py load_starter_templates` — sarlavha bo'yicha yaratadi yoki yangilaydi."""

ADVOCATE = [
    {"name": "advokat_fio", "label": "Advokatning F.I.Sh.", "type": "text"},
    {"name": "advokat_tashkiloti", "label": "Advokatlik tuzilmasi (byuro, firma, hay'at)", "type": "text"},
    {"name": "guvohnoma_raqami", "label": "Advokatlik guvohnomasi raqami", "type": "text"},
    {"name": "advokat_manzili", "label": "Advokatning manzili", "type": "text"},
    {"name": "advokat_telefon", "label": "Advokatning telefoni", "type": "phone"},
]

TEMPLATES = [
    {
        "title": "Advokat soʻrovi",
        "category": "ADVOCATE_REQUEST",
        "description": "Davlat organi, korxona yoki tashkilotdan maʼlumotnoma, tavsifnoma va boshqa hujjatlarni soʻrash.",
        "legal_basis": "“Advokatura toʻgʻrisida”gi Qonun, 7¹-modda (advokat soʻrovi; javob muddati — 15 kun)",
        "form_schema": [
            {"name": "tashkilot", "label": "Soʻrov yuboriladigan tashkilot", "type": "text"},
            {"name": "tashkilot_manzili", "label": "Tashkilot manzili", "type": "text", "required": False},
            *ADVOCATE,
            {"name": "mijoz", "label": "Kimning manfaatlari himoya qilinmoqda (F.I.Sh. yoki nomi)", "type": "text"},
            {"name": "ish_mazmuni", "label": "Qaysi ish yoki masala yuzasidan", "type": "text"},
            {"name": "soralayotgan_hujjatlar", "label": "Soʻralayotgan axborot (hujjatlar) — har biri yangi qatorda",
             "type": "textarea"},
        ],
        "body": """>> {{ tashkilot }}ga
{% if tashkilot_manzili %}>> {{ tashkilot_manzili }}
{% endif %}>> {{ advokat_tashkiloti }} advokati
>> {{ advokat_fio }}dan
>> (advokatlik guvohnomasi № {{ guvohnoma_raqami }})
>> {{ advokat_manzili }}, tel.: {{ advokat_telefon }}

## ADVOKAT SOʻROVI

Men, advokat {{ advokat_fio }}, {{ mijoz }} manfaatlarini himoya qilish yuzasidan {{ ish_mazmuni }} boʻyicha malakali yuridik yordam koʻrsatmoqdaman.
“Advokatura toʻgʻrisida”gi Oʻzbekiston Respublikasi Qonunining 7¹-moddasiga muvofiq advokat davlat organlari va boshqa organlarga, korxonalar, muassasalar va tashkilotlarga malakali yuridik yordam koʻrsatish uchun zarur boʻlgan maʼlumotnomalar, tavsifnomalar va boshqa hujjatlarni taqdim etish yuzasidan advokat soʻrovini yuborishga haqli.
Yuqoridagilarga asosan quyidagi axborot (hujjatlar)ni taqdim etishingizni soʻrayman:
{{ soralayotgan_hujjatlar }}
Qonunga muvofiq axborot (hujjatlar) advokat soʻrovi olingan sanadan eʼtiboran oʻn besh kundan kechiktirmay taqdim etiladi.

~ Advokat {{ advokat_fio }} | ____________
~ {{ bugun }} |""",
    },
    {
        "title": "Jinoyat ishi materiallari bilan tanishish toʻgʻrisida iltimosnoma",
        "category": "MOTION",
        "description": "Dastlabki tergov tamomlangach yoki ish tugatilganda himoyachining ish materiallari bilan "
                       "toʻliq tanishib chiqish huquqini taʼminlashni soʻrash.",
        "legal_basis": "JPK 375-modda (tanishib chiqish huquqini taʼminlash)\nJPK 376-modda (tanishib chiqish tartibi; "
                       "muddat cheklanmaydi)\nJPK 377-modda (tanishib chiqqandan keyin iltimoslar qilish)",
        "form_schema": [
            {"name": "organ", "label": "Tergov organi va tergovchi (masalan: Sergeli tumani IIB tergovchisi A.A. Aliyev)",
             "type": "text"},
            {"name": "ish_raqami", "label": "Jinoyat ishi raqami", "type": "text"},
            {"name": "ayblanuvchi", "label": "Gumon qilinuvchi / ayblanuvchining F.I.Sh.", "type": "text"},
            {"name": "holat", "label": "Holat", "type": "select",
             "options": ["dastlabki tergov tamomlanganligi eʼlon qilindi", "jinoyat ishi tugatildi"]},
            {"name": "qoshimcha", "label": "Qoʻshimcha soʻrov (masalan, nusxa olish, ashyoviy dalillar)",
             "type": "textarea", "required": False},
            *ADVOCATE,
        ],
        "body": """>> {{ organ }}ga
>> {{ ish_raqami }}-sonli jinoyat ishi boʻyicha
>> {{ ayblanuvchi }} himoyachisi
>> advokat {{ advokat_fio }}dan
>> ({{ advokat_tashkiloti }}, guvohnoma № {{ guvohnoma_raqami }})
>> {{ advokat_manzili }}, tel.: {{ advokat_telefon }}

## ILTIMOSNOMA
## (ish materiallari bilan tanishish toʻgʻrisida)

{{ ish_raqami }}-sonli jinoyat ishi boʻyicha {{ holat }}.
Oʻzbekiston Respublikasi Jinoyat-protsessual kodeksining 375-moddasiga muvofiq tergovchi himoyachiga ishdagi barcha materiallar bilan tanishib chiqish huquqini tushuntirishi va tanishib chiqish uchun ishni taqdim etishi, 376-moddasiga muvofiq esa materiallarni tikilgan va raqamlangan koʻrinishda, har bir jilddagi hujjatlar roʻyxati bilan taqdim etishi lozim; ish bilan tanishib chiqish uchun zarur boʻlgan muddat cheklanmaydi.
Yuqoridagilarga asosan:
- jinoyat ishining barcha materiallarini tanishib chiqish uchun taqdim etishingizni;
- tanishib chiqish vaqti va joyini oldindan xabar qilishingizni soʻrayman.
{% if qoshimcha %}Shuningdek: {{ qoshimcha }}
{% endif %}Ish materiallari bilan tanishib chiqqanimdan soʻng JPKning 377-moddasiga muvofiq iltimoslar berish huquqimni saqlab qolaman.

~ Himoyachi, advokat {{ advokat_fio }} | ____________
~ {{ bugun }} |""",
    },
    {
        "title": "Ishonchnoma (jismoniy shaxs nomidan, oddiy yozma shakl)",
        "category": "POWER_OF_ATTORNEY",
        "description": "Jismoniy shaxsning uchinchi shaxslar oldida vakillik qilish uchun yozma vakolati. "
                       "Notarial shakl talab qilinadigan hollarda notariusda rasmiylashtiriladi.",
        "legal_basis": "FK 134-modda (ishonchnoma tushunchasi)\nFK 135-modda (shakli: oddiy yozma yoki notarial)",
        "form_schema": [
            {"name": "beruvchi", "label": "Ishonch bildiruvchining F.I.Sh.", "type": "text"},
            {"name": "beruvchi_pasport", "label": "Ishonch bildiruvchining pasporti (seriya, raqam, kim tomonidan, qachon)",
             "type": "text"},
            {"name": "beruvchi_jshshir", "label": "Ishonch bildiruvchining JSHSHIR", "type": "jshshir"},
            {"name": "beruvchi_manzil", "label": "Ishonch bildiruvchining manzili", "type": "text"},
            {"name": "vakil", "label": "Ishonchli vakilning F.I.Sh.", "type": "text"},
            {"name": "vakil_pasport", "label": "Ishonchli vakilning pasporti", "type": "text"},
            {"name": "vakolatlar", "label": "Vakolatlar — har biri yangi qatorda", "type": "textarea"},
            {"name": "muddat", "label": "Ishonchnoma amal qiladigan sana (gacha)", "type": "date"},
            {"name": "joy", "label": "Tuzilgan joy (shahar, tuman)", "type": "text"},
        ],
        "body": """## ISHONCHNOMA

{{ joy }}, {{ bugun }}
Men, {{ beruvchi }} (pasport: {{ beruvchi_pasport }}, JSHSHIR: {{ beruvchi_jshshir }}, manzil: {{ beruvchi_manzil }}), ushbu ishonchnoma bilan {{ vakil }}ga (pasport: {{ vakil_pasport }}) quyidagi vakolatlarni beraman:
{{ vakolatlar }}
Ishonchnoma {{ muddat }}gacha amal qiladi. Vakolatlarni boshqa shaxsga oʻtkazish huquqi berilmaydi.
Ishonchnoma Oʻzbekiston Respublikasi Fuqarolik kodeksining 134–135-moddalariga muvofiq oddiy yozma shaklda berildi. Qonunchilikda notarial shakl talab qilingan harakatlar uchun ishonchnoma notarial tasdiqlanishi kerak.

~ Ishonch bildiruvchi: {{ beruvchi }} | ____________""",
    },
    {
        "title": "Qarzni undirish toʻgʻrisida daʼvo arizasi",
        "category": "CLAIM",
        "description": "Qarz shartnomasi (tilxat) boʻyicha qaytarilmagan pulni fuqarolik sudi orqali undirish.",
        "legal_basis": "FPK 188-modda (ish ariza berish yoʻli bilan qoʻzgʻatiladi)\nFPK 189-modda (arizaning mazmuni)\n"
                       "FK 732-modda (qarz shartnomasi)\nFK 735-modda (qarzni qaytarish majburiyati)",
        "form_schema": [
            {"name": "sud", "label": "Sud nomi (masalan: Fuqarolik ishlari boʻyicha Sergeli tumanlararo sudi)",
             "type": "text"},
            {"name": "davogar", "label": "Daʼvogarning F.I.Sh.", "type": "text"},
            {"name": "davogar_manzil", "label": "Daʼvogarning yashash joyi", "type": "text"},
            {"name": "davogar_telefon", "label": "Daʼvogarning telefoni", "type": "phone"},
            {"name": "vakil", "label": "Vakil (advokat) F.I.Sh. va manzili", "type": "text", "required": False},
            {"name": "javobgar", "label": "Javobgarning F.I.Sh.", "type": "text"},
            {"name": "javobgar_manzil", "label": "Javobgarning yashash joyi", "type": "text"},
            {"name": "qarz_sanasi", "label": "Qarz berilgan sana", "type": "date"},
            {"name": "qarz_summasi", "label": "Qarz summasi, soʻm", "type": "money"},
            {"name": "qaytarish_sanasi", "label": "Qaytarish muddati (shartnoma/tilxat boʻyicha)", "type": "date"},
            {"name": "qaytarilgan", "label": "Qisman qaytarilgan summa, soʻm (boʻlmasa — 0)", "type": "money"},
            {"name": "undiriladigan", "label": "Undiriladigan summa (daʼvo bahosi), soʻm", "type": "money"},
            {"name": "dalil", "label": "Qarzni tasdiqlovchi hujjat", "type": "select",
             "options": ["qarz shartnomasi", "tilxat (tilxat-raspiska)", "bank oʻtkazmasi toʻgʻrisidagi koʻchirma"]},
            {"name": "holatlar", "label": "Qoʻshimcha holatlar (talab qilinganligi, javobgarning javobi va h.k.)",
             "type": "textarea", "required": False},
        ],
        "body": """>> {{ sud }}ga
>> Daʼvogar: {{ davogar }}
>> Yashash joyi: {{ davogar_manzil }}, tel.: {{ davogar_telefon }}
{% if vakil %}>> Vakil: {{ vakil }}
{% endif %}>> Javobgar: {{ javobgar }}
>> Yashash joyi: {{ javobgar_manzil }}
>> Daʼvo bahosi: {{ undiriladigan }} soʻm

## DAʼVO ARIZASI
## (qarzni undirish toʻgʻrisida)

{{ qarz_sanasi }} kuni men javobgar {{ javobgar }}ga {{ qarz_summasi }} soʻm miqdorida qarz berganman, bu {{ dalil }} bilan tasdiqlanadi. Javobgar qarzni {{ qaytarish_sanasi }}gacha qaytarish majburiyatini olgan.
Belgilangan muddat oʻtgan boʻlsa-da, javobgar qarzni toʻliq qaytarmadi: qaytarilgan summa {{ qaytarilgan }} soʻmni, qaytarilmagan qarz {{ undiriladigan }} soʻmni tashkil etadi.
{% if holatlar %}{{ holatlar }}
{% endif %}Oʻzbekiston Respublikasi Fuqarolik kodeksining 732-moddasiga muvofiq qarz shartnomasi boʻyicha qarz beruvchi qarz oluvchiga pulni mulk qilib beradi, qarz oluvchi esa qarz beruvchiga oʻshancha summadagi pulni (qarz summasini) qaytarib berish majburiyatini oladi; 735-moddasiga muvofiq qarz oluvchi olingan qarz summasini shartnomada nazarda tutilgan muddatda va tartibda qaytarishi shart.
Yuqoridagilarga asosan va Fuqarolik protsessual kodeksining 188–189-moddalariga amal qilib, sizdan soʻrayman:
- javobgar {{ javobgar }}dan mening foydamga {{ undiriladigan }} soʻm qarzni undirishni;
- sud xarajatlarini javobgar zimmasiga yuklashni.

### Ilova:
- {{ dalil }} nusxasi;
- daʼvo arizasining javobgar uchun nusxasi;
- davlat boji toʻlanganligini tasdiqlovchi hujjat;
- shaxsni tasdiqlovchi hujjat nusxasi.

~ Daʼvogar: {{ davogar }} | ____________
~ {{ bugun }} |""",
    },
    {
        "title": "Hukm ustidan apellyatsiya shikoyati (jinoyat ishi)",
        "category": "APPEAL",
        "description": "Birinchi instansiya sudi hukmi ustidan himoyachining apellyatsiya shikoyati. "
                       "Muddat — hukm eʼlon qilingan kundan (mahkum uchun — koʻchirma nusxa topshirilgan kundan) oʻn sutka.",
        "legal_basis": "JPK 480-modda (shikoyat mazmuniga talablar)\nJPK 497⁴-modda (apellyatsiya shikoyati muddati — oʻn sutka)",
        "form_schema": [
            {"name": "apellyatsiya_sudi", "label": "Shikoyat yoʻllanayotgan sud (apellyatsiya instansiyasi)", "type": "text"},
            {"name": "birinchi_sud", "label": "Hukm chiqargan sud", "type": "text"},
            {"name": "hukm_sanasi", "label": "Hukm sanasi", "type": "date"},
            {"name": "mahkum", "label": "Mahkumning F.I.Sh.", "type": "text"},
            {"name": "modda", "label": "Ayblangan modda (masalan: JK 168-modda 2-qism)", "type": "text"},
            {"name": "jazo", "label": "Tayinlangan jazo", "type": "text"},
            {"name": "asoslar", "label": "Hukmning nimasi bilan rozi emassiz (dalillar, qonun buzilishlari) — har biri yangi qatorda",
             "type": "textarea"},
            {"name": "talab", "label": "Talab", "type": "select",
             "options": ["hukmni bekor qilib, ish yuritishni tugatishni (oqlov hukmi chiqarishni)",
                         "hukmni bekor qilib, ishni yangidan sud muhokamasiga yuborishni",
                         "hukmni oʻzgartirib, jazoni yengillashtirishni"]},
            *ADVOCATE,
        ],
        "body": """>> {{ apellyatsiya_sudi }}ga
>> {{ birinchi_sud }}ning {{ hukm_sanasi }}dagi hukmi ustidan
>> mahkum {{ mahkum }} himoyachisi
>> advokat {{ advokat_fio }}dan
>> ({{ advokat_tashkiloti }}, guvohnoma № {{ guvohnoma_raqami }})
>> {{ advokat_manzili }}, tel.: {{ advokat_telefon }}

## APELLYATSIYA SHIKOYATI

{{ birinchi_sud }}ning {{ hukm_sanasi }}dagi hukmi bilan {{ mahkum }} {{ modda }} bilan aybli deb topilib, unga {{ jazo }} jazosi tayinlangan.
Himoya hukmni asossiz va qonunga xilof deb hisoblaydi, chunki:
{{ asoslar }}
Bayon etilganlarga asosan va Oʻzbekiston Respublikasi Jinoyat-protsessual kodeksining 480-moddasi talablariga amal qilib, {{ birinchi_sud }}ning {{ hukm_sanasi }}dagi hukmini {{ talab }} soʻrayman.

### Ilova:
- shikoyatning nusxalari;
- himoyachining vakolatini tasdiqlovchi order.

~ Himoyachi, advokat {{ advokat_fio }} | ____________
~ {{ bugun }} |""",
    },
]
