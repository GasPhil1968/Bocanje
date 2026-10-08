import sys,os
from PIL import Image
d=sys.argv[1]; out=sys.argv[2]
rows=[['01_steinblock','02_wacholder','03_wacholder_verbissen','04_wacholderzweig','05_ziege'],
      ['06_zaehltisch','07_schemel','08_kerbholz'],
      ['09_wagenrad','10_planwagen']]
G=32; ims=[[Image.open(os.path.join(d,'rgba',n+'.png')) for n in r] for r in rows]
W=max(sum(i.width for i in r)+G*(len(r)+1) for r in ims)
H=sum(max(i.height for i in r) for r in ims)+G*(len(ims)+1)
s=Image.new('RGBA',(W,H),(255,0,255,255)); y=G
for r in ims:
    rh=max(i.height for i in r); tw=sum(i.width for i in r); gap=(W-tw)//(len(r)+1); x=gap
    for i in r: s.alpha_composite(i,(x,y+rh-i.height)); x+=i.width+gap
    y+=rh+G
s=s.convert('RGB'); s.save(out); s.resize((W*2,H*2),Image.NEAREST).save(out.replace('.png','@2x.png')); print(s.size)
