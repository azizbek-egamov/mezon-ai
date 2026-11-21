# MEZON AI — davom etish qo'llanmasi (yangilangan 2026-11-18; Yurxizmat.uz 2449 shablon + Metismenu 31 bo'lim + 17-bosqich)

**Yangi chatni shu fayldan boshlang.** Avval `CLAUDE.md` (loyiha qoidalari), keyin shu fayl. Foydalanuvchi bilan o'zbek tilida (lotin) gaplashing.

## 1. Qayerdamiz
Backend rejasi (1–12-bosqichlar) **tugagan**: Django 6.1 + RAG + ish tahlili + tariflar + 5 tilli interfeys.
**Faza 2**: backend ustiga **React veb-sayt, React admin panel va React Native (Expo) ilova**. **13-bosqich (API v1) tugadi**
(2026-10-29): `/api/v1/*` JSON API, JWT, OpenAPI. **14-bosqich (React veb-sayt) tugadi** (2026-10-29): `frontend/apps/web`,
brauzerda tekshirilgan. **15-bosqich (admin panel + admin API) tugadi** (2026-10-29): `frontend/apps/admin`, `/api/v1/admin/*`;
backend 231 test, frontend 11 test. **16-bosqich (Expo mobil ilova) kodi tayyor** (2026-10-29): `frontend/apps/mobile`, Node 22;
UI veb-rejimda va **jismoniy telefonda (Samsung Galaxy A16, Android 16) sinaldi** (2026-10-29, 4c-bo'lim). **17-bosqich (production tarmoq) — kod va zaxira tayyor** (2026-10-30, 4d-bo'lim): waitress + whitenoise, bitta domen (veb `/`, admin `/panel/`, API), shifrlangan zaxira; quick tunnel orqali HTTPS da sinaldi. **Domen yo'q** — named tunnel domen olingach ulanadi; tungi vazifalar (`schtasks`) ruxsat bilan yaratiladi. **Joriy holat (2026-11-18): backend testlari va 6 paket frontend typecheck — to'liq o'tgan. Yurxizmat.uz saytidan 964 ta hujjat 6 ta toifa va 31 ta bo'lim (metismenu iyerarxiyasi) bo'yicha bazaga to'liq o'tkazildi (jami 2,449 ta shablon: `uz-Latn`, `uz-Cyrl`, `ru`). Frontend `/templates` bo'limi subkategoriya filtrlari bilan boyitildi. Qoldi: `kaa` va `en` tillariga hamda yetishmayotgan ruschaga yuridik AI tarjimasi.**
Hozirgi veb (`mezon_backend/apps/*/templates`) — Django shablonlari + inline JS; u vaqtinchalik, SPA tayyor bo'lgach o'chiriladi.

### Backend bajarilganlari (batafsil: `mezon_backend/README.md`)
| # | Modul | Qisqacha |
|---|---|---|
| 1 | `apps/accounts` | telefon (+998) + parol, rollar CLIENT/LAWYER/MODERATOR/SUPERADMIN, `User.language`, ish faqat egasiga ko'rinadi |
| 2 | `apps/cases/storage.py` | PDF/hisobot Fernet bilan shifrlangan, zero-retention, ish o'chirish |
| 3–4 | `apps/lex_corpus`, `apps/rag` | 1501 yadro hujjati, tahrirlar tarixi, gibrid qidiruv (bge-m3 + Qdrant + reranker), iqtibosli javob, deterministik tekshiruvchi |
| 5 | `apps/cases/export.py` | "tanishdim" yuridik tasdiq → DOCX/PDF |
| 6 | `apps/doc_builder` | shablonli hujjatlar (AI siz), moderator tasdig'i |
| 7 | `lex_corpus/sync.py` | `sync_lex` tungi yangilash |
| 8 | `lex_corpus/translations.py` | kirill va rus matnlari, 3 tilli indeks (131 476 nuqta) |
| 9 | `apps/cases/intake.py`, `ocr.py`, `cyr_fix.py` | PDF/DOCX/JPG/PNG → bitta PDF, deskew, o'zbek kirill OCR tuzatishi |
| 10 | `apps/i18n` | uz-Latn, uz-Cyrl, ru, kaa (kirill), en; `i18n_sync`, `translit.py` |
| 11 | `apps/billing` | Bepul/Pro/Enterprise, kvotalar, `/billing/`, `grant_plan` |
| 12 | `apps/cases/case_types.py` | jinoyat / fuqarolik / iqtisodiy / ma'muriy / boshqa — doira + promptlar |

## 2. Qabul qilingan qarorlar (foydalanuvchi, 2026-10-29)
| Savol | Qaror |
|---|---|
| Veb-sayt | **Alohida React (Vite SPA)**, Django faqat API |
| Mobil | **Expo** (React Native) |
| Admin panel | **Alohida React admin** (Django admin emas) |
| Tashqi ulanish | hozircha **faqat USB `adb reverse`** (Cloudflare Tunnel keyinroq, production uchun) |
| Auth | **JWT** (simplejwt); veb — refresh **HttpOnly cookie** da, access xotirada; mobil — refresh tanada → `expo-secure-store` |
| UI (veb, admin) | **Tailwind + shadcn/ui**; tokenlar `designs/mezon_klassik/DESIGN.md` dan (`packages/web-kit/src/theme.css`) |
| Monorepo | **npm workspaces** (`frontend/`) |
| Git | **keyinroq** (foydalanuvchi 2026-10-29 da hozircha kerak emas dedi) — bosqich oxirida yana bir eslating |

Ochiq: mobil UI (NativeWind yoki oddiy StyleSheet) — 16-bosqich boshida so'rang.

