# MEZON AI — frontend (npm workspaces)

```
frontend/
  packages/api-client/   # @mezon/api-client — OpenAPI tiplari (schema.d.ts), JWT yangilovchi fetch, SSE o'quvchi, hisobot tiplari
  packages/i18n/         # @mezon/i18n — i18next + backend .po dan eksport qilingan kataloglar (locales/*.json)
  apps/web/              # @mezon/web — foydalanuvchi veb-sayti (Vite 6 + React 19 + Tailwind 4 + shadcn uslubidagi komponentlar)
  packages/web-kit/      # @mezon/web-kit — veb va admin uchun umumiy: UI komponentlari, tema (theme.css), API/auth/til provayderlari
  apps/admin/            # @mezon/admin — admin panel (SuperAdmin / yurist-moderator), :5174
  apps/mobile/           # @mezon/mobile — Expo SDK 58 (React Native 0.88) Android ilova
```

Node **22.23** (nvm-windows: `nvm use 22.23.4`; eski 20.18.0 ham o'rnatilgan). Veb/admin 14–15-bosqichda Node 20 da
yozilgani uchun versiyalar mahkamlangan (Vite 6, react-router 7, react-pdf 9, TS 5.9) — Node 22 da ham ishlaydi, yangilash ixtiyoriy.
Komponentlar shadcn uslubida qo'lda yozilgan (`packages/web-kit/src/ui`, Radix: `radix-ui`).
**React bitta versiya** (root `overrides`: react/react-dom 19.3.0 — Expo SDK 58 talabi; ikki nusxa RN da "Invalid hook call" beradi).

## Buyruqlar (`E:\mezon\frontend` da)
```bash
npm install
npm run dev:web            # http://localhost:5173, /api -> 127.0.0.1:8010 (asosiy dev server, tools/dev.ps1)
npm run dev:web:nollm      # /api -> 127.0.0.1:8011 — LLM siz server (mezon_backend/tools/dev_nollm.py), PUL KETMAYDI
npm run dev:nollm -w @mezon/admin   # admin panel http://localhost:5174 (LLM siz backend bilan)
npm run build:web          # apps/web/dist
npm run typecheck && npm test
npm run api:generate       # packages/api-client/openapi.yaml -> src/schema.d.ts
```
Claude Code da: `.claude/launch.json` → `qdrant`, `mezon-api-nollm`, `mezon-web-nollm`, `mezon-admin-nollm`,
`mezon-prod-nollm` (production rejim, LLM siz, quick tunnel domenlari bilan).

**Production build** (17-bosqich): Django tarqatadi — `mezon_backend/tools/prod.ps1 build` (ikkala build + collectstatic).
Vite `base` faqat build da: veb `/static/web/`, admin `/static/panel/`; admin router production da `basename="/panel"`.
Sahifa yo'llari: veb `/…`, admin `/panel/…`, API shu domenning `/api/v1/` i (dev dagidek nisbiy, CORS siz).

**Diqqat (pul):** `dev:web` (8010) da ish yuklash va chatga savol Claude API ni chaqiradi. UI ni sinashda `dev:web:nollm` ishlating.

## API klient (`@mezon/api-client`)
- `createApi({ origin, auth, headers })`: `client` (openapi-fetch, to'liq tiplangan: `client.GET("/api/v1/cases/")`),
  `raw(path)` (multipart, fayl, SSE; yo'l `/api/v1` siz), `download(path)` → `{blob, filename}`.
- 401 → bitta umumiy `refreshAccessToken()` (parallel so'rovlar uchun bir marta) va so'rov takrorlanadi.
- Xato — `ApiError {status, code, fields}`; `isQuota` (429 `quota_*`) → tariflar sahifasiga yo'naltirish.
- `ask(api, body, handlers)` — SSE chat (`aspects`, `sources`, `delta`, `verification`, `done`, `error`).
- Backend sxema o'zgarsa: `manage.py spectacular --validate --fail-on-warn --file ../frontend/packages/api-client/openapi.yaml`
  → `npm run api:generate`.

## Veb auth
Access token faqat xotirada; refresh — HttpOnly cookie (`mezon_refresh`, yo'l `/api/v1/auth/`). Sahifa ochilganda
`/auth/refresh` (cookie) bilan sessiya tiklanadi. Login/register `cookie: true` yuboradi.
Telefon maydoni `+998` prefiksini alohida ko'rsatadi, foydalanuvchi `90 123 45 67` qismini kiritadi; API ga
normallashgan `+998901234567` qiymat yuboriladi (`web-kit PhoneInput`; admin login ham shu komponentda).
Barcha web/admin parol maydonlari `PasswordInput`, mobil maydonlar `PasswordField` dan foydalanadi: ko'z tugmasi
bosib turilgandagina parol ko'rinadi, qo'yib yuborilganda darhol yashiriladi (mouse, touch va klaviatura).

## i18n
Matn kaliti — o'zbek lotin matnning o'zi: `t("Fayl tanlang")`, `t("{{n}} varaq", { n })`. Yangi matn qo'shish:
1. komponentda `t("…")` (literal satr; dinamik kalit ajratilmaydi — server kalitlari uchun `switch` bilan literal `t()` yozing);
2. `cd ../mezon_backend && .venv/Scripts/python manage.py i18n_sync` — frontend `*.ts(x)` ham skanerlanadi (`{{n}}` → `%(n)s`);
3. `locale/{ru,kaa,en}/LC_MESSAGES/django.po` da tarjima (uz-Cyrl avtomatik);
4. `manage.py i18n_export_json` → `packages/i18n/locales/*.json`. Backend testi barcha tillar to'liqligini tekshiradi.
Til tanlash: profil tili > shu brauzerda tanlangan (`localStorage mezon.lang`) > brauzer tili; tanlov `POST /auth/language` ga yoziladi,
server xabarlari `Accept-Language` bilan ham shu tilda keladi.

## Veb sahifalari (`apps/web/src/pages`)
| Yo'l | Sahifa | Dizayn |
|---|---|---|
| `/login`, `/register` | telefon + parol, rol (advokat/fuqaro), rozilik | autentifikatsiya_va_anti_fraud_flow |
| `/` | savol-javob: SSE, manbalar yo'nalish bo'yicha, [M#] havolalar, tekshiruv natijasi, javob tili/sana/chuqurlik, to'xtatish | — |
| `/cases` | ko'p faylli yuklash (drag & drop), ish turi, zero-retention, ro'yxat (holat 3 s da yangilanadi) | advokat_ishchi_stoli |
| `/cases/:id` | PDF ko'rgich (pdf.js, token bilan, keshsiz) + hisobot (4 tab, varaq tugmalari → PDF), retry, o'chirish; mobilda tablar | advokat_ishchi_stoli |
| — | yuridik tasdiq oynasi (TZ §12): ko'rsatkichlar, tasdiqlanmaganlar, moddalar, 4 bandli tekshiruv, format → tasdiq + yuklab olish | human_in_the_loop_yuridik_tasdiqlash |
| `/templates`, `/templates/:id` | shablonlar (qidiruv, turlar), sxemadan forma, qog'oz ko'rinishi, DOCX/PDF | hujjat_konstruktori |
| `/laws` | qonunlar bazasi: hujjat → modda (lotin/kirill/rus), ma'no bo'yicha qidiruv (LLM siz) | — |
| `/billing` | joriy tarif, sarf, tariflar | tariflar_va_obuna_boshqaruvi |
| `/profile` | F.I.Sh., guvohnoma, interfeys tili, chiqish | — |

Dizayn tokenlari: `packages/web-kit/src/theme.css` (`designs/mezon_klassik/DESIGN.md`; yorug'/qorong'i — `<html data-theme>`, `lib/theme.tsx`, `ThemeSwitch`). Semantik ranglar: `canvas`, `surface`, `subtle`, `line`, `ink`, `muted`, `primary`, `gold` (faqat qonun havolalari), `green/red/amber`. Shriftlar: Lora (sarlavha), Inter (matn).

## Umumiy paket (`@mezon/web-kit`)
`import { Button, Card, useAuth, notifyError, … } from "@mezon/web-kit"` — UI (`src/ui`), `Logo`, `LanguageSelect`,
`api` (HttpOnly refresh cookie), `AuthProvider`/`useAuth`, `LanguageProvider`/`useLanguage`, `notifyError`, `fieldErrors`,
`safeNext`, formatlash. Ilova CSS i: `@import "tailwindcss"; @import "@mezon/web-kit/theme.css"; @source "../../../packages/web-kit/src";`
(oxirgisi shart — aks holda paketdagi Tailwind klasslari yig'ilmaydi).
Dev da veb (5173) va admin (5174) bitta `localhost` cookie larini bo'lishadi (portlar cookie ni ajratmaydi) — bir brauzerda
ikkalasiga turli akkaunt bilan kirsangiz, oxirgisi qoladi. Production da subdomenlar alohida.

## Admin panel (`apps/admin`, 15-bosqich)
Kirish — oddiy akkaunt (`/auth/login`), so'ng `/api/v1/admin/me`: MODERATOR — faqat shablon moderatsiyasi va sinxronizatsiya
jurnali; SUPERADMIN (yoki Django superuser) — hammasi. Boshqalar — "ruxsat yo'q" ekrani.

| Yo'l | Sahifa |
|---|---|
| `/` | Boshqaruv paneli (designs/superadmin_anti_fraud_radar): foydalanuvchilar, faollik, AI xarajati (bugun/oy, 30 kunlik grafik), ishlar, shubhali IP, sinxronizatsiya, obunalar, so'nggi amallar |
| `/users`, `/users/:id` | qidiruv (telefon/F.I.Sh./guvohnoma), rol/shubhali/IP filtri; profil: rol, faollik, fraud belgisi, obuna berish/bekor qilish, sarf, ishlar metama'lumoti (nomsiz), jurnal |
| `/plans` | tarif konstruktori (narx, muddat, barcha limitlar, belgi, navbat, faollik), yangi tarif |
| `/payments` | holat bo'yicha, qo'lda to'lov (naqd/bank), "To'landi" → obuna, bekor qilish |
| `/costs` | AI xarajat radari: 7/30/90 kun, eng ko'p sarflaganlar, eng qimmat ishlar |
| `/antifraud` | bitta IP dagi akkauntlar guruhi, belgilash/bloklash |
| `/templates`, `/templates/:id` | shablon yaratish/tahrirlash (JSON sxema, matn), validatsiya, sinov ko'rinishi, tasdiqlash va e'lon |
| `/sync` | lex.uz sinxronizatsiyasi jurnali (log), majburiy ishga tushirish (superadmin) |
| `/audit` | amallar jurnali |

Grafik (`components/CostChart.tsx`) — dataviz qoidalari: bitta seriya, ko'k (qorong'i fonda kontrast tekshirilgan), hover tooltip, sr-only jadval.
Dev akkauntlar: `mezon_backend/data/secret/dev_accounts.txt` (LAWYER, SUPERADMIN, MODERATOR).

## Mobil ilova (`apps/mobile`, 16-bosqich) — Expo SDK 58, Android
Ekranlar (Expo Router, `src/app`): `login`, `register`, tablar — `index` (savol-javob, SSE), `cases` (tezkor skaner: kamera
ketma-ket, galereya, fayllar → bitta ish; ishlar ro'yxati), `billing`, `profile` (til, chiqish); `case/[id]` (holat, retry,
o'chirish, hisobot). Dizayn: `designs/tezkor_skaner_batch`, `advokat_ishchi_stoli`, `tariflar_va_obuna_boshqaruvi`.
- **Token**: refresh — `expo-secure-store` (Android Keystore), javob tanasida (cookie emas); access — xotirada (`src/lib/api.ts`).
- **API manzili**: `.env` → `EXPO_PUBLIC_API_URL=http://localhost:8011` (LLM siz, sukut — pulsiz); haqiqiy server — `.env.local`
  da `http://localhost:8010`. Telefon USB bilan: `powershell -ExecutionPolicy Bypass -File ..\..\mezon_backend\tools\adb_reverse.ps1`
  (8010, 8011, 8081 ni ulaydi; USB qayta ulanganda takrorlang).
- **SSE**: SDK 58 da global `fetch` = `expo/fetch` (oqimni qo'llaydi, whatwg `Request` tanasini o'qiydi) — umumiy
  `@mezon/api-client` `ask()` o'zgarishsiz ishlaydi; `TextDecoder` bo'lmasa — `createUtf8Decoder` zaxirasi.
- **Yuklash**: `expo/fetch` FormData da `{uri}` qismlarini qo'llamaydi — fayl `expo-file-system` `File` (Blob) bilan
  (`src/lib/upload.ts`, `authedFetch` — Request siz, 401 da bir marta yangilash).
- **Xavfsizlik**: `allowBackup=false`; cleartext HTTP faqat dev (`MEZON_ENV=production` da o'chadi, `app.config.ts`);
  PDF telefonda ko'rsatilmaydi va keshlanmaydi; rasmiy DOCX/PDF — veb-saytda.
- **Ishga tushirish**:
  - UI ni brauzerda: `node apps/mobile/scripts/dev-web.js` (Metro :8081, veb-rejim; launch.json `mezon-mobile-web`).
    LLM siz backend Metro uchun CORS ni o'zi yoqadi (`DJANGO_CORS_ORIGINS`, `tools/dev_nollm.py`).
  - Telefonda (dev build): `cd apps/mobile && npx expo run:android` (Android SDK `E:\android\Sdk`, Java 17) yoki tayyor APK:
    `android/app/build/outputs/apk/debug/app-debug.apk` → `adb install -r ...`, keyin `npx expo start` (Metro) + `adb_reverse.ps1`.
  - `android/` — `npx expo prebuild` bilan generatsiya qilinadi (CNG, git ga kirmaydi); konfiguratsiya faqat `app.config.ts` da.
  - **Release APK (mustaqil, Metro siz)**: `cd apps/mobile && npx expo prebuild -p android --no-install` →
    `cd android && gradlew assembleRelease` → `android/app/build/outputs/apk/release/app-release.apk`. API manzili build
    vaqtida `.env` dan JS ga yoziladi (hozir `http://localhost:8011`, USB). PC tomoni:
    `mezon_backend\tools\phone.ps1 start` (LLM siz server + telefon har ulanganda `adb reverse` ni o'zi tiklaydi).
  - **Imzo**: `credentials/release.keystore` + `release.properties` (`python apps/mobile/scripts/create-keystore.py`, bir marta;
    git ga kirmaydi; plugin `plugins/withReleaseSigning.js` ularni Gradle ga ulaydi). **Ikkala faylni zaxiralang** — kalit
    yo'qolsa, o'rnatilgan ilovani yangilab bo'lmaydi. Debug build boshqa kalit bilan — almashtirishda avval `adb uninstall uz.mezon.app`.
- **Oflayn**: server javob bermasa (kabel yo'q, server o'chiq) sessiya o'chmaydi — "Server bilan aloqa yoʻq" ekrani va
  "Qayta urinish" (`src/components/Offline.tsx`); sessiya faqat server refresh ni 4xx bilan rad etganda tozalanadi.
- Tekshiruv: `npx tsc --noEmit -p apps/mobile`, `npx expo-doctor` (20/20).
