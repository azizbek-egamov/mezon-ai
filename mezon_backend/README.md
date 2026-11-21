# MEZON AI — backend

TZ: `../TZ-v2.1.md`. Hozirgi holat: backend (1–12-bosqichlar) tayyor; faza 2 — JSON API v1 (13) va React veb-sayt (14, `../frontend/README.md`) tayyor; keyin admin va Expo (`../HANDOFF.md`).

## O'rnatish
```bash
python -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt
cp .env.example .env
.venv/Scripts/python manage.py migrate
```
PostgreSQL o'rnatilguncha SQLite (`data/dev.sqlite3`) ishlatiladi; o'tish uchun `.env` da `DATABASE_URL=postgres://...`.

## lex.uz korpusi (`apps/lex_corpus`)
```bash
# 1. Reyestrni import qilish (57 950 yozuv -> 57 884 hujjat, ~10 s)
.venv/Scripts/python manage.py import_registry

# 2. Hujjat matnini yuklab, moddalarga ajratish (kesh: data/lex_cache)
.venv/Scripts/python manage.py fetch_documents 111453 111460      # aniq hujjatlar
.venv/Scripts/python manage.py fetch_documents --tier CORE --skip-synced

# Testlar
.venv/Scripts/python manage.py test apps.lex_corpus
```

| Modul | Vazifasi |
|---|---|
| `normalize.py` | Yozuv aniqlash, apostrof/homoglif tuzatish, hujjat turi (14 tur), iyerarxiya vazni, korpus qatlami |
| `parser.py` | lex.uz HTML → moddalar, qismlar (har bir abzas element id si bilan), bo'lim/bob yo'li, tahrirlar ro'yxati |
| `lexuz_client.py` | Kechikish va disk keshi bilan yuklash; tahrir `?ONDATE=<yorliq>` |
| `models.py` | `LegalActDocument`, `LegalActEdition`, `LegalActArticle` (TZ §7.3) |

lex.uz sahifa tuzilishi bo'yicha eslatmalar `parser.py` boshidagi izohda.

### Yadro korpusi holati (2026-10-23)
1 499 hujjat yuklandi (xatosiz; kesh 303 MB, ~25 daq), keshdan qayta parsing ~1.5 daq.
Matn birliklari: 30 668 — modda 24 961, Plenum va boshqa bandlar 4 746, kirish qismi 727, butun matn 234.

Ma'lum cheklovlar:
- 2 hujjatda lex.uz sahifasining o'zida matn yo'q (5794730, 5679405).
- 5 ta o'zgartirish kirituvchi hujjatda 8 ta takroriy modda raqami (iqtiboslangan yangi matn qo'shtirnoqsiz keltirilgan).
- Qism raqamlash bo'sh ACT_TEXT ajratkichiga tayanadi — yurist bilan tanlab tekshirish kerak.

## Qonun tahrirlari tarixi va voqea sanasi (`apps/lex_corpus/history.py`, TZ §4.2.3)

