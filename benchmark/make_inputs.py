"""生成评测输入：干净图 -> 半分辨率 -> 合成退化（这样超分/重建才有意义）。"""
import os, json
import cv2, numpy as np
import importlib.util, sys

ROOT = r"E:\deepseek工作区\bench"
CLEAN = os.path.join(ROOT, "data", "clean")
INP = os.path.join(ROOT, "data", "input")
GT = os.path.join(ROOT, "data", "gt")
os.makedirs(INP, exist_ok=True); os.makedirs(GT, exist_ok=True)

spec = importlib.util.spec_from_file_location("deg", os.path.join(ROOT, "degrade.py"))
deg = importlib.util.module_from_spec(spec); spec.loader.exec_module(deg)

def imwrite(p, im):
    ok, buf = cv2.imencode(".png", im)
    with open(str(p), "wb") as f: f.write(buf.tobytes())

meta = []
files = sorted(f for f in os.listdir(CLEAN) if f.endswith(".png"))
for i, f in enumerate(files):
    clean = cv2.imdecode(np.fromfile(os.path.join(CLEAN,f), np.uint8), cv2.IMREAD_GRAYSCALE)
    h, w = clean.shape
    small = cv2.resize(clean, (w//2, h//2), interpolation=cv2.INTER_AREA)
    inp, mask = deg.degrade(small, seed=2000+i)
    imwrite(os.path.join(GT, f), clean)
    imwrite(os.path.join(INP, f), inp)
    imwrite(os.path.join(INP, f.replace(".png","_mask.png")), mask)
    meta.append({"id": f, "gt": [int(w), int(h)], "input": [int(inp.shape[1]), int(inp.shape[0])]})
    print(f, f"{inp.shape[1]}x{inp.shape[0]} -> {w}x{h}", flush=True)
json.dump(meta, open(os.path.join(ROOT,"data","inputs.json"),"w"), indent=1)
print("total", len(meta))