## 3. Muhit faktlari (muhim)
- Windows 11, Git Bash. **PC server vazifasini bajaradi**: RTX 2060S 8 GB, RAM 16 GB. Modellar GPU da; Qdrant alohida server.
- Ishga tushirish: `cd E:\mezon\mezon_backend` → `powershell -ExecutionPolicy Bypass -File tools\dev.ps1 start` (Qdrant :6333 + Django :8010, `--noreload`: **kod/shablon o'zgarsa qayta ishga tushiring**), `stop` — RAM ~2.4 GB bo'shatish. Testlar: `.venv\Scripts\python manage.py test apps` (~60 s, API chaqirmaydi).
- Node 22.23.4 (nvm-windows; `frontend/package.json` `engines >=22.13`), 20.18 ham bor. `adb`: `C:\platform-tools\adb.exe`. `cloudflared`: `E:\cloudflared\cloudflared.exe`. Docker/WSL yo'q.
- **Bash heredoc ichida Python kodiga backslash (`\n`, `\b`, `\{`) yozmang** — buziladi (bir necha marta bo'lgan). Python/TS fayllarni Write/Edit vositalari bilan yozing; bir martalik skriptlar uchun ham Write.
- Dev baza: SQLite `data/dev.sqlite3`; **hozir foydalanuvchi yo'q**. `manage.py createsuperuser` (telefon so'raydi; `is_staff` akkaunt kvotadan ozod) yoki ro'yxatdan o'ting + `grant_plan <telefon> PRO_MONTHLY`. Dev akkaunt parollari `data/secret/` da — chatga chiqarmang.
- **Pul**: LLM — Gemini (4g); API chaqiradigan amal (`ask`, ish tahlili, `analyze_case`) **faqat foydalanuvchi ruxsati bilan**. Testlar LLM ni mock qiladi. `.env` dagi kalitlarni (`GEMINI_API_KEY`, `ANTHROPIC_API_KEY`, `MEZON_DATA_KEYS`) hech qachon chiqarmang.
- Qdrant qo'lda ishga tushirilgan bo'lishi mumkin — `curl http://127.0.0.1:6333/collections` bilan tekshiring.
- Dizayn: `E:\mezon\designs\` — har bir ekran uchun `code.html` + `screen.png` (advokat_ishchi_stoli, autentifikatsiya_va_anti_fraud_flow, hujjat_konstruktori, human_in_the_loop_yuridik_tasdiqlash, tezkor_skaner_batch, tariflar_va_obuna_boshqaruvi, superadmin_anti_fraud_radar, imo_ishora_moduli) va eski `mezon_sovereign_precision/DESIGN.md`. **2026-10-30 dan amaldagi uslub — `designs/mezon_klassik/DESIGN.md`** (foydalanuvchiga eski qorong'i "pult" uslubi yoqmadi); screen.png lar faqat ekran tarkibi uchun.

## 4. API v1 holati (13-bosqich, batafsil: `mezon_backend/README.md` → "API v1")
- `apps/api` — barcha endpointlar `/api/v1/`: `auth/{login,register,refresh,logout,me,language}`, `cases/` (+`options`,
  `{id}`, `report`, `pdf`, `confirmation`, `export/{fmt}`, `retry`), `chat/ask` (SSE), `templates/` (+`{id}`, `preview`,
  `render/{fmt}`), `billing/{usage,plans}`, `laws/{documents,documents/{id},articles/{id},search}`, `i18n/languages`.
  Swagger: `/api/v1/docs/`. Xato shakli: `{"detail", "code"}`; 429 — tarif limiti (`quota_*`).
- Tayyor frontend artefaktlari: `frontend/packages/api-client/openapi.yaml` (OpenAPI 3, ogohlantirishsiz) va
  `frontend/packages/i18n/locales/*.json` (`manage.py i18n_export_json`, i18next formatida). Yangilash buyruqlari README da.
- Biznes mantiq servislarga ajratilgan (`apps/cases/services.py`, `apps/accounts/lockout.py`, `rag.views.parse_ask`,
  `doc_builder.views.file_response`) — eski HTML sahifalar ham shularni chaqiradi; SPA tayyor bo'lgach o'chiriladi.
- **LLM siz dev server**: `tools/dev_nollm.py 8011` (`.claude/launch.json` da `mezon-api-nollm`) — frontendni pulsiz
  ishlab chiqish uchun: tahlil/chat darhol xato bilan tugaydi, qolgani to'liq ishlaydi. Vite proxy `/api` → `:8011` (yoki `:8010`).
- Dev baza: dev akkaunt (`data/secret/dev_accounts.txt`, LAWYER) API orqali ro'yxatdan o'tkazilgan, **PRO_MONTHLY**
  (2026-11-28 gacha) va bitta tayyor ish (`Sintetik ish (import)`, DONE, tasdiqlangan) — hisobot ekranlarini sinash uchun.
- 13-bosqich mezoni `curl` bilan tekshirilgan: login → yuklash (201) → holat (QUEUED→RUNNING→FAILED, LLM o'chiq) → kvota
  qaytdi → retry → delete; import qilingan ishda report/pdf/confirmation/export; veb cookie oqimi, rotatsiya, logout;
  `laws/*` jonli (Qdrant + GPU).
- Yetishmaydi (keyingi bosqichlarda): admin API (15), parolni o'zgartirish/tiklash (SMS OTP bilan, TZ §8.2),
  frontend matnlarini `.po` ga ajratish (`catalog.py` ga `frontend/**/*.tsx` dagi `t("...")` ni qo'shish, `{{n}}` → `%(n)s`).

## 4a. Veb-sayt holati (14-bosqich, batafsil: `frontend/README.md`)
- `frontend/` — npm workspaces: `packages/api-client` (OpenAPI tiplari, token yangilovchi fetch, SSE), `packages/i18n`
  (i18next + `.po` eksporti), `apps/web` (Vite 6 + React 19 + Tailwind 4 + shadcn uslubi, Radix). Node 20.18 sababli versiyalar
  mahkamlangan (Vite 6, react-router 7, react-pdf 9, TS 5.9); shadcn CLI ishlamaydi (Node ≥ 20.18.1) — komponentlar qo'lda.
  **16-bosqich (Expo) oldidan Node 22 LTS ga o'tishni foydalanuvchiga taklif qiling** (tizimga o'rnatish — ruxsat bilan).
- Ishga tushirish: `cd frontend && npm run dev:web:nollm` (LLM siz backend :8011 bilan, pulsiz) yoki `npm run dev:web` (:8010).
  Claude Code: `.claude/launch.json` → `qdrant`, `mezon-api-nollm`, `mezon-web-nollm` (preview_start).
- Barcha eski Django sahifalari imkoniyatlari SPA da: chat (SSE), ishlar (yuklash, ro'yxat, PDF ko'rgich + varaq tugmalari,
  hisobot, HITL tasdiq oynasi + eksport, retry, o'chirish), shablonlar, tarif, til almashtirgich (5 til), profil; qo'shimcha —
  qonunlar bazasi (`/laws`). Mobil (<1024px) — pastki navigatsiya, ish sahifasida tablar.
- Brauzerda tekshirilgan (LLM siz serverda): login xatosi va kirish, sessiya tiklanishi, chat SSE (manbalar → kutilgan xato),
  ish yuklash (drag & drop) → holat → FAILED → kvota qaytishi, PDF varaqqa o'tish, tasdiq oynasi (4/4 belgi), shablon
  ko'rinishi, qonun moddasi 3 tilda, til almashtirish (kaa, ru), mobil ko'rinish, chiqish (refresh bekor). **Brauzerda fayl
  yuklab olish bosilmagan** (eksport API si curl bilan sinalgan).
- Frontend matnlari backend katalogida: `i18n_sync` `frontend/**/*.ts(x)` dagi `t("...")` ni ham ajratadi (README → i18n).

## 4b. Admin panel holati (15-bosqich, batafsil: `frontend/README.md`, `mezon_backend/README.md` → "Admin API")
- `frontend/packages/web-kit` — veb va admin uchun umumiy UI/auth/til qatlami (veb shu paketga o'tkazildi).
- `frontend/apps/admin` (:5174): dashboard (dizayn: superadmin_anti_fraud_radar), foydalanuvchilar, tarif konstruktori, to'lovlar
  (qo'lda + "to'landi"), AI xarajat radari, anti-fraud, shablon moderatsiyasi, lex.uz sinxronizatsiyasi, amallar jurnali.
  Ruxsat: MODERATOR — shablonlar + sinxronizatsiya; SUPERADMIN — hammasi.
- Backend: `User.registered_ip/last_login_ip`, `accounts.AuditEvent` (migratsiya `accounts.0003`), chat xarajati `UsageLog` ga.
- Dev akkauntlar (`data/secret/dev_accounts.txt`): `+998000000002` SUPERADMIN, `+998000000003` MODERATOR (+ avvalgi LAWYER).
- Brauzerda tekshirilgan (LLM siz serverda, vaqtinchalik demo ma'lumot bilan — keyin o'chirildi): advokat → "ruxsat yo'q",
  dashboard va grafik, foydalanuvchi profili → obuna berish, to'lovni tasdiqlash, tarif konstruktori, anti-fraud belgilash,
  moderator: shablon yaratish (validatsiya xatosi → tuzatish) → sinov ko'rinishi → tasdiq, ruscha interfeys, mobil.
  **Majburiy sinxronizatsiya tugmasi brauzerda bosilmagan** (lex.uz ga tarmoq + qayta indekslash; API unit test bilan).
- Sinovda topilib tuzatilgan: GROUP BY so'rovida tariflar tartibi; kirgach `?next=` e'tiborsiz qolardi (veb ham);
  rol nomi cookie tilida qolardi; chat xarajati umuman yozilmasdi; xodimlar anti-fraud radariga tushardi.

## 4c. Mobil ilova holati (16-bosqich, batafsil: `frontend/README.md` → "Mobil ilova")
- Node 22.23.4 o'rnatildi (nvm-windows, foydalanuvchi ruxsati bilan 2026-10-29); 20.18.0 ham qoldi. React — root `overrides` bilan 19.3.0.
- `frontend/apps/mobile` (Expo SDK 58, RN 0.88, Expo Router): kirish/ro'yxatdan o'tish (refresh — secure-store), savol-javob
  (SSE), tezkor skaner (kamera/galereya/fayllar → bitta ish), ishlar ro'yxati, ish sahifasi (holat, retry, o'chirish, hisobot), tarif,
  profil (5 til). PDF telefonda ko'rsatilmaydi; eksport — veb-saytda.
- Tekshirilgan: `tsc`, `expo-doctor` 20/20, veb-rejim brauzerda (LLM siz backend bilan): login → tablar, chat SSE (xato hodisasi),
  ishlar ro'yxati → hisobot, tarif, profil, til almashtirish (kaa). `expo prebuild` (android) muvaffaqiyatli; Gradle debug build —
  natija pastdagi "Gradle" bandida.
- **Telefonda sinaldi** (2026-10-29, Galaxy A16 SM-A165F, Android 16, debug APK + Metro, `adb reverse`, LLM siz backend :8011):
  ishga tushish, kirish (cleartext HTTP + secure-store), chat SSE (manbalar va xato hodisasi), tablar, ishlar ro'yxati, ilova ichidagi
  brauzer (lex.uz), tizim Photo Picker (2 rasm), hujjat tanlagich (PDF), multipart yuklash (32 varaq bitta ishga), holat so'rovi,
  FAILED ko'rinishi, "Qayta urinish" (POST retry → 200, qayta tahlil) va "Ishni o'chirish" (tasdiq oynasi → 204, ro'yxatga qaytish).
- Sinov paytida tuzatilgan: ish xatosida foydalanuvchiga ichki matn (`HTTPConnectionPool(host='127.0.0.1', port=9)...`) chiqardi →
  `apps/cases/worker.user_error` (umumiy `GENERIC_ERROR` / `BUDGET_ERROR`, tafsilot faqat server logida); o'chirilgan ish tafsiloti
  qayta so'ralib 404 olardi → `removeQueries` (veb kabi); dev da `alertError` asl sababni Metro logiga yozadi (`__DEV__`).
  Backend qayta ishga tushgan zahoti birinchi so'rov "Server bilan aloqa uzildi" bilan tugadi (eski ulanish), takrorida ishladi — kod xatosi emas.
- **Telefonda hali sinalmagan**: kamera bilan suratga olishning o'zi, tayyor (DONE) ish hisobotini telefonda ko'rish, tarif/profilda
  amallar, ro'yxatdan o'tish. Ish xatosi matni (`CaseRun.error`) bazada o'zbekcha saqlanadi — boshqa tillarga tarjima qilinmaydi.
  Telefonni ulab: `tools/adb_reverse.ps1`, APK o'rnatish, `npx expo start`.
- `tools/adb_reverse.ps1` — 8010/8011/8081 portlarini ulash.
- **Telefonga o'rnatilgan (2026-10-30)**: release APK (Metro siz, JS ichida; o'z kaliti `CN=MEZON AI` —
  `apps/mobile/credentials/`, git ga kirmaydi, **zaxiralash kerak**), USB orqali LLM siz serverga (`http://localhost:8011`).
  PC tomoni: `mezon_backend\tools\phone.ps1 start|status|stop` — `serve.py --nollm --http` + USB kuzatuvchi (telefon har
  ulanganda `adb reverse` ni o'zi tiklaydi; uzib-ulab sinaldi). Foydalanuvchi qarori: faqat USB, LLM siz backend.
  Telefonda sinaldi: kirish, chat SSE (manbalar + LLM siz xato), Ishlar, server o'chiq holatda ochish → "Server bilan aloqa
  yoʻq" ekrani (sessiya saqlanadi) → server yoqilib "Qayta urinish" → qayta kirishsiz davom.
  Tuzatilgan: server javob bermasa ilova sessiyani o'chirib yuborardi (`refreshSession` endi faqat 4xx da tozalaydi);
  `OllamaProvider.stream_text` `model` parametrini qabul qilmasdi (LLM siz serverda chat TypeError) — `rag/tests/test_providers.py`.
  Kompyuter qayta yonganda `phone.ps1 start` ni qo'lda ishga tushirish kerak (avtomatik — Task Scheduler, ruxsat bilan).

## 4d. Production tarmoq holati (17-bosqich, batafsil: `mezon_backend/README.md` → "Production tarmoq", "Zaxira nusxa")
- Foydalanuvchi qarorlari (2026-10-30): domen hali yo'q (hammasi tayyorlansin); quick tunnel bilan sinov — ha (bajarildi,
  yopildi); `waitress` + `whitenoise` o'rnatish — ha; tungi vazifalar — faqat tayyorlansin (yaratilmagan).
- Arxitektura: Cloudflare Tunnel → `tools/serve.py` (waitress, 127.0.0.1:8010, DEBUG=0) → Django. Veb SPA `/`, admin SPA
  `/panel/` (Vite `base` `/static/web/`, `/static/panel/`; `config/spa.py`), API `/api/v1/`. Eski Django sahifalari
  production da o'chiq (`MEZON_LEGACY_UI`), dev da o'zgarishsiz.
- Xavfsizlik: kuchsiz `DJANGO_SECRET_KEY` bilan ishga tushmaydi; HSTS (1 kun), HTTP→HTTPS, Secure cookie, COOP;
  `check --deploy` toza. Mijoz IP — `CF-Connecting-IP` (faqat 127.0.0.1 dan kelganda) — lockout/throttle/anti-fraud tunnel
  orqasida to'g'ri ishlaydi. Topilgan va tuzatilgan: waitress `X-Forwarded-Proto` ni o'chirardi → `trusted_proxy`;
  Django prefiksli static qidiruvi Windows da `/` bilan ishlamaydi → `index.html` STATIC_ROOT dan o'qiladi.
- Sinaldi (2026-10-30, `*.trycloudflare.com`, LLM siz): HTTPS, HTTP→HTTPS, login + HttpOnly/Secure cookie + refresh, SSE chat,
  veb va `/panel/` sahifalari (assetlar gzip, `immutable`), haqiqiy IP yozilishi; waitress SSE ni buferlamasligi o'lchandi;
  `prod.ps1 start/status/stop` (~20 s). Telefon ulanmagan edi — **mobil ilova HTTPS orqali sinalmagan**.
- Zaxira (`apps/ops`): AES-GCM bilan shifrlangan `.mzb` (kalit `MEZON_DATA_KEYS` dan; kalitlar arxivda yo'q), verify/restore;
  birinchi zaxira yaratildi: `E:\mezon\backups\mezon_20261030_135557.mzb` (122 MB). Qdrant snapshot tiklanishi sinov
  kolleksiyasida tekshirildi va o'chirildi. Disk: E: ~20 GB, D: ~18 GB bo'sh — `MEZON_BACKUP_KEEP=7`.
- Ma'lum: veb va admin bitta refresh cookie ni bo'lishadi (biridan chiqish — ikkalasidan); ikki tab bir vaqtda refresh
  qilsa, rotatsiya tufayli bittasi qayta kirishni so'rashi mumkin (oldindan bor muammo; kerak bo'lsa — refresh grace period).
  CSP (Content-Security-Policy) hali yo'q.

## 4e. Dizayn almashtirildi — "Mezon Klassik" (2026-10-30)
- Foydalanuvchiga eski qorong'i "missiya boshqaruv pulti" uslubi (sayt, admin, ilova) umuman yoqmadi. Sabablari (uning
  javobi): qorong'i rang, juda texnik (kod shrifti, inglizcha/kod yorliqlari), juda zich, tuzilma/qulaylik. Uch
  yo'nalishdan **A. Klassik yuridik** tanlandi, **yorug' + qorong'i rejim** bilan. Tizim: `designs/mezon_klassik/DESIGN.md`.
