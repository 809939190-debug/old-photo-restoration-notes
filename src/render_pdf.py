"""PDF → 高分辨率页面图。"""
from __future__ import annotations

import argparse
from pathlib import Path

import pypdfium2 as pdfium


def render(pdf_path: Path, out_path: Path, dpi: int = 300, page: int = 0) -> Path:
    doc = pdfium.PdfDocument(str(pdf_path))
    pg = doc[page]
    scale = dpi / 72.0
    bitmap = pg.render(scale=scale).to_pil()
    out_path.parent.mkdir(parents=True, exist_ok=True)
    bitmap.save(out_path)
    print(f"{out_path}  {bitmap.width}x{bitmap.height}")
    return out_path


def main() -> None:
    ap = argparse.ArgumentParser(description="把 PDF 每页渲染成图片")
    ap.add_argument("pdf")
    ap.add_argument("-o", "--out", default="work/page.png")
    ap.add_argument("--dpi", type=int, default=300)
    ap.add_argument("--page", type=int, default=0)
    args = ap.parse_args()
    render(Path(args.pdf), Path(args.out), args.dpi, args.page)


if __name__ == "__main__":
    main()
