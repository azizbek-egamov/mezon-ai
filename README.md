# ⚖️ MEZON AI — O'zbekiston Qonunchiligi Uchun Legal AI Platformasi

MEZON AI — O'zbekiston Respublikasi advokatlari, yuristlari va fuqarolari uchun mo'ljallangan sun'iy intellektga asoslangan yuridik tahlil platformasi.

Platforma **lex.uz** milliy qonunchilik bazasiga tayanib, yuridik savol-javoblar (gibrid semantik qidiruv + normativ asoslash), jinoyat va fuqarolik ishlari hujjatlarini tahlil qilish (OCR → faktlar xronologiyasi → moddalar ziddiyatlari), shablonli yuridik hujjatlar konstruktori hamda to'liq avtomatlashtirilgan tekshiruv (deterministik huquqiy tekshiruvchi) imkoniyatlarini taqdim etadi.

---

## 🏗 Loyiha Arxitekturasi va Tuzilishi

Loyiha zamonaviy mikroxizmatlar va monorepo arxitekturasida tashkil etilgan:

```
mezon/
├── mezon_backend/             # Asosiy backend (Django 6.1, DRF, Python 3.11–3.14)
│   ├── apps/
│   │   ├── accounts/          # Foydalanuvchilar, rollar (CLIENT/LAWYER/MODERATOR/SUPERADMIN), audit
│   │   ├── api/               # REST API v1 (/api/v1/*), JWT auth, Swagger/OpenAPI
│   │   ├── billing/           # Tariflar, limitlar, to'lovlar va anti-fraud tizimi
│   │   ├── cases/             # Ishlar kabineti: OCR, PII niqoblash, faktlar, DOCX/PDF eksport
│   │   ├── doc_builder/       # Shablonli hujjatlar konstruktori (deterministik generator)
│   │   ├── i18n/              # 5 ta til (uz-Latn, uz-Cyrl, ru, kaa, en) va transliteratsiya
│   │   ├── lex_corpus/        # lex.uz parseri, normativ aktlar reyestri va tahrirlar tarixi
│   │   ├── ops/               # Shifrlangan zaxira nusxalash (Fernet) va tiklash
│   │   └── rag/               # Gibrid qidiruv (BGE-M3 + Qdrant + Reranker), Gemini LLM, verifikatsiya
│   ├── config/                # Django asosiy sozlamalari (settings, urls, asgi/wsgi)
│   ├── tools/                 # Ishga tushirish, sinash va production skriptlari
│   ├── requirements.txt       # Python kutubxonalari
│   └── .env.example           # Backend muhit o'zgaruvchilari namunasi
│
├── frontend/                  # Frontend monorepo (npm workspaces)
│   ├── apps/
│   │   ├── web/               # Advokat va mijozlar veb-portali (React 19 + Vite 6 + Tailwind 4)
│   │   ├── admin/             # Boshqaruv va monitoring paneli (React 19 + Vite 6)
│   │   └── mobile/            # Mobil ilova (Expo SDK 58, React Native 0.88, Android/iOS)
│   ├── packages/
│   │   ├── api-client/        # OpenAPI tiplangan fetch mijoz, JWT auto-refresh, SSE chat oqimi
│   │   ├── i18n/              # i18next ko'p tillilik to'plami
│   │   └── web-kit/           # Umumiy UI komponentlar (shadcn/radix), tema, autentifikatsiya
│   ├── package.json           # Monorepo asosiy bog'liqliklari
│   └── README.md              # Frontend bo'yicha batafsil qo'llanma
│
├── qdrant_server/             # Qdrant vektor qidiruv serveri sozlamalari
│   └── config.yaml            # Mahalliy Qdrant konfiguratsiyasi (127.0.0.1:6333)
│
├── designs/                   # "Klassik yuridik" dizayn tizimi va ekran maketlari
├── analysis/                  # Tizim tahlili, diagnostika va test ssenariylari
├── CLAUDE.md                  # Claude Code / AI yordamchi uchun qo'llanma
├── HANDOFF.md                 # Loyihaning joriy holati va rivojlanish tarixi
└── TZ-v2.1.md                 # Texnik topshiriq (barcha § bandlari)
```

---

## 🚀 Yangi Kompyuterda Loyihani O'rnatish va Ishga Tushirish

Loyihani boshqa kompyuterda klonlab, noldan ishga tushirishda quyidagi qadamlarni tartib bilan bajaring.

### 1. Tizim Talablari

- **Operatsion tizim:** Windows 10/11, Linux (Ubuntu 22.04+) yoki macOS
- **Python:** 3.11, 3.12, 3.13 yoki 3.14
- **Node.js:** v20.18+ yoki v22.x (npm 10+)
- **Git**

---

### 2. Repozitoriyani Klonlash

```bash
git clone https://github.com/azizbek-egamov/mezon-ai.git
cd mezon-ai
```

---

### 3. Backend Sozlash (`mezon_backend`)

#### a) Virtual muhit yaratish va faollashtirish:

- **Windows (PowerShell):**
  ```powershell
  cd mezon_backend
  python -m venv .venv
  .venv\Scripts\Activate.ps1
  ```
- **Linux / macOS:**
  ```bash
  cd mezon_backend
  python3 -m venv .venv
  source .venv/bin/activate
  ```

#### b) Paketlarni o'rnatish:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

