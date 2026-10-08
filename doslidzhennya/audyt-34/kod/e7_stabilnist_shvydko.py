import gzip,csv,glob,sqlite3,collections,math
csv.field_size_limit(10**9)
T={}
for f in sorted(glob.glob('data/teksty/*.csv.gz')):
    for r in csv.DictReader((l.replace('\0','') for l in gzip.open(f,'rt',encoding='utf-8')),delimiter='\t'):
        T[r['doc_id']]=(r['klass'],r['date'])
c=sqlite3.connect('data/events.db')
rows=c.execute("select e.doc_id,e.grp,g.lat,g.lon from events e join geo g on g.doc_id=e.doc_id where g.precision in ('house','interp','base','cross')").fetchall()
# 30m grid-ish key: round to ~0.0003 deg lat (33m)
def key(la,lo): return (round(la/0.0003),round(lo/0.00045))
by=collections.defaultdict(lambda: collections.defaultdict(collections.Counter))
for d,g,la,lo in rows:
    t=T.get(d)
    if not t or t[0]!='B' or not t[1]: continue
    y=t[1][:4]
    by[g][y][key(la,lo)]+=1
for g in sorted(by):
    Y=by[g]
    for y in ('2024','2025'):
        cn=Y[y]; n=sum(cn.values())
        if n<200: continue
        v=sorted(cn.values(),reverse=True); s=0
        for i,x in enumerate(v):
            s+=x
            if s>=n/2: break
        print(g,y,'events',n,'places',len(cn),'places for 50%',i+1,'share of places with event %.3f'%((i+1)/len(cn)))
    a,b=Y['2024'],Y['2025']
    for k in (25,100):
        ta=set(x for x,_ in a.most_common(k)); tb=set(x for x,_ in b.most_common(k))
        if ta and tb: print('   top',k,'overlap 2024∩2025',len(ta&tb), 'jacc %.2f'%(len(ta&tb)/len(ta|tb)))
    # predictive: share of 2025 events at top-k 2024 places
    n25=sum(b.values())
    for k in (25,100):
        ta=[x for x,_ in a.most_common(k)]
        print('   2025 events at 2024 top',k,'%.3f'%(sum(b[x] for x in ta)/max(n25,1)))
