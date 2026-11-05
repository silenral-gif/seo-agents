#!/usr/bin/env python3
"""Request (re)indexing of a single URL via GSC URL inspection.

Flow: open property page -> paste URL into the inspect box -> click
REQUEST INDEXING -> wait for the live test (1-2 min) -> click the
confirm REQUEST INDEXING -> wait for "Indexing requested".

CRITICAL:
- Do NOT use the /search-console/inspect?...&id=<full-url> deep link; it 404s.
- Do NOT close the tab while the live test runs (cancels the test).
- GSC limits request-indexing to roughly 10-12 URLs per day per account.

Usage:
  python3 gsc_request_index.py --resource https://www.example.com/blog/ \
      --url https://www.example.com/blog/some-post/ [--port 9224] [--timeout 480]
"""
import argparse
import time
import urllib.parse

from playwright.sync_api import sync_playwright

from vevor_sites import add_site_argument, pick_resource

# Shadow-DOM piercing click: GSC renders its components inside shadow roots.
CLICK_REQUEST_INDEXING = """() => {
    let target = null;
    const walk = (root, depth) => {
        if (depth > 20 || target) return;
        for (const el of root.querySelectorAll('*')) {
            if (el.tagName === 'IFRAME') { try { walk(el.contentDocument, depth+1); } catch(e) {} continue; }
            if (!target) {
                const role = el.getAttribute('role') || (el.tagName === 'BUTTON' ? 'button' : '');
                const t = (el.innerText || '').toLowerCase().trim();
                if (role === 'button' && t === 'request indexing') { target = el; return; }
            }
            if (el.shadowRoot) walk(el.shadowRoot, depth+1);
        }
    };
    walk(document, 0);
    if (!target) return false;
    target.scrollIntoView({block:'center'});
    target.click();
    return true;
}"""

# Look for a role=button "request indexing" plus a status marker in page text.
STATUS = """() => {
    let btn = null;
    const walk = (root, depth) => {
        if (depth > 20) return;
        for (const el of root.querySelectorAll('*')) {
            if (el.tagName === 'IFRAME') { try { walk(el.contentDocument, depth+1); } catch(e) {} continue; }
            if (!btn) {
                const role = el.getAttribute('role') || (el.tagName === 'BUTTON' ? 'button' : '');
                const t = (el.innerText || '').toLowerCase().trim();
                if (role === 'button' && t === 'request indexing') { btn = t; return; }
            }
            if (el.shadowRoot) walk(el.shadowRoot, depth+1);
        }
    };
    walk(document, 0);
    const body = document.body.innerText.toLowerCase();
    let status = 'unknown';
    if (body.includes('indexing requested') || body.includes('indexing was requested')) status = 'CONFIRMED';
    else if (body.includes('testing if live url can be indexed')) status = 'LIVE_TEST_RUNNING';
    else if (body.includes('live test')) status = 'LIVE_TEST_DONE';
    else if (body.includes('url is on google')) status = 'ON_GOOGLE_PENDING_REQUEST';
    return {reqBtn: btn, status, bodySnippet: body.slice(0, 400)};
}"""


def main():
    ap = argparse.ArgumentParser()
    add_site_argument(ap)
    ap.add_argument("--url", required=True, help="target URL to request indexing for")
    ap.add_argument("--port", type=int, default=9224)
    ap.add_argument("--timeout", type=int, default=480, help="max seconds to wait for the flow")
    args = ap.parse_args()

    rid = urllib.parse.quote(pick_resource(args), safe="")
    overview = f"https://search.google.com/search-console?resource_id={rid}&hl=en"

    with sync_playwright() as p:
        b = p.chromium.connect_over_cdp(f"http://127.0.0.1:{args.port}")
        ctx = b.contexts[0]
        pg = ctx.new_page()
        pg.goto(overview, wait_until="domcontentloaded", timeout=60000)
        time.sleep(12)

        # 1) paste URL into the inspection box (aria-label starts with "Inspect any URL")
        box = pg.locator('input[aria-label^="Inspect any URL"]').first
        box.click()
        box.fill(args.url)
        time.sleep(1)
        box.press("Enter")
        print("INSPECT_SUBMITTED")
        time.sleep(20)  # inspection panel takes ~15-25s

        # 2) first REQUEST INDEXING click (triggers live test)
        print("CLICK_REQUEST_INDEXING:", pg.evaluate(CLICK_REQUEST_INDEXING))

        # 3) poll: wait for live test to finish, then click the confirm button
        confirmed = False
        confirm_clicked = False
        start = time.time()
        while time.time() - start < args.timeout:
            time.sleep(10)
            st = pg.evaluate(STATUS)
            print("[%03ds] status=%s reqBtn=%s" % (time.time() - start, st["status"], st["reqBtn"]))
            if st["status"] == "CONFIRMED":
                confirmed = True
                break
            if st["reqBtn"] and st["status"] != "LIVE_TEST_RUNNING" and not confirm_clicked:
                print(">>> clicking confirm REQUEST INDEXING")
                confirm_clicked = pg.evaluate(CLICK_REQUEST_INDEXING)
                time.sleep(6)

        print("RESULT:", "INDEXING_REQUESTED" if confirmed else "NOT_CONFIRMED_CHECK_WINDOW")
        # Leave the tab open for manual verification / screenshot.
        b.close()


if __name__ == "__main__":
    main()
