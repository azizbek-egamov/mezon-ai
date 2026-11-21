# MEZON AI — joriy holat tahlili va LLM API siz ish rejasi (2026-10-26)

Asos: TZ-v2.1.md, `mezon_backend` kodi va bazasi (2026-10-26 holatida tekshirildi). LLM API ga pul sarflanmaydi —
quyidagi ishlarning hammasi kod, lokal modellar yoki lex.uz dan yuklash bilan bajariladi.

## 1. Nima tayyor

| Qism | Holat | Raqamlar |
|---|---|---|
| lex.uz reyestri | ✅ | 57 884 hujjat; CORE 1 499, EXTENDED 10 835, ON_DEMAND 45 550 |
| Yadro korpusi (joriy tahrir) | ✅ | 1 499 hujjat, 30 668 modda/band, `lex_elem_id` havolalar |
| Gibrid qidiruv | ✅ | bge-m3 dense+sparse, reranker, iyerarxiya vazni, o'zgartiruvchi hujjatlarga jarima |
| Iqtibosli javob + tekshiruv | ✅ | «iqtibos»[M#] so'zma-so'z tekshiriladi (Claude API bilan) |
| Ish tahlili zanjiri | ✅ prototip | OCR → PII → faktlar → ziddiyatlar → lex.uz asoslash; case_01: 12/12 |
| OCR | ✅ | RapidOCR, bosma matn CER 0.51% |
| PII niqoblash | ✅ | regex + ism qoidalari, case_01 da 0 sizish |
| Veb (chat, /cases/) | ✅ prototip | Django shablonlari, fon oqimi |
| Testlar | ✅ | 50 ta |

## 2. Kamchiliklar (muhimlik bo'yicha)

### 🔴 Xavfsizlik — haqiqiy ish yuklashdan OLDIN tuzatilishi shart
1. **Login yo'q.** `/cases/` dagi barcha ishlar, PDF lar va hisobotlar havolani bilgan har kimga ochiq. Rollar
   (CLIENT/LAWYER/MODERATOR/SUPERADMIN, TZ §1.3) yo'q.
2. **Hisobotlar diskda ochiq.** `data/case_runs/*.json` da F.I.Sh. va boshqa ma'lumotlar niqobsiz, yuklangan PDF lar ham
   shifrlanmagan. TZ §5.3: asl qiymatlar shifrlangan, Zero-Retention rejimi (tahlildan keyin fayl o'chiriladi).
3. **API chegarasi umumiy.** Xarajat chegarasi jarayon bo'yicha, foydalanuvchi bo'yicha emas — kvotalar yo'q (TZ §7.2).

### 🟠 Huquqiy to'g'rilik
4. **Tahrirlar tarixi yo'q.** Bazada 6 742 tahrir yorlig'i bor, lekin moddalar faqat joriy tahrir bo'yicha
   (30 668 ta, hammasi `is_current`), `valid_from/valid_until` bo'sh. TZ §4.2.3 talab qiladi: voqea sanasidagi tahrir.
   Hozir 2024-yilgi voqeaga 2026-yilgi matn keltirilishi mumkin — bu advokat uchun eng xavfli xato.
5. **Deterministik tekshiruv to'liq emas** (TZ §4.3.1). Iqtibos matni tekshiriladi, lekin: modda voqea sanasida
   kuchdami; hujjat kuchini yo'qotganmi; "…bundan mustasno", "Eslatma" qismlari tushib qolmaganmi — tekshirilmaydi.
6. **Hujjat statusi va sanalari:** `effective_from` 0 ta hujjatda to'ldirilgan.
7. **Faqat jinoyat ishlari** uchun qidiruv doirasi bor (`CASE_SCOPES`). Fuqarolik, iqtisodiy, ma'muriy, mehnat
   (TZ §7.4 `case_category`) yo'q.

### 🟡 Funksional bo'shliqlar
8. **Ko'p tillilik:** moddalarning faqat 121 tasida kirill matni bor, rus matni umuman yo'q (TZ §5.4: lotin, kirill,
   rus indekslanadi). Interfeys i18n yo'q (matnlar shablonlarga yozilgan).
9. **Sinxronizatsiya yo'q** (TZ §6.4): lex.uz dagi yangi hujjat va tahrirlar avtomatik olinmaydi.
10. **Yuklash:** faqat bitta PDF. DOCX, JPG/PNG, bir ishga bir nechta fayl, 60 varaqdan ortiq — yo'q.
    OCR: deskew/tozalash yo'q, o'zbek kirilidagi ў қ ғ ҳ tanilmaydi.
11. **Hujjatlar konstruktori yo'q** (TZ §5.1): shablonlar (docxtpl), forma, DOCX/PDF.
12. **Human-in-the-Loop yo'q** (TZ §12): "tanishdim" tasdig'i, DOCX/PDF eksport, `lawyer_confirmed`.
13. **Billing, anti-fraud, SuperAdmin** (TZ §7.1–7.2, §8) — umuman yo'q.
14. **Sud amaliyoti** importi — siz ma'lumot bergach.

### ⚪ Infratuzilma
15. SQLite (TZ: PostgreSQL 16 + FTS/pg_trgm), Celery/Redis o'rniga oqim (thread), ichki Qdrant — bitta jarayon.
    Dev PC da Docker yo'q, shuning uchun bu server bosqichida qilinadi; kod Postgres ga tayyor (`DATABASE_URL`).
16. Bitta GPU navbati, WebSocket o'rniga 2 s lik so'rov — beta uchun yetarli.

### TZ bilan nomuvofiqlik
- TZ §13 1-qaror: "tashqi AI API ishlatilmaydi". Amalda Claude API ishlatilmoqda. TZ ni yangilash yoki lokal LLM
  provayderini (Ollama, allaqachon bor) zaxira sifatida saqlash kerak.

## 3. LLM API siz bajariladigan ishlar rejasi

| # | Ish | TZ | Nega birinchi | Hajm |
|---|---|---|---|---|
| 1 | **Akkauntlar va kirish:** telefon + parol (SMS OTP keyin), rollar, ish faqat egasiga ko'rinadi, admin | §1.3, §7.1 | Haqiqiy ishdan oldin shart | 1–2 kun |
| 2 | **Ma'lumotlarni himoyalash:** hisobot va PDF ni shifrlash (Fernet/AES), Zero-Retention (tahlildan keyin PDF o'chirish), ishni o'chirish tugmasi | §5.3 | Advokatlik siri | 1 kun |
| 3 | **Tahrirlar tarixi:** yadro kodekslarining barcha tahrirlarini yuklash, `valid_from/until`, "voqea sanasi" bo'yicha qidiruv | §4.2.3, §6.1 | Eng xavfli huquqiy xato | 2–3 kun (+ fon yuklash) |
| 4 | **Deterministik tekshiruvchi:** modda bazada bor va sanada kuchda; istisno/eslatma qismlari tushmagan; status | §4.3.1–2 | 3 ga tayanadi | 1–2 kun |
| 5 | **HITL va eksport:** "tanishdim" oynasi, hisobotni DOCX/PDF qilish (docxtpl) | §12 | Advokatga tayyor mahsulot | 1–2 kun |
| 6 | **Hujjatlar konstruktori (AI siz):** shablon modeli, JSON-sxemadan forma, 3–5 ta boshlang'ich shablon | §5.1.1 | Sotiladigan funksiya, LLM kerak emas | 2–3 kun |
| 7 | **lex.uz sinxronizatsiyasi:** RSS + oxirgi 60 kun, yangi tahrirda qayta indekslash | §6.4 | Korpus eskirmasin | 1 kun |
| 8 | **Kirill va rus matnlari:** yadro hujjatlarining til versiyalarini yuklash va indekslash | §5.4 | 5 til talabi | 1–2 kun (+ fon) |
| 9 | **Yuklash kengaytmasi:** DOCX, JPG/PNG, bir nechta fayl, deskew | §1.2 | Haqiqiy ishlar shunday keladi | 1–2 kun |
| 10 | **Interfeys i18n** (uz-Latn, uz-Cyrl, ru, kaa, en) | §5.4 | | 1–2 kun |
| 11 | **Tariflar va kvotalar** (Payme/Click — merchant kalitlari kelgach) | §7.2, §8 | | 2–3 kun |
| 12 | **Boshqa ish turlari:** fuqarolik/iqtisodiy/ma'muriy uchun qidiruv doiralari | §7.4 | | 0.5 kun |

Tavsiya: **1 → 2 → 3 → 4** tartibida. 1–2 bo'lmasa haqiqiy ish yuklab bo'lmaydi; 3–4 bo'lmasa tizim eskirgan qonunni
keltirishi mumkin. Keyin 5–6 (advokatga ko'rinadigan qiymat).
