"""后处理：柔化、降饱和、对比图。

模型输出普遍偏锐，直接用像 CG 渲染；加一点高斯模糊 + 颗粒才有胶片感。
上色版再降饱和并混入黑白，否则会像油画。
"""
from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw


def imread_any(path: Path, flags=cv2.IMREAD_COLOR) -> np.ndarray:
    return cv2.imdecode(np.fromfile(str(path), dtype=np.uint8), flags)


def imwrite_any(path: Path, img: np.ndarray) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ok, buf = cv2.imencode(path.suffix or ".png", img)
    if not ok:
        raise ValueError(f"写不出图片: {path}")
    buf.tofile(str(path))


def soften(gray: np.ndarray, blur: float, contrast: float, grain: float, lift: float) -> np.ndarray:
    x = cv2.GaussianBlur(gray.astype(np.float32), (0, 0), blur)
    if contrast > 0:
        mean = x.mean()
        x = (x - mean) * (1.0 - contrast) + mean
    x = x - lift + np.random.normal(0, grain, x.shape)
    return np.clip(x, 0, 255).astype(np.uint8)


def mute(color: np.ndarray, bw: np.ndarray, saturation: float, mix: float) -> np.ndarray:
    hsv = cv2.cvtColor(color, cv2.COLOR_BGR2HSV).astype(np.float32)
    hsv[:, :, 1] *= saturation
    col = cv2.cvtColor(hsv.astype(np.uint8), cv2.COLOR_HSV2BGR).astype(np.float32)
    gray = cv2.cvtColor(bw if bw.ndim == 2 else cv2.cvtColor(bw, cv2.COLOR_BGR2GRAY),
                        cv2.COLOR_GRAY2BGR).astype(np.float32)
    out = col * (1 - mix) + gray * mix
    out = out * 0.95 + 10 + np.random.normal(0, 1.8, out.shape)
    return np.clip(out, 0, 255).astype(np.uint8)


def cmd_soften(args) -> None:
    src, out = Path(args.src), Path(args.out)
    for p in sorted([*src.glob("*.png"), *src.glob("*.jpg")]):
        gray = imread_any(p, cv2.IMREAD_GRAYSCALE)
        res = soften(gray, args.blur, args.contrast, args.grain, args.lift)
        imwrite_any(out / (p.stem + ".png"), res)
        print(f"{p.name} 柔化完成")


def cmd_mute(args) -> None:
    src, ref, out = Path(args.src), Path(args.reference), Path(args.out)
    for p in sorted([*src.glob("*.png"), *src.glob("*.jpg")]):
        color = imread_any(p)
        ref_p = ref / (p.stem + ".png")
        bw = imread_any(ref_p, cv2.IMREAD_GRAYSCALE) if ref_p.exists() else cv2.cvtColor(color, cv2.COLOR_BGR2GRAY)
        imwrite_any(out / (p.stem + ".png"), mute(color, bw, args.saturation, args.mix))
        print(f"{p.name} 降饱和完成")


def cmd_sheet(args) -> None:
    cols = [Path(p) for p in args.inputs]
    labels = args.labels.split(",") if args.labels else [c.name for c in cols]
    names = sorted(p.name for p in cols[0].glob("*.png"))
    height = args.height
    rows = []
    for name in names:
        tiles = []
        for col in cols:
            p = col / name
            if not p.exists():
                p = col / (Path(name).stem + ".jpg")
            if not p.exists():
                continue
            im = Image.open(p).convert("RGB")
            w = int(im.width * height / im.height)
            tiles.append(im.resize((w, height), Image.LANCZOS))
        if not tiles:
            continue
        width = sum(t.width for t in tiles) + 16 * (len(tiles) - 1)
        row = Image.new("RGB", (width, height + 22), (255, 255, 255))
        d = ImageDraw.Draw(row)
        x = 0
        for tile, label in zip(tiles, labels):
            row.paste(tile, (x, 22))
            d.text((x, 4), label, fill=(0, 0, 0))
            x += tile.width + 16
        rows.append(row)
    if not rows:
        raise SystemExit("没有可用的图片")
    width = max(r.width for r in rows)
    sheet = Image.new("RGB", (width, sum(r.height for r in rows)), (255, 255, 255))
    y = 0
    for r in rows:
        sheet.paste(r, (0, y))
        y += r.height
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(args.out)
    print(f"{args.out}  {sheet.width}x{sheet.height}")


def main() -> None:
    ap = argparse.ArgumentParser(description="柔化 / 降饱和 / 对比图")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s1 = sub.add_parser("soften", help="黑白柔化 + 颗粒")
    s1.add_argument("src")
    s1.add_argument("-o", "--out", required=True)
    s1.add_argument("--blur", type=float, default=1.1)
    s1.add_argument("--contrast", type=float, default=0.03)
    s1.add_argument("--grain", type=float, default=2.2)
    s1.add_argument("--lift", type=float, default=1.0)

    s2 = sub.add_parser("mute", help="彩色降饱和并混入黑白")
    s2.add_argument("src")
    s2.add_argument("reference", help="对应的黑白版目录")
    s2.add_argument("-o", "--out", required=True)
    s2.add_argument("--saturation", type=float, default=0.72)
    s2.add_argument("--mix", type=float, default=0.18)

    s3 = sub.add_parser("sheet", help="拼对比图")
    s3.add_argument("inputs", nargs="+")
    s3.add_argument("-o", "--out", required=True)
    s3.add_argument("--labels", default=None, help="逗号分隔")
    s3.add_argument("--height", type=int, default=360)

    args = ap.parse_args()
    {"soften": cmd_soften, "mute": cmd_mute, "sheet": cmd_sheet}[args.cmd](args)


if __name__ == "__main__":
    main()
