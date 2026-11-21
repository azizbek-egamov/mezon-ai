# “MEZON AI” — Texnik topshiriq (TZ) v2.1

**O‘zbekiston Respublikasi qonunchiligi va sud amaliyoti asosida ishlovchi intellektual yuridik ekotizim**

| | |
|---|---|
| Loyiha nomi | MEZON AI — Multi-Agent Legal AI & Smart Document Platform |
| Versiya | 2.1 (2026-10-23). v2.0 (`MEZON-AI.pdf`) ning tuzatilgan va lex.uz ma’lumotlari tahlili bilan to‘ldirilgan nusxasi |
| Ma’lumot manbalari | lex.uz (reyestr + hujjat matnlari), Oliy sud Plenumi qarorlari, sud amaliyoti (buyurtmachi taqdim etadigan tayyor to‘plam) |
| Texnologik stek | Python (Django DRF, FastAPI, Celery, LangGraph), React + Vite + TypeScript, React Native (iOS/Android), PostgreSQL 16, Qdrant, Redis |
| AI modellar | Faqat lokal (open-source) modellar; tashqi pullik AI API ishlatilmaydi |
| Dev muhiti | NVIDIA RTX 2060 Super (8 GB VRAM), 16 GB RAM — kvantlangan rejim |
| Production server | Bulutdan ijaraga olinadigan 24 GB VRAM GPU server (RTX 3090/4090, A10G, L4) — vLLM rejim |
| To‘lov | Payme, Click |
| Xavfsizlik | O‘RQ-547 (Shaxsga doir ma’lumotlar), advokatlik siri (PII niqoblash), 4 qatlamli anti-fraud |

> **Annotatsiya.** Tizim advokatlar, yuristlar va fuqarolar uchun 100+ varaqli ish hujjatlarini raqamlashtiradi, faktlar va ziddiyatlarni ajratadi, voqea sanasida amalda bo‘lgan normalarni topadi, xulosani 3 marta avtomatik tekshiradi va har bir tasdiqqa manba biriktiradi. Yakuniy xulosa advokat tasdig‘idan (Human-in-the-Loop) keyingina eksport qilinadi.

### v2.0 dan asosiy o‘zgarishlar
1. lex.uz ning haqiqiy id, havola va tahrir formatlari kiritildi (§6.1); `legal_act_*` sxemasi tuzatildi (§7.3).
2. Korpus tarkibi aniq raqamlar bilan belgilandi (§6.2): reyestr 57 950, yadro ~1 550 hujjat.
3. Normativ iyerarxiya vaznlari to‘liq jadval bo‘ldi (§4.2), o‘zgartirish kirituvchi hujjatlar uchun koeffitsiyent qo‘shildi.
4. “99.5%”, “Zero-Hallucination”, “100% himoya” kabi va’dalar o‘lchanadigan KPI larga almashtirildi (§10).
5. 8 GB rejimdagi o‘tkazuvchanlik hisobi va tarif limitlarining unga bog‘liqligi kiritildi (§3.3, §8.1).
6. Imo-ishora tili moduli 2-fazaga o‘tkazildi (§5.2, §11).
7. “LexAI” nomi qoldiqlari, bo‘sh mundarija, kesilgan jadvallar va imlo xatolari tuzatildi.
8. Buyurtmachi qarorlari kiritildi (§13): tashqi AI API yo‘q, to‘lov Payme/Click, sud amaliyoti buyurtmachi to‘plamidan, Elasticsearch o‘rniga Qdrant gibrid qidiruvi, server bulutdan.

---

## Mundarija
1. Loyiha konsepsiyasi
2. Nima uchun Fine-tuning emas, balki Hybrid RAG + Multi-Agent
3. Apparat ta’minoti va AI modellar
4. Multi-agent tahlil zanjiri
5. Funksional modullar
6. Qonunchilik korpusi (lex.uz)
7. Ma’lumotlar bazasi strukturasi
8. Obuna, limitlar va anti-fraud
9. Dasturiy arxitektura
10. Sifat mezonlari (KPI) va qabul qilish
11. Yo‘l xaritasi
12. Huquqiy himoya va Human-in-the-Loop
13. Qabul qilingan qarorlar

---

## 1. Loyiha konsepsiyasi

### 1.1 Asosiy muammo
Advokat murakkab jinoyat, fuqarolik, iqtisodiy yoki ma’muriy ishni qabul qilganda qo‘lida 100–500 varaq hujjat bo‘ladi: tergov bayonnomalari, ekspertiza xulosalari, shartnomalar, dalolatnomalar, guvoh ko‘rsatmalari.
- Ularni o‘qish, sanalar va ko‘rsatmalar orasidagi ziddiyatlarni topish, mos moddalar va Plenum qarorlarini izlash 2–3 ish kunini oladi.
- Inson omili sababli 60-betdagi kichik muddat xatosini o‘tkazib yuborish yoki kuchini yo‘qotgan hujjatga tayanish xavfi yuqori.

### 1.2 MEZON AI yechimi
Foydalanuvchi mobil ilova yoki veb-sayt orqali hujjatlarni skanerlaydi (yoki PDF/DOCX/JPG yuklaydi). Tizim:
1. Lotin, kirill, rus, qoraqalpoq va ingliz tillaridagi hujjatlarni raqamlashtiradi (OCR). Aniqlik §10 dagi KPI bo‘yicha o‘lchanadi.
2. Shaxsiy ma’lumotlarni (F.I.Sh., JSHSHIR, pasport, telefon) lokal serverda niqoblaydi.
3. Har bir sahifadan faktlar, sanalar, summalar va ishtirokchilarni ajratib, ichki ziddiyatlar jadvalini tuzadi.
4. lex.uz va Plenum qarorlaridan voqea sodir bo‘lgan sanada amalda bo‘lgan normalarni topadi.
5. Xulosani 3 marta avtomatik tekshiradi va har bir gapga manba (ish varag‘i + lex.uz havolasi) biriktiradi.
6. Advokat tasdig‘idan so‘ng xulosa va protsessual hujjatlarni DOCX/PDF ko‘rinishida beradi.

