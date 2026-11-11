import os, json, collections
import cv2, numpy as np
import metrics

ROOT = r"E:\deepseek工作区\bench"
GT=os.path.join(ROOT,"data","gt"); INP=os.path.join(ROOT,"data","input_v2"); RES=os.path.join(ROOT,"results_v2")
face = metrics.Face()
def imread(p, f=cv2.IMREAD_GRAYSCALE): return cv2.imdecode(np.fromfile(str(p),np.uint8), f)

rows=[]
for m in sorted(d for d in os.listdir(RES) if os.path.isdir(os.path.join(RES,d))):
    for f in sorted(x for x in os.listdir(os.path.join(RES,m)) if x.endswith(".png")):
        p=os.path.join(RES,m,f); gt=imread(os.path.join(GT,f)); out=imread(p)
        if gt is None or out is None: continue
        if out.shape!=gt.shape: out=cv2.resize(out,(gt.shape[1],gt.shape[0]))
        mask=imread(os.path.join(INP,f.replace(".png","_mask.png")))
        if mask is not None and mask.shape!=gt.shape: mask=cv2.resize(mask,(gt.shape[1],gt.shape[0]))
        resid=float(np.mean(np.abs(out.astype(np.float32)-gt.astype(np.float32))[mask>60])) if mask is not None and (mask>60).any() else float("nan")
        dg=face.detect(gt); sim=float("nan")
        if dg:
            e1=face.embed(gt,dg); do=face.detect(out); e2=face.embed(out,do) if do else None
            if e1 is not None and e2 is not None: sim=float(np.dot(e1,e2))
        rows.append({"method":m,"file":f,"psnr":float(metrics.psnr(gt,out)),"ssim":float(metrics.ssim(gt,out)),
                     "damage_residual":resid,"id_sim":sim})
agg=collections.defaultdict(lambda: collections.defaultdict(list))
for r in rows:
    for k in ("psnr","ssim","id_sim","damage_residual"):
        v=r[k]
        if isinstance(v,float) and not np.isnan(v): agg[r["method"]][k].append(v)
print(f"{'method':<14}{'PSNR':>8}{'SSIM':>8}{'IDsim':>8}{'resid':>9}{'n':>4}")
summary={}
for m,d in sorted(agg.items()):
    summary[m]={k:round(float(np.mean(v)),3) for k,v in d.items()}
    summary[m]["n"]=len(d.get("psnr",[]))
    print(f"{m:<14}{summary[m].get('psnr',0):>8.2f}{summary[m].get('ssim',0):>8.3f}"
          f"{summary[m].get('id_sim',0):>8.3f}{summary[m].get('damage_residual',0):>9.1f}{summary[m]['n']:>4}")
json.dump(rows, open(os.path.join(RES,"metrics_raw.json"),"w"), indent=1)
json.dump(summary, open(os.path.join(RES,"summary.json"),"w"), indent=1)
