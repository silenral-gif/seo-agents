#!/usr/bin/env python3
"""Read GSC Performance report totals (clicks / impressions / CTR / position).

Do NOT fight the date-picker UI: performance report URLs accept
start_date / end_date query params directly (format YYYYMMDD).

Usage:
  python3 gsc_perf.py --resource https://www.example.com/ \
      --start 20261001 --end 20261031 [--port 9224]

Requirements: gsc_window.py running (logged in), CDP port reachable.
"""
import argparse
import re
import time
import urllib.parse

from playwright.sync_api import sync_playwright

from vevor_sites import add_site_argument, pick_resource


def build_url(resource: str, start: str, end: str) -> str:
    rid = urllib.parse.quote(resource, safe="")
    return (
        "https://search.google.com/search-console/performance/search-analytics"
        f"?resource_id={rid}&start_date={start}&end_date={end}&hl=en"
    )


def main():
    ap = argparse.ArgumentParser()
    add_site_argument(ap)
    ap.add_argument("--start", required=True, help="YYYYMMDD")
    ap.add_argument("--end", required=True, help="YYYYMMDD")
    ap.add_argument("--port", type=int, default=9224)
    args = ap.parse_args()

    resource = pick_resource(args)
    url = build_url(resource, args.start, args.end)
    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{args.port}")
        ctx = b.contexts[0]
        pg = ctx.new_page()
        pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(12)  # let the report finish loading
        pg.bring_to_front()

        t = pg.evaluate("() => document.body.innerText")
        # chart description contains the actual applied date range; use it to verify
        cidx = t.find("Chart, containing counts")
        chart = t[cidx:cidx + 150].replace("\n", " ") if cidx > -1 else "(chart desc not found)"

        def grab(pattern):
            m = re.search(pattern, t)
            return m.group(1) if m else "not found"

        print("PROPERTY:", resource)
        print("RANGE:", args.start, "->", args.end)
        print("CHART_DESC:", chart)
        print("TOTAL_CLICKS:", grab(r"Total clicks\s*\n?\s*([\d,.]+[KkMm]?)"))
        print("TOTAL_IMPRESSIONS:", grab(r"Total impressions\s*\n?\s*([\d,.]+[KkMm]?)"))
        print("AVG_CTR:", grab(r"Average CTR\s*\n?\s*([\d.]+%)"))
        print("AVG_POSITION:", grab(r"Average position\s*\n?\s*([\d.]+)"))
        b.close()


if __name__ == "__main__":
    main()
