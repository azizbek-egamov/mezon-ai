import json, sys, re, collections as C
sys.stdout.reconfigure(encoding='utf-8')
docs = json.load(open(sys.argv[1], encoding='utf-8'))
print([(d['id'],d['act_date'],d['act_type'][:40],d['title'][:60]) for d in docs if re.search(r'Konstitutsiyasi$|Конституцияси$', d['title'].strip())][:5])
mix = [d for d in docs if re.search(r'[A-Za-zʻʼ][а-яёўқғҳ]|[а-яёўқғҳ][A-Za-z]', d['title'])]
print("sarlavhada aralash yozuvli so'z (homoglif):", len(mix), [d['title'][:70] for d in mix[:3]])
lat_pos = [d for d in docs if not d['id'].startswith('-') and d['act_date'].endswith(('2025','2026'))]
print("2025-26 dagi musbat id lar:", len(lat_pos), "| manfiy:", sum(1 for d in docs if d['id'].startswith('-') and d['act_date'].endswith(('2025','2026'))))
print("2025-26 musbat id act_type:", C.Counter(re.sub(r'.*(vazir|qoʻmita|agentlig|bank|palata|Kengash|hokim|inspeksiya).*', r'\1', d['act_type']) for d in lat_pos).most_common(8))
q=[d for d in docs if d['act_type']=='Oʻzbekiston Respublikasining Qonuni']
print("\nQonunlar:", len(q), "kuchda:", sum(d['status']=='kuchda' for d in q), "| o'zgartirish kirituvchi:", sum(1 for d in q if re.search(r"o.zgartish|o.zgartirish|qo.shimcha",d['title'])))
ys=C.Counter(d['act_date'][-4:] for d in q); print("qonunlar yillar bo'yicha (2017+):", [(y,ys[y]) for y in map(str,range(2017,2027))])
print("bo'sh act_number bo'lgan Qonunlar:", sum(1 for d in q if not d['act_number']))
