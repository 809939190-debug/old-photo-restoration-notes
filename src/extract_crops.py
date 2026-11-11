"""从整页扫描图里定位每张照片。

思路：用户手工圈出的截图（screens/*.png）当作模板，在多尺度下做归一化相关匹配，
把最佳匹配位置映射回原分辨率，得到每张照片的精确裁切框。
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import cv2
import numpy as np


def imread_any(path: Path) -> np.ndarray:
    """cv2.imread 不支持非 ASCII 路径，用 imdecode 绕开。"""
    buf = np.fromfile(str(path), dtype=np.uint8)
    img = cv2.imdecode(buf, cv2.IMREAD_COLOR)
    if img is None:
        raise ValueError(f"读不出图片: {path}")
    return img


def imwrite_any(path: Path, img: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(path.suffix or ".png", img)
    if not ok:
        raise ValueError(f"写不出图片: {path}")
    buf.tofile(str(path))


def locate(page: np.ndarray, screen: np.ndarray, scales=(0.5, 0.75, 1.0, 1.5, 2.0, 3.0)):
    """返回 (x, y, w, h, score)，坐标已换算回 page 尺度。"""
    pg = cv2.cvtColor(page, cv2.COLOR_BGR2GRAY)
    sc = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    best = None
    for s in scales:
        tw, th = int(page.shape[1] * s), int(page.shape[0] * s)
        page_s = cv2.resize(pg, (tw, th), interpolation=cv2.INTER_AREA)
        # 截图可能被压缩过，尺寸和目标不一致，逐档尝试模板缩放
        for k in (0.25, 0.33, 0.4, 0.5, 0.6, 0.75, 0.9):
            tpl = cv2.resize(sc, None, fx=k, fy=k, interpolation=cv2.INTER_AREA)
            if tpl.shape[0] >= page_s.shape[0] or tpl.shape[1] >= page_s.shape[1]:
                continue
            res = cv2.matchTemplate(page_s, tpl, cv2.TM_CCOEFF_NORMED)
            _, mx, _, loc = cv2.minMaxLoc(res)
            if best is None or mx > best[4]:
                x, y = loc
                best = (x / s, y / s, tpl.shape[1] / s, tpl.shape[0] / s, float(mx))
    return best


def main() -> None:
    ap = argparse.ArgumentParser(description="用截图模板定位页面里的每张照片")
    ap.add_argument("page")
    ap.add_argument("--screens", default="screens")
    ap.add_argument("-o", "--out", default="crop_user")
    ap.add_argument("--min-score", type=float, default=0.55)
    args = ap.parse_args()

    page = imread_any(Path(args.page))
    out = Path(args.out)
    screens = sorted(Path(args.screens).glob("*.png")) + sorted(Path(args.screens).glob("*.jpg"))
    boxes = {}
    for i, sp in enumerate(screens, 1):
        box = locate(page, imread_any(sp))
        if box is None or box[4] < args.min_score:
            print(f"[skip] {sp.name} 匹配分过低: {box[4] if box else 0:.3f}")
            continue
        x, y, w, h, score = box
        x0, y0 = max(0, int(x)), max(0, int(y))
        x1, y1 = min(page.shape[1], int(x + w)), min(page.shape[0], int(y + h))
        name = f"photo_{i:02d}.png"
        imwrite_any(out / name, page[y0:y1, x0:x1])
        boxes[name] = {"box": [x0, y0, x1, y1], "score": round(score, 4)}
        print(f"{name}  score={score:.3f}  {x1 - x0}x{y1 - y0}")

    (out / "boxes.json").write_text(json.dumps(boxes, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
