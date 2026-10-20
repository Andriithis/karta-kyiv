# Е5, центральний чат 20.10: розрізненість кольорів видів (CAM02-UCS ΔE), CVD і проєктор.
import numpy as np, itertools, colorsys
from colorspacious import cspace_convert, deltaE
N=['Порядок','Торгівля','Наркотики','Насильство','Майно','ДТП','Пор.на дорозі']
P={'світла (графіт)':['#A54D09','#009178','#5056B0','#BD5460','#3C74C2','#417341','#8a7e9c'],
   'темна (крейда)':['#FFA76E','#5ADAB7','#9B99F0','#F78265','#8AC0F1','#85BB8F','#d890ba']}
BG={'світла (графіт)':'#eef0ee','темна (крейда)':'#2b2f36'}
h=lambda s:np.array([int(s[i:i+2],16) for i in (1,3,5)])/255
def lum(c):
    c=np.where(c<=0.03928,c/12.92,((c+0.055)/1.055)**2.4);return 0.2126*c[0]+0.7152*c[1]+0.0722*c[2]
def cr(a,b):
    la,lb=sorted([lum(a),lum(b)]);return (lb+0.05)/(la+0.05)
VYDY=['звичайний','протанопія','дейтеранопія','тританопія','проєктор']
def sim(c,t):
    if t=='звичайний':return c
    if t=='проєктор': return c*0.65+0.35*np.array([.6,.6,.6])
    cvd={'протанопія':'protanomaly','дейтеранопія':'deuteranomaly','тританопія':'tritanomaly'}[t]
    return np.clip(cspace_convert(c,{'name':'sRGB1+CVD','cvd_type':cvd,'severity':100},'sRGB1'),0,1)
def worst(cs):
    m=99
    for t in VYDY:
        s=[sim(c,t) for c in cs]
        for i,j in itertools.combinations(range(7),2):
            m=min(m,deltaE(s[i],s[j],input_space='sRGB1',uniform_space='CAM02-UCS'))
    return m
for nm,pal in P.items():
    cs=[h(x) for x in pal];bg=h(BG[nm])
    print('\n==',nm,'фон',BG[nm])
    print('контраст до фону:',', '.join(f'{N[i]} {cr(c,bg):.1f}' for i,c in enumerate(cs)))
    for t in VYDY:
        s=[sim(c,t) for c in cs]
        pr=sorted((deltaE(s[i],s[j],input_space='sRGB1',uniform_space='CAM02-UCS'),N[i],N[j]) for i,j in itertools.combinations(range(7),2))
        print(f'{t:13s} найгірші пари:',' ; '.join(f'{a}–{b} {d:.1f}' for d,a,b in pr[:3]))
    base=worst(cs);best=(base,None)
    for k in range(7):
        hh,ll,ss=colorsys.rgb_to_hls(*cs[k])
        for dh in np.linspace(-0.06,0.06,7):
            for L in np.linspace(max(.2,ll-.15),min(.85,ll+.15),7):
                for S in (ss*0.8,ss,min(1,ss*1.2)):
                    c=np.array(colorsys.hls_to_rgb((hh+dh)%1,L,S))
                    if cr(c,bg)<3: continue
                    t=cs.copy();t[k]=c;w=worst(t)
                    if w>best[0]+0.3: best=(w,k,'#%02x%02x%02x'%tuple((c*255).round().astype(int)))
    print('зараз найгірша пара',round(base,1),'→ найкраща заміна одного кольору',best)
