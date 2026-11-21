import json, sys, re, collections as C
from datetime import date
sys.stdout.reconfigure(encoding='utf-8')
docs = json.load(open(sys.argv[1], encoding='utf-8'))
print("JAMI:", len(docs))
keys = C.Counter(tuple(sorted(d)) for d in docs); print("KEYS:", keys.most_common(3))
for k in ['id','title','act_type','act_number','act_date','status']:
    empty = sum(1 for d in docs if not str(d.get(k,'')).strip())
    print(f"bo'sh {k}: {empty} ({empty/len(docs):.1%})")
ids = [d['id'] for d in docs]
print("noyob id:", len(set(ids)), "| dublikat:", len(ids)-len(set(ids)))
neg = sum(1 for i in ids if i.startswith('-')); print("manfiy id (lotin):", neg, "musbat (kirill):", len(ids)-neg)
absid = C.Counter(i.lstrip('-') for i in ids)
pairs = sum(1 for v in absid.values() if v>1); print("lotin+kirill juft (bir abs id):", pairs, "| noyob abs id:", len(absid))
# script detection by title
cyr = re.compile('[Ѐ-ӿ]')
def script(t):
    c = len(cyr.findall(t)); l = len(re.findall('[A-Za-z]', t))
    return 'kirill' if c>l else 'lotin'
sc = C.Counter((('-' if i.startswith('-') else '+'), script(d['title'])) for i,d in zip(ids,docs))
print("id ishorasi x sarlavha yozuvi:", dict(sc))
ru = sum(1 for d in docs if re.search(r'\b(о|об|и|в|на|по)\b', d['title']) and 'ў' not in d['title'] and 'қ' not in d['title'] and 'ғ' not in d['title'] and 'ҳ' not in d['title'] and cyr.search(d['title']))
print("ruscha bo'lishi mumkin bo'lgan sarlavhalar:", ru)
print("\nSTATUS:", C.Counter(d['status'] for d in docs))
at = C.Counter(d['act_type'] for d in docs)
print("\nact_type noyob:", len(at)); 
for t,n in at.most_common(40): print(f"  {n:6d}  {t}")
# grouped act category
def cat(t):
    t=t.lower()
    for k,v in [('kodeks','Kodeks'),('кодекс','Kodeks'),('konstitutsiya','Konstitutsiya'),('конституция','Konstitutsiya'),('qonuni','Qonun'),('закон','Qonun'),('қонуни','Qonun'),('farmoni','Prezident farmoni'),('фармони','Prezident farmoni'),('указ','Prezident farmoni'),('prezidentining qarori','Prezident qarori'),('президентининг қарори','Prezident qarori'),('постановление президента','Prezident qarori'),('vazirlar mahkamasi','VM qarori/farmoyishi'),('вазирлар маҳкамаси','VM qarori/farmoyishi'),('кабинета министров','VM qarori/farmoyishi'),('plenum','Plenum'),('пленум','Plenum'),('buyrug','Vazirlik buyrug‘i'),('буйруғ','Vazirlik buyrug‘i'),('приказ','Vazirlik buyrug‘i'),('farmoyish','Farmoyish'),('фармойиш','Farmoyish'),('распоряжение','Farmoyish'),('kengash','Kengash/Oliy Majlis qarori'),('кенгаш','Kengash/Oliy Majlis qarori'),('senat','Kengash/Oliy Majlis qarori'),('сенат','Kengash/Oliy Majlis qarori'),('palata','Kengash/Oliy Majlis qarori'),('палата','Kengash/Oliy Majlis qarori'),('qaror','Boshqa qaror'),('қарор','Boshqa qaror'),('постановлен','Boshqa qaror'),('shartnoma','Xalqaro shartnoma'),('битим','Xalqaro shartnoma'),('bitim','Xalqaro shartnoma'),('договор','Xalqaro shartnoma'),('соглашение','Xalqaro shartnoma'),('konvensiya','Xalqaro shartnoma'),('конвенция','Xalqaro shartnoma')]:
        if k in t: return v
    return 'Boshqa' if t else '(bo‘sh)'