> **Eslatma (PyTorch GPU qo'llab-quvvatlash uchun):**  
> Agar kompyuteringizda NVIDIA GPU bo'lsa va undan foydalanmoqchi bo'lsangiz:
> ```bash
> pip install torch==2.14.1 --index-url https://download.pytorch.org/whl/cu121
> ```

#### c) `.env` faylini yaratish:

`mezon_backend/.env.example` dan `.env` faylini yarating:

- **Windows (PowerShell):**
  ```powershell
  Copy-Item .env.example .env
  ```
- **Linux / macOS:**
  ```bash
  cp .env.example .env
  ```

Endi `.env` faylini ochib, quyidagi muhim kalitlarni to'ldiring:
1. `DJANGO_SECRET_KEY` — tasodifiy uzun qator.
2. `MEZON_DATA_KEYS` — fayllarni shifrlash kaliti. Uni yaratish uchun:
   ```bash
   python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
   ```
3. `GEMINI_API_KEY` — Google AI Studio dan olingan bepul API kalitingiz ([aistudio.google.com](https://aistudio.google.com/)).

#### d) Ma'lumotlar bazasi migratsiyasi:

```bash
python manage.py migrate
python manage.py createsuperuser  # Admin uchun hisob yaratish
```

---

### 4. Vektor Qidiruv Serveri (Qdrant)

MEZON AI gibrid qidiruv uchun Qdrant vektor bazasidan foydalanadi. Uni ishga tushirishning 2 ta qulay usuli bor:

#### 1-usul: Docker orqali (Eng oson va tavsiya etilgan):
```bash
docker run -d -p 6333:6333 -p 6334:6334 -v qdrant_storage:/qdrant/storage:z qdrant/qdrant
```

#### 2-usul: Qdrant Binary yuklab olish:
- [Qdrant rasmiy relizlar sahifasi](https://github.com/qdrant/qdrant/releases)dan tizimingizga mos faylni yuklab oling (masalan, Windows uchun `qdrant-x86_64-pc-windows-msvc.zip`).
- `qdrant.exe` ni `qdrant_server/` papkasiga joylashtiring.
- Ishga tushirish:
  ```powershell
  cd qdrant_server
  .\qdrant.exe --config-path config.yaml
  ```

> **Eslatma:** Agar Qdrant serverni ishga tushirmasangiz, backend avtomatik ravishda ichki xotira (in-memory) rejimida ishlay oladi (`.env` da `QDRANT_URL=` ni bo'sh qoldiring).

---

### 5. Backend Serverni Ishga Tushirish

Backendni odatiy yoki LLM siz (mablag' tejash) rejimida ishga tushirish mumkin:

- **Odatiy rejim (port 8010):**
  ```bash
  python manage.py runserver 8010
  ```
- **LLM-siz Dev rejim (Pulsiz / UI sinovlari uchun, port 8011):**
  ```bash
  python tools/dev_nollm.py 8011
  ```
- **API Hujjatlari (Swagger):**  
  Brauzerda: `http://127.0.0.1:8010/api/v1/docs/`

---

### 6. Frontend Sozlash va Ishga Tushirish (`frontend`)

Frontend monorepo bo'lib, npm workspaces orqali boshqariladi.

#### a) Paketlarni o'rnatish:
```bash
cd frontend
npm install
```

#### b) Loyihalarni ishga tushirish:

- **Veb-sayt (Mijoz & Advokat portali):**
  ```bash
  npm run dev:web
  # Brauzerda ochiladi: http://localhost:5173
  ```

- **Veb-sayt (LLM-siz dev backend bilan):**
  ```bash
  npm run dev:web:nollm
  ```

- **Admin Panel (Superadmin & Moderator):**
  ```bash
  npm run dev -w @mezon/admin
  # Brauzerda ochiladi: http://localhost:5174
  ```

- **Mobil ilova (Expo):**
  ```bash
  cd apps/mobile
  npx expo start
  ```

#### c) Kod sifatini tekshirish va testlar:
```bash
cd frontend
npm run typecheck    # TypeScript tiplarini tekshirish
npm test             # Vitest testlarini ishga tushirish
```

---

## 🧪 Avtomatlashtirilgan Testlar

Loyiha yuqori test qamroviga ega bo'lib, barcha tekshiruvlar API chaqiruvlarisiz (mock rejimida) tezkor ishlaydi:

```bash
# Backend testlari (288+ test)
cd mezon_backend
python manage.py test apps

# Frontend testlari (22+ unit test)
cd frontend
npm test
```

---

## 🔒 Xavfsizlik va Ma'lumotlarni Saqlash

1. **Maxfiylik:** Barcha maxfiy kalitlar (`.env`, `credentials/`, `secret/`) `.gitignore` ga kiritilgan va repozitoriyaga chiqmaydi.
2. **Advokat siri:** Yuklangan tergov va sud hujjatlari diskda faqat Fernet 128-bit AES shifrlangan holatda saqlanadi (`apps/cases/storage.py`).
3. **PII Niqoblash:** Tizimga yuklangan hujjatlardagi fuqarolarning shaxsiy ma'lumotlari (F.I.Sh., pasport, telefon, manzil) sun'iy intellektga yuborilishidan oldin to'liq niqoblanadi.

---

## 📝 Litsenziya va Mualliflik

Loyiha muallifi: **Azizbek Egamov**  
Repozitoriya: [https://github.com/azizbek-egamov/mezon-ai.git](https://github.com/azizbek-egamov/mezon-ai.git)
