# lex.uz metadata tahlili — `barcha_57950_hujjat.json`

Sana: 2026-10-23. Skriptlar: `analysis/analyze.py`, `analyze2.py`, `analyze3.py`
(`python -I analysis/analyze.py lex-uz-dagi-qonunlar/barcha_57950_hujjat.json`).

## 1. Umumiy holat
| Ko'rsatkich | Qiymat |
|---|---|
| Yozuvlar | 57 950 (dublikat id yo'q) |
| Maydonlar | 10 ta, hamma yozuvda bir xil: id, title, act_type, act_number, act_date, status, url, passport_url, pdf_url, word_url |
| Matn | **yo'q** — faqat metadata |
| Kuchda / kuchini yo'qotgan | 41 369 (71%) / 16 581 (29%) |
| Sana oralig'i | 1948-07-09 … 2026-10-19 (yig'ilgan sana: 2026-10-20) |
| Tartib | sana bo'yicha kamayuvchi, 0 buzilish (sanasizlar aralash joylashgan) |
| URL lar | hammasi id dan to'g'ri yasalgan (0 nomuvofiq) — saqlash shart emas, id dan hosil qilsa bo'ladi |

## 2. Maydonlar to'liqligi
| Maydon | Bo'sh | Izoh |
|---|---|---|
| act_number | 14 044 (24%) | asosan vazirlik buyruqlari, standartlar, shartnomalar |
| act_date | 5 998 (10%) | standartlashtirish agentligi (1 042), Moliya vazirligi (964), Bitim/Konvensiya |
| act_type | 40 | **jumladan Konstitutsiya!** (`-6445145`, `-20596`, Qoraqalpog'iston `-4953674`) |
| act_type axlat | 56× `'1'`, `'s'`, `'f'`, `'123'`, `'or'`, `'\uf020\uf020'` … | lex.uz manba xatolari |

## 3. Hujjat turlari (act_type: 5 025 noyob qiymat)
Normallashtirish (katta/kichik harf, bo'shliq) 4 290 gacha tushiradi; bitta tur o'nlab yozilishga ega
(masalan Plenum uchun 20 xil: "Plenumining", "plenumning", "Plenuminingning", "Oliy Sudi" …).

| Kategoriya (kalit so'z bo'yicha) | Jami | Kuchda |
|---|---|---|
| Oliy Majlis palatalari / Kengashlar qarorlari | 16 232 | 95% |
| Vazirlar Mahkamasi | 11 859 | 52% |
| Boshqa qarorlar (hokim, bank, qo'mita…) | 11 232 | 65% |
| Aniqlanmagan | 5 929 | 53% |
| Vazirlik buyruqlari | 3 723 | 64% |
| Prezident qarori | 3 618 | 79% |
| Prezident farmoni | 1 865 | 60% |
| Qonun | 1 717 (sof "O'zR Qonuni" — 1 436) | 81% |
| Xalqaro shartnoma | 1 224 | 98% |
| Plenum | 316 | 69% (kuchda 218) |
| Konstitutsiyaviy qonun | 60 | 98% |
| Kodeks | 25 | 92% |

**Kuchdagi 21 kodeks** ro'yxati olingan (JK `-111453`, JPK `-111460`, FK-1 `-111189`, FK-2 `-180552`,
MJtK `-97664`, Mehnat `-6257288`, Soliq `-4674902`, FPK `-3517337`, IPK `-3523891`, MSIYuK `-3527353`,
Oila, Uy-joy, Yer, Suv, Havo, Bojxona, Budjet, Saylov, Shaharsozlik, JIK …).
Eslatma: "Gaaga axloq kodeksi" va "Axloq kodeksi" ham `kodeks` deb belgilangan — ular kodeks emas.

## 4. Til / yozuv va id ishorasi
- Manfiy id: 52 384 (hammasi lotin). Musbat id: 5 566 → 2 537 kirill/rus + **3 029 lotin**.
- Musbat-lotin hujjatlarning 87% i 2025–2026 yillarga to'g'ri keladi (mahalliy Kengash, hokim, palata qarorlari).
  ⇒ **Xotiradagi "id ishorasi = yozuv" qoidasi yangi hujjatlar uchun ishonchsiz.** Yozuvni sarlavha belgilaridan aniqlash kerak.
- Bir abs(id) ning lotin+kirill juftligi faqat 66 ta (57 884 noyob abs id) — ro'yxat amalda har hujjatning bitta nusxasi.
- ~710 sarlavha ruscha (standartlar: "Водки", "Айран" kabi 1 so'zli sarlavhalar), Qoraqalpoq tilidagilar ham bor.
- 23 sarlavhada lotin so'z ichida kirill harflar (homoglif: "pаrlаmеnt") — qidiruvda topilmay qoladi.
- Apostrof: `ʻ` 240 394, `ʼ` 11 808, `'` 132, `` ` `` 97 — normallashtirish shart.
- 585 sarlavhada ortiqcha bo'shliq; 3 ta sarlavha faqat "." dan iborat.

## 5. Vaqt dinamikasi
- 2020-yillar: 26 573 (46%), 2010-yillar: 14 333, 2000-yillar: 6 191, 1990-yillar: 4 776.
- Kuchdagi ulush yoshga qarab tushadi: 1990-lar 24%, 2000-lar 45%, 2010-lar 64%, 2020-lar 91%.
- Eng faol yil — 2022 (5 160). 2026: 2 364 (sentyabr 151, oktyabr 51 — lex.uz ga kiritishdagi kechikish ehtimoli; qayta sync kerak).
- Qonunlar yiliga 50–120 ta (2024 — 121); qonunlarning **54% i (775) o'zgartirish kirituvchi**.

## 6. MEZON uchun xulosalar
1. **Core korpus hajmi**: kuchdagi Qonun+Kodeks+Konst.qonun+Plenum = **1 546** (xotiradagi ~1 500 bahosi tasdiqlandi).
   O'zgartirish kirituvchilarni chiqarsak — 738 ta "asosiy" hujjat. + Konstitutsiya (`-6445145`) **qo'lda qo'shilishi shart** —
   act_type bo'sh bo'lgani uchun har qanday tur filtri uni tashlab ketadi.
2. Kengaytirilgan korpus: kuchdagi Prezident farmon/qarorlari 4 173 + VM qarorlari 6 172 — on-demand qatlamga mos.
3. **Retrieval shovqini**: 29% hujjat (16 861) o'zgartirish/qo'shimcha kirituvchi; 1 588 "kuchini yo'qotgan deb topish".
   Ular uchun past vazn yoki alohida `is_amending` bayrog'i kerak. Takroriy sarlavhalar 4 416 ta
   ("kun tartibi to'g'risida" 454, "Xalqaro shartnomani tasdiqlash" 301) — sarlavha bo'yicha dedup qilmang, id bo'yicha qiling.
4. **act_type ni kanonik turga xaritalash** (≈15 kategoriya + organ) registry.db da alohida ustun bo'lishi kerak; xom qiymat ishonchsiz.
5. Normallashtirish zanjiri: apostroflarni `ʻ`/`ʼ` ga birlashtirish, homoglif kirill→lotin, bo'shliqlarni qisqartirish, yozuvni belgilar bo'yicha aniqlash.
6. Act_number formatlari tur haqida signal beradi: `PF-N-son` (farmon), `PQ-N-son` (Prezident qarori),
   `N-N-N-Q/N-son` (Senat/palata), `N-IV/V-son` (Oliy Majlis chaqiriqlari) — act_type bo'sh/axlat bo'lsa zaxira klassifikator sifatida ishlatish mumkin.
7. Status faqat ikki qiymatli; "qisman kuchini yo'qotgan" yoki "kuchga kirmagan" holatlar yo'q — modda darajasidagi holatni matn parseridan olish kerak.

## 7. Boshqa fayllar
- `lex_scraper.py`: ASP.NET postback orqali `unique` qidiruv; status faqat ikona klassidan (`status_code_y`) aniqlanadi;
  checkpoint har 20 sahifada; qayta urinish bitta. README da "~28 450" va "~1 586" — eskirgan raqamlar (hozir qonunlar 1 436).
- `designs/` — 8 ta ekran (HTML + PNG) va `DESIGN.md`; `MEZON-AI.pdf` — TZ (ma'lumot emas, tahlil qilinmadi).
- Xotirada tilga olingan `backend/`, `data/registry.db`, `mezon_ai_tz.txt` hozir `E:\mezon` da **mavjud emas**.
