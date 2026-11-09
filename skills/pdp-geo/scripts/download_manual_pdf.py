#!/usr/bin/env python3
"""
下载 VEVOR 商详页的说明书/手册 PDF。

原理：
  VEVOR 商详页里「User manual-en (PDF)」的链接是
  <a href="/pages/contact-us/<MPN>">，真正的 PDF 文件地址不在静态 HTML 里，
  而是通过 contact-us 页面动态输出，形如：
    https://mdm-goods.vevor.net/mdm-goods-service-prod/<文件名>.pdf
  文件名含中文/全角字符和时间戳后缀，无法用 SKU 直接拼出。

用法：
  # 单个 SKU（mpn 可省略，脚本会从本地 HTML 或页面自动取）
  python3 download_manual_pdf.py --sku 010693825584

  # 从本地 HTML 批量（读 manifest.jsonl 的 sku+url，逐一下载）
  python3 download_manual_pdf.py --manifest /path/to/manifest.jsonl --out <outdir>

  # 已知 mpn 直接下
  python3 download_manual_pdf.py --mpn ZYZZFXDPBCTKTZCEC001V0

依赖：仅标准库（urllib）。
"""

import argparse
import os
import re
import ssl
import urllib.request

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 Chrome/120 Safari/537.36"
BASE = "https://www.vevor.com"
CTX = ssl.create_default_context()


def http_get(url, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=timeout, context=CTX) as r:
        return r.read().decode("utf-8", errors="ignore")


def get_mpn_from_page(sku_or_url):
    """从商详页 URL 或本地 HTML 拿 mpn。"""
    url = sku_or_url
    if not url.startswith("http"):
        url = f"https://www.vevor.com/p/{sku_or_url}"  # 占位，实际依赖下方 mpn 提取
    html = http_get(url)
    # mpn 形如 15-20 位大写字母数字
    m = re.search(r'"(?:sku|mpn)"\s*:\s*"([A-Z0-9]{15,})"', html)
    return m.group(1) if m else None


def get_pdf_filename(mpn):
    """访问 contact-us 页，抓 PDF 真实文件名。"""
    page = http_get(f"{BASE}/pages/contact-us/{mpn}")
    # 匹配 md m-goods.vevor.net ... .pdf（文件名可能含中文/编码）
    m = re.search(r'(mdm-goods\.vevor\.net/[^\s"\'<>]+?\.pdf)', page)
    if not m:
        # 页面里可能是转义后的 \\/ 形式
        m = re.search(r'(mdm-goods\\?\.vevor\\?\.net[^\s"\'<>]+?\.pdf)', page)
    if not m:
        return None
    path = m.group(1).replace("\\/", "/").replace("\\", "")
    return "https://" + path


def download(pdf_url, outdir, outname=None):
    os.makedirs(outdir, exist_ok=True)
    if outname is None:
        outname = pdf_url.rsplit("/", 1)[-1]
    outpath = os.path.join(outdir, outname)
    req = urllib.request.Request(pdf_url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=120, context=CTX) as r:
        data = r.read()
        ct = r.headers.get("Content-Type", "")
    with open(outpath, "wb") as fp:
        fp.write(data)
    return outpath, len(data), ct


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sku", help="商品 SKU（websku，如 010693825584）")
    ap.add_argument("--mpn", help="商品 MPN（如 ZYZZFXDPBCTKTZCEC001V0）")
    ap.add_argument("--manifest", help="manifest.jsonl 路径，批量模式")
    ap.add_argument("--out", default=".", help="输出目录")
    args = ap.parse_args()

    if args.manifest:
        with open(args.manifest, encoding="utf-8") as f:
            lines = [l for l in f if l.strip()]
        for line in lines:
            import json
            rec = json.loads(line)
            sku = rec.get("sku")
            url = rec.get("url", "")
            mpn = get_mpn_from_page(url) if url else None
            if not mpn:
                print(f"[SKIP] {sku}: 未取到 mpn")
                continue
            pdf = get_pdf_filename(mpn)
            if not pdf:
                print(f"[SKIP] {sku}: contact-us 页无 PDF")
                continue
            try:
                outpath, size, ct = download(pdf, args.out)
                print(f"[OK] {sku} -> {outpath} ({size} bytes, {ct})")
            except Exception as e:
                print(f"[ERR] {sku}: {e}")
        return

    mpn = args.mpn
    if not mpn:
        if not args.sku:
            print("需提供 --sku 或 --mpn")
            return
        mpn = get_mpn_from_page(args.sku)

    if not mpn:
        print("未能解析 mpn")
        return

    pdf = get_pdf_filename(mpn)
    if not pdf:
        print(f"contact-us 页未找到 PDF（mpn={mpn}）")
        return
    outpath, size, ct = download(pdf, args.out)
    print(f"[OK] {mpn} -> {outpath} ({size} bytes, {ct})")


if __name__ == "__main__":
    main()
