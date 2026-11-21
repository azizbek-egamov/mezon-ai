# MEZON AI — Claude Code uchun loyiha qo'llanmasi

O'zbekiston advokatlari uchun legal AI platforma: lex.uz qonunchiligi bo'yicha iqtibosli savol-javob, jinoyat ishi
hujjatlarini tahlil qilish (OCR → faktlar → ziddiyatlar → lex.uz asoslash), shablonli hujjatlar.
**Foydalanuvchi bilan o'zbek tilida (lotin) gaplashing.** Kod izohlari va docstringlar ham o'zbekcha.

## Asosiy hujjatlar
- `TZ-v2.1.md` — texnik topshiriq (§ raqamlari kodda havola qilinadi).
- `analysis/HOLAT_TAHLILI_2026-10-26.md` — kamchiliklar tahlili va 12 bosqichli backend rejasi (**bajarilgan**).
- `designs/mezon_klassik/DESIGN.md` — **amaldagi dizayn tizimi** (2026-10-30, foydalanuvchi tanlovi "Klassik yuridik": iliq oq fon,
  Lora sarlavhalar + Inter matn, to'q ko'k + oltin, yorug'/qorong'i rejim, texnik yorliqlarsiz). Eski qorong'i
  `mezon_sovereign_precision` va `designs/*/screen.png` — **eskirgan** (faqat ekranlar tarkibi uchun ma'lumot).
- `mezon_backend/README.md` — har bir modulning batafsil tavsifi, buyruqlar, o'lchangan natijalar.
- `HANDOFF.md` — **shu yerdan boshlang**: nima qilingani, qabul qilingan qarorlar, faza 2 (React veb, React admin, Expo ilova) rejasi.

## Tuzilma (`mezon_backend/`, Django 6.1, Python 3.14)
- `apps/accounts` — telefon bilan kirish, rollar (CLIENT/LAWYER/MODERATOR/SUPERADMIN), `AUTH_USER_MODEL=accounts.User`.
- `apps/lex_corpus` — lex.uz reyestri, parser, tahrirlar tarixi (`history.py`), sinxronizatsiya (`sync.py`, `registry.py`).
- `apps/rag` — gibrid qidiruv (bge-m3 + Qdrant + reranker), iqtibosli javob, tekshiruvchilar (`answer.verify_answer`,
  `verifier.verify_legal`), LLM provayderi (`llm.py`: **Gemini** — amaldagi; Anthropic/Ollama adapterlari ham bor; xarajat chegarasi,
  oqim uzilsa `LLMInterrupted` + qayta urinish), indekslash (`indexer.py`). Huquqiy bo'lmagan savol (`legal=false`) lex.uz da
  qidirilmaydi — AI o'zi qisqa javob beradi, savol kvotasi qaytariladi (`views._smalltalk_events`).
- `apps/cases` — ish yuklash, OCR, PII niqoblash, faktlar, tahlil, huquqiy asoslash, shifrlangan saqlash, DOCX/PDF eksport.
- `apps/doc_builder` — shablonli hujjatlar (AI siz), umumiy DOCX/PDF yozuvchi `writers.py`.
- `apps/i18n` — 5 til (uz-latn, uz-cyrl, ru, kaa, en), `manage.py i18n_sync` (gettext asbobi yo'q), `translit.py`.
- `apps/billing` — tariflar, kvotalar (`quota.py`), obuna, to'lov modellari.
- `apps/api` — JSON API v1 (`/api/v1/*`, DRF + JWT + OpenAPI, Swagger `/api/v1/docs/`), admin API `/api/v1/admin/*`
  (MODERATOR/SUPERADMIN, har amal `accounts.AuditEvent` ga); mantiq `apps/cases/services.py` va boshqalarda.
- `apps/ops` — shifrlangan zaxira nusxa (`manage.py backup [verify|restore]`, kalit `MEZON_DATA_KEYS`).
- Production (17-bosqich, README "Production tarmoq"): `tools/serve.py` (waitress, DEBUG=0), `tools/prod.ps1 build|start|status|stop`,
  `config/spa.py` (veb SPA `/`, admin SPA `/panel/`), Cloudflare Tunnel `tools/cloudflared/config.example.yml`. Domen hali yo'q.
- `frontend/` — npm workspaces (`frontend/README.md`): `packages/api-client`, `packages/i18n`, `packages/web-kit` (umumiy UI/auth),
  `apps/web` (veb, :5173), `apps/admin` (admin panel, :5174), `apps/mobile` (Expo SDK 58, Android; `tools/adb_reverse.ps1`). `npm run dev:web:nollm` (LLM siz backend bilan), `npm run typecheck && npm test`.

## Ishga tushirish (PowerShell yoki Git Bash dan)
```
cd E:\mezon\mezon_backend
powershell -ExecutionPolicy Bypass -File tools\dev.ps1 start     # Qdrant :6333 + Django :8010 (fonda)
powershell -ExecutionPolicy Bypass -File tools\dev.ps1 stop      # ishlatilmasa — to'xtating (RAM ~2.4 GB)
.venv\Scripts\python manage.py test apps                          # 288 test, ~185 s, API chaqirmaydi (2026-11-13)
cd E:\mezon\frontend; npm run typecheck; npm test                 # 6 paket tsc, 22 test (web 10, admin 1, api-client 11)
```
- Qdrant server (`E:\mezon\qdrant_server`, `.env` da `QDRANT_URL`) **ishlab turishi kerak** — qidiruv, indekslash va
  sinxronizatsiya undan foydalanadi. Bir nechta jarayon bir vaqtda ishlay oladi.
- LLM siz dev server (frontend/API sinovi, pul ketmaydi): `.venv\Scripts\python tools\dev_nollm.py 8011`.
  Haqiqiy Gemini bilan dev server (PULLIK, :8011): `tools\dev_llm.py 8011` (`.claude/launch.json` → `mezon-api-gemini`).
  Production rejimini LLM siz sinash: `tools\serve.py --port 8011 --nollm` (HTTP da HTTPS ga yo'naltiradi — curl ga
  `-H "X-Forwarded-Proto: https"`). Git Bash dan `prod.ps1 start` chiqishini quvurga emas, faylga yo'naltiring (server
  handle'larni meros oladi — quvur yopilmaydi).
- Tunnel/tizim xizmati/`schtasks` yaratish va internetga ochish — **faqat foydalanuvchi ruxsati bilan**.
- Telefondagi ilova (release APK, USB, LLM siz :8011): PC da `tools\phone.ps1 start`. Mobil release build — `frontend/README.md`.
- Django `--noreload` bilan ishlaydi: **shablon (.html) yoki kod o'zgarsa — serverni qayta ishga tushiring.**
- Dev akkaunt (faqat lokal): `data/secret/dev_accounts.txt`. Parolni chatga chiqarmang. Oddiy akkaunt Bepul tarifda
  (1 ish, 3 savol): `manage.py grant_plan <telefon> PRO_MONTHLY`; xodim (`is_staff`) kvotadan ozod.

## Muhit faktlari (muhim)
- Windows 11, Git Bash. Konsol cp1251 — Python skriptlarda `sys.stdout.reconfigure(encoding="utf-8")`.
- **Bash heredoc ichida Python kodiga backslash (`\b`, `\S`, `\n`) yozmang** — buziladi (bir marta kodga backspace
  belgisi tushib qolgan). Python fayllarni faqat Edit/Write vositalari bilan o'zgartiring.
- Docker va WSL yo'q. Node 22 (nvm-windows; 20.18 ham bor), Java 17, Android SDK (`E:\android\Sdk`), `adb`
  (`C:\platform-tools`), `cloudflared` (`E:\cloudflared`) bor. Tarmoq: hozircha USB `adb reverse`. Baza — SQLite (`data/dev.sqlite3`), Postgres ga o'tish `DATABASE_URL` bilan.
- Apparat: RTX 2060S 8 GB, RAM 16 GB. Modellar GPU da (fp16, `E:/models/*-fp16`). Foydalanuvchi ba'zan o'yin
  o'ynaydi — GPU band bo'lsa qidiruv sekinlashadi, bu xato emas.
- Python fayllarda o'zbekcha matn: foydalanuvchiga ko'rinadigan satrlarda `ʻ` (oʻ, gʻ) va `ʼ` (tutuq belgisi).

## Xavfsizlik va pul
- `.env` da `GEMINI_API_KEY`, `ANTHROPIC_API_KEY` va `MEZON_DATA_KEYS` (fayllarni shifrlash kaliti) bor — **hech qachon chiqarmang**.
  `MEZON_DATA_KEYS` yo'qolsa, shifrlangan PDF/hisobotlar ochilmaydi.
- **LLM = faqat Gemini** (`LLM_PROVIDER=gemini`, `LLM_MODEL*=gemini-3.1-flash-lite`; foydalanuvchi qarori, offline/Ollama yo'q).
  `.env` da LLM bloki ikki marta (eski Claude + Gemini) — oxirgisi amal qiladi. Narx jadvali (`GEMINI_PRICES`) taxminiy.
  **API chaqiradigan amallar** (ish yuklash/tahlil, `ask`, `analyze_case`, chatga savol) **faqat foydalanuvchi aniq ruxsat bersa**
  (Claude balansi ~$0.30 edi, Gemini hisobi cheklovi noma'lum). Testlar LLM ni mock qiladi.
- UI matnlarida (bosh sahifa namunasi, tarjimalar) modda raqami yozsangiz ham — bazadan tekshiring (2026-11-13: `LandingPage`
  da MK 86/100 noto'g'ri chiqdi).
- Ish fayllari diskda faqat shifrlangan (`apps/cases/storage.py`); hisobot va eksportlar no-store.
- Tizim sozlamalarini (rejalashtirilgan vazifa va h.k.) faqat foydalanuvchi ruxsati bilan o'zgartiring.

## Ish uslubi
- Har bir o'zgarishga test yozing va `manage.py test apps` ni ishga tushiring.
- Qonun moddasini matnga yozishdan oldin bazadan tekshiring (`LegalActArticle`, `edition__is_current=True`) —
  modda raqamini o'ylab topmang.
- Yangi modul yoki buyruq — README ga qisqa bo'lim qo'shing. Yangi foydalanuvchi matni — `gettext`/`{% trans %}` + `manage.py i18n_sync`.
- Bosqich oxirida HANDOFF.md ni yangilang. Loyiha hali git da emas (faqat `frontend/apps/mobile/.git` — Expo shabloni, 1 commit) —
  `git init` ni taklif qiling. Tungi vazifalar (`schtasks`) yaratilmagan: lex.uz sinxronizatsiyasi oxirgi marta 2026-10-26,
  zaxira nusxa — 2026-10-30 (yangi zaxira: `manage.py backup`).