- Veb/admin: `web-kit/theme.css` — CSS o'zgaruvchilar (`--mz-*`) + `@theme inline`; semantik klasslar (`bg-canvas`,
  `bg-surface`, `bg-subtle`, `text-ink`, `text-muted`, `primary`, `gold`…); eski `obsidian/slate-1/slate-2/blue` nomlari
  hamma joyda almashtirildi. `lib/theme.tsx` (`ThemeProvider`, `ThemeSwitch`, `useTheme`), index.html da birinchi chizishdan
  oldingi skript. Lora + Inter (`@fontsource-variable`), Plus Jakarta / JetBrains Mono olib tashlandi. `font-mono` →
  `tabular-nums`, KATTA HARFLI yorliqlar yo'q, 12px dan kichik matn yo'q, `PageHeader`, kirish sahifasi — ikki ustun.
  Foydalanuvchidan yashirildi: chatdagi token/narx/vaqt, hisobotdagi niqoblash soni va narx, model nomi, shablon versiyasi.
  Admin: "AI xarajatlari", "Shubhali faollik"; bosh sahifada tarif kodi o'rniga nomi (`plan__name`, API test qo'shildi).
- Mobil: `lib/theme.ts` (ikki palitra, o'zgaruvchan `colors`), `lib/themeContext.tsx` (secure-store, tizim sozlamasi,
  rejim almashganda navigator qayta chiziladi), `ui.tsx` uslublari `rebuildStyles()` bilan; `@expo-google-fonts/lora|inter`
  (`useFonts`, splash shriftlar yuklanguncha). Profilda "Koʻrinish" (Yorugʻ/Qorongʻi/Tizim). Yangi APK yig'ildi va o'rnatildi.
