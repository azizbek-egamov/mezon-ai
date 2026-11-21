# Lex.uz Qonun Hujjatlari Parseri

Ushbu loyiha [lex.uz](https://lex.uz) milliy qonunchilik bazasidagi qonun hujjatlarining ID-lari va metadatalarini `requests` hamda `BeautifulSoup4` yordamida to'liq parsing qilib, JSON formatda saqlash uchun mo'ljallangan.

[rss](https://lex.uz/uz/rss) ga kirsangiz barcha yangilangan va yangi yaratilgan qonunlar ro'yxati xml formatda chiqadi.

## Xususiyatlari
- **Tezkor va yengil**: Brauzer emulyatorlari (Selenium/Playwright) shart emas — to'g'ridan-to'g'ri HTTP sessiya va ASP.NET WebForms postback orqali ishlaydi.
- **Natija formati**: Har bir hujjatning `id`si, nomi (`title`), qabul qilingan sanasi (`act_date`), raqami (`act_number`), holati (`status`), hujjat to'liq havolasi (`url`), pasport havolasi (`passport_url`), PDF va Word yuklab olish havolalari bilan birga JSON ga yoziladi.
- **Moslashuvchan filtrlar**:
  - `--type qonun` (Faqat O'zbekiston Respublikasi Qonunlari, ~1,586 ta)
  - `--type all` (Barcha milliy normativ-huquqiy hujjatlar, ~28,450+ ta)
  - `--type kodeks`, `farmon`, `qaror`
  - `--lang 4` (O'zbekcha lotin, `3` - kirill, `1` - ruscha)
  - `--pages N` (Test qilish uchun N ta sahifa bilan cheklash)

## O'rnatish

```bash
pip install -r requirements.txt
```

## Ishga tushirish

1. **Faqat Qonunlar (O‘RQ) ID larini yig'ish**:
```bash
python lex_scraper.py --type qonun --output qonunlar.json
```

2. **Barcha milliy qonunchilik hujjatlarini yig'ish (~28,450 ta)**:
```bash
python lex_scraper.py --type all --output barcha_hujjatlar.json
```

3. **Sinov tariqasida dastlabki 5 ta sahifani olish**:
```bash
python lex_scraper.py --type qonun --pages 5 --output test.json
```
