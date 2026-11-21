# MEZON AI TZ (`MEZON-AI.pdf`) tahlili

Sana: 2026-10-23. Manba: `E:\mezon\MEZON-AI.pdf`. Hujjatning o'zida yozilishicha, bu "Loyiha Arxitekturasi v2.0", 2026-yil oktabr, 15 sahifa.
Taqqoslash uchun: `TAHLIL.md` (lex.uz metadata tahlili) va 2026-10-22 dagi loyiha qarorlari.

## 1. TZ qisqacha mazmuni
| Bo'lim | Mazmuni |
|---|---|
| 1. Konsepsiya | Advokatning 100–500 varaqli ishi qo'lda 2–3 kunda o'qiladi. Tizim quyidagilarni bajaradi: OCR (lotin, kirill, rus, qoraqalpoq; 99.5%), PII niqoblash, faktlar va ziddiyatlar jadvali, voqea sanasida amalda bo'lgan moddalarni qidirish, 3 karra tekshiruv, har bir gapga manba biriktirish |
| 2. Apparat va modellar | Fine-tuning taqiqlanadi, Hybrid RAG + iyerarxiya grafigi ishlatiladi. **8 GB (hozirgi PC):** Qwen2.5-7B Q4_K_M (4.8 GB), bge-m3 (1.1 GB), reranker, PaddleOCR va GLiNER CPU/ONNX da. **24 GB (kelajak server):** Qwen2.5-14B-AWQ/32B, vLLM, Surya OCR. `.env` orqali almashtiriladi; murakkab ishlar uchun gibrid API (Gemini/Claude/DeepSeek, PII niqoblangan holda) |
| 3. Multi-agent | LangGraph siklik grafi: (1) OCR, deskew, lotin↔kirill transliteratsiya, 5 sahifalik bloklarda map-reduce, fakt JSON (entities, timeline, summalar, protsessual sanalar), ziddiyatlar matritsasi → (2) Qdrant + Elasticsearch BM25, iyerarxiya vazni, sana bo'yicha tahrir filtri → (3) Critic 3 marta: bazada tekshirish, iqtibos va istisnolarni solishtirish, "Devil's advocate" → (4) iqtibosli xulosa |
| 4. Modullar | Hujjat konstruktori (200+ docxtpl shablon, AI bilan to'ldirish, TipTap muharrir), imo-ishora tili (MediaPipe → gloss → LLM; 3D avatar), advokatlik siri (PIIVault, Redis AES-256, Zero-Retention) |
| 5. Obuna va anti-fraud | Free / Pro / Enterprise tariflari Admin paneldan boshqariladi. Anti-fraud 4 qatlamdan iborat: DeviceCheck/App Attest, Play Integrity + Widevine ID; FingerprintJS; +998 SMS OTP + VPN/ASN bloki; sessiya limiti (1 veb + 1 mobil) |
| 6. Ma'lumotlar bazasi | users_user, antifraud_device_registry, billing_*, legal_act_document, legal_act_article, cases_*, templates_document_template |
| 7. Arxitektura | Django + Celery (`lexai_backend/apps/...`), React + Vite + TS (split-screen ishchi stol, SuperAdmin), React Native (avtomatik batch skaner, WebSocket progress, push) |
| 8. Yo'l xaritasi | 16 hafta, 5 bosqich: lex.uz + RAG → OCR + agentlar → shablon, to'lov, anti-fraud → veb + admin → mobil, imo-ishora, 24 GB server + beta |
| HITL | Eksportdan oldin "Yuridik tasdiqlash oynasi" ko'rsatiladi, unda moddalar va ularning maqomi bo'ladi |

`designs/` dagi 8 ekran TZ modullarini to'liq qoplaydi: ishchi stol (7.2), anti-fraud flow (5.2), konstruktor (4.1), HITL (8), imo-ishora (4.2), superadmin radar (7.2), tariflar (5.1), batch skaner (7.3).

## 2. TZ va mavjud ma'lumot o'rtasidagi tafovutlar (eng muhimi)
| TZ talabi | Haqiqiy holat (`TAHLIL.md`) | Kerakli ish |
|---|---|---|
| Manba: "lex.uz (to'liq baza), Plenum, public.sud.uz kazuslari" | Faqat 57 950 ta metadata bor. Matn, Plenum matni va sud kazuslari yo'q | Core (1 546) parser kerak. Plenum bandlari bo'yicha alohida parser kerak. public.sud.uz uchun hali hech narsa yo'q, uning foydalanish shartlarini ham tekshirish kerak |
| `legal_act_document.lex_id` = "111453" | id ishorasi lotin/kirillni bildiradi, lekin 2025–26 yildagi 3 029 ta hujjatda bu qoida buziladi | PK = `abs(id)` + alohida `script` ustuni. Har bir tildagi nusxa uchun asl id saqlanadi |
| `title_uz_lat / cyr / ru` | Ro'yxatda har hujjatda bitta sarlavha bor; lotin+kirill juftligi faqat 66 ta | Boshqa yozuvdagi sarlavha hujjat sahifasidan olinadi yoki transliteratsiya qilinadi |
| `doc_type` ENUM: CONSTITUTION, CODE, LAW, PLENUM, DECREE, VMQ | act_type 5 025 xil yozilgan, Konstitutsiyada bo'sh, 56 tasida `'1'` | Kanonik xaritalash kerak. Enum'ga yetishmaydigan turlar: CONST_LAW, PRES_RESOLUTION (PQ), PARLIAMENT, MINISTRY_ORDER, INTL_TREATY, LOCAL, OTHER |
| `effective_from / effective_until` | Metadata'da faqat qabul sanasi (`act_date`, 10% bo'sh) bor; kuchga kirish va kuchini yo'qotish sanasi yo'q | Hujjat matni yoki tahrirlar tarixidan (`?ONDATE`) olinadi. `act_date` ni `effective_from` deb ishlatmaslik kerak |
| `status` ACTIVE/REPEALED | Ikki qiymat bor; modda darajasidagi holat yo'q | Modda darajasidagi holat va "kuchga kirmagan" holati alohida saqlanadi |
| `direct_lex_url` = `lex.uz/docs/111453#168`, iqtibos `111460#173` | Anchor modda raqami emas, element id. URL `/uz/docs/-111453#<elem_id>` ko'rinishida | `legal_act_article` ga `lex_elem_id` ustuni qo'shiladi |
| `official_number` (O'RQ-547, PQ-123) | `act_number` 24% bo'sh. Formatlari: `PF-N-son`, `PQ-N-son`, `N-N-N-Q/N-son` | 1-tekshiruvda (VMQ-249 ni qidirish) raqamni normallashtirish va sana bilan birga qidirish kerak; raqam o'zi yagona emas |
| Iyerarxiya: Konst 1.0 > Konst.qonun/Kodeks 0.95 > Qonun 0.90 > Plenum … | PDF da qator kesilib qolgan, qolgan vaznlar ko'rinmaydi. 29% hujjat o'zgartirish kirituvchi | To'liq jadval yurist bilan kelishiladi. O'zgartirish kirituvchi hujjatlarga jarima koeffitsiyenti beriladi |
| "Har kecha 02:00 da lex.uz sinxronizatsiyasi" | Sentyabr–oktyabr 2026 to'liq emas, lex.uz ga kechikib kiritiladi | Sync oxirgi 60 kunni qayta tekshirishi kerak, faqat yangi id lar yetarli emas |

## 3. Oldingi qarorlar
2026-10-23 da foydalanuvchi 22-oktabrdagi barcha qarorlarni bekor qildi; loyiha 0 dan, `TZ-v2.1.md` asosida davom etadi.
TZ ning o'z texnik tanlovlari (Elasticsearch, ixtiyoriy gibrid API, React Native, 16 hafta, Click/Payme) v2.1 da saqlandi;
munozarali joylar v2.1 ning 13-bo'limiga "Ochiq savollar" sifatida chiqarildi.
- **Nom**: "LexAI Uzbekistan" va `lexai_backend/` qoldiqlari v2.1 da MEZON ga almashtirildi.

## 4. Texnik xavflar va realizm tekshiruvi
1. **VRAM byudjeti 8.0/8.0 GB, zaxira yo'q.** O'lchangan Qwen ~5 GB. 7B uchun 8–16K kontekstda KV-kesh qo'shimcha joy oladi. bge-m3 ni indekslashdan keyin CPU/ONNX ga o'tkazish yoki LLM bilan navbatma-navbat yuklash kerak (TZ dagi "Sequential Resource Allocation" g'oyasi to'g'ri).
2. **Tezlik va tarif limitlari mos kelmaydi.** O'lchangan tezlik 16.8 tok/s. 150 varaq ≈ 30 blok × ~800 token fakt JSON ≈ 24 000 token ≈ **~24 daqiqa** faqat ekstraksiya uchun. Bunga prefill, qidiruv va 3 ta Critic o'tishi qo'shiladi, natijada bitta katta ish ≈ 40–60 daqiqa. Pro tarifning "kuniga 10 ta katta ish" va'dasi bitta 2060S da bitta foydalanuvchiga ham yetmaydi. Tarif raqamlari 24 GB server va vLLM ga moslab berilishi yoki demo davrida yumshatilishi kerak.
3. **"99.5% OCR", "Zero-Hallucination", "100% huquqiy himoya"** — bu marketing va'dalari, o'lchanadigan talab emas. Qo'lyozma, muhr va qoraqalpoq tili uchun PaddleOCR 99.5% bermaydi. HITL javobgarlikni kamaytiradi, lekin "100% himoya" degan da'voni yurist hamkor bilan tekshirish kerak. Taklif: TZ ga o'lchanadigan mezonlar kiritilsin (CER, tasdiqlangan iqtibos ulushi, hallucination_score chegarasi).
4. **Qwen 7B va o'zbek tili.** 7B modelning o'zbek tilida huquqiy matn yozish va JSON ekstraksiya sifati hali tekshirilmagan. Demo uchun eng katta noaniqlik shu. Kichik eval to'plami kerak (yurist hamkor bilan 20–30 ta savol).
5. **Anti-fraud va O'RQ-547.** Widevine ID, FingerprintJS, IP/ASN ma'lumotlari ham shaxsga doir ma'lumot bo'lishi mumkin; maxfiylik siyosati va rozilik kerak. Play Integrity va DeviceCheck ishlashi uchun server kaliti va Play Console sozlamalari kerak. iOS ga Mac bo'lmagani uchun App Attest faqat EAS orqali ishlaydi.
6. **Imo-ishora moduli** (o'zbek imo-ishora tili, gloss lug'ati, 3D avatar) — alohida ilmiy-tadqiqot hajmidagi ish, bunga ma'lumotlar to'plami ham kerak. Uni demo va 16 haftalik rejadan chiqarib, keyingi bosqichga qoldirish tavsiya etiladi.
7. **200+ shablon** — bu kontent ishi (yurist hamkor bajaradi), dasturiy ish emas. Demo uchun 3–5 tasi yetadi.
8. **PII Vault + gibrid API.** API bo'lmagani uchun niqoblash hozircha faqat log va saqlash xavfsizligi uchun kerak; tashqariga ma'lumot ketmaydi. Demo uchun soddalashtirish mumkin.

## 5. Hujjat sifati (PDF ning o'zi)
- "Contents" sahifasi bo'sh: mundarija generatsiya qilinmagan.
- Ko'p sarlavha va matnda bo'shliqlar yo'qolgan ("LoyihaKonsepsiyasivaMuammoYechimi"). 2.2, 6.x jadvallarida ustunlar bir-birining ustiga chiqib ketgan.
- 3.2-bo'limdagi iyerarxiya qatori sahifadan chiqib kesilgan; 7.1 dagi daraxt izohlari ham kesilgan.
- Imlo xatolari: "Patpiska" (obuna), "ORQ-547" / "OʻRQ-547" aralash yozilgan.
- 3-bo'lim sarlavhasida "4 bosqichli", annotatsiyada "3 bosqichli tekshiruv" deyilgan; bu ikki xil narsa (4 bosqich, 3 tekshiruv), lekin tushunarsiz yozilgan.

## 6. Tavsiya: TZ ga kiritiladigan o'zgarishlar
1. Ma'lumot manbalari bo'limiga 3 qatlamli korpus (reyestr, core 1 546, on-demand) va lex.uz ning haqiqiy id/anchor formatini yozish.
2. `legal_act_document` / `legal_act_article` sxemasini 2-bo'limdagi jadval asosida tuzatish: abs_id + script, lex_elem_id, kengaytirilgan doc_type, is_amending, edition_date.
3. ES va Qdrant sparse tanlovini benchmarkga qoldirish; gibrid API ni ixtiyoriy deb belgilash.
4. Imo-ishora modulini 2-fazaga o'tkazish.
5. Tarif limitlarini o'lchangan tezlikka moslash va marketing va'dalarini o'lchanadigan KPI larga aylantirish.

> **Holat:** 6-bo'lim tavsiyalari `TZ-v2.1.md` da qo'llandi (2026-10-23).