### 1.3 Foydalanuvchi rollari
`CLIENT` (fuqaro), `LAWYER` (advokat/yurist), `MODERATOR` (yurist-moderator: shablonlar, sifat nazorati), `SUPERADMIN`.

---

## 2. Nima uchun Fine-tuning emas, balki Hybrid RAG + Multi-Agent
Qonunlarni modelga fine-tuning orqali “yodlatish” taqiqlanadi:
- **Dinamik qonunchilik.** lex.uz ga yiliga 4–5 mingta yangi hujjat qo‘shiladi (2024 — 4 450, 2025 — 4 487). Fine-tuning qilingan model eski tahrirni “amaldagi” deb ko‘rsatadi.
- **Gallyutsinatsiya.** Model modda, qism va band raqamlarini adashtiradi (masalan, JK 168-modda 3-qism “a” bandi o‘rniga “b”).
- **Isbotlanuvchanlik.** Advokatga rasmiy matnning aniq bandi va havolasi kerak.

Shu sababli tizim **Hybrid RAG (dense + sparse) + normativ iyerarxiya + 3 karra tekshiruv agentlari** asosida quriladi.

---

## 3. Apparat ta’minoti va AI modellar

### 3.1 Modellar ro‘yxati
Kelajakda 24 GB serverga o‘tilganda kod o‘zgarmaydi — faqat `.env` dagi model nomi almashtiriladi.

| Komponent | Dev PC: RTX 2060S (8 GB) | Server (24 GB) | Vazifasi |
|---|---|---|---|
| Asosiy LLM (Reasoning, Critic) | Qwen2.5-7B-Instruct GGUF Q4_K_M (Ollama/llama.cpp, ≈5 GB) | Qwen2.5-14B-Instruct-AWQ (≈10.5 GB) yoki Qwen2.5-32B Q4 (≈18.5 GB), vLLM | Fakt ekstraksiyasi, huquqiy tahlil, tekshiruv, xulosa |
| Embedding | BAAI/bge-m3 (GPU FP16 ≈1.1 GB yoki ONNX/CPU) | bge-m3 GPU FP16 | Dense + sparse vektorlar, 8192 token kontekst |
| Reranker | bge-reranker-v2-m3 (ONNX CPU INT8) | GPU FP16 | Top-50 dan eng mos 5–10 tasini tanlash |
| OCR | PaddleOCR PP-OCRv4 (CPU) + OpenCV preprocessing | Surya OCR + PaddleOCR GPU | Skaner, jadval, muhr, qo‘lyozma |
| PII | Regex (JSHSHIR, pasport, INN, telefon) + GLiNER-multi-v2.1 (CPU) | GLiNER GPU | `<SHAXS_1>` tokenlariga almashtirish |
| Imo-ishora (2-faza) | MediaPipe Holistic (qurilmada) | Pose + ST-GCN, 3D avatar | §5.2 |

Tashqi pullik AI API ishlatilmaydi (§13): barcha bosqichlar lokal modellarda bajariladi.

### 3.2 VRAM boshqaruvi (8 GB)
8 GB da OCR, embedding, reranker va 7B LLM bir vaqtda ishlasa, xotira to‘ladi (OS va display 1–1.5 GB oladi). Shuning uchun Celery da **Sequential Resource Allocation** qo‘llanadi:
1. PaddleOCR, GLiNER va reranker ONNX Runtime orqali CPU da ishlaydi.
2. GPU faqat LLM (≈5 GB) + bge-m3 (≈1.1 GB) uchun. KV-kesh uchun zaxira qoldiriladi: LLM konteksti 8K bilan cheklanadi. Ommaviy indekslash paytida LLM to‘xtatiladi.
3. GPU vazifalari bitta `gpu` navbatida, bitta worker bilan bajariladi (parallel yuklash yo‘q).
4. `LLMProvider` (adapter pattern) — `LOCAL_OLLAMA` (dev) va `LOCAL_24GB_VLLM` (server) provayderlari; model nomi `.env` dan olinadi.

### 3.3 O‘tkazuvchanlik hisobi
Dev PC da o‘lchangan generatsiya tezligi ≈16.8 token/s (Qwen2.5-7B Q4_K_M). Taxminiy hisob:

| Ish hajmi | Ekstraksiya (blok × ~800 token) | Qidiruv + 3 tekshiruv + xulosa | Jami |
|---|---|---|---|
| 15 varaq (Free) | 3 blok ≈ 2.5 daq | ≈ 5–8 daq | ≈ 10 daq |
| 150 varaq (Pro) | 30 blok ≈ 24 daq | ≈ 15–25 daq | ≈ 40–60 daq |

Xulosa: 8 GB PC — faqat ishlab chiqish va yopiq beta uchun (soatiga 1–2 ta katta ish). Tijoriy tariflar 24 GB server (vLLM, batching) ishga tushgandan keyin ochiladi. Aniq raqamlar 1-bosqich oxirida benchmark bilan yangilanadi.

---

## 4. Multi-agent tahlil zanjiri
Tizim oddiy chat-bot emas, balki LangGraph asosidagi siklik holat grafi. Har bir bosqich holati `cases_legal_case.pipeline_status` da saqlanadi va WebSocket orqali foydalanuvchiga ko‘rsatiladi.

