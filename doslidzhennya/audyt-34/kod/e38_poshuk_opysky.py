# Центральний чат, 20.10.2026: стійкість пошуку до описок (36.18.7).
# Назви вулиць — з data/geokoder_kmda.csv.gz; запити — e12b_a4_zapyty.json, група «помилка в літері».
# S2 — триграми (як у E12b), S4 — відстань редагування по словах з допуском за довжиною слова.
import pandas as pd, json, re, collections
d=pd.read_csv('data/geokoder_kmda.csv.gz',sep='\t')
TYP=r'^(вул\.?|вулиця|просп\.?|проспект|бульв\.?|бульвар|пров\.?|провулок|пл\.?|площа|алея|узвіз|шосе|наб\.?|набережна|проїзд|тупик|майдан|дорога|спуск)\s+'
def nm(s):
    s=s.lower().replace('’',"'").replace('ʼ',"'")
    s=re.sub(TYP,'',s.strip()); return s
cnt=collections.Counter(d.street)
streets={}
for s,c in cnt.items(): streets.setdefault(nm(s),[]).append((s,c))
names=list(streets)
def dl(a,b,mx=3):
    la,lb=len(a),len(b)
    if abs(la-lb)>mx: return mx+1
    D=[[0]*(lb+1) for _ in range(la+1)]
    for i in range(la+1): D[i][0]=i
    for j in range(lb+1): D[0][j]=j
    for i in range(1,la+1):
        for j in range(1,lb+1):
            c=a[i-1]!=b[j-1]
            D[i][j]=min(D[i-1][j]+1,D[i][j-1]+1,D[i-1][j-1]+c)
            if i>1 and j>1 and a[i-1]==b[j-2] and a[i-2]==b[j-1]: D[i][j]=min(D[i][j],D[i-2][j-2]+1)
    return D[la][lb]
tri=lambda w:{w[j:j+3] for j in range(max(1,len(w)-2))}
def s2(q):
    qs=q.split();res=[]
    for n in names:
        ws=n.split();sc=0
        for w in qs:
            if any(x.startswith(w) for x in ws): sc+=2
            elif len(w)>=4 and any(len(tri(w)&tri(x))/max(len(tri(w)|tri(x)),1)>=0.4 for x in ws): sc+=1
            else: sc=-1;break
        if sc>=0: res.append((-sc,n))
    return [n for _,n in sorted(res)]
def s4(q):
    qs=q.split();res=[]
    for n in names:
        ws=n.split();tot=0;ok=True
        for w in qs:
            best=9
            for x in ws:
                if x.startswith(w): best=0;break
                lim=0 if len(w)<4 else (1 if len(w)<8 else 2)
                dd=min(dl(w,x[:len(w)],lim),dl(w,x,lim))
                if dd<=lim: best=min(best,dd)
            if best==9: ok=False;break
            tot+=best
        if ok: res.append((tot,-sum(c for _,c in streets[n]),n))
    return [n for *_,n in sorted(res)]
Q=json.load(open('doslidzhennya/audyt-34/kod/e12b_a4_zapyty.json'))
HN=re.compile(r'\s+\d[\dА-Яа-яІЇЄҐ/\- ]*$')
sk=lambda s:' '.join(sorted(s.split()))
def ciel(x): return nm(x['ціль'].split(',')[0])
T=[x for x in Q if x['vyd']=='помилка в літері']
for f in (s2,s4):
    t1=t5=0
    for x in T:
        r=[sk(n) for n in f(nm(HN.sub('',x['q']).strip()))]
        t1+= bool(r) and r[0]==sk(ciel(x)); t5+= sk(ciel(x)) in r[:5]
    print(f.__name__,'top-1',t1,'top-5',t5,'з',len(T))
for q in ['хрищатик','саксаган','лобанов','теліг','вокзальна','бесарабська','перемог','заболотн','грушевсьго','оболонський','драгоманова']:
    print(q,'| S2:',s2(q)[:2],'| S4:',s4(q)[:2])
