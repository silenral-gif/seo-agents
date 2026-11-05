#!/usr/bin/env python3
"""Launch a persistent, visible Chromium window dedicated to Google Search Console.

- Uses Playwright's bundled Chromium (do NOT use the system Chrome binary; it
  crashes with GPU/sandbox errors in this environment).
- Persistent user profile: the Google login survives restarts.
- Opens a CDP remote-debugging port so other scripts can take over the window.

Usage:
  python3 gsc_window.py [--port 9224] [--profile-dir /path/to/profile]

Keep it running in the background (it blocks while the window is open).
"""
import argparse
import pathlib
import time

from playwright.sync_api import sync_playwright

GSC_URL = "https://search.google.com/search-console"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=9224)
    ap.add_argument("--profile-dir", default=str(pathlib.Path.home() / ".workbuddy-gsc-profile"))
    args = ap.parse_args()

    profile = pathlib.Path(args.profile_dir)
    profile.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(profile),
            headless=False,
            args=[
                "--no-sandbox",
                "--disable-gpu",
                "--disable-dev-shm-usage",
                f"--remote-debugging-port={args.port}",
                # reduce automation fingerprint so Google login is accepted
                "--disable-blink-features=AutomationControlled",
            ],
        )
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.goto(GSC_URL, wait_until="load", timeout=60000)
        print("GSC_WINDOW_OPEN", pg.title(), "|", pg.url, flush=True)
        print(f"CDP_PORT={args.port}", flush=True)
        print("If not logged in, log in manually in this window now.", flush=True)
        # Keep the window alive until the user closes it.
        try:
            while not pg.is_closed():
                time.sleep(1)
        except Exception as e:
            print("wait end:", e, flush=True)
        print("BROWSER_CLOSED", flush=True)


if __name__ == "__main__":
    main()
