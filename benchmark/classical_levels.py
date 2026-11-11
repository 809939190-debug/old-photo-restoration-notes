import os
import cv2, numpy as np
ROOT = r"E:\deepseek工作区\bench"
def imread(p,f=cv2.IMREAD_GRAYSCALE): return cv2.imdecode(np.fromfile(str(p),np.uint8),f)
def imwrite(p,im):
    os.makedirs(os.path.dirname(str(p)),exist_ok=True)
    ok,buf=cv2.imencode(".png",im)
    with open(str(p),"wb") as f: f.write(buf.tobytes())
for lvl in ["L1","L2","L3","L4"]:
    src=os.path.join(ROOT,"data",lvl); gt=os.path.join(ROOT,"data","clean")
    files=sorted(f for f in os.listdir(src) if f.endswith(".png") and "_mask" not in f)
    for f in files:
        inp=imread(os.path.join(src,f)); g=imread(os.path.join(gt,f))
        h,w=g.shape
        den=cv2.fastNlMeansDenoising(inp,None,h=10,templateWindowSize=7,searchWindowSize=21)
        up=cv2.resize(den,(w,h),interpolation=cv2.INTER_LANCZOS4)
        sh=cv2.addWeighted(up,1.35,cv2.GaussianBlur(up,(0,0),1.2),-0.35,0)
        lo,hi=np.percentile(sh,1),np.percentile(sh,99)
        out=np.clip((sh.astype(np.float32)-lo)*((240-15)/max(hi-lo,1e-3))+15,0,255).astype(np.uint8)
        imwrite(os.path.join(ROOT,"results_levels",lvl,"classical",f), out)
    print(lvl, "classical done", flush=True)
