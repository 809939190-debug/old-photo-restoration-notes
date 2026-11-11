"""火山方舟 Seedream 图生图客户端。

用法：
    export ARK_API_KEY=...
    python src/seedream.py restore up_all/ -o restored/ --model pro
    python src/seedream.py color restored/ -o colored/

设计要点：
- 幂等：目标文件已存在就跳过，中断后重跑不会重复计费。
- 提示词把"保留五官/嘴型/脸型"写死，这是保真的关键。
- 默认 2K 输出，逐张串行（并发容易被限流）。
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import time
from pathlib import Path

import requests

ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/images/generations"

MODELS = {
    "pro": "doubao-seedream-5-0-pro-260628",
    "flash": "doubao-seedream-5-0-flash-260915",
}

RESTORE_PROMPT = (
    "修复这张老照片：清除纸面的霉斑、水渍与划痕，去掉四周波浪花边纸框。"
    "严格保留人物原有的五官相貌、脸型、嘴型与眉眼，不得美化、不得改变长相，"
    "不要添加原图没有的物品或装饰。"
)

COLOR_PROMPT = (
    "给这张黑白老照片上色：克制的年代色彩，肤色自然偏暖，不浓艳；"
    "衣服与背景的颜色符合上世纪五六十年代。保留老照片的朦胧感与颗粒。"
    "人物五官、嘴型、构图完全不变，不要重绘面部，不要添加或删除任何物品和文字。"
)


def encode(path: Path) -> str:
    data = base64.b64encode(path.read_bytes()).decode()
    mime = "image/png" if path.suffix.lower() == ".png" else "image/jpeg"
    return f"data:{mime};base64,{data}"


def generate(api_key: str, model: str, prompt: str, image: Path, size: str = "2K",
             retries: int = 3, timeout: int = 300) -> bytes:
    payload = {
        "model": model,
        "prompt": prompt,
        "image": [encode(image)],
        "response_format": "url",
        "size": size,
        "watermark": False,
    }
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            resp = requests.post(ENDPOINT, headers=headers, json=payload, timeout=timeout)
            if resp.status_code != 200:
                last_err = f"HTTP {resp.status_code}: {resp.text[:200]}"
                time.sleep(2 * attempt)
                continue
            url = resp.json()["data"][0]["url"]
            img = requests.get(url, timeout=timeout)
            img.raise_for_status()
            return img.content
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
            time.sleep(2 * attempt)
    raise RuntimeError(f"{image.name} 生成失败: {last_err}")


def run(src: Path, out: Path, model: str, prompt: str, size: str) -> None:
    key = os.environ.get("ARK_API_KEY")
    if not key:
        raise SystemExit("请先设置环境变量 ARK_API_KEY")
    out.mkdir(parents=True, exist_ok=True)
    files = sorted([*src.glob("*.png"), *src.glob("*.jpg")])
    for i, p in enumerate(files, 1):
        dst = out / (p.stem + ".jpg")
        if dst.exists():
            print(f"[{i}/{len(files)}] {p.name} 已存在，跳过")
            continue
        t0 = time.time()
        data = generate(key, MODELS[model], prompt, p, size)
        dst.write_bytes(data)
        print(f"[{i}/{len(files)}] {p.name} -> {dst.name}  {len(data) // 1024}KB  {time.time() - t0:.0f}s")


def main() -> None:
    ap = argparse.ArgumentParser(description="Seedream 图生图批处理")
    sub = ap.add_subparsers(dest="cmd", required=True)

    for name, helptext in (("restore", "清污 + 去花边（黑白）"), ("color", "黑白上色")):
        sp = sub.add_parser(name, help=helptext)
        sp.add_argument("src")
        sp.add_argument("-o", "--out", required=True)
        sp.add_argument("--model", choices=list(MODELS), default="pro")
        sp.add_argument("--size", default="2K")
        sp.add_argument("--prompt", default=None, help="覆盖内置提示词")

    args = ap.parse_args()
    default_prompt = RESTORE_PROMPT if args.cmd == "restore" else COLOR_PROMPT
    run(Path(args.src), Path(args.out), args.model, args.prompt or default_prompt, args.size)


if __name__ == "__main__":
    main()
