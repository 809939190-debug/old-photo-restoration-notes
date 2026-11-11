"""评测：PSNR / SSIM / 损伤残留 / 人脸一致性（SCRFD + ArcFace）。"""
import os, json
import cv2, numpy as np
import onnxruntime as ort

ROOT = r"E:\deepseek工作区\bench"
GT = os.path.join(ROOT,"data","gt")
INP = os.path.join(ROOT,"data","input")
RES = os.path.join(ROOT,"results")
DET = os.path.join(ROOT,"models","buffalo_sc","det_500m.onnx")
REC = os.path.join(ROOT,"models","buffalo_sc","w600k_mbf.onnx")
TEMPLATE = np.array([[38.2946,51.6963],[73.5318,51.5014],[56.0252,71.7366],
                     [41.5493,92.3655],[70.7299,92.2041]], np.float32)

def imread(p, flags=cv2.IMREAD_GRAYSCALE):
    return cv2.imdecode(np.fromfile(str(p), np.uint8), flags)

def psnr(a,b):
    mse = np.mean((a.astype(np.float32)-b.astype(np.float32))**2)
    return 99.0 if mse<=1e-9 else 10*np.log10(255.0**2/mse)

def ssim(a,b):
    a=a.astype(np.float32); b=b.astype(np.float32)
    C1,C2=(0.01*255)**2,(0.03*255)**2
    k=(11,11)
    mu1=cv2.GaussianBlur(a,k,1.5); mu2=cv2.GaussianBlur(b,k,1.5)
    s1=cv2.GaussianBlur(a*a,k,1.5)-mu1*mu1
    s2=cv2.GaussianBlur(b*b,k,1.5)-mu2*mu2
    s12=cv2.GaussianBlur(a*b,k,1.5)-mu1*mu2
    return float(np.mean(((2*mu1*mu2+C1)*(2*s12+C2))/((mu1**2+mu2**2+C1)*(s1+s2+C2))))

class Face:
    SIZE = 640
    def __init__(self):
        so=ort.SessionOptions(); so.intra_op_num_threads=4
        self.det=ort.InferenceSession(DET, so, providers=["CPUExecutionProvider"])
        self.rec=ort.InferenceSession(REC, so, providers=["CPUExecutionProvider"])
        self.din=self.det.get_inputs()[0].name
        self.rin=self.rec.get_inputs()[0].name

    def detect(self, img):
        h,w = img.shape[:2]
        s = self.SIZE/max(h,w)
        nw,nh = int(w*s), int(h*s)
        nw32, nh32 = (nw+31)//32*32, (nh+31)//32*32
        x = cv2.resize(img,(nw32,nh32)).astype(np.float32)
        sx, sy = nw32/nw, nh32/nh
        x = (x-127.5)/128.0
        blob = np.repeat(x[:,:,None],3,axis=2).transpose(2,0,1)[None].astype(np.float32)
        outs = self.det.run(None, {self.din: blob})
        scores, boxes, kpss = outs[0:3], outs[3:6], outs[6:9]
        best=None
        for si,(sc,bx,kp) in enumerate(zip(scores,boxes,kpss)):
            stride = 8*(2**si)
            fh, fw = nh32//stride, nw32//stride
            ys,xs = np.mgrid[0:fh,0:fw]
            centers = np.stack([xs,ys],-1).reshape(-1,2).astype(np.float32)*stride
            n = centers.shape[0]
            if bx.shape[0] != n*2:  # 每个位置 2 个 anchor
                repeat = bx.shape[0]//n
                centers = np.repeat(centers, repeat, axis=0)
            else:
                centers = np.repeat(centers, 2, axis=0)
            conf = sc.reshape(-1)
            for i in range(min(conf.shape[0], centers.shape[0])):
                if conf[i] < 0.5: continue
                d = bx[i]*stride
                x1,y1 = centers[i,0]-d[0], centers[i,1]-d[1]
                x2,y2 = centers[i,0]+d[2], centers[i,1]+d[3]
                area=(x2-x1)*(y2-y1)
                if best is None or area>best[0]:
                    kp5 = (kp[i].reshape(5,2)*stride) if kp.shape[1]==10 else None
                    best=(area,(x1,y1,x2,y2),kp5)
        if best is None: return None
        area,(x1,y1,x2,y2),kp5 = best
        k = 1.0/s
        return ((x1/sx*k, y1/sy*k, x2/sx*k, y2/sy*k), None if kp5 is None else np.stack([kp5[:,0]/sx*k, kp5[:,1]/sy*k],1))

    def embed(self, img, det):
        box, kp5 = det
        if kp5 is not None:
            M,_ = cv2.estimateAffinePartial2D(kp5.astype(np.float32), TEMPLATE)
            if M is not None:
                crop = cv2.warpAffine(img, M, (112,112), flags=cv2.INTER_LINEAR)
            else:
                x1,y1,x2,y2=[int(v) for v in box]; crop=cv2.resize(img[max(0,y1):y2,max(0,x1):x2],(112,112))
        else:
            x1,y1,x2,y2=[int(v) for v in box]
            crop = img[max(0,y1):y2, max(0,x1):x2]
            if crop.size==0: return None
            crop = cv2.resize(crop,(112,112))
        c=(crop.astype(np.float32)-127.5)/128.0
        blob=np.repeat(c[:,:,None],3,axis=2).transpose(2,0,1)[None].astype(np.float32)
        e=self.rec.run(None,{self.rin:blob})[0][0]
        return e/(np.linalg.norm(e)+1e-9)

def main():
    face=Face()
    methods=sorted(d for d in os.listdir(RES) if os.path.isdir(os.path.join(RES,d)) and d not in ("ours",))
    rows=[]
    for m in methods:
        files=sorted(f for f in os.listdir(os.path.join(RES,m)) if f.endswith(".png"))
        for f in files:
            gt=imread(os.path.join(GT,f)); out=imread(os.path.join(RES,m,f))
            if out is None: continue
            if out.shape!=gt.shape: out=cv2.resize(out,(gt.shape[1],gt.shape[0]))
            mask=imread(os.path.join(INP,f.replace(".png","_mask.png")))
            if mask is not None and mask.shape!=gt.shape: mask=cv2.resize(mask,(gt.shape[1],gt.shape[0]))
            resid=float(np.mean(np.abs(out.astype(np.float32)-gt.astype(np.float32))[mask>40])) if mask is not None and (mask>40).any() else float("nan")
            dg=face.detect(gt); sim=float("nan")
            if dg:
                e1=face.embed(gt,dg)
                do=face.detect(out); e2=face.embed(out,do) if do else None
                if e1 is not None and e2 is not None: sim=float(np.dot(e1,e2))
            rows.append({"method":m,"file":f,"psnr":psnr(gt,out),"ssim":ssim(gt,out),"damage_residual":resid,"id_sim":sim})
            print(m,f,f"psnr={rows[-1]['psnr']:.2f} ssim={rows[-1]['ssim']:.3f} id={sim:.3f} resid={resid:.1f}",flush=True)
    json.dump(rows,open(os.path.join(RES,"metrics_raw.json"),"w"),indent=1)

if __name__=="__main__":
    main()