### 4.1 1-bosqich: raqamlashtirish va faktlar ekstraksiyasi
1. **Pre-processing:** deskew, soya va shovqinni tozalash, muhr va imzolarni koordinatalari bilan belgilash.
2. **Multi-script normallashtirish:** asl matn o‘zgarmasdan saqlanadi. Qidiruv indeksi uchun lotin ↔ kirill transliteratsiya, apostroflarni birlashtirish (`ʻ ʼ ' \``), so‘z ichidagi kirill-lotin homogliflarni tuzatish.
3. **Hierarchical map-reduce:** hujjat 5 sahifalik bloklarga bo‘linadi. Fact Extractor har bir blokdan JSON chiqaradi (JSON-sxema bilan cheklangan generatsiya):
   - `entities` — ishtirokchilar va roli (da’vogar, javobgar, ayblanuvchi, guvoh, ekspert);
   - `timeline_events` — sana, vaqt, voqea, manba (`fayl`, `sahifa`, `abzas`, `bbox`);
   - `monetary_claims` — summalar, jarimalar, zarar, shartnoma raqamlari;
   - `procedural_dates` — ish qo‘zg‘atilgan sana, qamoqqa olish, da’vo muddati.
4. **Ziddiyatlar matritsasi:** faktlar o‘zaro solishtiriladi. Masalan: “12-varaqda voqea 14:00 da, 78-varaqdagi guvoh ko‘rsatmasida 19:30 da”.

### 4.2 2-bosqich: huquqiy qidiruv (Legal Researcher)
1. **Gibrid qidiruv:** Qdrant da bge-m3 dense (semantik) + sparse (kalit so‘zlar, atamalar) vektorlari; modda va hujjat raqami ko‘rsatilgan so‘rovlar PostgreSQL da aniq qidiriladi. Natijalar RRF bilan birlashtiriladi, keyin reranker saralaydi.
2. **Iyerarxiya vazni** (`hierarchy_weight`; yurist-hamkor tasdiqlaydi):

| Hujjat turi | Vazn |
|---|---|
| Konstitutsiya | 1.00 |
| Konstitutsiyaviy qonun, Kodeks | 0.95 |
| Qonun | 0.90 |
| Oliy sud Plenumi qarori | 0.85 |
| Prezident farmoni | 0.80 |
| Prezident qarori | 0.75 |
| Vazirlar Mahkamasi qarori | 0.70 |
| Idoraviy hujjat (vazirlik buyrug‘i va h.k.) | 0.65 |
| Mahalliy hokimiyat qarori, boshqalar | 0.60 |

   O‘zgartirish kirituvchi va “kuchini yo‘qotgan deb topish” hujjatlariga (`is_amending = true`, reyestrning ≈29% i) qo‘shimcha ×0.5 koeffitsiyent qo‘llanadi — ular asosiy hujjat matnini takrorlaydi.
3. **Vaqt filtri (retroaktivlik):** voqea 2022-yil 15-martda sodir bo‘lgan bo‘lsa, agent normaning o‘sha sanadagi tahririni (`?ONDATE=15.03.2022`) va bugungi tahririni oladi hamda qonunning orqaga qaytish kuchi qoidalari bo‘yicha solishtiradi.

### 4.3 3-bosqich: uch karra tekshiruv (Critic & Verifier)
Dastlabki xulosa foydalanuvchiga ko‘rsatilmaydi. U 3 ta alohida tekshiruvdan o‘tadi:
1. **Deterministik tekshiruv (kod darajasida):** xulosadagi har bir iqtibos (hujjat + modda/band) bazadan qidiriladi. Hujjat raqami yagona kalit emas (reyestrdagi hujjatlarning 24% ida raqam yo‘q), shuning uchun qidiruv `hujjat turi + raqam + sana` yoki `abs_id` bo‘yicha bajariladi. Modda bazada bo‘lmasa yoki voqea sanasida kuchda bo‘lmasa, xulosa rad etilib, 2-bosqichga qaytariladi.
2. **Iqtibos va istisno tekshiruvi:** keltirilgan mazmun rasmiy matnga solishtiriladi; “…bundan mustasno”, “Eslatma” kabi istisno qismlari tushib qolmaganligi tekshiriladi.
3. **Qarshi tomon pozitsiyasi (Devil’s Advocate):** prokuror, da’vogar yoki sudya keltirishi mumkin bo‘lgan modda va dalillar tahlil qilinadi va xavflar ro‘yxati tuziladi.

Maksimal qayta ishlash sikli — 3. Undan keyin ham o‘tmagan tasdiqlar xulosadan olib tashlanadi va “tasdiqlanmadi” deb belgilanadi.

