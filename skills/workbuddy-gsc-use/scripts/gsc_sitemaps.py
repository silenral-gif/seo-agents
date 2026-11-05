#!/usr/bin/env python3
"""GSC Sitemaps page: list submitted sitemaps, optionally submit one.

Usage:
  # probe only (list sitemaps + status + discovered pages)
  python3 gsc_sitemaps.py --resource https://www.example.com/ [--port 9224]

  # submit (resubmit) a sitemap
  python3 gsc_sitemaps.py --resource https://www.example.com/ --submit sitemap/sitemap-index.xml
"""
import argparse
import time
import urllib.parse

from playwright.sync_api import sync_playwright

from vevor_sites import add_site_argument, pick_resource


def page_url(resource: str) -> str:
    rid = urllib.parse.quote(resource, safe="")
    return f"https://search.google.com/search-console/sitemaps?resource_id={rid}&hl=en"


def main():
    ap = argparse.ArgumentParser()
    add_site_argument(ap)
    ap.add_argument("--submit", default=None, help="sitemap path, e.g. sitemap/sitemap-index.xml")
    ap.add_argument("--port", type=int, default=9224)
    args = ap.parse_args()

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{args.port}")
        ctx = b.contexts[0]
        pg = ctx.new_page()
        pg.goto(page_url(pick_resource(args)), wait_until="load", timeout=60000)
        pg.wait_for_timeout(9000)

        if args.submit:
            box = pg.locator("input[aria-label='Enter sitemap URL']")
            box.fill(args.submit)
            pg.wait_for_timeout(500)
            print("FILLED:", box.input_value())
            # SUBMIT button lives in light DOM; plain query is enough
            ok = pg.evaluate(
                """() => {
                    const el = [...document.querySelectorAll('button,[role=button]')]
                        .find(e => (e.textContent||'').trim().toUpperCase() === 'SUBMIT');
                    if (el) { el.click(); return true; }
                    return false;
                }"""
            )
            print("SUBMIT_CLICKED:", ok)
            pg.wait_for_timeout(6000)
            # list refreshes; Submitted date becomes today on success
            t = pg.evaluate("() => document.body.innerText")
            low = t.lower()
            for kw in ["success", "error", "could not"]:
                i = low.find(kw)
                if i > -1:
                    print("CONFIRM:", t[max(0, i - 80):i + 120].replace("\n", " | "))
                    break

        idx = pg.evaluate("() => document.body.innerText").find("Submitted sitemaps")
        t = pg.evaluate("() => document.body.innerText")
        print("---- SITEMAP LIST ----")
        print(t[idx:idx + 1500] if idx > -1 else t[:1500])
        b.close()


if __name__ == "__main__":
    main()
