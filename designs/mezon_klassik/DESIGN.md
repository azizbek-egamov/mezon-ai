---
name: Mezon Klassik
supersedes: designs/mezon_sovereign_precision (2026-10-30, foydalanuvchi qarori)
colors:
  light:
    canvas: '#F7F4EC'      # sahifa foni — iliq fil suyagi
    surface: '#FFFFFF'     # kartalar, panellar
    subtle: '#F1ECE0'      # hover, input foni, ikkinchi darajali bloklar
    line: '#E4DCCB'        # chegara
    ink: '#1D2433'         # asosiy matn
    muted: '#6B6658'       # ikkinchi darajali matn (canvas ustida AA)
    primary: '#1F3A5F'     # to'q ko'k — asosiy amal
    primary-fg: '#FFFFFF'
    gold: '#8A6A1F'        # qonun havolalari (matn); fon — gold/10
    green: '#2F7D4F'
    red: '#B4382F'
    amber: '#A9671A'
  dark:
    canvas: '#17181B'      # iliq qorong'i (ko'k-qora emas)
    surface: '#1F2024'
    subtle: '#292A2F'
    line: '#34353B'
    ink: '#ECEAE4'
    muted: '#A19D93'
    primary: '#9DBBE0'
    primary-fg: '#10213A'
    gold: '#D9B565'
    green: '#6CC08F'
    red: '#EB7B70'
    amber: '#E2A65A'
typography:
  heading: Lora (serif, 600) — sahifa va bo'lim sarlavhalari, logotip
  body: Inter (400/500/600) — barcha interfeys matni, 16px / 1.65
  mono: faqat haqiqiy kod/ID (masalan, ish raqami) — interfeys yorliqlarida ishlatilmaydi
rounded: { sm: 6px, DEFAULT: 8px, md: 10px, lg: 12px, xl: 16px, full: 9999px }
---

## G'oya
MEZON — advokat uchun ishonchli yordamchi. Ko'rinishi **huquqiy jurnal yoki yaxshi advokatlik firmasi** kabi:
toza, yorug', o'qishga qulay, jiddiy, lekin og'ir emas. Oldingi "missiya boshqaruv pulti" uslubi (ko'k-qora fon,
kod shrifti, texnik yorliqlar, zichlik) foydalanuvchiga yoqmadi — 2026-10-30 da shu tizim bilan almashtirildi.

## Tamoyillar
1. **Yorug' — asosiy, qorong'i — tanlov.** Tizim sozlamasiga ergashadi, foydalanuvchi qo'lda almashtira oladi
   (veb: `localStorage["mezon.theme"]`, mobil: profil). Ikkala rejim ham bir xil tokenlardan.
2. **Odamcha til.** Ekranda texnik so'zlar yo'q: "SHA-256", "tokens/s", "CRITIC", "PRECISION", katta harfli kod
   yorliqlari ishlatilmaydi. Yorliqlar oddiy jumla harfida ("Ish tahlili", "ISH TAHLILI" emas).
3. **Havo.** Bitta ekranda bitta asosiy vazifa. Kartalar orasida 16–24px, ichida 20–24px. Asosiy matn 16px.
4. **Bitta asosiy tugma.** Har ekranda to'q ko'k to'ldirilgan tugma bittadan oshmaydi; qolganlari — chegarali yoki matnli.
5. **Oltin — faqat qonun.** Oltin rang faqat lex.uz moddalari va rasmiy manbalar uchun (iqtibos chiplari).
6. **Holat ranglari** (yashil, qizil, sariq) — faqat ma'no bilan: tasdiqlandi / xavf / ogohlantirish. Fon — rangning
   10% i, matn — rangning o'zi.

## Komponentlar
- **Tugma:** balandlik 40px (kichik 34px), radius 8px, 500–600 qalinlik. Asosiy — `primary` fon; ikkinchi darajali —
  `surface` fon + `line` chegara; xavfli — qizil matn, qizil chegara; matnli — faqat `primary` rang.
- **Karta:** `surface` fon, 1px `line` chegara, radius 12px, juda yengil soya (yorug' rejimda). Chap rangli chiziq
  faqat holat uchun (xavf, ogohlantirish).
- **Input:** `surface` fon, 1px `line`, radius 8px, 44px; fokus — 2px `primary` halqa.
- **Iqtibos chipi (lex.uz):** radius to'liq, `gold/10` fon, `gold/30` chegara, `gold` matn, "JK 168-modda" kabi.
- **Navigatsiya:** veb — chapda oq panel, faol bo'lim `subtle` fon + to'q ko'k matn; mobil — pastda 4 ta bo'lim,
  faol bo'lim `primary`.
- **Sarlavhalar:** Lora 600; sahifa 28–32px (mobil 24px), bo'lim 20px, karta 17px.
- **Bo'sh holat:** ikonka + bitta jumla + bitta tugma; uzr so'rash emas, taklif.

## Logotip
To'q ko'k kvadrat (radius 8) ichida oltin serif "M"; yonida Lora 600 "Mezon". Qo'shimcha shior yo'q.