### 4.4 4-bosqich: iqtibosli xulosa
Manbasiz huquqiy tasdiq chiqarilmaydi. Format:
> “Tergov organining ekspertiza tayinlash haqidagi qarori bilan ayblanuvchi o‘z vaqtida tanishtirilmagan **[Manba: 1-tom, 44-varaq, 2-abzas]**. Bu O‘zbekiston Respublikasi JPKning 173-moddasi **[lex.uz: /uz/docs/-111460#‹elem_id›]** hamda Oliy sud Plenumining 24-son qarori 12-bandi talablarining buzilishi hisoblanadi.”

Havola modda raqami bilan emas, lex.uz sahifasidagi element id si bilan quriladi (§6.1).

---

## 5. Funksional modullar

### 5.1 Aqlli hujjatlar konstruktori
1. **Deterministik shablon to‘ldirish (AIsiz):** da’vo arizalari, apellyatsiya/kassatsiya shikoyatlari, advokat so‘rovlari, mehnat, ijara, oldi-sotdi shartnomalari, ishonchnomalar. Forma JSON-sxemadan avtomatik chiziladi; pasport/rekvizit rasmidan OCR orqali F.I.Sh., JSHSHIR va manzil to‘ldiriladi. `docxtpl` orqali .docx/.pdf (Times New Roman 14 pt, hoshiyalar saqlanadi).
   Shablon kutubxonasi yurist-moderatorlar tomonidan bosqichma-bosqich to‘ldiriladi: ishga tushishda kamida 10 ta, maqsad — 200+.
2. **AI yordamida to‘ldirish:** ish tahlilidan keyin “Kassatsiya shikoyati (yoki himoya nutqi) shablonini to‘ldir” — faktlar, ziddiyatlar va moddalar shablonga joylashtiriladi.
3. **Ichki muharrir:** TipTap/ProseMirror; belgilangan abzasni AI bilan qayta yozish (“Shu bandni Fuqarolik kodeksi asosida kuchaytir”). AI o‘zgartirgan matn ham §4.3 tekshiruvidan o‘tadi.

### 5.2 Imo-ishora tili moduli (2-faza)
Eshitish va nutqida nuqsoni bo‘lgan fuqarolar uchun:
- **Sign-to-Text:** MediaPipe Holistic (qo‘l 2×21, tana 33 nuqta, yuz mimikasi) → ketma-ketlik modeli → glosslar → LLM grammatik to‘g‘ri huquqiy savol tuzadi.
- **Text-to-Sign:** xulosa soddalashtiriladi va 3D avatar (WebGL/Three.js, RN Filament) orqali ko‘rsatiladi.

Oldindan talab: o‘zbek imo-ishora tili bo‘yicha ma’lumotlar to‘plami va gloss lug‘ati, imo-ishora mutaxassislari bilan hamkorlik. Shu sababli modul 16 haftalik asosiy rejadan tashqarida (§11).

### 5.3 Advokatlik siri va O‘RQ-547
1. **PII niqoblash:** OCR dan keyin matn LLM ga yetib borishidan oldin PIIVault dan o‘tadi: “Fuqaro Karimov Anvar Botirovich (JSHSHIR: 3120…)” → “Fuqaro `<SHAXS_1>` (JSHSHIR: `<ID_1>`)”. Asl qiymatlar Redis da AES-256 bilan shifrlangan holda, TTL bilan saqlanadi.
2. **De-anonimizatsiya:** xulosa foydalanuvchiga yuborilishidan oldin tokenlar asl qiymatlarga qaytariladi.
3. **Zero-Retention rejimi:** tahlil tugagach yuklangan fayllar o‘chiriladi; faqat foydalanuvchi kaliti bilan shifrlangan xulosa saqlanadi.
4. Ma’lumotlar O‘zbekiston hududidagi serverlarda saqlanadi (O‘RQ-547 lokalizatsiya talabi). GPU server xorijda bo‘lsa, unga faqat niqoblangan matn yuboriladi va u yerda saqlanmaydi (§13, 5-qaror).

### 5.4 Ko‘p tillilik
Tizim 5 tilda ishlaydi: **o‘zbek (lotin)**, **o‘zbek (kirill)**, **rus**, **qoraqalpoq**, **ingliz**.

| Qatlam | Talab |
|---|---|
| Interfeys (veb, mobil, admin) | Barcha matnlar tarjima fayllarida (`uz-Latn`, `uz-Cyrl`, `ru`, `kaa`, `en`); kodda qotirilgan matn bo‘lmaydi. Veb va mobil — i18next, backend xabarlari — Django gettext. Til foydalanuvchi profilida saqlanadi |
| AI javobi | Foydalanuvchi tanlagan tilda (savol tilidan qat’i nazar sozlanadi) |
| Qonun iqtiboslari | **Faqat rasmiy matndan**, tanlangan tildagi lex.uz versiyasidan. Rasmiy versiya yo‘q bo‘lsa (masalan, qoraqalpoq yoki ingliz), iqtibos asl tilda keltiriladi, yonida **“norasmiy tarjima”** belgisi bilan tarjimasi beriladi |
| O‘zbek lotin ↔ kirill | AI faqat bitta yozuvda yozadi; ikkinchisi deterministik transliteratsiya bilan hosil qilinadi (rasmiy iqtiboslar bundan mustasno — ular lex.uz dagi tayyor matndan olinadi) |
| Qidiruv | bge-m3 ko‘p tilli: savol istalgan tilda bo‘lishi mumkin; korpusda o‘zbek lotin, kirill va rus versiyalari indekslanadi |
| Hujjat shablonlari | Har bir shablonning tillar bo‘yicha versiyalari; sudga beriladigan hujjat tili protsessual qoidalarga mos tanlanadi |
| OCR | Kirish hujjatlari: lotin, kirill, rus, qoraqalpoq, ingliz |

Qoraqalpoq tili kam resursli til: AI ning bu tildagi javob sifati §10 dagi sinov to‘plamida alohida o‘lchanadi. Sinov to‘plamida har 5 til bo‘yicha savollar bo‘ladi.

---

## 6. Qonunchilik korpusi (lex.uz)

### 6.1 lex.uz formatlari (tekshirilgan)
- **Hujjat id:** belgisi yozuvni bildiradi (`-111453` — lotin, `111453` — kirill), lekin 2025–2026 yillardagi ≈3 000 hujjatda bu qoida buziladi. Shuning uchun tizim `abs_id` + `script` saqlaydi va yozuvni sarlavha belgilaridan aniqlaydi.
- **Hujjat sahifasi:** `div.lx_elem` elementlarining tekis ketma-ketligi, har birida raqamli `id`. Modda sarlavhasi — `CLAUSE_DEFAULT` klassi (“168-modda. Firibgarlik”), indeks belgilari `<sup>` da.
- **Havola:** `https://lex.uz/uz/docs/-111453#<elem_id>` (anchor — element id, modda raqami emas).
- **Tahrirlar:** `?ONDATE=<yorliq>`; yorliq `dd.mm.yyyy` yoki bir kunda bir nechta tahrir bo‘lsa `dd.mm.yyyy NN` (masalan, JK uchun 163 ta tahrir). Ro‘yxatda kelajak sanali (hali kuchga kirmagan) tahrirlar ham bo‘ladi.
- **Til versiyalari:** har bir tilning matni alohida hujjat id siga ega. URL dagi `/uz/`, `/ru/`, `/en/` prefiksi faqat sayt interfeysi tilini o‘zgartiradi. Versiyalar sahifadagi til almashtirgichdan olinadi (masalan, JK: lotin `-111453`, kirill `111453`, rus `111457`). Yadro korpusida (1 499 hujjat, 2026-10-24): kirill va rus versiyasi deyarli hammasida, **ingliz versiyasi ≈730 tasida** bor; qoraqalpoq versiyasi til almashtirgichda yo‘q (qoraqalpoq matnlar reyestrda alohida hujjat sifatida uchraydi).
- **Yangilanishlar:** `https://lex.uz/uz/rss`.

### 6.2 Korpus tarkibi
Reyestr (`barcha_57950_hujjat.json`, 2026-10-20 holatiga): 57 950 hujjat, 71% kuchda.

| Qatlam | Tarkib | Hajm | Ishlov |
|---|---|---|---|
| Reyestr | Barcha hujjatlar metadatasi | 57 950 | PostgreSQL (FTS + pg_trgm sarlavha bo‘yicha qidiruv) |
| Yadro | Kuchdagi Konstitutsiya, konstitutsiyaviy qonunlar, 21 kodeks, qonunlar, Plenum qarorlari | ≈1 550 (shundan ≈740 tasi o‘zgartirish kirituvchi emas) | To‘liq parsing: modda/qism/band, barcha tahrirlar, Qdrant (dense + sparse) |
| Kengaytirilgan | Kuchdagi Prezident farmon/qarorlari (≈4 170), VM qarorlari (≈6 170) | ≈10 300 | 2-navbatda to‘liq indekslash |
| Qolganlari | Idoraviy, mahalliy, xalqaro | ≈30 000 | So‘rov bo‘yicha yuklash va keshlash |
| Sud amaliyoti | Buyurtmachi taqdim etadigan tayyor sud qarorlari to‘plami | aniqlanadi | Format kelgach import, PII niqoblash va Qdrant indekslash (§13) |

**Muhim:** Konstitutsiya (`-6445145`) reyestrda turi va sanasisiz keladi — yadro ro‘yxatiga qo‘lda kiritiladi.

### 6.3 Metadata sifati va normallashtirish
- `act_type` 5 025 xil yozilgan (masalan, Plenum uchun 20 xil), 40 tasi bo‘sh, ≈70 tasi axlat (`'1'`, `'s'`). Kanonik `doc_type` ga lug‘at + qoidalar orqali xaritalanadi; raqam formati (`PF-…`, `PQ-…`, `…-Q/…-son`) zaxira belgi sifatida ishlatiladi.
- `act_number` 24% bo‘sh, `act_date` 10% bo‘sh.
- Sarlavhalar: apostroflar (4 xil), homogliflar, ortiqcha bo‘shliqlar normallashtiriladi; asl qiymat ham saqlanadi.
- Status faqat “kuchda” / “kuchini yo‘qotgan”; modda darajasidagi holat va kuchga kirish sanasi hujjat matni va tahrirlardan olinadi. `act_date` (qabul qilingan sana) `effective_from` sifatida ishlatilmaydi.

### 6.4 Sinxronizatsiya
Har kecha 02:00 da: RSS + reyestrning birinchi sahifalari bo‘yicha yangi hujjatlar; **oxirgi 60 kunlik hujjatlar status va tahrirlar bo‘yicha qayta tekshiriladi** (lex.uz ga hujjatlar kechikib kiritiladi). Yadro hujjatlarida yangi tahrir paydo bo‘lsa, ular qayta parsing va indekslanadi. So‘rovlar orasida kechikish (≥0.5 s) saqlanadi.

---

## 7. Ma’lumotlar bazasi strukturasi (PostgreSQL 16 + Qdrant)

### 7.1 Foydalanuvchilar va anti-fraud
**users_user**
| Ustun | Turi | Tavsif |
|---|---|---|
| id | UUID PK | |
| phone_number | VARCHAR(20) UNIQUE | Tasdiqlangan +998… raqam |
| full_name | VARCHAR(255) | F.I.Sh. |
| role | ENUM | CLIENT, LAWYER, MODERATOR, SUPERADMIN |
| advocate_license_no | VARCHAR(50) NULL | Advokatlik guvohnomasi |
| oneid_pinfl_hash | VARCHAR(64) NULL | OneID/MyID JSHSHIR ning SHA-256 xeshi (tuz bilan) |
| is_fraud_flagged | BOOLEAN | |
| consents_json | JSONB | Shaxsiy ma’lumot va qurilma identifikatorlariga rozilik (sana, versiya) |

**antifraud_device_registry**
| Ustun | Turi | Tavsif |
|---|---|---|
| id | UUID PK | |
| hardware_fingerprint | VARCHAR(128) UNIQUE | Widevine ID / App Attest / FingerprintJS xeshi |
| platform | ENUM | IOS, ANDROID, WEB |
| free_trial_consumed | BOOLEAN | |
| consumed_by_user_id | UUID FK | |
| associated_users_count | INTEGER | |
| last_ip_address | INET | + ASN |
| is_blacklisted | BOOLEAN | |

### 7.2 Tariflar va limitlar
**billing_subscription_plan:** id SERIAL PK; code VARCHAR(30) UNIQUE (FREE, PRO_MONTHLY, ENTERPRISE_YEARLY); price_uzs DECIMAL(12,2); daily_case_limit INT; monthly_case_limit INT NULL; lifetime_case_limit INT NULL (FREE = 1); max_pages_per_case INT; daily_template_limit INT; priority_queue BOOLEAN.
**billing_user_quota_log:** user_id UUID FK; quota_date DATE; cases_used_today INT; pages_processed_today INT; llm_tokens_used INT; gpu_seconds_used INT; llm_cost_usd DECIMAL(10,4).
**billing_payment:** id; user_id; provider ENUM (CLICK, PAYME); amount_uzs; status; external_id; created_at.

### 7.3 Qonunchilik korpusi
**legal_act_document**
| Ustun | Turi | Tavsif |
|---|---|---|
| abs_id | BIGINT PK | `abs(lex.uz id)` |
| lex_id_lat / lex_id_cyr | VARCHAR(16) NULL | Har bir yozuvdagi asl id (masalan `-111453` / `111453`) |
| doc_type | ENUM | CONSTITUTION, CONST_LAW, CODE, LAW, PLENUM, PRES_DECREE, PRES_RESOLUTION, VMQ, PARLIAMENT, MINISTRY, LOCAL, INTL_TREATY, OTHER |
| act_type_raw | TEXT | lex.uz dagi asl qiymat |
| issuer | VARCHAR(255) | Qabul qilgan organ (normallashtirilgan) |
| hierarchy_weight | FLOAT | 0.60–1.00 (§4.2) |
| official_number | VARCHAR(100) NULL | O‘RQ-547, PQ-123, … |
| adoption_date | DATE NULL | Qabul qilingan sana |
| effective_from / effective_until | DATE NULL | Matn va tahrirlardan |
| title_uz_lat / title_uz_cyr / title_ru | TEXT | Mavjudlari |
| status | ENUM | ACTIVE, REPEALED, NOT_IN_FORCE |
| is_amending | BOOLEAN | O‘zgartirish kirituvchi / kuchini yo‘qotgan deb topuvchi hujjat |
| corpus_tier | ENUM | CORE, EXTENDED, ON_DEMAND |
| content_hash, last_synced_at | | Yangilikni aniqlash uchun |

**legal_act_edition:** id; document_id FK; edition_date DATE; source_url (`?ONDATE=`); fetched_at; content_hash.

**legal_act_article**
| Ustun | Turi | Tavsif |
|---|---|---|
| id | BIGSERIAL PK | |
| document_id | BIGINT FK | |
| edition_id | FK | Qaysi tahrirga tegishli |
| article_number | VARCHAR(50) | “168”, “168¹” |
| part / clause | VARCHAR(20) NULL | Qism / band |
| heading | TEXT | “Firibgarlik” |
| content_uz_lat / content_uz_cyr | TEXT | Rasmiy matn |
| lex_elem_id | VARCHAR(32) | lex.uz sahifadagi element id |
| valid_from / valid_until | DATE NULL | Modda tahririning amal qilish oralig‘i |
| qdrant_point_id | UUID | |
| direct_lex_url | VARCHAR(500) | `https://lex.uz/uz/docs/-111453#<lex_elem_id>` |

### 7.4 Advokat ishlari, tahlil va shablonlar
**cases_legal_case:** id UUID; user_id FK; case_category ENUM (CRIMINAL, CIVIL, ECONOMIC, ADMINISTRATIVE, LABOR); client_role ENUM (PLAINTIFF, DEFENDANT, ACCUSED, VICTIM); total_pages INT; pipeline_status ENUM (UPLOADING, OCR_RUNNING, FACT_EXTRACTION, LEGAL_SEARCH, CRITIC_PASS_1, CRITIC_PASS_2, CRITIC_PASS_3, AWAITING_LAWYER, COMPLETED, FAILED); zero_retention BOOLEAN.
**cases_source_file:** id; case_id FK; file_name; pages INT; storage_path; sha256.
**cases_extracted_fact:** id BIGSERIAL; case_id FK; source_file_id FK; page_number INT; bbox_coordinates JSONB `[x1,y1,x2,y2]`; event_date DATE NULL; fact_type ENUM; fact_summary TEXT; contradicts_fact_id BIGINT NULL.
**cases_analysis_report:** id; case_id FK; verification_passes INT (standart 3); unverified_claims_count INT; executive_summary TEXT; contradictions_json JSONB; legal_qualification_json JSONB (moddalar, Plenum bandlari, havolalar); defense_strategy TEXT; risk_warnings TEXT; lawyer_confirmed BOOLEAN; lawyer_confirmed_at TIMESTAMP.
**templates_document_template:** id UUID; title VARCHAR(255); category; docx_file_path VARCHAR(500) (Jinja2 teglari); form_schema_json JSONB; version; approved_by FK (moderator).

---

## 8. Obuna, limitlar va anti-fraud

### 8.1 Tarif rejalari
Barcha limitlar Admin paneldan boshqariladi (kodda qotirilmaydi). Quyidagi qiymatlar — 24 GB server uchun boshlang‘ich taklif; dev PC da faqat yopiq beta ishlaydi (§3.3).

| Ko‘rsatkich | Bepul | Pro (oylik) | Enterprise (yillik, byuro) |
|---|---|---|---|
| Ish tahlili | Umrbod 1 marta (akkaunt va qurilmaga) | Kuniga 10, oyiga 300 gacha | Kuniga 35 + VIP navbat |
| Bitta ish hajmi | 15 varaq | 150 varaq | 500 varaq |
| Shablonlar | 1 ta (suv belgisi bilan) | Cheksiz + AI tahrirlash | Cheksiz + korporativ shablonlar, firma blankasi |
| Huquqiy savol-javob (chat) | 3 ta savol | Kuniga 100 | Cheksiz, jamoaviy (3–5 foydalanuvchi) |

To‘lov: Payme va Click, veb-sayt orqali. Mobil ilovada obuna veb-sayt orqali rasmiylashtiriladi (§13, 2-qaror).

### 8.2 4 qatlamli anti-fraud
1. **Mobil attestatsiya:** iOS — DeviceCheck + App Attest + Keychain; Android — Play Integrity API + MediaDrm Widevine ID. Emulyator va root qilingan qurilmalarda bepul tarif berilmaydi.
2. **Brauzer fingerprint:** FingerprintJS → `visitor_hash`.
3. **SMS OTP + IP/ASN:** faqat +998 raqamlar (Eskiz.uz / PlayMobile); VPN, proxy, Tor va data-center IP lardan bepul tahlil bloklanadi.
4. **Sessiya limiti:** bir vaqtda 1 veb + 1 mobil sessiya; yangi qurilmadan kirilganda eskisi chiqariladi.

Qurilma identifikatorlari va fingerprintlar shaxsga doir ma’lumot hisoblanishi mumkin: ular faqat xesh ko‘rinishida saqlanadi, maxfiylik siyosatida ochiq yoziladi va foydalanuvchi roziligi (`consents_json`) olinadi.

---

## 9. Dasturiy arxitektura

### 9.1 Backend (Django + FastAPI + Celery)
```
mezon_backend/
├── config/              # Django settings, ASGI/WebSockets, Celery
└── apps/
    ├── accounts/        # JWT, OneID, SMS OTP, rollar
    ├── antifraud/       # DeviceCheck, Play Integrity, FingerprintJS, IP/ASN
    ├── billing/         # Tariflar, Payme/Click webhooklar, kvotalar
    ├── lex_corpus/      # lex.uz reyestr, parser, tahrirlar, sync, Qdrant indekser
    ├── cases/           # Fayl yuklash, OCR, tahlil natijalari
    ├── ai_engine/
    │   ├── hardware/    # 8 GB / 24 GB model loader, GPU navbati
    │   ├── pii_vault/   # Niqoblash / qaytarish
    │   ├── rag/         # Qdrant dense+sparse, PostgreSQL FTS, reranker
    │   ├── agents/      # LangGraph: Extractor, Researcher, Critic, Reporter
    │   └── verifier/    # Deterministik iqtibos va status tekshiruvi
    ├── doc_builder/     # docxtpl, TipTap JSON → DOCX/PDF
    ├── sign_language/   # 2-faza
    └── admin_dashboard/ # Analitika va boshqaruv API
```
Celery navbatlari: `default`, `ocr` (CPU), `gpu` (bitta worker), `sync`.

### 9.2 Veb (React + Vite + TypeScript)
1. **Advokat ishchi stoli (split-screen):** chapda PDF ko‘ruvchi (react-pdf) — ziddiyatli abzaslar bbox bilan sariq/qizil ajratiladi; o‘ngda xulosa, ziddiyatlar jadvali, lex.uz moddalari va TipTap muharrir. `[42-varaq]` iqtibosiga bosilsa, PDF o‘sha varaqqa o‘tadi; lex.uz iqtibosiga bosilsa, modda matni (tegishli tahrir sanasi bilan) ochiladi.
2. **SuperAdmin paneli:** tarif va limitlar konstruktori; anti-fraud monitor (bir qurilmada 2+ akkaunt, 1 tugma bilan bloklash); AI sifat va xarajatlar radari (Critic nechta xatoni ushladi, GPU vaqti, tokenlar); shablonlar boshqaruvi; lex.uz sinxronizatsiya holati.

### 9.3 Mobil ilova (React Native — iOS va Android)
- **Batch skaner:** qog‘oz chetini avtomatik topish, varaq aylantirilganda avtomatik suratga olish, oq-qora kontrast, WebP/PDF siqish.
- **Real-time progress:** WebSocket orqali bosqichlar, tugaganda push (FCM/APNs).
- **Imo-ishora kamerasi** — 2-faza.

### 9.4 Dizayn
UI `designs/` dagi 8 ta ekran va `designs/mezon_sovereign_precision/DESIGN.md` dizayn tizimiga mos quriladi.

---

## 10. Sifat mezonlari (KPI) va qabul qilish
Yurist-hamkor bilan tayyorlangan **test to‘plami** (kamida 30 ta anonimlashtirilgan real ish + 100 ta huquqiy savol) bo‘yicha o‘lchanadi:

| Mezon | Maqsad (beta) |
|---|---|
| OCR: bosma matn, CER | ≤ 2% |
| OCR: qo‘lyozma, CER | o‘lchanadi, alohida maqsad belgilanadi |
| Fakt ekstraksiyasi: recall (sana, summa, ishtirokchi) | ≥ 90% |
| Iqtiboslar: bazada mavjud va voqea sanasida kuchda | 100% (deterministik tekshiruv kafolatlaydi) |
| Iqtiboslar: mazmunan to‘g‘ri (yurist bahosi) | ≥ 90% |
| Ziddiyatlar: topilganlarning to‘g‘riligi (precision) | ≥ 80% |
| PII: JSHSHIR va pasport niqoblash recall | ≥ 99% |
| Javob tili: 5 til bo‘yicha yurist bahosi (savodli, atamalar to‘g‘ri) | o‘zbek, rus, ingliz ≥ 90%; qoraqalpoq — o‘lchanadi |
| 15 varaqli ish, uchidan-uchigacha vaqt | ≤ 10 daq (8 GB), ≤ 3 daq (24 GB) |

---

## 11. Yo‘l xaritasi (16 hafta + 2-faza)
| Hafta | Bosqich | Ishlar | Natija |
|---|---|---|---|
| 1–3 | 1. Korpus + gibrid RAG | Docker: PostgreSQL, Qdrant, Redis. Reyestr importi va normallashtirish, yadro parseri (modda/band, tahrirlar, `lex_elem_id`), bge-m3 indekslash. LLM benchmarki (§3.3) | Modda bo‘yicha qidiruv, to‘g‘ri havolalar |
| 4–7 | 2. OCR + multi-agent | Buyurtmachining sud amaliyoti to‘plamini import qilish, PaddleOCR, PII Vault, LangGraph zanjiri (Extractor → Researcher → 3× Critic → Reporter), test to‘plami va KPI o‘lchovi | 15–50 varaqli ish uchun iqtibosli xulosa |
| 8–10 | 3. Shablonlar, to‘lov, anti-fraud | docxtpl, TipTap, Click/Payme, tariflar, 4 qatlamli anti-fraud | Pullik tariflar mexanizmi |
| 11–13 | 4. Veb va Admin panel | Split-screen ishchi stol, HITL oynasi, SuperAdmin | Veb beta |
| 14–16 | 5. Mobil + server | RN batch skaner, push, 24 GB serverga ko‘chirish (vLLM, 14B/32B), bulutdan GPU server ijarasi (§13, 5-qaror), advokatlar bilan yopiq beta | Tijoriy ishga tushirishga tayyorlik |
| 2-faza | Imo-ishora tili | Ma’lumotlar to‘plami, Sign-to-Text, 3D avatar | — |

---

## 12. Huquqiy himoya va Human-in-the-Loop
Xulosa PDF/DOCX ko‘rinishida eksport qilinishidan oldin **“Yuridik tasdiqlash oynasi”** chiqadi: xulosada ishlatilgan barcha moddalar, ularning lex.uz dagi maqomi va tahrir sanasi, tasdiqlanmagan tasdiqlar ro‘yxati. Advokat “Asosiy dalillar va qonun moddalari bilan tanishdim” tugmasini bosgandan keyingina rasmiy fayl yaratiladi (`lawyer_confirmed`, vaqt belgisi bilan).

Bu mexanizm, foydalanuvchi shartnomasi va “tizim yuridik maslahat emas, advokat uchun yordamchi vosita” degan ogohlantirish bilan birga, dastur egasining javobgarlik xavfini kamaytiradi. Yakuniy huquqiy pozitsiya yurist-hamkor tomonidan tasdiqlanadi.

---

## 13. Qabul qilingan qarorlar
2026-10-23 dagi qarorlar:

| # | Masala | Qaror | Asos / oqibat |
|---|---|---|---|
| 1 | Tashqi AI API | **Ishlatilmaydi** (byudjet yo‘q) | Barcha modellar lokal. `LLMProvider` adapteri saqlanadi, lekin `HYBRID_API` provayderi yozilmaydi. Mijoz matni uchinchi tomon AI provayderlariga yuborilmaydi — advokatlik siri uchun ustunlik |
| 2 | To‘lov | **Payme va Click** | Veb-saytda to‘g‘ridan-to‘g‘ri. Mobil ilovada obuna sotish Google Play / App Store qoidalariga zid kelishi mumkin; shuning uchun mobil ilovada obuna veb-sayt orqali rasmiylashtiriladi (ilova ichida faqat akkauntga kirish). Do‘kon talablari ilova chiqarishdan oldin qayta tekshiriladi |
| 3 | Sud amaliyoti | **public.sud.uz dan yig‘ilmaydi** | Buyurtmachi tayyor sud qarorlari to‘plamini taqdim etadi. Format va hajm kelgach, import va indekslash (§6.2) rejalashtiriladi |
| 4 | Iyerarxiya vaznlari va KPI | **§4.2 va §10 dagi qiymatlar qabul qilindi** | Ular boshlang‘ich qiymatlar: 2-bosqichdagi test to‘plami natijasiga qarab Admin paneldan o‘zgartiriladi. Test to‘plamidagi to‘g‘ri javoblarni yurist tekshiradi |
| 5 | Server | **Bulutdan GPU server ijaraga olinadi** | O‘RQ-547 ga ko‘ra fuqarolarning shaxsga doir ma’lumotlari O‘zbekiston hududidagi serverlarda saqlanishi kerak. Shuning uchun: (a) foydalanuvchilar bazasi va yuklangan fayllar — O‘zbekistondagi serverda; (b) GPU server O‘zbekistonda topilsa — hammasi bitta joyda; topilmasa — xorijdagi GPU serverga faqat PII niqoblangan matn yuboriladi va u yerda saqlanmaydi. Variant (b) yurist bilan tasdiqlanadi |
| 6 | Qidiruv dvigateli | **Elasticsearch ishlatilmaydi.** Qdrant gibrid qidiruvi (bge-m3 dense + sparse) + PostgreSQL to‘liq matnli qidiruvi (FTS, pg_trgm) | ES alohida 2–4 GB RAM va xizmat talab qiladi; 16 GB RAM li dev PC da LLM bilan birga sig‘maydi. bge-m3 bitta modelda dense va sparse vektor beradi; aniq modda raqami va hujjat raqami bo‘yicha qidiruv PostgreSQL da deterministik bajariladi |
