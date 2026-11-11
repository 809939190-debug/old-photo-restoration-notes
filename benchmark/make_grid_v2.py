import os
from PIL import Image, ImageDraw
ROOT = r"E:\deepseek工作区\bench"
RES=os.path.join(ROOT,"results_v2"); GT=os.path.join(ROOT,"data","gt"); INP=os.path.join(ROOT,"data","input_v2")
methods=[("input","重度退化输入"),("classical","传统流程"),("pro_single","pro 单次"),("pipeline","放大→修复→重绘")]
ids=["clean_01.png","clean_04.png","clean_07.png","clean_10.png"]
h=290; rows=[]
for fid in ids:
    tiles=[]
    for m,lab in methods:
        p=os.path.join(INP,fid) if m=="input" else os.path.join(RES,m,fid)
        if not os.path.exists(p): p=os.path.join(GT,fid)
        im=Image.open(p).convert("RGB"); w=int(im.width*h/im.height)
        tiles.append((im.resize((w,h), Image.LANCZOS), lab))
    W=sum(t.width for t,_ in tiles)+14*(len(tiles)-1)
    row=Image.new("RGB",(W,h+20),(255,255,255)); d=ImageDraw.Draw(row); x=0
    for im,lab in tiles:
        row.paste(im,(x,20)); d.text((x,3), lab, fill=(0,0,0)); x+=im.width+14
    rows.append(row)
W=max(r.width for r in rows); H=sum(r.height for r in rows)
s=Image.new("RGB",(W,H),(255,255,255)); y=0
for r in rows: s.paste(r,(0,y)); y+=r.height
p=os.path.join(RES,"grid_v2.png"); s.save(p); print(p, s.size)