cc = C.Counter(cat(d['act_type']) for d in docs)
print("\nKATEGORIYA:"); 
for t,n in cc.most_common(): 
    act = sum(1 for d in docs if cat(d['act_type'])==t and d['status']=='kuchda')
    print(f"  {n:6d}  kuchda {act:6d} ({act/n:.0%})  {t}")
print("\n'Boshqa' namunalar:", [t for t,_ in C.Counter(d['act_type'] for d in docs if cat(d['act_type'])=='Boshqa').most_common(15)])
# dates
bad=0; years=C.Counter(); future=[]; dts=[]
for d in docs:
    m = re.fullmatch(r'(\d\d)\.(\d\d)\.(\d{4})', d['act_date'])
    if not m: bad+=1; continue
    try: dt = date(int(m[3]),int(m[2]),int(m[1]))
    except ValueError: bad+=1; continue
    dts.append(dt); years[dt.year]+=1
    if dt > date(2026,10,23): future.append(d['id'])
print("\nSANA: noto'g'ri/bo'sh:", bad, "| min:", min(dts), "max:", max(dts), "| kelajak:", len(future))
dec = C.Counter((y//10)*10 for y in years.elements()); print("o'n yilliklar:", sorted(dec.items()))
print("so'nggi yillar:", [(y,years[y]) for y in range(2015,2027)])
# status by decade
for dcd in sorted(dec):
    ds=[d for d in docs if re.fullmatch(r'\d\d\.\d\d\.(\d{4})',d['act_date']) and int(d['act_date'][-4:])//10*10==dcd]
    print(f"  {dcd}s: {len(ds)} ta, kuchda {sum(x['status']=='kuchda' for x in ds)/len(ds):.0%}")
# act_number
an = C.Counter(re.sub(r'\d+','N',d['act_number']) for d in docs); print("\nact_number shakllari:", an.most_common(10))
# titles
tl = [len(d['title']) for d in docs]; tl.sort()
print("\nsarlavha uzunligi: min", tl[0], "median", tl[len(tl)//2], "max", tl[-1])
amend = sum(1 for d in docs if re.search(r"o.zgartish|o.zgartirish|qo.shimcha|изменени|дополнени|ўзгартиш|ўзгартириш|қўшимча", d['title'], re.I))
print("o'zgartirish/qo'shimcha kirituvchi hujjatlar:", amend, f"({amend/len(docs):.0%})")
invalid = sum(1 for d in docs if re.search(r"o.z kuchini yo.qotgan|ўз кучини йўқотган|утратившими силу", d['title'], re.I))
print("'kuchini yo'qotgan deb topish' hujjatlari:", invalid)
tt = C.Counter(d['title'] for d in docs); dup=[(t,n) for t,n in tt.items() if n>1]
print("takroriy sarlavhalar:", len(dup), "| eng ko'p:", sorted(dup,key=lambda x:-x[1])[:5])
# url consistency
badurl = sum(1 for d in docs if d['url']!=f"https://lex.uz/uz/docs/{d['id']}" or d['pdf_url']!=f"https://lex.uz/uz/pdfs/{d['id']}"); print("URL nomuvofiq:", badurl)
# codes list
print("\nKODEKSLAR (kuchda):")
for d in docs:
    if cat(d['act_type'])=='Kodeks' and d['status']=='kuchda' and d['id'].startswith('-'): print("  ", d['id'], d['act_date'], d['title'][:90])
# whitespace issues
ws = sum(1 for d in docs if d['title']!=d['title'].strip() or '  ' in d['title']); print("\nsarlavhada ortiqcha bo'shliq:", ws)
apos = C.Counter(ch for d in docs for ch in d['title'] if ch in "'`‘’ʻʼ"); print("apostrof turlari:", apos)
