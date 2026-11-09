#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
verify_pdf.py —— PDF 交叉验证兜底：给定 SKU + 一个数字/事实，判断它在说明书 PDF 里有无旁证。

动机：
  商详页（HTML）是面向买家的、经运营维护的规格源，通常比通用说明书更贴近当前
  SKU 实际。但 HTML 里的数字也可能写错。本脚本提供「到说明书 PDF 里搜一搜」的
  兜底：把一个存疑的数字/关键词，在该 SKU 的说明书全文里做检索，返回命中情况，
  供 AI 一审时判断「有旁证 / 无旁证 / PDF 缺失」。

  注意：VEVOR 说明书一个 PDF 常覆盖多个型号，命中只能说明「该数字在说明书里出现」，
  不能证明它一定属于当前 SKU 的型号——这是旁证，不是铁证。

用法：
  python3 verify_pdf.py <SKU> --needle "24V" [--needle "500W"] [--pdf-dir DIR]

  例：
  python3 verify_pdf.py 010100045763 --needle "24V"
  python3 verify_pdf.py 010100045763 --needle "24V" --needle "500W" --needle "30 lbs"

输出：
  对每个 needle，报告：命中 / 未命中，命中时列出页码与上下文片段（前后 ~40 字符）。
  若该 SKU 无 PDF，明确输出「无 PDF（约 16% SKU 无说明书，仅 HTML 单源）」。
"""
import sys, os, re, glob, argparse

try:
    from pypdf import PdfReader
except ImportError:
    from PyPDF2 import PdfReader

PDF_DIR = "/Users/lixin/Documents/GEO/data/manual-pdfs-2026-11-06/pdfs"
CTX = 40  # 命中上下文前后字符数


def find_pdfs(sku, pdf_dir):
    return sorted(glob.glob(os.path.join(pdf_dir, f"{sku}__*.pdf")))


def pdf_pages(pdf_path):
    reader = PdfReader(pdf_path)
    pages = []
    for p in reader.pages:
        try:
            t = (p.extract_text() or "")
        except Exception:
            t = ""
        pages.append(re.sub(r"[ \t]+", " ", t))
    return pages


def search_needle(pages, needle):
    """返回 [(页码, 上下文片段), ...]"""
    hits = []
    # 归一化 needle：数字里常见全角/单位差异，宽松匹配
    pat = re.compile(re.escape(needle), re.I)
    for i, t in enumerate(pages, 1):
        for m in pat.finditer(t):
            s = max(0, m.start() - CTX)
            e = min(len(t), m.end() + CTX)
            ctx = t[s:e].strip()
            hits.append((i, ctx))
    return hits


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("sku")
    ap.add_argument("--needle", action="append", required=True,
                    help="要验证的数字/关键词，可多次传入")
    ap.add_argument("--pdf-dir", default=PDF_DIR)
    args = ap.parse_args()

    pdfs = find_pdfs(args.sku, args.pdf_dir)
    if not pdfs:
        print(f"[无PDF] SKU {args.sku} 无说明书（约 16% SKU 无 PDF，仅 HTML 单源）")
        sys.exit(0)

    print(f"SKU {args.sku} → {len(pdfs)} 个 PDF：{', '.join(os.path.basename(p) for p in pdfs)}")
    print("=" * 70)

    for pdf in pdfs:
        pages = pdf_pages(pdf)
        print(f"\n[{os.path.basename(pdf)}]")
        for needle in args.needle:
            hits = search_needle(pages, needle)
            if hits:
                print(f"  ✓ 命中 '{needle}'：{len(hits)} 处")
                for pg, ctx in hits[:5]:
                    print(f"      P{pg}: …{ctx}…")
                if len(hits) > 5:
                    print(f"      （其余 {len(hits)-5} 处略）")
            else:
                print(f"  ✗ 未命中 '{needle}'（说明书里无此数字/关键词）")


if __name__ == "__main__":
    main()
