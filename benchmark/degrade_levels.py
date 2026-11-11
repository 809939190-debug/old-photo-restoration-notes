"""损坏强度梯度：同一张干净图，生成 4 档退化，用来找方法的"崩溃边界"。
severity 控制：霉斑数量/面积、撕裂数、划痕数、失焦、褪色程度、JPEG 质量。"""
import os, json, random
import cv2, numpy as np

ROOT = r"E:\deepseek工作区\bench"
CLEAN = os.path.join(ROOT,"data","clean")
def imwrite(p, im):
    os.makedirs(os.path.dirname(str(p)), exist_ok=True)
    ok,buf=cv2.imencode(".png", im)
    with open(str(p),"wb") as f: f.write(buf.tobytes())

def blotches(img, rng, n, size_k, alpha):
    h,w = img.shape
    mask = np.zeros((h,w), np.float32)
    for _ in range(n):
        cx,cy = rng.randint(0,w), rng.randint(0,h)
        R = rng.randint(int(min(h,w)*0.05*size_k), int(min(h,w)*0.20*size_k))
        m = np.zeros((h,w), np.uint8)
        for _ in range(rng.randint(3,6)):
            cv2.circle(m,(cx+rng.randint(-R//2,R//2), cy+rng.randint(-R//2,R//2)), max(3,rng.randint(R//3,R)), 255, -1)
        m = cv2.GaussianBlur(m,(0,0), max(1,R*0.25)).astype(np.float32)/255
        mask = np.maximum(mask, m*rng.uniform(alpha*0.7, alpha))
    b = img.astype(np.float32)
    b = b*(1-mask) + rng.uniform(115,205)*mask
    return np.clip(b,0,255).astype(np.uint8), (mask*255).astype(np.uint8)

def tears(img, rng, n, size_k):
    h,w = img.shape
    mask = np.zeros((h,w), np.uint8)
    for _ in range(n):
        cx,cy = rng.randint(0,w), rng.randint(0,h)
        pts=[]
        for _ in range(rng.randint(3,6)):
            dx, dy = int(w*0.10*size_k), int(h*0.10*size_k)
            pts.append((int(cx+rng.randint(-dx, dx)), int(cy+rng.randint(-dy, dy))))
        cv2.fillPoly(mask,[np.array(pts,np.int32)],255)
    b = img.astype(np.float32); b[mask>0] = rng.uniform(220,245)
    return b.astype(np.uint8), mask

def scratches(img, rng, n):
    h,w = img.shape
    mask = np.zeros((h,w), np.uint8)
    for _ in range(n):
        x,y = rng.randint(0,w), rng.randint(0,h); pts=[(x,y)]
        for _ in range(rng.randint(2,5)):
            x += rng.randint(-w//4,w//4); y += rng.randint(-h//4,h//4); pts.append((x,y))
        cv2.polylines(mask,[np.array(pts,np.int32)],False,rng.randint(190,255),rng.randint(1,2),cv2.LINE_AA)
    b = img.astype(np.float32); m = mask.astype(np.float32)/255
    b = b*(1-m*0.9)+240*(m*0.9)
    return np.clip(b,0,255).astype(np.uint8), mask

LEVELS = {
 "L1": dict(blot_n=4, blot_size=1.0, blot_alpha=0.65, tear_n=2, tear_size=1.0, scratch_n=20, blur=(0.7,1.1), fade=(0.62,0.76), mean=(155,175), noise=(3,6),  jpeg=(35,50)),
 "L2": dict(blot_n=7, blot_size=1.25,blot_alpha=0.80, tear_n=3, tear_size=1.2, scratch_n=30, blur=(0.9,1.4), fade=(0.50,0.62), mean=(160,180), noise=(5,9),  jpeg=(28,40)),
 "L3": dict(blot_n=10,blot_size=1.5, blot_alpha=0.90, tear_n=5, tear_size=1.5, scratch_n=40, blur=(1.2,1.8), fade=(0.38,0.50), mean=(165,188), noise=(6,11), jpeg=(20,32)),
 "L4": dict(blot_n=14,blot_size=1.8, blot_alpha=0.96, tear_n=7, tear_size=2.0, scratch_n=55, blur=(1.6,2.4), fade=(0.26,0.38), mean=(170,195), noise=(8,14), jpeg=(15,26)),
}

def degrade(clean, level, seed):
    rng = random.Random(seed); cfg = LEVELS[level]
    h,w = clean.shape
    small = cv2.resize(clean,(max(64,w//2),max(64,h//2)),interpolation=cv2.INTER_AREA)
    out = small
    out,m1 = blotches(out,rng,cfg["blot_n"],cfg["blot_size"],cfg["blot_alpha"])
    out,m2 = tears(out,rng,cfg["tear_n"],cfg["tear_size"])
    out,m3 = scratches(out,rng,cfg["scratch_n"])
    out = cv2.GaussianBlur(out,(0,0),rng.uniform(*cfg["blur"]))
    f = out.astype(np.float32)
    f = (f-f.mean())*rng.uniform(*cfg["fade"]) + rng.uniform(*cfg["mean"])
    f = f + np.random.normal(0, rng.uniform(*cfg["noise"]), f.shape)
    out = np.clip(f,0,255).astype(np.uint8)
    ok,buf = cv2.imencode(".jpg", out, [int(cv2.IMWRITE_JPEG_QUALITY), rng.randint(*cfg["jpeg"])])
    out = cv2.imdecode(buf, cv2.IMREAD_GRAYSCALE)
    damage = np.maximum(np.maximum(m1,m2),m3)
    return out, damage

def main():
    files = sorted(f for f in os.listdir(CLEAN) if f.endswith(".png"))
    meta=[]
    for lvl in LEVELS:
        for i,f in enumerate(files):
            clean = cv2.imdecode(np.fromfile(os.path.join(CLEAN,f), np.uint8), cv2.IMREAD_GRAYSCALE)
            inp, mask = degrade(clean, lvl, seed=5000+i+int(lvl[1])*100)
            d = os.path.join(ROOT,"data",lvl)
            imwrite(os.path.join(d,f), inp)
            imwrite(os.path.join(d,f.replace(".png","_mask.png")), mask)
            meta.append({"level":lvl,"id":f,"size":[int(inp.shape[1]),int(inp.shape[0])]})
        print(lvl, "done", len(files), flush=True)
    json.dump(meta, open(os.path.join(ROOT,"data","levels.json"),"w"), indent=1)

if __name__ == "__main__":
    main()