- `python manage.py fetch_history --scope criminal [--since 2016-01-01]` (yoki abs_id lar / `--codes`): hujjatning
  barcha tahrirlari (`?ONDATE=`) yuklanadi va har bir modda/band uchun **faqat matni o'zgarganda** yangi versiya
  yoziladi: `valid_from` (tahrir sanasi) – `valid_until` (keyingi o'zgarishdan bir kun oldin). Joriy tahrir
  qatorlari (Qdrant da) o'z joyida qoladi; eski versiyalar alohida qatorlar, havolasi `?ONDATE=` bilan.
  `unit_key` ('ARTICLE:168#1') — tahrirlar orasida barqaror kalit. `history_from` — tarix qaysi sanadan bor.
- Kelajak sanali tahrirlar ham olinadi (valid_from > bugun). Bir kunda bir nechta tahrir bo'lsa, oraliq versiya
  tashlanadi. Taxmin: tahrir yorlig'idagi sana — kuchga kirish sanasi.
- Qidiruv joriy matn bo'yicha topadi, keyin `apply_date(hits, on_date)`: moddaning sanadagi versiyasi olinadi
  (`as_of`: same / changed / not_yet / unknown). `changed` — LLM ga ikkala matn beriladi ("voqea sanasidagi" va
  "hozirgi"; yengillashtiruvchi o'zgarish — orqaga qaytish kuchi), iqtibos ikkalasidan ham tekshiriladi;
  `not_yet` (sanada hali yo'q norma) — natijadan chiqariladi; `unknown` — tarix yuklanmagan, izoh bilan.
- Chat: ixtiyoriy "voqea sanasi" maydoni (`/api/ask` da `on_date`). Ish tahlili: har bir topilma uchun sana —
  uning faktlaridagi eng kech sana (`legal.finding_date`).
- `fetch_documents` hujjatni qayta yuklasa, tarix tozalanadi — keyin `fetch_history` ni qayta ishga tushiring.
- Cheklov: hozirgi tahrirda yo'q (chiqarilgan) moddalar Qdrant da indekslanmagan — sanadagi qidiruv ularni
  topmaydi (bazada bor, `as_of` ishlatmaydi).

## Deterministik huquqiy tekshiruvchi (`apps/rag/verifier.py`, TZ §4.3.1–2)

`verify_answer` (iqtibos manbada so'zma-so'z bormi) dan keyin chat javobi va ish bo'yicha har bir huquqiy baho
bazaga solishtiriladi (`verify_legal`):
- keltirilgan hujjat kuchdami (kuchini yo'qotgan — **xato**);
- "JK 168-modda", "JPK 226-moddasining 2-qismi" kabi havolalar: modda hujjatda yo'q — **xato** (o'ylab topilgan);
  voqea sanasida hali kuchga kirmagan yoki chiqarilgan — **xato**; qism raqami moddadagi qismlar sonidan katta —
  ogohlantirish (qismlar abzatslardan taxminan sanaladi);
- iqtibos olingan qismda iqtibosga va javobga kirmagan "…bundan mustasno", "…qo'llanilmaydi" — ogohlantirish
  (istisno tushib qolgan); moddada "Izoh" — ma'lumot;
- sanadagi tahrir aniqlanmasa: tarix yuklangan hujjatda — ogohlantirish, tarixsiz hujjatda (Plenum) — ma'lumot.
Xato bo'lgan baho "tekshiruvdan o'tmagan" hisoblanadi va (muhimligi yuqori bo'lsa) kuchliroq model bilan qayta
baholanadi. Real case_01 hisobotidagi 20 ta bahoda soxta xato chiqmadi.

## Qdrant server va xotira (2026-10-26)

- Qdrant endi alohida server: `E:/mezon/qdrant_server/qdrant.exe` (rasmiy v1.20.0, Windows), sozlama
  `E:/mezon/qdrant_server/config.yaml` — faqat 127.0.0.1, telemetriyasiz, ma'lumot `data/qdrant_server` da.
  Ishga tushirish: `.claude/launch.json` dagi `qdrant` (avval u, keyin `mezon-backend`), yoki
  `qdrant.exe --config-path E:/mezon/qdrant_server/config.yaml`. `.env`: `QDRANT_URL=http://127.0.0.1:6333`.
- Kolleksiya diskdan ishlaydi (vektorlar, HNSW, sparse indeks, payload — on_disk). Dense qidiruv `exact=True`
  (41 ming nuqtada ~10 ms; ichki rejimdagi natijalar bilan 100% bir xil, ichki rejim ~136 ms edi).
- Eski ichki kolleksiyani ko'chirish: `python manage.py migrate_qdrant --url http://127.0.0.1:6333`.
  Ichki rejim (`data/qdrant`) zaxira sifatida qoldi — `QDRANT_URL` bo'sh bo'lsa ishlatiladi.
- Modellar GPU da (fp16): `E:/models/bge-m3-fp16`, `E:/models/bge-reranker-v2-m3-fp16` — asl `.bin` ning
  safetensors nusxasi (natija bir xil, RAM da ~1 GB kam). Videokartada ~2.2 GB.
- O'lchov: dev server ~5 GB RAM → Django ~1.9 GB + Qdrant ~0.5 GB. Endi bir nechta jarayon (veb server va
  buyruqlar) Qdrant'dan bir vaqtda foydalana oladi.

## lex.uz bilan sinxronizatsiya (`apps/lex_corpus/sync.py`, TZ §6.4)

- `python manage.py sync_lex [--days 60] [--check-codes] [--no-index]`:
  1. RSS (`/uz/rss`, kuchga kirish sanasi bilan) va reyestr qidiruvining birinchi sahifalari (oxirgi 60 kun) o'qiladi;
  2. yangi hujjatlar reyestrga qo'shiladi, maqomi o'zgarganlari yangilanadi (yadrodan chiqqani indeksdan o'chiriladi);
  3. qayta tekshiriladigan yadro hujjatlari: yangi yadro hujjatlari; yangi o'zgartirish kirituvchi hujjat sahifasida
     havola qilingan yadro hujjatlari; kelajak sanali tahriri kuchga kirgan hujjatlar; `--check-codes` — barcha
     kodekslar. Joriy tahrir yorlig'i o'zgargan bo'lsa — qayta parsing, qayta indekslash (`apps/rag/indexer.py`) va
     tahrirlar tarixini yangilash; o'zgarmagan bo'lsa faqat yangi (kelajak) tahrirlar ro'yxatga qo'shiladi;
  4. natija `SyncRun` jurnalida (admin → "lex.uz sinxronizatsiyalari").
- Birinchi haqiqiy ishga tushirish (2026-10-26, 14 kun): 37 yangi hujjat, Soliq kodeksi yangi tahrirga
  (21.10.2026) yangilandi, 2 yangi qonun indekslandi, 51 s.
- Tungi ishga tushirish: `tools/nightly_sync.ps1` (Qdrant ishlamasa vaqtincha yoqadi, yakshanba `--check-codes`,
  jurnal `data/logs/sync_YYYYMMDD.log`). Windows Task Scheduler:
  `schtasks /Create /TN "MEZON lex.uz sync" /SC DAILY /ST 02:00 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File E:\mezon\mezon_backend	ools
ightly_sync.ps1"`.
  Production da — Celery beat yoki cron.

## Kirill va rus matnlari (`apps/lex_corpus/translations.py`, TZ §5.4, 8-bosqich)

lex.uz da har bir til versiyasi alohida hujjat: lotin — manfiy id (-111453), kirill — musbat (111453), rus — boshqa
raqam (111457). id lar hujjat sarlavhasidagi til almashtirgichdan olinadi (`parser.parse_language_links`).
```bash
.venv/Scripts/python manage.py fetch_translations --tier CORE --skip-done   # ~55 daq (2 ta so'rov/hujjat, 1 s kechikish)
.venv/Scripts/python manage.py build_index --langs cyr ru                   # mavjud indeksga QO'SHADI (~90 ming bo'lak)
```
- Moddalar asosiy (lotin) moddaga `unit_key` ("ARTICLE:168#1") bo'yicha moslanadi. Matn `content_uz_cyr` / `content_ru`,
  sarlavha, qismlar (til sahifasidagi element id lari bilan), bo'lim yo'li — `LegalActArticle.i18n[til]`.
  `source_lang` — `heading/parts` qaysi tilda. Holat — `LegalActDocument.translations[til]` (matched/total, stale, rejected).
- Tarjima tahriri asosiydan sanasi bilan farq qilsa, uning ro'yxatidagi mos tahrir (`?ONDATE=`) olinadi; bo'lmasa `stale`
  (javob manbasida ogohlantirish). Moddalarning <50% mos kelmasa — tarjima saqlanmaydi (`rejected`).
- Indeks: har bir til alohida bo'laklar (`payload.lang`, `label`); asosiy til id lari o'zgarmagan. Qidiruv tilga
  qaramay ishlaydi, bir moddaning nusxalari `dedupe_languages` bilan birlashadi; natija `search(..., lang="ru")` /
  `search_aspects(..., lang=)` bilan so'ralgan tilga o'tkaziladi (`localize_hits`; `models.corpus_lang("uz-Cyrl")`).
  Til versiyasi yo'q bo'lsa — asosiy tilda (`payload.lang_fallback`). Eski tahrirlar (`as_of`) faqat asosiy tilda.
- `sync_lex`: yangilangan hujjatning kirill/rus matni ham qayta olinadi; `stale` tarjimalar har kecha qayta tekshiriladi.
- Natija (2026-10-27, 1 501 yadro hujjati): kirill 1 497 hujjat, 30 558/30 558 modda moslashdi; rus 1 474 hujjat
  (29 888/29 951), 21 hujjatda rus matni yo'q yoki tuzilma boshqa (17 tasida lex.uz sahifasi bo'sh) — rad etildi.
- Parser tuzatildi: rus "Статья N." (o'zgartirish kirituvchi qonunlar) va "РАЗДЕЛ / Глава" bo'lim yo'li.

## Gibrid qidiruv (`apps/rag`)
GPU uchun torch: `pip install torch==2.14.1+cu130 --index-url https://download.pytorch.org/whl/cu130`.
```bash
.venv/Scripts/python manage.py build_index --recreate          # 41 461 bo'lak, ~21 daq (RTX 2060S)
.venv/Scripts/python manage.py search "mast holda mashina haydash" -n 5
.venv/Scripts/python manage.py eval_search                     # 20 savollik tezkor sinov
.venv/Scripts/python manage.py diag_search                     # bosqichlar bo'yicha tashxis
```
Zanjir: aniq havola ("JK 168-modda") → bge-m3 dense + sparse (Qdrant, RRF, 100 nomzod; o'zgartirish
kirituvchi hujjatlar sukut bo'yicha chiqariladi) → bge-reranker-v2-m3 → iyerarxiya vazni.

Sinov natijalari (2026-10-24, 20 savol):

| Sozlama | Hit@1 | Hit@5 | MRR | Vaqt | Narx |
|---|---|---|---|---|---|
| Qidiruv + reranker | 60% | 70% | 0.65 | 3.6 s | bepul |
| + so'rov o'girish, lokal Qwen 2.5 7B | 45% | 60% | 0.52 | 7.9 s | bepul |
| + so'rov o'girish, Claude Opus 5.5 (effort low) | **80%** | **95%** | **0.87** | 4.3 + 9.6 s | ~$0.005 / savol |

Claude ni yoqish: `.env` da `LLM_PROVIDER=anthropic` va `ANTHROPIC_API_KEY` (kalit faqat `.env` dan
o'qiladi, umumiy `ANTHROPIC_*` muhit o'zgaruvchilari e'tiborga olinmaydi). Model: `LLM_MODEL` (sukut `claude-opus-5-5`).
Tezlashtirishdan keyin (sparse faqat asl savolda, filtr Python da, 40 nomzod reranker ga):
Hit@1 **85%**, Hit@5 95%, iliq holatda qidiruv ~2.4 s (birinchi chaqiruv model va Qdrant yuklanishi bilan ~20 s).
So'rov o'girishlari keshlanadi (`data/cache`).

## Iqtibosli javob (`apps/rag/answer.py`)
```bash
.venv/Scripts/python manage.py ask "aldab pul olgan odamga qanday jazo" [--lang ru|uz-Cyrl|en|kaa] [--effort low|medium|high]
```
Qidiruv → 8 ta manba [M1..M8] → LLM javobi (stream) → kod tekshiruvi: har bir [M#] mavjudmi, «iqtibos» [M#]
manba matnida so'zma-so'z bormi, tilga olingan "N-modda" manbalarda bormi. Bitta javob (Opus 5.5, medium) ≈ $0.08–0.10,
birinchi so'z ~7 s, to'liq javob ~20–30 s.
Cheklov: iqtibos qilinmagan, o'z so'zi bilan aytilgan raqamlar (jazo muddatlari, jadvallar) hali tekshirilmaydi.

### Ko'p yo'nalishli qidiruv (`search_aspects`)
Murakkab savol bir nechta huquq sohasiga tegadi. Zanjir: Claude savolni yo'nalishlarga ajratadi
(`query_rewrite.plan_aspects`) → har bir yo'nalish alohida qidiriladi va reranker bilan baholanadi → har bir
yo'nalishdan 10 tagacha nomzod (bitta hujjatdan ≤4) → yakuniy manbalarni Claude tanlaydi (`source_select.py`;
bge-reranker o'zbekchada beqaror, masalan JK 266 ni tushirib yuborardi). Claude ishlamasa — reranker tartibi.

| Tahlil chuqurligi | Yo'nalishlar | Manbalar | Misol (mast haydovchi YTH) |
|---|---|---|---|
| tez (`low`) | ≤2 | ≤8 | — |
| o'rta (`medium`) | ≤4 | ≤15 | qidiruv ~15–30 s |
| chuqur (`high`) | ≤6 | ≤25 | qidiruv 17 s, birinchi so'z 44 s, jami 85 s, $0.26 |

## Sintetik ish (hujjat tahlilini sinash uchun)
`python tools/make_synthetic_case.py` → `fixtures/cases/case_01/case_01.pdf` (30 varaq, lotin + kirill + rus;
barcha shaxslar to'qima) va `answer_key.json` (8 ta ziddiyat, 4 ta protsessual muammo, PII qiymatlari,
xronologiya — har biri varaq raqamlari bilan).

## Ish hujjati tahlili (`apps/cases`)
```bash
.venv/Scripts/python manage.py analyze_case fixtures/cases/case_01/case_01.pdf --key fixtures/cases/case_01/answer_key.json
```
Zanjir: PDF sahifa matni (`pdf_text.py`) → PII niqoblash (`pii.py`: JSHSHIR, telefon, pasport, karta; ismlar hali yo'q)
→ 5 varaqlik bloklardan faktlar (`extract.py`: har bir fakt varaq + aynan iqtibos bilan, bloklar parallel)
→ iqtibos o'sha (yoki qo'shni) varaqda so'zma-so'z bormi — kod tekshiradi → xronologiya → ziddiyatlar va protsessual
muammolar (`analysis.py`: faqat tasdiqlangan faktlar, fakt id lari kod bilan tekshiriladi, varaqlar faktlardan olinadi).
Hisobot: `data/case_runs/<vaqt>.json`.

case_01 natijasi (2026-10-24, Opus 5.5): 30 varaq, 112 fakt (100% iqtibos tasdiqlandi), 11 ziddiyat + 11 protsessual
muammo; kalitdagi 12 bandning 12 tasi topildi (qo'lda ham tekshirildi), PII sizmadi; 170 s, $0.82.
Ma'lum kamchilik: bank ko'chirmasidagi kirim qatorlari ajratilmagani sababli bitta noto'g'ri "arifmetik ziddiyat" chiqdi.

### Huquqiy asoslash (`legal.py`)
Har bir topilma: LLM huquqiy qidiruv so'rovlarini tuzadi (bitta chaqiruv) → lex.uz dan 6 tagacha modda → LLM topilmani
FAQAT shu manbalar asosida baholaydi (verdict: qonun_buzilishi / buzilish_ehtimoli / huquqiy_ahamiyatli / asossiz),
me'yorni «aynan» [M#] keltiradi, hisob qonunga zid bo'lsa tuzatadi → `verify_answer` iqtiboslarni tekshiradi.
`--from-report` bilan faktlar va topilmalar oldingi hisobotdan olinadi (qayta to'lovsiz).

case_01 (22 topilma): 22/22 baho tekshiruvdan o'tdi, 49 ta iqtibos manbaga so'zma-so'z mos; "72 soat" xatosi
JPK 226 iqtibosi bilan 48 soatga tuzatildi; tanib olish — JPK 127 ("kamida uchta fotosurat"), ekspertiza bilan
tanishtirish — JPK 179, ayblov xulosasi talablari — JPK 379. 183 s, $1.09.
Kamchiliklar: ba'zi manbalar boshqa sohadan (Ma'muriy sud, Iqtisodiy protsessual kodekslari) — jinoyat ishida
qidiruvni JPK/JK/Konstitutsiya/Plenum bilan cheklash kerak; asoslash faktlardagi xatoni (bank arifmetikasi)
tuzata olmaydi, chunki asl sahifani ko'rmaydi.

## Xarajat nazorati va modellar (2026-10-25)
- `LLM_BUDGET_USD` (sukut $0.30) — bitta jarayon uchun chegara; tugasa `BudgetExceeded`, API ga so'rov ketmaydi.
  `analyze_case --budget X` bilan buyruq uchun alohida. Har bir chaqiruv `data/llm_usage.jsonl` ga yoziladi.
- Bosqichlar bo'yicha model: `LLM_MODEL_REWRITE|PLAN|SELECT|EXTRACT|ANALYSIS|LEGAL|ANSWER` (sukut `LLM_MODEL`).

| Sinov | Opus 5.5 | Sonnet 5.5 | Haiku 5.5 |
|---|---|---|---|
| So'rov o'girish (20 savol): Hit@1 / Hit@5 / narx | 85% / 95% / $0.097 | 70% / 95% / $0.051 | 50% / 75% / $0.002 |
| case_01 faktlar: fakt / iqtibos tasdig'i / narx | 112 / 100% / $0.54 | — | 127 / 100% / $0.014 |
| case_01 ziddiyatlar (kalit 12 band) / narx | 12/12 / $0.28 | 12/12 (medium) / ~$0.10 | — |
| case_01 huquqiy asoslash: tekshiruvdan o'tdi / narx | 22/22 / $1.09 | — | 15/22 / $0.018 |

Standart (`.env`): rewrite/plan/select/analysis/answer — Sonnet 5.5, extract/legal — Haiku 5.5,
legal_retry — Sonnet 5.5 (kaskad: tekshiruvdan o'tmagan Haiku baholari Sonnet bilan qayta baholanadi) — faqat muhimligi yuqori
topilmalar uchun; o'rta muhimlikdagi o'tmagan baho ogohlantirish bilan qoladi. Iqtibos «...» yoki "..." da bo'lishi mumkin,
partiyadagi boshqa topilma manbasidan aynan iqtibos ham qabul qilinadi. Xato bilan tugagan ish /cases/<id>/ sahifasidagi
"Qayta urinish" tugmasi bilan qayta navbatga qo'yiladi. Tahlil (ziddiyatlar / protsessual) ikki parallel chaqiruvda.
case_01 kaskad natijasi: 22/22 tekshiruvdan o'tdi, 4 tasi qayta baholandi, $0.091; butun ish ≈ $0.20 (Opus: ~$1.9).
Iqtibos qoidasi: verdict `qonun_buzilishi`/`buzilish_ehtimoli` bo'lsa, kamida bitta tekshirilgan «iqtibos» [M#] shart,
aks holda baho o'tmagan hisoblanadi va Sonnet ga qayta yuboriladi (boshqa verdictlarda — faqat ogohlantirish).
case_01: iqtiboslar 8 → 31, 11 ta qayta baholandi, 19/22 o'tdi (3 tasi Sonnet dan keyin ham iqtibossiz — ⚠ bilan
ko'rsatiladi), asoslash $0.20; butun ish ≈ $0.31 (Opus: ~$1.9).
Xarajat chegarasi qat'iy (2026-10-25): har bir chaqiruv oldindan eng yuqori narxini band qiladi; band qilinganlar
bilan chegaradan oshsa — parallel chaqiruvlar tugashini kutadi. Oshib ketish ko'pi bilan bitta chaqiruv narxicha.
Jinoyat ishida huquqiy qidiruv doirasi: JPK, JK, Konstitutsiya, JIK va Plenum qarorlari (`analyze_case --category`).

Haiku rasmiy huquqiy atamalarni bilmaydi ("tovlamachilik" o'rniga "shantaj"). Sonnet "high" effort da tahlil
bosqichida 16k tokenga yetib kesildi ($0.19 behuda) — "medium" ishlatiladi. Arzon sozlamada case_01 to'liq tahlili:
$0.13 (Opus: ~$1.9).

## Ko'p formatli yuklash va OCR yaxshilanishi (9-bosqich, 2026-10-28)

- **Yuklash** (`apps/cases/intake.py`): `/cases/` da bir yoki bir nechta fayl — PDF, DOCX, JPG/PNG (≤ `CASE_MAX_FILES`=20,
  jami ≤ `CASE_MAX_MB`=50 MB, ≤ `CASE_MAX_PAGES`=200 varaq). Hammasi yuklash paytida **bitta PDF** ga birlashtiriladi
  (tahlil zanjiri, varaq tugmalari va shifrlangan saqlash o'zgarmaydi); varaq raqamlari fayllar bo'ylab davom etadi,
  oraliqlar `CaseRun.sources` da va ish sahifasida ko'rsatiladi. Bitta PDF — o'zgarishsiz saqlanadi.
  JPG/PNG — bitta sahifa (EXIF yo'nalishi qo'llanadi, matn qatlamisiz → OCR); DOCX — abzats va jadval matni TNR 14 bilan
  matn qatlamli PDF ga chiziladi (hujjat ichidagi rasmlar o'qilmaydi — ogohlantirish). Parolli PDF, buzuq fayl, >60 mln
  piksel rasm rad etiladi.
- **Katta ish**: bitta ish xarajat chegarasi = `max(CASE_BUDGET_USD, varaq × CASE_BUDGET_PER_PAGE_USD=0.015)`.
  Haqiqiy 100+ varaqli ish bilan hali sinalmagan (case_01: 30 varaq ≈ $0.13–0.31).
- **Qiyshiq skaner** (`ocr.deskew`): gorizontal proyeksiya bo'yicha ±12° gacha burchak topiladi va to'g'rilanadi
  (<0.4° tegilmaydi). Sinov: ±3…9° burilgan sahifa qoldiq 0.1°, OCR matni to'g'ri sahifa bilan 99.9% bir xil.
- **Oʻzbek kirill** (`apps/cases/cyr_fix.py`): RapidOCR ў қ ғ ҳ ni у к г х deb o'qiydi. lex.uz kirill matnlaridan
  so'z chastotalari lug'ati (`python manage.py build_cyr_vocab`, 48 ming so'z, `data/cache/uz_cyr_vocab.json`) bo'yicha
  tiklanadi; faqat o'zbekcha deb topilgan sahifalarga, rus matni buzilmaydi. case_01 12-varaq: xatolar 48 → 12
  (o'xshashlik 95.4% → 98.9%); qolganlari ismlar va lug'atda yo'q so'zlar — sahifa baribir ogohlantirish bilan belgilanadi.

## Interfeys tillari — i18n (`apps/i18n`, TZ §5.4, 10-bosqich, 2026-10-28)

- **Tillar**: `uz-latn` (manba), `uz-cyrl`, `ru`, `kaa` (qoraqalpoq, **kirill yozuvida** — lex.uz dagi qoraqalpoq huquqiy matnlari
  kabi), `en`. TZ kodlari (`uz-Latn`…) ↔ Django kodlari: `apps/i18n/codes.py`. Django da `uz-latn/uz-cyrl/kaa` yo'q —
  `settings.EXTRA_LANG_INFO` bilan qo'shilgan.
- **Til tanlash** (`middleware.UserLocaleMiddleware`): kirgan foydalanuvchining profili (`User.language`) > cookie
  (`django_language`) > brauzer tili (`Accept-Language`: `uz` → lotin) > sukut. Har bir sahifa sarlavhasida til
  almashtirgichi (`POST /i18n/set/`) — profilga va cookie ga yozadi.
- **Matnlar**: shablon va kodda manba matnning o'zi (o'zbek lotin) msgid: `{% trans %}`, `{% blocktrans trimmed %}`,
  Python da `gettext`/`gettext_lazy`, brauzer JS ida `gettext("…")` + `fmt(gettext("%(n)s …"), {n: 3})`
  (`/jsi18n/` katalogi, `interpolate`). Kataloglar — `locale/<til>/LC_MESSAGES/django.po|mo`.
- **Katalog asbobi**: Windows da gettext yo'qligi uchun `python manage.py i18n_sync` (matnlarni ajratadi, `.po` ni
  yangilaydi, `.mo` ni yozadi; `--strict` — tarjimasiz yoki placeholder mos kelmasa xato, `--show-missing`). Yangi
  matn qo'shgach shuni ishga tushiring, `ru`/`en`/`kaa` da `msgstr` ni to'ldiring. `uz-cyrl` avtomatik:
  `translit.lat_to_cyr`. Test (`test_i18n`) kataloglar eskirmaganini va to'liqligini tekshiradi.
- **Standart xatolar** (`apps/i18n/errors.py`): Django/DRF ning inglizcha standart matni UI ga uzatilmaydi;
  validator kodi (`password_too_short`, `required`, `invalid_choice` va boshqalar) loyiha katalogidagi xabarga
  aylantiriladi. Bu auth, barcha DRF serializerlari va dinamik hujjat formalariga bir xil tatbiq etiladi.
- **Transliteratsiya** (`translit.py`): lotin ↔ kirill, deterministik. lex.uz dagi 400 ta juft modda bilan o'lchandi:
  lotin→kirill 99.6%, kirill→lotin 99.7% o'xshashlik (farqlar asosan o'zlashma so'zlar: instansiya/инстанция, subyekt/субъект).
- **Javob tili**: chatdagi tanlagich (sukut — interfeys tili) AI javobini shu tilda yozdiradi va qidiruvga
  `lang=corpus_lang(...)` beradi — iqtiboslar shu tildagi rasmiy lex.uz matnidan (8-bosqich); qoraqalpoq/inglizda — o'zbek lotin.
  Server xabarlari (`/api/ask` xatolari, tekshiruvchi ogohlantirishlari) interfeys tilida.
- **Tarjima qilinmagan** (o'zbekcha qoladi): DOCX/PDF eksport matnlari, tahlil jarayoni bosqich nomlari ("Skaner sahifalar OCR…"),
  LLM yaratgan hisobot mazmuni, `history.py` izohlari, admin panel, hujjat shablonlari mazmuni.
  **Qoraqalpoq tarjimalarini ona tili egasi tekshirishi shart** (mashina tarjimasi).

## Tariflar va kvotalar (`apps/billing`, TZ §7.2, §8.1, 11-bosqich, 2026-10-28)

- **Modellar**: `Plan` (limitlar, bo'sh chegara — cheksiz), `Subscription`, `UsageLog` (billing_user_quota_log: kunlik ish/varaq/savol/hujjat
  soni va LLM narxi), `Payment` (Click / Payme / qo'lda). Boshlang'ich tariflar TZ §8.1 bo'yicha (migratsiya 0002):

| | Bepul | Pro (oylik, 30 kun) | Enterprise (yillik) |
|---|---|---|---|
| Ish tahlili | umrbod 1 | kuniga 10, oyiga 300 | kuniga 35, navbatda oldinda |
| Bitta ish | 15 varaq | 150 | 500 (texnik chegara `CASE_MAX_PAGES`=200 dan oshmaydi) |
| Savol-javob | jami 3 | kuniga 100 | cheksiz |
| Shablon (DOCX/PDF yuklab olish) | jami 1, tarif belgisi bilan | cheksiz | cheksiz |

  Narxlar TZ da yo'q — `price_uzs` bo'sh ("narx belgilanmagan"); **Admin → Tariflar** da limit va narxni o'zgartiring.
- **Mantiq** (`quota.py`): `plan_for` (faol obuna → eng yuqori tarif, tugagan → Bepul; xodim/superuser/SUPERADMIN va
  `BILLING_ENFORCED=0` — cheksiz), `reserve_case/chat/template` (tekshirish va sarfni oshirish bitta tranzaksiyada),
  `refund_case`, `record_cost`, `activate_subscription` (mavjud obuna tugashidan uzaytiradi), `mark_paid` (takroran xavfsiz).
- **Ulanish**: ish yuklash (`/cases/upload` — sahifalar va limit), tahlil xatosi → kvota qaytariladi (`CaseRun.quota_refunded`),
  "Qayta urinish" yana band qiladi; muvaffaqiyatli tahlil narxi `UsageLog` ga yoziladi; ish navbati ustuvorlikli
  (Enterprise oldinda); `/api/ask` — limit oshsa 429; shablonni DOCX/PDF olish (ko'rib chiqish bepul), bepul tarifda hujjat boshi va
  oxirida "bepul tarifda tayyorlandi" belgisi.
- **Sahifalar**: `/billing/` (joriy tarif, sarf, barcha tariflar; 5 tilda), `/api/billing/usage`.
- **Qo'lda tarif berish**: `python manage.py grant_plan +998901234567 PRO_MONTHLY --days 30` yoki Admin → Obunalar; to'lovni
  tasdiqlash — Admin → To'lovlar → "To'langan deb belgilash".
- **Hali yo'q**: Payme/Click webhooklari (savdogar kalitlari kerak; tayyor kirish nuqtasi — `quota.mark_paid(payment)`),
  anti-fraud (qurilma/IP/OTP, TZ §8.2), jamoaviy akkaunt (Enterprise 3–5 foydalanuvchi), "AI tahrirlash", firma blankasi,
  haqiqiy suv belgisi (hozir matn belgisi).

## Ish turlari (`apps/cases/case_types.py`, 12-bosqich, 2026-10-28)

- **Turlar**: `criminal` (sukut), `civil`, `economic`, `administrative`, `any` ("boshqa / aralash" — butun korpus). `/cases/` yuklash
  shaklida tur tanlanadi (`CaseRun.category`); `analyze_case --category` ham shu turlar bilan.
- **Qidiruv doirasi** (huquqiy asoslash faqat shu hujjatlardan qidiradi, + Oliy sud Plenumi qarorlari): turning o'z protsessual
  kodeksi (FPK / IPK / MSIYuK), materyal kodekslari va tegishli qonunlar; jinoyat kodekslari boshqa turlarga aralashmaydi.
  Barcha id lar bazada tekshirilgan (`manage.py check_case_scopes` — yadro, kuchda, joriy tahrirda moddalar bor):
  fuqarolik — FK-1/2, FPK, Oila, Uy-joy, Yer, Mehnat, Konstitutsiya, Davlat boji, Iste'molchilar, Ijara, Xususiy mulk,
  Sud hujjatlarini ijro etish; iqtisodiy — FK-1/2, IPK, MChJ, Raqobat, Investitsiya, Lizing, Hakamlik, Xo'jalik subyektlari
  (2 ta qonun), Davlat boji, ijro; ma'muriy — MSIYuK, MJtK, Ma'muriy tartib-taomillar, Soliq, Bojxona, Litsenziyalash,
  Shaharsozlik, Yer, Davlat boji, ijro.
- **Promptlar**: jinoyat ishi matnlari o'zgarishsiz; boshqa turlarda rol (vakil-advokat), ajratishdagi protsessual harakatlar,
  ziddiyat vazifasidagi "yakuniy hujjat", **protsessual muammolar vazifasi** (fuqarolik: da'vo muddati, talabnoma, xabarnomalar,
  shikoyat muddatlari; iqtisodiy: penya/jarima hisobi, pretenziya, yurisdiksiya; ma'muriy: protokol, jazo qo'llash muddati,
  shikoyat tartibi), huquqiy so'rov namunalari va orqaga qaytish kuchi qoidasi turga moslanadi. Almashtiriladigan iboralar
  asl promptda borligini va boshqa turlarda jinoyat so'zlari qolmaganini testlar tekshiradi.
- **Sinov** (`check_case_scopes --eval`, API siz): har bir tur uchun 6 savol — hujjat darajasida Hit@5 18/18, Hit@1 17/18;
  doiradan tashqari hujjat chiqmadi. **Haqiqiy fuqarolik/iqtisodiy/ma'muriy ish hujjati bilan LLM tahlili sinalmagan**
  (API puli; sintetik ish faqat jinoyat: `fixtures/cases/case_01`).
- **Tahrirlar tarixi**: `fetch_history --scope civil economic administrative` (yuqoridagi hujjatlar, 2016 dan) — voqea sanasidagi
  matn va "modda sanada kuchdami" tekshiruvi endi shu turlarda ham ishlaydi.

Natija (28.10): 3 ta doiradagi 37 hujjatning hammasida tarix bor (36 ta tahrir, jami ~1 soat); IPK ning bitta tahrir sahifasi
(14.10.2026) lex.uz da 404 — tarixda bitta bo'shliq. Misol: MJtK 36-modda (jazo qo'llash muddatlari) 01.06.2022 sanasida
boshqacha tahrirda ekani aniqlandi.

## Ish tahlili veb sahifasi (`/cases/`)
```bash
.venv/Scripts/python manage.py runserver 127.0.0.1:8010     # 8000 boshqa loyiha bilan band bo'lishi mumkin
.venv/Scripts/python manage.py import_case_report data/case_runs/<hisobot>.json --pdf <ish.pdf>   # API siz namoyish
```
- `/cases/` — fayllarni yuklash (PDF, DOCX, JPG/PNG; chegaralar yuqorida, "9-bosqich") va ishlar ro'yxati.
- `/cases/<id>/` — chapda PDF, o'ngda jonli progress → hisobot (xulosa, protsessual muammolar va ziddiyatlar
  huquqiy baho bilan, xronologiya, faktlar). Varaq tugmasi PDF ni o'sha varaqqa o'tkazadi; [M#] — lex.uz abzasiga havola.
- Tahlil server ichidagi bitta fon oqimida (`apps/cases/worker.py`), ketma-ket; production da Celery bilan almashtiriladi.
  Har bir ishga `CASE_BUDGET_USD` (sukut $0.50) qo'shimcha xarajat chegarasi ajratiladi.
- Server qayta ishga tushsa: yarim qolgan tahlil — "Xato", navbatdagilar qayta navbatga qo'yiladi.

## OCR — skaner qilingan PDF (`apps/cases/ocr.py`)
RapidOCR 3.10 (PaddleOCR PP-OCRv5 modellari, ONNX, **CPU**) + pypdfium2 (sahifani 200 DPI rasmga). PaddleOCR ning
o'zi (paddlepaddle) Python 3.14 uchun chiqarilmagan. O'rnatilgan hajm ~200 MB (onnxruntime 48 MB, OpenCV 113 MB,
rapidocr 32 MB); lotin/kirill modellari birinchi ishlatilganda yuklanadi (~8 MB dan).
- Matn qatlami bor sahifa — undan; yo'q bo'lsa — OCR. Avval lotin modeli; ishonch < 0.95 bo'lsa kirill ham,
  yaxshirog'i olinadi. Juda past ishonch (< 0.75) — sahifa 180° aylantirib qayta o'qiladi.
- `Global.use_cls=False`: qator yo'nalishi modeli qiyshiq lotin qatorlarini teskari o'girib yo'qotardi (CER 9% → 0.5%).
- Har bir sahifa: `source`, `ocr_confidence`, `ocr_warning`; < 0.85 — hisobotda "yomon o'qilgan" deb ko'rsatiladi.

```bash
.venv/Scripts/python tools/make_scanned_copy.py fixtures/cases/case_01/case_01.pdf fixtures/cases/case_01/case_01_scan.pdf
.venv/Scripts/python manage.py ocr_eval fixtures/cases/case_01/case_01_scan.pdf --reference fixtures/cases/case_01/case_01.pdf
```
case_01 skaner nusxasi (150 DPI, qiyshiqlik, shovqin, JPEG): **CER 0.51%**, 2.1 s/varaq (CPU). Ma'lum cheklov:
kirill modeli lug'atida o'zbekcha ў қ ғ ҳ yo'q — ular у к г х bo'lib chiqadi (o'zbek kirill sahifa CER 4.6%,
bu harflarsiz 0.44%; sahifa ogohlantirish bilan belgilanadi). Qo'lyozma va muhrlar sinalmagan.
OCR matnida ham PII niqoblash tekshirildi: 19 shaxs, kalitdagi qiymatlardan birortasi ochiq qolmaydi.

## Shaxsiy ma'lumotlarni niqoblash (`apps/cases/pii.py`)
Raqamlar (JSHSHIR, telefon, pasport, karta) + ism-familiyalar (qoidalar asosida, API siz): to'liq F.I.Sh. va
initsialli shakllar topiladi, familiya o'zagining barcha shakllari (Qodirovaning, Кодировой) bitta `<SHAXS_n>` ga,
lotin va kirill bitta shaxsga bog'lanadi. case_01: 19 shaxs, kalitdagi 26 ta PII qiymatidan birortasi LLM ga
ketmaydi, joy nomlari va oddiy so'zlar (Sergeli, Tergov, Toshkent…) saqlanadi. Cheklov: familiyasiz ismlar
("Otabek") niqoblanmaydi.

## Akkauntlar va kirish (`apps/accounts`, 2026-10-26)

- `accounts.User` (TZ §7.1): telefon (+998…) bilan kirish, rollar CLIENT / LAWYER / MODERATOR / SUPERADMIN,
  advokatlik guvohnomasi, shaxsiy ma'lumotga rozilik (`consents_json`, versiya va sana). SMS OTP — keyingi bosqich.
- `/accounts/register/`, `/accounts/login/`, `/accounts/logout/` (faqat POST). Ro'yxatdan o'tishda rol faqat
  LAWYER yoki CLIENT; parol kamida 8 belgi, oddiy/raqamli parollar rad etiladi.
- Parolni taxmin qilishdan himoya: 15 daqiqada bitta raqamga 5 ta, bitta IP dan 20 ta xato urinishdan keyin 429.
- Chat (`/`, `/api/ask`) va barcha `/cases/` sahifalari faqat kirganlar uchun (API — 401 JSON).
  Har bir ish egasiga biriktirilgan; begona ish so'ralsa 404.
- Admin: `python manage.py createsuperuser` (telefon raqami so'raladi), `/admin/`.
- Akkauntlardan oldingi egasiz ishlar: `python manage.py assign_cases <telefon>`.
- Lokal dev sinov akkaunti: `data/secret/dev_accounts.txt` (faqat 127.0.0.1 uchun).

## Ish fayllarini himoyalash (`apps/cases/storage.py`, TZ §5.3)

- Yuklangan PDF va tayyor hisobot (unda F.I.Sh. ochiq) diskda faqat shifrlangan `.enc` fayl sifatida saqlanadi
  (Fernet: AES-128-CBC + HMAC-SHA256). Kalit — `.env` dagi `MEZON_DATA_KEYS` (vergul bilan bir nechta: birinchisi
  joriy, qolganlari eski fayllarni ochish uchun — kalitni almashtirish). **Kalit yo'qolsa, fayllarni ochib bo'lmaydi.**
  Production da (DEBUG=0) kalitsiz server fayl yozmaydi.
- Tahlil uchun PDF vaqtinchalik ochiladi va ish tugashi bilan o'chiriladi; PDF/hisobot javoblari `no-store`.
- Zero-Retention: yuklashda "Tahlil tugagach PDF ni o'chirish" belgisi — hisobot qoladi, PDF o'chiriladi.
- "Ishni o'chirish" tugmasi: PDF, hisobot va yozuv butunlay o'chadi (faqat `DATA_DIR` ichidagi fayllar).
- Eski ochiq fayllarni shifrlash: `python manage.py encrypt_case_files [--dry-run]`.
- Cheklov: kalit serverda — TZ dagi "foydalanuvchi kaliti bilan shifrlash" (server ham ocha olmaydigan) hali yo'q.

## Yuridik tasdiq va DOCX/PDF eksport (`apps/cases/export.py`, TZ §12)

- Tayyor ish sahifasida "Rasmiy hisobot (DOCX / PDF)…" → "Yuridik tasdiqlash" oynasi: xulosada keltirilgan barcha
  qonun moddalari (hujjat, modda, tahrir, hujjat holati — kuchda/kuchini yo'qotgan) va tekshiruvdan o'tmagan baholar.
- Advokat "Asosiy dalillar va qonun moddalari bilan tanishdim" belgisini qo'yib tasdiqlaydi →
  `CaseRun.lawyer_confirmed_at`. Tasdiqsiz `/cases/<id>/export.docx|pdf` — 403.
- Fayl: sarlavha, tasdiq shtampi (F.I.Sh., vaqt), xulosa, tasdiqlanmagan baholar, protsessual muammolar va ziddiyatlar
  (huquqiy baho, tuzatish, himoyachi uchun, manbalar lex.uz havolalari bilan), xronologiya, foydalanilgan qonunlar
  ro'yxati, "yuridik maslahat emas" ogohlantirishi. Tekshiruvdan o'tmagan baho "TASDIQLANMAGAN" deb belgilanadi;
  `[M3]` → `[226-modda]`. Times New Roman (DOCX 14 pt), PDF shriftlari `EXPORT_FONT_DIR` dan (sukut C:/Windows/Fonts;
  Linux serverda — Times/Liberation Serif TTF papkasi).
- Fayllar diskka yozilmaydi — xotirada yaratilib, `no-store` bilan yuboriladi.

## Hujjatlar konstruktori (`apps/doc_builder`, TZ §5.1.1 — AI siz)

- `/templates/` — shablonlar ro'yxati, `/templates/<id>/` — forma → "Ko'rib chiqish" (qog'oz ko'rinishi) →
  DOCX/PDF (Times New Roman 14 pt, hoshiyalar 3/1.5/2 sm). To'ldirilgan ma'lumotlar saqlanmaydi.
- `DocumentTemplate`: forma sxemasi (JSON: `name`, `label`, `type` = text|textarea|date|number|money|select|phone|jshshir,
  `required`, `options`) + matn (Django shablon tili `{{ maydon }}`, `{% if %}`; `{{ bugun }}` — bugungi sana).
  Qator belgilari: `>>` o'ngga (kimga/kimdan), `##` markaz sarlavha, `###` bo'lim, `- ` band, `~ chap | o'ng` imzo.
  Saqlashda tekshiriladi: sxema to'g'ri, matn sintaksisi, matndagi barcha maydonlar sxemada bor.
- Moderator: `/admin/` → "Hujjat shablonlari"; "Tasdiqlash" amali faqat MODERATOR/SUPERADMIN uchun. Matn yoki forma
  o'zgarsa versiya oshadi va tasdiq bekor bo'ladi; tasdiqlanmagan shablon "namuna · moderator tasdiqlamagan" belgisi bilan.
- Boshlang'ich 5 shablon (`python manage.py load_starter_templates`): advokat so'rovi ("Advokatura to'g'risida"gi
  Qonun 7¹), ish materiallari bilan tanishish iltimosnomasi (JPK 375–377), ishonchnoma (FK 134–135), qarzni undirish
  da'vo arizasi (FPK 188–189, FK 732, 735), apellyatsiya shikoyati (JPK 480, 497⁴). Havolalar bazadagi joriy matn bilan
  tekshirilgan; matnlar yurist tasdig'ini talab qiladi.
- DOCX/PDF chizish umumiy: `apps/doc_builder/writers.py` (ish hisoboti eksporti ham shundan foydalanadi).

## Veb chat va API
```bash
.venv/Scripts/python manage.py runserver 127.0.0.1:8000     # http://127.0.0.1:8000/ — chat sahifasi
```
- `POST /api/ask` `{"question", "lang", "effort"}` → `text/event-stream`: `sources`, `delta`…, `verification`, `done`, `error`.
- Server ishga tushganda modellar va Qdrant fonda yuklanadi (~26 s, `RAG_WARMUP=0` bilan o'chiriladi).
- Qidiruv bitta qulf ostida (ichki Qdrant va GPU), LLM stream lari parallel.
- Ichki Qdrant'ni bir vaqtda faqat bitta jarayon ochadi: server ishlayotganda `search`/`ask`/`eval_search` buyruqlari ishlamaydi.
- Faqat kirgan foydalanuvchilar uchun, savollar tarif kvotasi bilan cheklangan (`apps/billing`); har bir savol API pulini sarflaydi.

## API v1 (`apps/api`, faza 2 — 13-bosqich, 2026-10-29)
Veb SPA, admin panel va Expo ilova uchun JSON API: DRF + `djangorestframework-simplejwt` + `drf-spectacular` + CORS.
Eski HTML sahifalar (sessiya + CSRF) SPA tayyor bo'lguncha o'zgarishsiz ishlaydi; biznes mantiq umumiy
(`apps/cases/services.py`, `apps/accounts/lockout.py`, `rag.views.parse_ask/answer_response`, `doc_builder.views.file_response`).

- **Hujjat**: `/api/v1/docs/` (Swagger UI), sxema `/api/v1/schema/` (dev da ochiq, `DEBUG=0` da faqat xodimlar).
  Frontend uchun: `manage.py spectacular --validate --fail-on-warn --file ../frontend/packages/api-client/openapi.yaml`
  (ogohlantirishsiz bo'lishi shart) → `openapi-typescript`.
- **Auth** (`/api/v1/auth/`): `login`, `register` (IP dan 5/daq burst; oshsa shu oy ichida 3, 5, 10, 20, 40, 60 daqiqa…
  progressiv tanaffus, yangi oyda yana 3 daqiqadan), `refresh`, `logout`, `me` (GET/PATCH: `full_name`,
  `advocate_license_no`, `language`), `language`. Access 15 daq (`Authorization: Bearer`), refresh 14 kun, har yangilashda
  rotatsiya + eskisi qora ro'yxatda (`token_blacklist`). `cookie: true` (veb) — refresh **HttpOnly cookie** da
  (`mezon_refresh`, yo'l `/api/v1/auth/`, SameSite=Strict), tanada yo'q; `refresh` tanasiz yuborilsa cookie dan olinadi.
  Mobil — refresh tanada (`expo-secure-store`). Kirish bloklash HTML sahifa bilan umumiy (5 urinish/raqam, 20/IP, 15 daq).
- **Til**: token bilan kelganda profil tili yoqiladi (`apps/api/authentication.py`) — xato va kvota xabarlari, SSE
  shu tilda. Til kodlari: TZ (`uz-Latn`) ham, Django (`uz-latn`) ham qabul qilinadi.
- **Ishlar** (`/api/v1/cases/`): ro'yxat (sahifalab, 20 ta), `POST` multipart (`files` takrorlanadi, `category`, `title`,
  `zero_retention`), `options`, `{id}` (holat, `DELETE`), `report`, `pdf`, `confirmation` (GET/POST `acknowledged`),
  `export/{docx|pdf}` (tasdiqsiz 403), `retry`. Begona ish — 404. Hisobot/PDF/eksport `no-store`.
- **Chat**: `POST /api/v1/chat/ask` — SSE (hodisalar HTML chat bilan bir xil); 400/429 — JSON. `Accept: text/event-stream`
  406 bermaydi (`apps/api/negotiation.py`).
- **Shablonlar**: `templates/`, `{id}` (`form_schema`, `legal_basis`), `{id}/preview` `{"values": {...}}` → bloklar,
  `{id}/render/{docx|pdf}` (kvota; bepul tarifda belgi). To'ldirilgan ma'lumot saqlanmaydi.
- **Tariflar**: `billing/usage`, `billing/plans` (ochiq). **Qonunlar**: `laws/documents?q=` (matni bazadagi hujjatlar),
  `laws/documents/{id}` (moddalar ro'yxati), `laws/articles/{id}?lang=lat|cyr|ru` (tilda bo'lmasa — asosiy til),
  `laws/search?q=` (gibrid qidiruv, LLM siz; Qdrant kerak, aks holda 503). **Tillar**: `i18n/languages`.
- **Xatolar**: `{"detail", "code"}` (`apps/api/exceptions.py`); validatsiya — `{maydon: [xabar]}`. Standart JSON,
  autentifikatsiya, ruxsat, HTTP usuli, media turi va maydon validatsiyasi xatolari tanlangan profil/cookie/brauzer
  tilida; 429 — tarif limiti (`code`: `quota_pages|quota_daily|quota_monthly|quota_lifetime`) → mijoz `/billing` ga yo'naltiradi.
- **LLM siz dev server**: `.venv/Scripts/python tools/dev_nollm.py 8011` — LLM yopiq portga yo'naltirilgan, tahlil va chat
  darhol xato bilan tugaydi (kvota qaytadi), qolgani to'liq ishlaydi. Frontendni pulsiz ishlab chiqish uchun.
- **i18n frontend uchun**: `manage.py i18n_export_json` → `../frontend/packages/i18n/locales/<uz-Latn|uz-Cyrl|ru|kaa|en>.json`
  (i18next, `keySeparator: false`; `%(n)s` → `{{n}}`) + `languages.json`.
- Testlar: `apps/api/tests` — auth (cookie/rotatsiya/blacklist/bloklash va 5 tildagi validatsiya), ishlar, chat,
  shablonlar, qonunlar, sxema. 2026-11-12 to'liq backend to'plami: 287/287.
- Testlar endi xotira keshidan foydalanadi (`settings.py`, `sys.argv[1] == "test"`): avval `accounts` testlaridagi
  `cache.clear()` dev keshini (`data/cache`, LLM so'rov o'girish natijalari) o'chirib yuborardi.
- 14-bosqichda qo'shildi: `templates` javobida `is_approved` (moderator tasdig'i), `cases/{id}` da `sources` tiplangan
  (`CaseSourceSerializer`: name, kind, first_page, last_page).

### Frontend matnlari katalogda (`apps/i18n/catalog.py`, 14-bosqich)
`i18n_sync` endi `../frontend/apps` va `../frontend/packages` dagi `*.ts(x)` fayllaridan `t("...")` chaqiruvlarini ham
ajratadi (`node_modules`, `dist`, `*.d.ts`, `*.test.ts(x)` dan tashqari); i18next `{{n}}` → `%(n)s`. Shablon satri
(`${...}`) li kalit ajratilmaydi. Shu sabab "barcha tillar to'liq tarjima qilingan" testi frontend matnlarini ham qamraydi.

## Admin API (`/api/v1/admin/*`, 15-bosqich, 2026-10-29)
`apps/api/views/admin.py`, `serializers_admin.py`, `permissions.py`. Ruxsat: `IsStaffRole` (MODERATOR/SUPERADMIN/superuser) —
`me`, `templates/*`, `sync/` (ro'yxat); qolgani `IsSuperAdmin`.
- `me`, `dashboard`, `users/` (q, role, flagged, ip), `users/{id}` (GET; PATCH: full_name, role, advocate_license_no,
  is_active, is_fraud_flagged — o'zini o'zgartirib bo'lmaydi, SUPERADMIN rolini faqat Django superuser beradi; rol
  MODERATOR/SUPERADMIN bo'lsa `is_staff` avtomatik), `users/{id}/subscriptions` (POST {plan, days}),
  `subscriptions/` (?current), `subscriptions/{id}/cancel`, `plans/` (GET/POST), `plans/{id}` (GET/PATCH; kod o'zgarmaydi,
  o'chirish yo'q), `payments/` (GET ?status / POST qo'lda), `payments/{id}/mark-paid` (`quota.mark_paid`, takror xavfsiz),
  `payments/{id}/cancel`, `costs` (?days 7–90), `antifraud` (?min), `sync/`, `sync/start` (fon oqimi, 409 agar bajarilmoqda),
  `templates/` (?pending; POST), `templates/{id}` (PATCH — `DocumentTemplate.clean()` validatsiyasi, versiya/tasdiq
  qoidalari modelda), `templates/{id}/approve` (tasdiq + e'lon), `templates/{id}/preview`, `audit/`.
- **Advokatlik siri**: admin javoblarida ish nomi, hisobot, PDF yo'q — faqat metama'lumot (`AdminCaseSerializer`).
- **Audit**: `accounts.AuditEvent` (actor, action, target, details, ip) — har bir o'zgartiruvchi admin amali; Django admin da faqat o'qish.
- **Anti-fraud**: `User.registered_ip` / `last_login_ip` (HTML va API kirish/ro'yxatdan o'tishda yoziladi, `accounts/audit.py`);
  radar — bitta IP da ≥ N akkaunt (xodimlar hisobga olinmaydi). NAT/byuro ortidagi halol foydalanuvchilar ham tushishi mumkin — bu signal.
- **AI xarajati**: chat savollari narxi ham endi `UsageLog.llm_cost_usd` ga yoziladi (`rag.views._answer_events`, `owner`);
  avval faqat ish tahlili yozilardi.
- Testlar: `apps/api/tests/test_admin_api.py` (13).

## Production tarmoq (17-bosqich, 2026-10-30)

Bitta domen, bitta jarayon: **Cloudflare Tunnel → waitress (`tools/serve.py`, faqat 127.0.0.1:8010) → Django**.
HTTPS Cloudflare da tugaydi; port ochilmaydi, router sozlanmaydi. Veb SPA — `/`, admin SPA — `/panel/`, API — `/api/v1/`,
Django admin — `DJANGO_ADMIN_PATH` (dev da sukut `admin/`; **production da berilmasa yopiq** — unda kirish lockout'i yo'q,
xodimlar uchun `/panel/`; kerak bo'lsa maxfiy yo'l bering). CORS kerak emas, refresh HttpOnly cookie o'zgarmaydi.
SPA sahifalariga **CSP** qo'shiladi (`MEZON_CSP=enforce|report|off`, production da sukut `enforce`; inline tema skripti xesh bilan).
Tezlik cheklovlari: `API_ASK_RATE` (sukut `20/min`), `API_LAWS_SEARCH_RATE` (`30/min`); registratsiya uchun
`API_REGISTER_BURST`, `API_REGISTER_WINDOW_SECONDS`, `API_REGISTER_COOLDOWNS` progressiv IP himoyasi;
hisoblagichlar alohida `security` keshida (bir nechta jarayon bo'lsa — Redis). Qidiruv navbatida 60 s dan ortiq kutgan so'rov
503 (`search_busy`) oladi.
```
powershell -ExecutionPolicy Bypass -File tools\prod.ps1 build    # npm build (veb, admin) + collectstatic
powershell -ExecutionPolicy Bypass -File tools\prod.ps1 start    # Qdrant + server + tunnel (config.yml bo'lsa), ~20 s
powershell -ExecutionPolicy Bypass -File tools\prod.ps1 status   # /api/v1/health: baza va Qdrant
powershell -ExecutionPolicy Bypass -File tools\prod.ps1 stop
```
- `DJANGO_DEBUG=0` (serve.py majburlaydi) da: `DJANGO_SECRET_KEY` >= 50 belgi bo'lmasa server ishga tushmaydi;
  `SECURE_PROXY_SSL_HEADER`, HTTP→HTTPS (`DJANGO_SSL_REDIRECT`, `/api/v1/health` bundan ozod), HSTS (`DJANGO_HSTS_SECONDS`,
  sukut 1 kun — barqaror bo'lgach 31536000), Secure cookie, COOP; eski Django sahifalari o'chiq (`MEZON_LEGACY_UI`);
  Swagger faqat xodimlarga; jurnal `data/logs/mezon.log` (10 MB × 5). `manage.py check --deploy` — ogohlantirishsiz.
- `.env` (production): `DJANGO_ALLOWED_HOSTS=<domen>`, `DJANGO_CSRF_TRUSTED_ORIGINS=https://<domen>` (Django admin uchun).
- **Mijoz IP**: tunnel orqasida hamma so'rov 127.0.0.1 dan keladi — haqiqiy IP `CF-Connecting-IP` dan
  (`accounts.lockout.client_ip`, `MEZON_CLIENT_IP_HEADER`), faqat so'rov lokal proksidan kelganda. Lockout, ro'yxatdan
  o'tish chastotasi (`api/throttling.py`), audit va anti-fraud IP lari shundan. waitress `X-Forwarded-Proto` ga faqat
  127.0.0.1 dan ishonadi (aks holda uni o'chirib, HTTPS so'rovni ham qayta yo'naltirardi).
- Statik: whitenoise; Vite `base` — `/static/web/`, `/static/panel/` (faqat build da), xeshlangan fayllar 1 yil
  `immutable` keshda, `index.html` — `no-cache` (`config/spa.py`). Admin router `basename="/panel"` (faqat production build).
- SSE chat: waitress oqimni buferlamaydi (o'lchandi); har oqim bitta ip — `--threads 16` (`MEZON_THREADS`), `channel_timeout` 300 s.
- **Veb va admin bitta domenda bitta refresh cookie ni bo'lishadi**: biridan chiqish ikkinchisidan ham chiqaradi;
  ikki SPA (yoki ikki tab) bir vaqtda refresh qilsa, rotatsiya tufayli bittasi qayta kirishni so'rashi mumkin.
- Holat tekshiruvi: `GET /api/v1/health` → `{"status": "ok"|"degraded", "database", "search"}` (503 — biror qism ishlamasa).

### Cloudflare Tunnel (domen kerak)
1. Domenni Cloudflare ga ulang (bepul tarif yetadi). 2. `E:\cloudflared\cloudflared.exe tunnel login` (brauzerda),
`tunnel create mezon`, `tunnel route dns mezon <domen>`. 3. `tools\cloudflared\config.example.yml` → `config.yml`
(git ga kirmaydi), `<TUNNEL_ID>`, `<DOMEN>` ni to'ldiring. 4. `.env` ga domen (yuqoriga qarang), `tools\prod.ps1 start`.
Kompyuter qayta yonganda avtomatik ishga tushirish — `cloudflared service install` yoki Task Scheduler (tizim sozlamasi —
egasining ruxsati bilan). Vaqtinchalik sinov (domensiz): `tools\serve.py --port 8011 --nollm --trycloudflare` va
`cloudflared tunnel --url http://127.0.0.1:8011` — tasodifiy `*.trycloudflare.com` HTTPS manzil; sinovdan so'ng yoping.
2026-10-30 da shu yo'l bilan tekshirilgan: login + HttpOnly/Secure cookie + refresh, SSE chat, veb va `/panel/`, HTTP→HTTPS,
haqiqiy IP yozilishi.

### Mobil ilova (production)
`MEZON_ENV=production` (cleartext HTTP o'chadi) va `EXPO_PUBLIC_API_URL=https://<domen>` bilan release build. Release
imzo kaliti (keystore) hali yaratilmagan — yaratilgach parol menejerida va zaxirada saqlang (yo'qolsa, ilovani yangilab
bo'lmaydi).

## Zaxira nusxa (`apps/ops`, `manage.py backup`)
```
manage.py backup                       # baza + ish fayllari -> MEZON_BACKUP_DIR/mezon_YYYYMMDD_HHMMSS.mzb
manage.py backup --qdrant              # + qidiruv indeksi (Qdrant snapshot)
manage.py backup verify <fayl.mzb>     # ochib tekshiradi: har faylning SHA-256, baza quick_check, yozuvlar soni
manage.py backup restore <fayl.mzb> <yangi_papka>   # ochadi; ishlab turgan data/ ga tegmaydi
```
- Ichida: `db.sqlite3` (SQLite online backup — server to'xtatilmaydi), `files/uploads`, `files/case_runs`,
  `files/llm_usage.jsonl`, `qdrant/*.snapshot`, `manifest.json`. Kirmaydi: `lex_cache` (lex.uz dan qayta yuklanadi), kesh,
  modellar, `.env`, `data/secret`.
- **Shifrlangan** (AES-256-GCM, 1 MB bo'laklar; kalit `MEZON_DATA_KEYS` ning birinchisidan HKDF): o'zgartirish, kesish va
  bo'laklar o'rnini almashtirish aniqlanadi; kalit almashtirilgach ham eski zaxiralar ochiladi (`MEZON_DATA_KEYS` dagi
  barcha kalitlar sinaladi). **`MEZON_DATA_KEYS` va `DJANGO_SECRET_KEY` ni alohida (parol menejerida) saqlang** — zaxirada yo'q.
- Joy: `MEZON_BACKUP_DIR` (sukut `E:\mezon\backups`; imkon bo'lsa boshqa disk yoki tashqi nusxa), `MEZON_BACKUP_KEEP`
  (sukut 7) ta eng yangisi qoladi. O'lchov (2026-10-30): 752 MB baza → 122 MB, 22 s; `--qdrant` bilan 816 MB, 49 s;
  verify 11–18 s. Qdrant snapshot alohida kolleksiyaga yuklab tekshirildi (131 476 nuqta, asl bilan teng).
- Tiklash (server to'xtatilgach: `tools\prod.ps1 stop`): `backup restore` → `db.sqlite3` ni `data/dev.sqlite3` o'rniga,
  `files/uploads`, `files/case_runs` ni `data/` ga ko'chiring (`CaseRun` dagi yo'llar mutlaq — `MEZON_DATA_DIR` bir xil
  bo'lsin). Qidiruv indeksi: `curl -X POST "http://127.0.0.1:6333/collections/lex_articles/snapshots/upload?priority=snapshot" -F snapshot=@qdrant/<nom>.snapshot`
  (yoki snapshot siz: `manage.py build_index --recreate --langs lat cyr ru` bilan qayta qurish — uzoq).
- Tungi vazifa: `tools\nightly_backup.ps1` (har kuni; yakshanba `--qdrant`; yaratilgach darhol `verify`; jurnal
  `data\logs\backup_YYYYMMDD.log`). Task Scheduler ga qo'shish (**hali yaratilmagan**, egasining ruxsati bilan):
  ```
  schtasks /Create /TN "MEZON\nightly_sync" /SC DAILY /ST 02:00 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File E:\mezon\mezon_backend\tools\nightly_sync.ps1"
  schtasks /Create /TN "MEZON\nightly_backup" /SC DAILY /ST 03:30 /TR "powershell -NoProfile -ExecutionPolicy Bypass -File E:\mezon\mezon_backend\tools\nightly_backup.ps1"
  ```

## PostgreSQL ga o'tish (reja, hali bajarilmagan)
SQLite bitta jarayon (waitress + ish navbati) uchun yetadi; ko'p foydalanuvchi yoki Celery ishchilari paydo bo'lganda:
1. PostgreSQL (Windows o'rnatuvchisi), `mezon` baza va foydalanuvchi; `psycopg` allaqachon `requirements.txt` da.
2. `DATABASE_URL=postgres://mezon:<parol>@127.0.0.1:5432/mezon` bilan `manage.py migrate` (bo'sh baza).
3. Ko'chirish: SQLite da `manage.py dumpdata --natural-foreign --exclude contenttypes --exclude auth.permission
   --exclude admin.logentry -o dump.json`, Postgres da `manage.py loaddata dump.json` (korpus katta — `lex_corpus` ni
   alohida qism bilan; 37 410 modda, ~750 MB). So'ng `manage.py test apps` va qidiruvni tekshirish.
4. Zaxira: `manage.py backup` SQLite uchun; Postgres da `pg_dump -Fc` + ish fayllari (buyruqqa `--pg` qo'shish kerak bo'ladi).
5. Kesh: fayl kesh → Redis (lockout hisoblagichlari jarayonlar orasida umumiy bo'lishi uchun).