- Brauzerda tekshirilgan: kirish, chat (javob + manbalar), ishlar, ish hisoboti, tarif, hujjatlar, qonunlar, profil,
  admin bosh sahifa/foydalanuvchilar/tariflar; yorug' va qorong'i. Ma'lum: dev da veb (:5173) va admin (:5174) bitta
  `localhost` cookie ni bo'lishadi — StrictMode dagi ikki marta refresh rotatsiya tufayli bitta tabni chiqarib yuborishi mumkin.
- Telefonda tekshirildi (2026-10-30, release APK): kirish, chat, Ishlar, ish hisoboti, Tarif, Profil, rejim almashtirish (yorugʻ/qorongʻi),
  uz/ru/en tillari; APK ustidan qayta oʻrnatish va qayta ishga tushirishda sessiya saqlanadi. Telefonda tuzatilgan: pastki menyu Android
  imo-ishora chizigʻiga tegardi (safe-area), sarlavhali ekranda tepada ortiqcha boʻshliq (`Screen header`), "narx belgilanmagan" narx kabi katta edi.
  Bir marta (yangilashdan keyin) sessiya yoʻqolgani kuzatildi — qayta takrorlanmadi, sababi aniqlanmadi.

## 4f. Kod-review tuzatishlari (2026-11-05)
To'liq kod-review (xavfsizlik, RAG/ish tahlili, frontend) o'tkazildi; birinchi navbatdagi xatolar tuzatildi. Backend 262 test, frontend 15 test (hammasi o'tdi).
- **Kesh**: kirish urinishlari va throttle endi alohida `security` keshida (`CACHES["security"]`, LocMem, `MAX_ENTRIES` katta) —
  LLM natijalari keshi (`default`, MAX_ENTRIES 50 000) ularni tasodifiy "cull" bilan o'chirmaydi. Production da bir nechta jarayon bo'lsa — Redis.
- **Worker** (`apps/cases/worker.py`): `_loop` xatoda o'lmaydi; ish atomik `QUEUED→RUNNING` bilan egallanadi (o'chirilgan/takror ish o'tkazib yuboriladi);
  hisobotni yozish xatosi ham ishni FAILED qiladi; `_active` to'plami takror navbatga qo'yishni to'sadi; `recover_interrupted` shu jarayondagi
  ishlarga tegmaydi; `retry_case` atomik; `quota.refund_case/record_cost` `F()` bilan.
- **lex.uz sinxronizatsiyasi**: bo'sh/yarmidan kam moddali sahifa rad etiladi (`sync.check_page_sane`, `SuspiciousPage`), kesh nusxasi tiklanadi, kesh atomik yoziladi;
  `reindex_documents` avval yozadi, keyin eskirgan bo'laklarni o'chiradi (embedding xatosida hujjat indeksdan yo'qolmaydi).
- **Frontend**: veb refresh — bitta promise + Web Locks, faqat 4xx da sessiya tugaydi (tarmoq/5xx — xato); mobil `refreshSession` — single-flight;
  chat oqimi `done` siz tugasa `incomplete` → "javob to'liq emas" xabari; buzuq SSE `data:` oqimni uzmaydi; veb chat sahifasi chiqilganda oqimni to'xtatadi.
- i18n: mobilning 19 ta tarjimasiz matni ru/en/kaa ga qo'shildi (kaa — mashina tarjimasi, ona tili egasi tekshirsin).
- **Ikkinchi to'plam (2026-11-05)**:
  - `ask` (20/min) va `laws_search` (30/min) throttle; qidiruv navbati 60 s dan keyin 503 `search_busy` (`rag/locks.search_slot`);
    GPU qulfi endi faqat qidiruv/reranker qismida — LLM rejalash va manba tanlovi qulfdan tashqarida (`search_aspects(slot=…)`).
  - Chat savol kvotasi xatoda (qidiruv/LLM/byudjet) qaytariladi (`quota.refund_chat`); byudjet xatosi foydalanuvchiga `$` va sozlama nomisiz.
  - Gemini kaliti URL dan `x-goog-api-key` sarlavhasiga; hisobotdagi faktlar/huquqiy baho xatolari umumiy matn (tafsilot logda).
  - PII: bir familiyali turli shaxslar ism bilan ajratiladi (Karimov Jasur / Karimova Malika); yolg'iz "Karimov" — `<SHAXS_1>/<SHAXS_2>`.
  - `verify_answer`: iqtibos ko'rsatilgan `[M#]` manbada bo'lishi shart (`iqtibos_boshqa_manbada`); "6-modda" "16-modda" ichidan topilmaydi.
  - CSP (SPA sahifalari, `MEZON_CSP`, production da `enforce`): yangi build (`staticfiles/` qayta yig'ildi) bilan `serve.py --nollm --http`
    da veb kirish sahifasi va `/panel/` brauzerda CSP buzilishisiz ochildi (inline tema skripti xesh bilan; xesh CRLF→LF normallashtiriladi).
    **Kirgandan keyingi sahifalar (PDF ko'rgich/pdf.js worker, chat SSE) CSP ostida brauzerda sinalmagan** — nosozlik chiqsa `MEZON_CSP=report`;
    Django `/admin/` production da yopiq (`DJANGO_ADMIN_PATH` berilsa ochiladi); router `errorElement` (`web-kit RouteError`);
    mobil `userInterfaceStyle: automatic` (**yangi APK yig'ilmagan**).
- **Hali qilinmagan**: SMS OTP (Eskiz/PlayMobile hisobi kerak), IPv6 /64 throttle, qonun tahriri sanasini tanlash (`legal.finding_date`),
  PII regexlari (manzil, tug'ilgan sana, STIR, hisob raqami…) va prompt-injection qoidasi, global LLM byudjetini foydalanuvchi/kun bo'yicha ajratish,
  superadmin himoyasi, audit to'liqligi, `lawyer` roli va tasdiq vaqti, `activate_subscription` (muddatsiz tarif), mobil chat unmount abort, accessibility.
  **Git hali yo'q.**

## 4g. Gemini va chat tuzatishlari (2026-11-05…07)
- **LLM = faqat Gemini** (`.env`: `LLM_PROVIDER=gemini`, model `gemini-3.1-flash-lite` — `*-latest` nomlari va 3.5/3.8 modellari 503 "high demand" berdi).
  Offline/Ollama ishlatilmaydi (foydalanuvchi qarori). Narx `ANTHROPIC_PRICES` jadvalida **taxminiy** (0.25/1.50) — Google narxnomasi bilan solishtiring.
- Dev: `.claude/launch.json` → `qdrant` + `mezon-api-gemini` (`tools/dev_llm.py`, :8011, haqiqiy Gemini) + `mezon-admin-nollm` (:5174) + `mezon-mobile-web` (:8081).
  `mezon-api-nollm` — faqat pulsiz UI sinovi uchun. `.env` da ikkita LLM bloki bor (Claude va Gemini) — Gemini bloki oxirida va ustun; tozalash kerak.
- **Tayyor javob yo'q**: salomlashuv ro'yxati (`is_simple_greeting`) o'chirildi. Savolni yo'nalishlarga ajratuvchi LLM bosqichi `legal` belgisini ham qaytaradi:
  huquqiy bo'lmasa — lex.uz da qidirilmaydi, javobni AI o'zi yozadi (`views._smalltalk_events`), kvota qaytariladi. **Haqiqiy savollarda uzoq muddat sinalmagan.**
- **Oqim uzilishi**: Gemini oqim o'rtasida xato (503) qaytarsa javob jim kesilardi. Endi `GeminiProvider.stream_text` `LLMInterrupted` ko'taradi,
  `views._llm_stream` bir marta qayta urinadi (mijozga `reset` hodisasi — matn tozalanadi), aks holda aniq xato + kvota qaytariladi.
- Mobil veb: brauzer fokus ramkasi (`noOutline`, `ui.tsx`). Foydalanuvchi `0e8616f6-…` Enterprise (yillik) tarifida (dev baza).
- Hali git yo'q; oxirgi zaxira 2026-10-30; lex.uz oxirgi sinxronizatsiya 2026-10-26 (tungi vazifalar yaratilmagan).

## 4h. Telefon formati va progressiv registratsiya himoyasi (2026-11-12)
- Web login/register telefoni: `+998` alohida prefiks, foydalanuvchi qismi `90 123 45 67`; API ga
  `+998901234567` yuboriladi (`web-kit PhoneInput`, formatter va komponent testlari).
- Registratsiyaning eski `10/hour` throttli olib tashlandi. Yangi IP burst himoyasi: 60 soniyada 5 ta urinish;
  oshsa shu kalendar oyida 3, 5, 10, 20, 40, 60 daqiqa, 3/12/24 soat progressiv tanaffus. Yangi oyda yana
  3 daqiqadan boshlanadi. Sozlamalar: `API_REGISTER_BURST`, `API_REGISTER_WINDOW_SECONDS`, `API_REGISTER_COOLDOWNS`.
- Tekshiruv: backend 283/283, frontend 20/20, barcha TypeScript paketlari, i18n 496/496 × 5 til; serverlar restart qilindi.

## 4i. Interfeys tilidagi validatsiya va alert xatolari (2026-11-12)
- Ro'yxatdan o'tishdagi Django parol validatorlari endi inglizcha xabarni to'g'ridan-to'g'ri bermaydi:
  `password_too_short`, `password_too_common`, `password_entirely_numeric`, `password_too_similar` kodlari
  tanlangan interfeys tiliga tarjima qilinadi (`apps/i18n/errors.py`).
- Shu markaziy qatlam barcha DRF maydon validatsiyalariga ham qo'llanadi. Noto'g'ri JSON, token/sessiya, ruxsat,
  topilmadi, HTTP usuli, media turi va javob formati xatolari ham profil/cookie/`Accept-Language` tilida qaytadi.
- Dinamik hujjat formasi va shablon sxemasi xatolari tarjimaga o'tkazildi. Fon tahlili va server restartidan qolgan
  `CaseRun.error` endi ish egasining profil tilida saqlanadi; ichki texnik tafsilot UI ga chiqmaydi.
- Kataloglar: 539/539 × 5 til (`uz-latn`, `uz-cyrl`, `ru`, `kaa`, `en`). Tekshiruv: backend 287/287,
  frontend 20/20, barcha TypeScript paketlari typecheck dan o'tdi.

## 4j. Admin telefon formati va parolni bosib ko'rish (2026-11-12)
- Admin login telefoni ham umumiy `web-kit PhoneInput` ga o'tdi: ekranda `+998 | 90 123 45 67`, API ga
  `+998901234567` yuboriladi.
- Web, admin, mobil login/register va eski Django auth sahifalaridagi barcha parol inputlarida ko'z tugmasi bor.
  Parol toggle bo'lib ochiq qolmaydi: mouse/touch/Space/Enter bosib turilganda ko'rinadi, qo'yib yuborilganda,
  pointer chiqib ketganda yoki fokus yo'qolganda yana yashiriladi.
- `PasswordInput` uchun pointer va klaviatura regressiya testlari qo'shildi; ko'z tugmasining accessibility matni
  5 tilga tarjima qilindi. Kataloglar: 540/540 × 5 til.

## 4k. To'liq tahlil (2026-11-13) — haqiqiy holat va topilmalar
**Tekshirildi**: backend `manage.py test apps` — 288/288 OK (184 s); frontend `typecheck` (6 paket) toza, vitest 22/22 (api-client 11, admin 1,
web 10). Serverlar (Qdrant, Django) o'chiq edi — jonli qidiruv/chat bu tahlilda sinalmagan. Dev baza: 6 akkaunt (4 LAWYER, 1 MODERATOR,
1 SUPERADMIN), 1 ta DONE ish, 5 shablon, 57 924 hujjat / 37 410 modda (bazada), obunalar: 1 Pro + 1 Enterprise, migratsiya `accounts.0003` oxirgisi.
**Yangi (4h–4j dan tashqari)**: veb ommaviy bosh sahifa (`LandingPage.tsx`, `/` — kirmagan uchun; kirgan `/chat` ga) va `NotFoundPage`.

**Topilgan nosozliklar (ustuvorlik bo'yicha; hali tuzatilmagan, faqat hujjatlar yangilandi):**
1. **TUZATILDI (2026-11-13)** — `LandingPage.tsx` namunasi endi MK 161 (ish beruvchi tashabbusi bilan bekor qilish) va MK 560 (sudga murojaat
   muddatlari: ishga tiklash — buyruq nusxasi topshirilgandan 3 oy) ga tayanadi; ru/en/kaa tarjimalari qo'shildi (kaa — mashina tarjimasi),
   kataloglar 540/540, brauzerda ko'rildi. Quyidagi tavsif — nima noto'g'ri bo'lgani: **Bosh sahifadagi namunada noto'g'ri modda raqamlari**
   (`apps/web/src/pages/LandingPage.tsx`, `PreviewCard`): "МК 86-modda — Ish beruvchi
   tashabbusi bilan bekor qilish" va "МК 100-modda — Mehnat nizolarini hal etish". Bazada (Mehnat kodeksi, `abs_id=6257288`, amaldagi tahrir):
   86-modda = *Jamoa kelishuvlari shartlarining haqiqiy emasligi*; 100-modda = *…oʻrtacha oylik ish haqini ishga joylashtirish davrida saqlab
   qolish kafolatlari*; ish beruvchi tashabbusi bilan bekor qilish = **161-modda**. "1 oy ichida sudga" muddati ham tekshirilmagan.
   Advokatlar uchun mahsulotning birinchi sahifasida soxta iqtibos — jiddiy; matn 5 tilli katalogda ham bor (`i18n_sync` kerak).
2. **Testlar haqiqiy `data/llm_usage.jsonl` ga yozadi**: `rag/tests/test_gemini_provider.py` `DATA_DIR` ni almashtirmaydi — har test yurishida
   `gemini-flash-lite-latest` yozuvlari qo'shiladi (95 ta, ≈$0.005). Console/Google hisobi bilan solishtirish uchun jurnal ifloslanadi.
3. **Gemini xarajati kam hisoblanishi mumkin** (kodni o'qib topildi, jonli tekshirilmagan): `llm.py` faqat `promptTokenCount` va
   `candidatesTokenCount` ni sanaydi; Gemini API javobida "thinking" tokenlari alohida `thoughtsTokenCount` da kelishi mumkin — shunda
   xarajat va `LLM_BUDGET_USD` real sarfdan past chiqadi. `usageMetadata` ni bitta haqiqiy javobda tekshiring. `gemini-3.1-flash-lite` narxi taxminiy.
4. **`LLM_BUDGET_USD=0.30` — jarayon umri uchun chegara** (`GeminiProvider.budget_usd`): production serverda shu summa tugagach barcha chat/tahlil
   "AI xizmati hozircha band" bo'ladi (qayta ishga tushirguncha). Foydalanuvchi/kun bo'yicha byudjet kerak (4f "qilinmagan" ro'yxatida bor).
5. **Huquqiy bo'lmagan savollar kvotasiz**: `_smalltalk_events` kvotani qaytaradi — Bepul akkaunt (3 savol) cheksiz AI suhbat qila oladi
   (faqat `ask` 20/min throttle). Xarajat `record_cost` ga yoziladi, lekin chegara yo'q. (LLM rejalovchisi xato bersa `plan_aspects`
   huquqiy `fallback` qaytaradi — suhbat yo'liga tushmaydi; bu to'g'ri.)
6. **Tungi vazifalar yo'q** (`schtasks` ro'yxatida MEZON yo'q): lex.uz sinxronizatsiyasi oxirgi 2026-10-26, zaxira 2026-10-30 (14 kun oldin),
   `token_blacklist_outstandingtoken` 111 ta va o'sadi (`flushexpiredtokens` jadvalda yo'q). E: diskda 16 GB (88%) bo'sh.
7. **Release imzo kaliti** `frontend/apps/mobile/credentials/release.keystore` — faqat shu diskda, zaxira arxiviga kirmaydi (yo'qolsa ilovani
   yangilab bo'lmaydi).
8. Eskirgan hujjatlar: `.env.example` (`LLM_PROVIDER: ollama | anthropic`, `GEMINI_API_KEY` yo'q, `GEMINI_*` sozlamalari yo'q); `mezon_backend/README.md`
   da "Gemini" umuman tilga olinmagan va 107-qatorda buzilgan yo'l (`mezon_backend<TAB>ools` — `\t` tab bo'lib ketgan); `LLM_MODEL_*` `.env` da
   ikki blok (oxirgisi amal qiladi).
9. Kichik: `ProgressiveRegisterThrottle` get/set atomik emas (parallel so'rovlar burstdan o'tishi mumkin); throttle/lockout `LocMemCache` — server
   qayta ishga tushganda tozalanadi; `*` marshruti (`NotFoundPage`) faqat kirganlar uchun, kirmagan foydalanuvchi noma'lum URL da `/login` ga
   tushadi; `frontend/apps/mobile/.git` — alohida ichki repo (Expo shabloni), ildiz repo bilan to'qnashadi (`git init` oldidan hal qiling).
**Git hali yo'q** — `git init` ni yana taklif qiling (mobil ichki `.git` ni avval olib tashlang yoki submodule qiling).

## 4l. Koʻp formatli hujjatlar, 'Yagona Hujjat' yigʻish va Gemini 2.0 Flash Vision OCR (2026-11-17)
- **DOCX rasmlari**: Word hujjatlari ichidagi barcha ichki rasmlar (`_extract_docx_images`) ajratilib, alohida varaq sifatida umumiy `master.pdf` va ish korpusiga qoʻshiladi (ogohlantirish: `X ta ichki rasm ajratib olindi...`).
- **Gemini 2.0 Flash Vision OCR**: `apps/rag/llm.py` ga `transcribe_image` metodi qoʻshildi (multimodal `inlineData` JPEG base64). Qatʼiy deterministik yuridik tizimli prompt (`temperature=0.0`) orqali qoʻlyozma matnlar `[QOʻLYOZMA: ...]`, muhrlar `[MUHR: ...]`, jadvallar Markdown sifatida olinadi. Oʻzbek kirillcha `ў, қ, ғ, ҳ` va lotincha `oʻ, gʻ` 100% asliday saqlanadi. Xarajat: 1 sahifa rasm $\approx$ $0.00023 (~3 soʻm).
- **Smart gibrid OCR**: `apps/cases/ocr.py` va `pdf_text.py` yangilandi (`ocr_image_smart`). `CASE_VISION_OCR=1` boʻlsa Vision OCR ishlaydi, tarmoq uzilishi yoki xatoda lokal RapidOCR ga zaxira sifatida avtomatik oʻtadi.
- **Manifest va hisobot**: `Page` va `report` ga `has_handwriting`, `stamps`, `ocr_cost_usd` va `manifest` qoʻshildi. Frontend `Report.tsx` da qoʻlyozma mavjudligi nishoni (`Badge`) chiqadi.
- **Holat**: backend 291/291 test OK (160 s), frontend 22/22 vitest OK, 6 paket TypeScript toza, 541/541 x 5 til toʻliq sinxron. Dev serverlar (Qdrant :6333, Django :8010, Web :5173, Admin :5174) ishlab turibdi.

## 4m. Yurxizmat.uz to'liq integratsiyasi va Hujjat shablonlari bazasi (2026-11-18)
- **Tahlil va parser**: `yurxizmat.uz` katalogi (49 sahifa, 966 hujjat) skanerlandi va 964 ta hujjatning barcha 3 tildagi (`oz`, `uz`, `ru`) HTML formasi, input maydonlari va andozalari `mezon_backend/data/yurxizmat/raw/` ga yuklandi.
- **Metismenu iyerarxiyasi**: `https://yurxizmat.uz/oz/categories/` dagi `ul.metismenu.sidebarMenu.list-unstyled` menyusiga 100% mos 6 ta asosiy toifa va 31 ta bo'lim ajratildi:
  1. *Shartnomalar* (`contracts` — 8 bo'lim: yuridik, ko'chmas mulk, avtotransport, xizmat ko'rsatish, boshqa, kelishuvlar, bitimlar, ishonchnomalar)
  2. *Arizalar* (`statements` — 4 bo'lim: yuridik, jismoniy, bolalarga oid, iltimosnomalar)
  3. *Shaxsiy tarkibga oid hujjatlar* (`personal-documents` — 6 bo'lim: arizalar, bildirgilar, buyruqlar, dalolatnomalar, kelishuvlar va shartnomalar, boshqa)
  4. *Notarial tasdiqlanadigan hujjatlar* (`notarial` — 4 bo'lim: arizalar, vasiyatnomalar, ishonchnomalar, shartnomalar)
  5. *Sudga oid hujjatlar* (`court` — 5 bo'lim: da'vo arizalar, arizalar, bayonnomalar, appelyatsiya/kassatsiya, iltimosnomalar)
  6. *Korporativ hujjatlar* (`corporate-documents` — 4 bo'lim: talabnomalar, ustavlar, dalolatnomalar/bayonnomalar, boshqa)
  Barcha 966 ta hujjat `mezon_backend/data/yurxizmat/full_doc_mapping.json` da toifa va bo'limga to'liq xaritalandi.
- **Backend va Ma'lumotlar bazasi**: `apps/doc_builder/models.py` da `DocumentTemplate` modeliga `subcategory` va `subcategory_slug` qo'shildi (`0003_documenttemplate_subcategory_and_more.py`). Bazada jami **2,449 ta shablon** shakllantirildi (`uz-Latn`: 965, `uz-Cyrl`: 955, `ru`: 529). Har bir shablon uchun form input sxemasi, o'zgaruvchilar va render/docx generatori tayyor.
- **API va Frontend**:
  - `/api/v1/templates/?category=...&subcategory=...` filtrlari qo'shildi, OpenAPI schema va `@mezon/api-client` yangilandi.
  - `frontend/apps/web/src/pages/templates/TemplatesPage.tsx` sahifasida 6 ta asosiy toifa tablari, dinamik bo'limlar filtri, kartochkalarda subkategoriya nishoni (badge) va guruhlash integratsiya qilindi.
- **Keyingi qadamlar**:
  1. Qoraqalpoq (`kaa`) va Ingliz (`en`) tillariga (hamda ruschasi bo'lmagan 435 ta hujjatga) Lex.uz terminologiyasini saqlagan holda AI yordamida batch tarjima qilish.
  2. Frontendda hujjatni to'ldirish (FillForm modal) va jonli preview ko'rish oynasini yanada takomillashtirish.

## 5. Tavsiya etilgan arxitektura
```
E:\mezon\
  mezon_backend\     # Django (mavjud) — /api/v1/* JSON API, DRF
  frontend\          # YANGI: npm workspaces (yoki pnpm)
    packages\api-client\   # OpenAPI dan generatsiya qilingan TS klient + SSE yordamchisi (veb va mobil umumiy)
    packages\i18n\         # locale/*.po dan chiqarilgan JSON + i18next sozlamasi (veb, admin, mobil umumiy)
    apps\web\              # foydalanuvchi veb-sayti (Vite + React + TS)
    apps\admin\            # admin panel (Vite + React + TS)
    apps\mobile\           # Expo (React Native + TS)
```
- **Auth**: DRF + `djangorestframework-simplejwt` (access 15 daq + refresh rotatsiya) — veb va mobil bir xil. Mobil: `expo-secure-store`. Veb: access xotirada + refresh `HttpOnly` cookie (yoki dastlab localStorage — foydalanuvchiga ayting). Xodim/admin uchun alohida ruxsat sinflari (`role`, `is_staff`).
- **OpenAPI**: `drf-spectacular` → `openapi-typescript` bilan tiplar. Hozirgi `*_required` dekoratorli view lardan biznes mantiqni servis funksiyalariga ajrating (`quota`, `intake`, `worker` allaqachon ajratilgan) va API view lari ularni chaqirsin; eski HTML view lar SPA tayyor bo'lguncha qolsin.
- **CORS/CSRF**: `django-cors-headers`; `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` ni `.env` dan. Dev: Vite proxy (`/api` → `127.0.0.1:8010`) — CORS kerak emas.
- **SSE chat**: veb — `fetch` + `ReadableStream` (hozirgi `chat.html` dagi parser tayyor namuna). Expo da: `expo/fetch` (streaming qo'llab-quvvatlaydi, SDK 52+) yoki `react-native-sse`; avval kichik prototip bilan tekshiring.
- **Mobil skaner**: telefon kamerasi bilan bir nechta rasm → `files` ko'p-fayl yuklashi (`intake.py` JPG/PNG ni bitta PDF ga birlashtiradi) — `designs/tezkor_skaner_batch` shuni nazarda tutadi. Kvota: `quota.reserve_case` yuklashda ishlaydi.
- **i18n**: manba matnlar `locale/<til>/LC_MESSAGES/django.po` da (msgid — o'zbek lotin). Frontend uchun alohida katalog yaratmang: `manage.py i18n_export_json` buyrug'ini yozing (`.po` → `packages/i18n/*.json`), yangi matn qo'shganda `i18n_sync` + eksport. Til kodlari: TZ `uz-Latn|uz-Cyrl|ru|kaa|en` ↔ Django `uz-latn|uz-cyrl|ru|kaa|en` (`apps/i18n/codes.py`).
- **Tarif/kvota**: `apps/billing/quota.py` (`plan_for`, `reserve_*`, `usage_summary`); javobda 429 + xabar. Mobil/veb bu xabarni ko'rsatsin va `/billing` ga yo'naltirsin.
- **Xavfsizlik**: PII logga yozilmasin; hisobot va PDF `no-store`; tokenlar logda yo'q; yuklash hajmi `CASE_MAX_MB`; mobil ilova PDF ni keshlamasin yoki shifrlasin.

## 6. USB orqali ulanish (`adb reverse`) — hozirgi tarmoq rejasi
Telefon USB kabel bilan PC ga (USB debugging yoqilgan). PC da:
```
C:\platform-tools\adb.exe devices                       # qurilma "device" ko'rinsin
C:\platform-tools\adb.exe reverse tcp:8010 tcp:8010     # telefondagi localhost:8010 -> PC dagi Django
C:\platform-tools\adb.exe reverse tcp:8081 tcp:8081     # Metro (Expo dev) uchun
```
- Ilova API manzili: `http://localhost:8010` (telefon ichida `localhost` = PC). Django `ALLOWED_HOSTS` da `localhost` bor.
- Android 9+ da oddiy HTTP (cleartext) bloklanadi: Expo da dev uchun `expo-build-properties` → `android.usesCleartextTraffic: true` (faqat dev build; production — faqat HTTPS). Expo Go bilan emas, **dev build** (`npx expo run:android` yoki EAS dev build) bilan ishlang, chunki Expo Go cheklovlari bor.
- `adb reverse` har safar USB uzilganda/qurilma qayta ulanganda **qayta bajariladi** — skript qiling (`tools/adb_reverse.ps1`).
- iOS yo'q (Mac yo'q) — faqat Android. App Attest/DeviceCheck (TZ §8.2) keyinga.
- **Production** (keyin): `E:\cloudflared\cloudflared.exe tunnel` — named tunnel `api.<domen>` → `http://127.0.0.1:8010`, HTTPS Cloudflare da tugaydi; Django da `SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")`, `CSRF_TRUSTED_ORIGINS`, `DEBUG=0`. Domen kerak bo'ladi (hozir yo'q) — quick tunnel (`trycloudflare.com`) faqat vaqtinchalik sinov uchun.

## 7. Bosqichlar (faza 2)
Har bir bosqich: kod + test + README/HANDOFF yangilash. Bosqich boshida foydalanuvchiga 1 qatorda nima qilinishini ayting.
- ~~**13. API v1 poydevori**~~ **TAYYOR (2026-10-29)** — DRF + simplejwt + drf-spectacular + CORS; `/api/v1/auth/*` (login, register, refresh, logout, me, language), `cases` (ro'yxat, multipart yuklash, holat, hisobot, PDF stream, confirm, export, delete, retry), `chat` (SSE ni saqlab), `templates` (ro'yxat, sxema, preview/yuklab olish), `billing` (usage, plans), `search` (modda/hujjat ko'rish, ixtiyoriy), `i18n_export_json`. Testlar (eski 188 tasi buzilmasin). Tamom mezoni: `curl` bilan token olib to'liq oqim (login → yuklash → holat → hisobot) ishlaydi; OpenAPI sxema yaratiladi.
- ~~**14. Veb-sayt (`frontend/apps/web`)**~~ **TAYYOR (2026-10-29)** — kirish/ro'yxatdan o'tish, chat (SSE, manba havolalari, tekshiruv natijasi), ish yuklash/ro'yxat/hisobot (PDF ko'rgich + varaq tugmalari), yuridik tasdiq oynasi + eksport, hujjat konstruktori, tarif sahifasi, til almashtirgichi (5 til). Dizayn: `designs/`. Tamom mezoni: hozirgi Django sahifalaridagi barcha imkoniyatlar SPA da; brauzerda tekshirilgan.
- ~~**15. Admin panel (`frontend/apps/admin`) + admin API**~~ **TAYYOR (2026-10-29)** — SuperAdmin dashboard (`designs/superadmin_anti_fraud_radar`, `tariflar_va_obuna_boshqaruvi`): foydalanuvchilar, obunalar/tariflar konstruktori (`Plan` maydonlari), to'lovlar ("to'langan deb belgilash" → `quota.mark_paid`), sinxronizatsiya holati (`SyncRun`), shablon moderatsiyasi (`approved_by`), AI xarajat radari (`UsageLog.llm_cost_usd`, `CaseRun.cost_usd`), anti-fraud monitor (hozircha oddiy: bir IP da ko'p akkaunt). Ruxsat: faqat `MODERATOR`/`SUPERADMIN`.
- ~~**16. Mobil ilova (`frontend/apps/mobile`, Expo)**~~ **TAYYOR (2026-10-29), telefonda sinaldi** (4c; kamera suratining o'zi va hisobot ko'rish telefonda sinalmagan) — kirish, chat, kamera/galereya/fayl bilan ish yuklash, hisobot ko'rish, tarif. `adb reverse` oqimi (6-bo'lim), dev build. SSE ni avval prototip bilan tekshiring.
- ~~**17. Production tarmoq**~~ **TAYYOR, domen kutilmoqda (2026-10-30)** — HTTPS sozlamalari, production serveri (`tools/serve.py`, `tools/prod.ps1`), SPA tarqatish, mijoz IP, `/api/v1/health`, shifrlangan zaxira (`manage.py backup`, `tools/nightly_backup.ps1`), Postgres rejasi (README). Qoldi: domen + `cloudflared tunnel login` (egasi), `config.yml`, `schtasks` (ruxsat bilan; buyruqlar README da), mobil release build va imzo kaliti, telefonda HTTPS sinovi.

## 8. Backend qoldiqlari (faza 2 davomida, kerak bo'lsa)
- To'lov: Payme/Click webhooklari (merchant kalitlari kerak) — kirish nuqtasi `quota.mark_paid(payment)`; tarif narxlari TZ da yo'q (`Plan.price_uzs` bo'sh).
- Anti-fraud (TZ §8.2): qurilma/IP/SMS OTP — qilinmagan; SMS uchun Eskiz.uz/PlayMobile hisobi kerak.
- Haqiqiy (anonimlashtirilgan) ish bilan LLM tahlili sinalmagan — hech bir tur uchun (jinoyat uchun faqat sintetik `fixtures/cases/case_01`). Fuqarolik/iqtisodiy/ma'muriy doiralarni yurist ko'rib chiqsin.
- Qoraqalpoq (kirill) tarjimasi mashina tarjimasi — ona tili egasi tekshirsin. DOCX/PDF eksport matnlari va tahlil bosqich nomlari hali o'zbekcha.
- Savol tilida aniq havola ("УК 168 статья") va rus javobda `ARTICLE_MENTION_RE`; uz-Cyrl javob uchun "AI lotinda yozadi → translit" sxemasi.
- TZ §13 1-qaror ("tashqi AI API yo'q") amalda Claude API ishlatilyapti — TZ ni yangilash kerak. API kaliti avval chatda ko'ringan — Anthropic Console da almashtirish tavsiya etilgan.
- **Loyiha git da emas** — faza 2 boshida `git init` + birinchi commit taklif qiling (`.gitignore`: `.env`, `data/`, `.venv`; `frontend/node_modules` ham qo'shing). Frontend monorepo uchun alohida `.gitignore`.

## 9. Ma'lum cheklovlar
- Chat: qidiruv yoki LLM xatosi bilan tugagan savol ham savol kvotasini band qiladi (ish tahlilidagi kabi qaytarish yo'q) — `quota.refund_chat` kerak.
- Mobil: ruxsat matnlari (kamera/galereya) faqat o'zbekcha (`app.config.ts`); ekran rasmini taqiqlash (FLAG_SECURE,
  `expo-screen-capture`) yo'q; jest testlari yo'q (faqat tsc + expo-doctor); iOS yo'q.
- Admin: to'lov webhooklari (Payme/Click) yo'q — faqat qo'lda; anti-fraud — faqat IP qoidasi (qurilma/SMS yo'q);
  majburiy sinxronizatsiya server ichidagi fon oqimida (production da Celery/schtasks). Dev da veb va admin `localhost`
  cookie larini bo'lishadi.
- Tahlil bosqich nomlari (`stage`) hozircha faqat o'zbekcha.
- `lex_corpus` modellaridagi `DocType`/`Status` yorliqlari (`Kodeks`, `Amalda`) tarjima qilinmagan — `/laws` da ruscha
  interfeysda ham o'zbekcha ko'rinadi (`gettext_lazy` ga o'tkazish kerak).
- Veb asosiy bundle ~711 KB (gzip 212 KB); pdf.js va `/laws` alohida bo'lakda. Kerak bo'lsa yana bo'lish mumkin.
- Ishni o'chirish tasdig'i `window.confirm` (dizayndagi dialog emas).
- Fakt ajratishda LLM xatosi bloklar bo'yicha yutib yuboriladi ("0 ta fakt ajratildi") va tahlil davom etadi — LLM
  qisman ishlamasa, bo'sh faktlar bilan pullik keyingi bosqichlar chaqirilishi mumkin (13-bosqich sinovida ko'rindi; ko'rib chiqing).
- Chiqarib tashlangan moddalar Qdrant da yo'q (sanadagi qidiruv ularni topmaydi); 2023 gacha eski Konstitutsiya yo'q.
- Huquqiy baho (Haiku/Sonnet) mazmunan xato qilishi mumkin — tekshiruvchi faqat iqtibos, modda va sanani tekshiradi.
- Eski hisobotlarda "SHAXS_7" kabi tokenlar qolgan (faqat yangi tahlillarga tuzatish ta'sir qiladi).
- Ish tahlili server ichidagi bitta fon oqimida (`apps/cases/worker.py`), ketma-ket; production da Celery.
- `--noreload` rejimi: shablon/kod o'zgarsa serverni qayta ishga tushiring.
