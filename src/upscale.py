"""放大 + 轻微锐化。

为什么先放大再送模型：小图会触发生成模型"重新想象"人脸，
放大到 2000~3000px 再送，模型倾向于"补细节"而不是"重画"。
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np


def imread_any(path: Path) -> np.ndarray:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), cv2.IMREAD_COLOR)


def imwrite_any(path: Path, img: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(path.suffix or ".png", img)
    if not ok:
        raise ValueError(f"写不出图片: {path}")
    buf.tofile(str(path))


def upscale_one(img: np.ndarray, scale: float, sharpen: float = 0.2) -> np.ndarray:
    big = cv2.resize(img, None, fx=scale, fy=scale, interpolation=cv2.INTER_LANCZOS4)
    if sharpen > 0:
        big = cv2.addWeighted(big, 1.0 + sharpen, cv2.GaussianBlur(big, (0, 0), 1.5), -sharpen, 0)
    return big


def main() -> None:
    ap = argparse.ArgumentParser(description="批量放大图片")
    ap.add_argument("src")
    ap.add_argument("-o", "--out", required=True)
    ap.add_argument("--scale", type=float, default=2.5)
    ap.add_argument("--sharpen", type=float, default=0.2)
    args = ap.parse_args()

    src, out = Path(args.src), Path(args.out)
    for p in sorted(src.glob("*.png")) + sorted(src.glob("*.jpg")):
        img = upscale_one(imread_any(p), args.scale, args.sharpen)
        imwrite_any(out / (p.stem + ".png"), img)
        print(f"{p.name} -> {img.shape[1]}x{img.shape[0]}")


if __name__ == "__main__":
    main()
