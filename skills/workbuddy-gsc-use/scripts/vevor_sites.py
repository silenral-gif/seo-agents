#!/usr/bin/env python3
"""VEVOR 站点 -> GSC resource_id 对照表。

所有同事负责的都是 VEVOR 站点，脚本统一支持 --site <key> 快捷参数，
不用手拼 resource_id。

- resource 均按 URL-prefix property 形式书写（https:// 开头、/ 结尾）。
- status 含义（2026-11-05 全部在 GSC 账号实测过一轮）：
    confirmed  已验证为 URL-prefix property，可直接用
    unverified 账号里没查到该形式的 property，可能未注册或注册为
               Domain property；用 --resource "sc-domain:vevor.es" 试
"""

SITES = {
    # ---- 主站 / 内容站（2026-11-05 GSC 实测确认）----
    "www":       {"resource": "https://www.vevor.com/",            "desc": "英文主站（美国/全球）", "status": "confirmed"},
    "eur":       {"resource": "https://eur.vevor.com/",            "desc": "欧洲专区分站",           "status": "confirmed"},
    "diy-ideas": {"resource": "https://www.vevor.com/diy-ideas/",  "desc": "DIY 内容子站（独立 property）", "status": "confirmed"},
    # ---- 国家站（2026-11-05 实测为有效 URL-prefix property）----
    "ca":        {"resource": "https://www.vevor.ca/",             "desc": "加拿大（英语）",   "status": "confirmed"},
    "uk":        {"resource": "https://www.vevor.co.uk/",          "desc": "英国（英语）",     "status": "confirmed"},
    "au":        {"resource": "https://www.vevor.com.au/",         "desc": "澳大利亚（英语）", "status": "confirmed"},
    "de":        {"resource": "https://www.vevor.de/",             "desc": "德国（德语）",     "status": "confirmed"},
    "fr":        {"resource": "https://www.vevor.fr/",             "desc": "法国（法语）",     "status": "confirmed"},
    "it":        {"resource": "https://www.vevor.it/",             "desc": "意大利（意语）",   "status": "confirmed"},
    "mx":        {"resource": "https://www.vevor.mx/",             "desc": "墨西哥（西语）",   "status": "confirmed"},
    "pl":        {"resource": "https://www.vevor.pl/",             "desc": "波兰（波兰语）",   "status": "confirmed"},
    # ---- 账号里没查到 URL-prefix 形式，需人工核实 ----
    "es":        {"resource": "https://www.vevor.es/",             "desc": "西班牙（西语）",   "status": "unverified"},
    "nl":        {"resource": "https://www.vevor.nl/",             "desc": "荷兰（荷语）",     "status": "unverified"},
}


def resolve_site(key: str) -> str:
    if key not in SITES:
        valid = ", ".join(sorted(SITES))
        raise SystemExit(f"unknown --site '{key}'. valid keys: {valid}")
    return SITES[key]["resource"]


def add_site_argument(ap):
    """Register --site / --resource on an argparse parser (resource is optional)."""
    group = ap.add_mutually_exclusive_group(required=True)
    group.add_argument("--site", choices=sorted(SITES),
                       help="VEVOR site shortcut, e.g. www / eur / diy-ideas / de")
    group.add_argument("--resource", help="explicit GSC property (URL prefix or sc-domain:...)")
    return ap


def pick_resource(args) -> str:
    if getattr(args, "site", None):
        return resolve_site(args.site)
    return args.resource
