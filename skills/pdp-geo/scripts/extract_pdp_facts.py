#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
extract_pdp_facts.py —— 把 VEVOR 商详页抽成「干净事实」，供 AI 生成 About-this-Item 五类文本。

目的（配合 GEO 工作流）：
  1. 省点数/token：只把「标题 + 规格 + Features + 评价 + 价格 + JSON-LD」喂给 AI，
     而不是贴整页 HTML（几十万字符）。
  2. 防幻觉：事实源干净、可对账，AI 每句都能追溯回这份 JSON 的哪一行。

用法：
  python3 extract_pdp_facts.py <URL> [--out DIR]

  例：
  python3 extract_pdp_facts.py "https://www.vevor.com.au/.../p_010739664790"
  python3 extract_pdp_facts.py "https://www.vevor.com/.../p_010473451978" --out /tmp/facts

输出：
  <out>/<websku>.json   结构化事实（机器读）
  <out>/<websku>.md     干净事实清单（人读 / 直接粘给 AI）
  并在终端打印 md 全文。
"""
import re, sys, json, html, pathlib, subprocess, argparse

UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36")


def fetch(url):
    out = subprocess.run(
        ["curl", "-sL", "-A", UA, "-H", "Accept-Language: en,en-US;q=0.9",
         "--max-time", "40", url],
        capture_output=True)
    if out.returncode != 0 or not out.stdout:
        raise RuntimeError(f"fetch failed: {out.stderr.decode()[:200]}")
    return out.stdout.decode("utf-8", "ignore")


def clean(t):
    t = re.sub(r"<script[\s\S]*?</script>", " ", t, flags=re.I)
    t = re.sub(r"<style[\s\S]*?</style>", " ", t, flags=re.I)
    t = re.sub(r"<[^>]+>", " ", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r"\n\s*\n+", "\n", t)
    return t.strip()


def extract(raw):
    text = clean(raw)

    title = re.search(r"<title>(.*?)</title>", raw, re.I | re.S)
    title = re.sub(r"\s+", " ", title.group(1)).strip() if title else ""

    meta_desc = re.search(r'<meta name="description" content="(.*?)"', raw, re.I | re.S)
    meta_desc = html.unescape(meta_desc.group(1)).strip() if meta_desc else ""

    # 规格键值对（两种常见结构）
    specs = {}
    for m in re.finditer(r'DM_PS-item">\s*<span class="DM_PS-label">([^<]+)</span>\s*<span class="DM_PS-value">([^<]*)</span>', raw):
        specs[m.group(1).strip()] = html.unescape(m.group(2)).strip()
    for m in re.finditer(r'<dt>([^<]+)</dt>\s*<dd>([^<]*)</dd>', raw):
        k = m.group(1).strip()
        if k not in specs:
            specs[k] = html.unescape(m.group(2)).strip()

    # Features & Details 正文
    feats = ""
    i = text.find("Features & Details")
    if i >= 0:
        seg = text[i + len("Features & Details"):]
        cut = seg.find("Product specification")
        feats = (seg[:cut] if cut >= 0 else seg[:1500]).strip()

    # 评价：优先取 JSON-LD 里的 review，其次取 window.REVIEWS_DATA
    reviews = []
    for m in re.finditer(r'<script[^>]*application/ld\+json[^>]*>(.*?)</script>', raw, re.S):
        try:
            blob = json.loads(m.group(1))
        except Exception:
            continue
        def walk(o):
            if isinstance(o, dict):
                if o.get("@type") == "Product":
                    rv = o.get("review")
                    if isinstance(rv, list):
                        for r in rv:
                            reviews.append({
                                "body": (r.get("reviewBody") or "").strip(),
                                "rating": r.get("reviewRating", {}).get("ratingValue", "")
                                if isinstance(r.get("reviewRating"), dict) else "",
                            })
                for v in o.values():
                    walk(v)
            elif isinstance(o, list):
                for v in o:
                    walk(v)
        walk(blob)
    if not reviews:
        m = re.search(r'"allReview"\s*:\s*\[', raw)
        if m:
            seg = raw[m.start():]
            dec = json.JSONDecoder()
            arr, _ = dec.raw_decode(seg[seg.find("["):])
            for r in arr:
                reviews.append({"body": (r.get("content") or "").strip(),
                                "rating": r.get("rate_overall", "")})

    # 价格 / SKU / 评分 / 品牌
    price = re.search(r'"price"\s*:\s*([0-9.]+)', raw)
    price = price.group(1) if price else ""
    sku = re.search(r'"sku"\s*:\s*"([^"]+)"', raw)
    sku = sku.group(1) if sku else ""
    rating = re.search(r'"ratingValue"\s*:\s*"([0-9.]+)"', raw)
    rating = rating.group(1) if rating else ""
    rc = re.search(r'"reviewCount"\s*:\s*([0-9]+)', raw)
    rc = rc.group(1) if rc else ""

    return {
        "url": "",  # 由调用方回填
        "websku": "",  # 由调用方从 url 提取
        "title": title,
        "meta_description": meta_desc,
        "specs": specs,
        "features": feats,
        "reviews": reviews,
        "price": price,
        "sku": sku,
        "rating": rating,
        "review_count": rc,
    }


def to_md(d):
    L = []
    L.append(f"# {d['title']}")
    L.append("")
    if d["price"]:
        L.append(f"- Price: ${d['price']}")
    if d["rating"]:
        L.append(f"- Rating: {d['rating']}/5 ({d['review_count']} reviews)")
    if d["sku"]:
        L.append(f"- SKU: {d['sku']}")
    L.append("")
    if d["specs"]:
        L.append("## Specifications")
        for k, v in d["specs"].items():
            if v:
                L.append(f"- {k}: {v}")
        L.append("")
    if d["features"]:
        L.append("## Features & Details")
        L.append(d["features"])
        L.append("")
    if d["reviews"]:
        L.append("## Reviews (verbatim)")
        for r in d["reviews"]:
            star = f" [{r['rating']}★]" if r["rating"] else ""
            L.append(f"-{star} {r['body']}")
        L.append("")
    if d["meta_description"]:
        L.append("## Meta Description")
        L.append(d["meta_description"])
        L.append("")
    return "\n".join(L).strip() + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("url")
    ap.add_argument("--out", default="/Users/lixin/Documents/GEO/data/pdp-facts")
    args = ap.parse_args()

    raw = fetch(args.url)
    d = extract(raw)
    m = re.search(r"-p_(\d+)", args.url)
    websku = m.group(1) if m else re.search(r"([A-Z0-9]{18,})", raw).group(1)
    d["url"] = args.url
    d["websku"] = websku

    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)
    (outdir / f"{websku}.json").write_text(
        json.dumps(d, ensure_ascii=False, indent=1), "utf-8")
    (outdir / f"{websku}.md").write_text(to_md(d), "utf-8")

    print(to_md(d))
    print(f"\n[已保存] {outdir}/{websku}.json  ·  {outdir}/{websku}.md")


if __name__ == "__main__":
    main()
