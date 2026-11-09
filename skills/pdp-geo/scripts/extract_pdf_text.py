#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_pdf_text.py —— 把 VEVOR 说明书/手册 PDF 抽成纯文本（带页码），供数字/事实交叉验证。

背景：
  VEVOR 说明书 PDF 是矢量文本层（非扫描件），字符层面提取准确率接近 100%，
  不存在 OCR 识别错误。但说明书结构高度不统一：有的有「TECHNICAL DATA /
  PARAMETERS」章节，有的完全没有；且一个 PDF 常覆盖多个型号（如
  MODEL:2527/2528/2529/2530），无法可靠地自动对应到单个 SKU。

  因此本脚本不做「自动抽规格表」这种脆弱操作，只做「全文抽文本」，
  供 verify_pdf.py 做检索式交叉验证（HTML 里某数字存疑时，到 PDF 搜有无旁证）。

用法：
  python3 extract_pdf_text.py <pdf路径> [--out DIR]

  例：
  python3 extract_pdf_text.py /Users/lixin/Documents/GEO/data/manual-pdfs-2026-11-06/pdfs/010100045763__1.pdf
  python3 extract_pdf_text.py 010100045763 --pdf-dir /Users/lixin/Documents/GEO/data/manual-pdfs-2026-11-06/pdfs

输出：
  <out>/<sku>__<序号>.txt   —— 每页一行「[P页码] 文本」，供 grep/检索
  并在终端打印前若干字符预览。

依赖：pypdf（pip install pypdf；旧版为 PyPDF2）
"""
import sys, re, os, glob, argparse, pathlib

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader


PDF_DIR = "/Users/lixin/Documents/GEO/data/manual-pdfs-2026-11-06/pdfs"


def extract_text(pdf_path):
    """返回 list[str]，第 i 项为第 i+1 页的纯文本（无文本页为空串）。"""
    reader = PdfReader(pdf_path)
    pages = []
    for p in reader.pages:
        try:
            t = (p.extract_text() or "")
        except Exception:
            t = ""
        # 归一化：合并空白，但保留换行便于定位
        t = re.sub(r"[ \t]+", " ", t)
        pages.append(t)
    return pages


def to_text(pages):
    out = []
    for i, t in enumerate(pages, 1):
        if t.strip():
            out.append(f"[P{i}] {t}")
    return "\n".join(out)


def resolve_pdf(sku_or_path, pdf_dir=PDF_DIR):
    """支持传完整路径，或传 SKU（自动按 <sku>__*.pdf 前缀定位，可能多个）。"""
    p = pathlib.Path(sku_or_path)
    if p.exists() and p.suffix.lower() == ".pdf":
        return [str(p)]
    prefix = sku_or_path
    hits = sorted(glob.glob(os.path.join(pdf_dir, f"{prefix}__*.pdf")))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="PDF 路径，或 SKU（自动按 <sku>__*.pdf 定位）")
    ap.add_argument("--pdf-dir", default=PDF_DIR)
    ap.add_argument("--out", default=None, help="输出目录，默认与 PDF 同目录")
    args = ap.parse_args()

    pdfs = resolve_pdf(args.target, args.pdf_dir)
    if not pdfs:
        print(f"[未找到] 无 PDF 匹配：{args.target}", file=sys.stderr)
        sys.exit(1)

    for pdf in pdfs:
        pages = extract_text(pdf)
        txt = to_text(pages)
        n_text = sum(1 for t in pages if t.strip())
        base = os.path.basename(pdf)
        sku = base.split("__")[0]
        outdir = pathlib.Path(args.out) if args.out else pathlib.Path(pdf).parent
        outpath = outdir / f"{sku}__{base.split('__')[1].split('.')[0]}.txt"
        outpath.write_text(txt, "utf-8")
        total_chars = sum(len(t) for t in pages)
        print(f"[OK] {base} → {outpath}")
        print(f"     页数={len(pages)} 有文本页={n_text} 总字符={total_chars}")
        # 预览前 300 字符
        preview = txt[:300].replace("\n", " ")
        print(f"     预览: {preview}")


if __name__ == "__main__":
    main()
