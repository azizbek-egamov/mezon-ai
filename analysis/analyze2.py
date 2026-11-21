import json, sys, re, collections as C
sys.stdout.reconfigure(encoding='utf-8')
docs = json.load(open(sys.argv[1], encoding='utf-8'))
cyr = re.compile('[Ѐ-ӿ]')
lat = lambda t: len(re.findall('[A-Za-z]',t)) >= len(cyr.findall(t))
pl = [d for d in docs if not d['id'].startswith('-') and lat(d['title'])]
print("musbat id + lotin, act_type top:", C.Counter(d['act_type'] for d in pl).most_common(8))
print("ularning yillari:", sorted(C.Counter(d['act_date'][-4:] for d in pl).most_common(12)))
print("namuna:", [(d['id'],d['title'][:60]) for d in pl[:4]])
pk = [d for d in docs if not d['id'].startswith('-') and not lat(d['title'])]
print("\nmusbat id + kirill act_type top:", C.Counter(d['act_type'] for d in pk).most_common(6))
# pairs
by = C.defaultdict(list)
for d in docs: by[d['id'].lstrip('-')].append(d)
pr = [v for v in by.values() if len(v)>1]
print("\njuftlar namunasi:"); 
for v in pr[:4]: print("  ", [(x['id'], x['title'][:50], x['status']) for x in v])
print("juftlarda status farqi:", sum(1 for v in pr if len({x['status'] for x in v})>1))
# id ranges per year
ys = C.defaultdict(list)
for d in docs:
    if d['act_date']: ys[int(d['act_date'][-4:])].append(abs(int(d['id'])))
print("\nyil -> abs id oralig'i:", [(y, min(v), max(v)) for y,v in sorted(ys.items()) if y in (1995,2005,2015,2020,2025,2026)])
# order check: is list sorted by date desc?
from datetime import datetime
seq=[datetime.strptime(d['act_date'],'%d.%m.%Y') for d in docs if d['act_date']]
inv=sum(1 for a,b in zip(seq,seq[1:]) if b>a); print("sana bo'yicha tartib buzilishlari (kamayuvchi kutilgan):", inv, "/", len(seq))
nodate=[d for d in docs if not d['act_date']]
print("\nsanasiz hujjatlar act_type:", C.Counter(d['act_type'] for d in nodate).most_common(8))
print("sanasiz namunalar:", [(d['id'],d['title'][:50],d['act_type'][:40]) for d in nodate[:5]])
print("sanasizlar ro'yxatdagi o'rni (indekslar min/max):", min(i for i,d in enumerate(docs) if not d['act_date']), max(i for i,d in enumerate(docs) if not d['act_date']))
# anomalies
print("\nact_type anomaliyalari:")
for t,n in C.Counter(d['act_type'] for d in docs).items():
    if len(t)<4 or re.search(r'[A-Za-z][Ѐ-ӿ]|[Ѐ-ӿ][A-Za-z]', t): print(f"   {n:4d} {t!r}")
print("\nqisqa sarlavhalar:", [(d['id'],d['title']) for d in docs if len(d['title'])<8][:15])
print("\nKonstitutsiya:", [(d['id'],d['act_date'],d['title'][:70]) for d in docs if 'onstitutsiya' in d['act_type'] or 'онституц' in d['act_type']][:6])
print("\nkodeks act_type'lar:", C.Counter(d['act_type'] for d in docs if 'odeks' in d['act_type'] or 'одекс' in d['act_type']))
print("kodeks sarlavhali hujjatlar soni:", sum(1 for d in docs if re.search(r'\bkodeksi\b', d['title'])))
# act_type normalization potential
norm = lambda t: re.sub(r'\s+',' ',t.lower().replace('с','c').replace('о','o')).strip()
print("\nact_type noyob:", len({d['act_type'] for d in docs}), "-> kichik harf/bo'shliq normallashtirilgandan keyin:", len({norm(d['act_type']) for d in docs}))
# plenum list
pl=[d for d in docs if 'lenum' in d['act_type'] and d['status']=='kuchda']
print("\nkuchdagi Plenum qarorlari:", len(pl), C.Counter(d['act_type'] for d in pl))
# core corpus estimate
core = [d for d in docs if d['status']=='kuchda' and re.search(r"Qonuni|kodeks|Konstitutsiya|Plenum", d['act_type'], re.I)]
print("CORE (kuchda Qonun+Kodeks+Konstitutsiya+Plenum):", len(core))
core2 = [d for d in core if not re.search(r"o.zgartish|o.zgartirish|qo.shimcha", d['title'], re.I)]
print("  shundan o'zgartirish kirituvchi bo'lmaganlar:", len(core2))
pres=[d for d in docs if d['status']=='kuchda' and re.search(r"Prezident", d['act_type'])]
print("kuchdagi Prezident farmon/qarorlari:", len(pres), "| VM qarorlari kuchda:", sum(1 for d in docs if d['status']=='kuchda' and 'Vazirlar Mahkamasi' in d['act_type']))
# 2026 monthly
m=C.Counter(d['act_date'][3:5] for d in docs if d['act_date'].endswith('2026')); print("\n2026 oylar bo'yicha:", sorted(m.items()))
