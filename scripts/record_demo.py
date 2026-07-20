"""Record Infobroker desk demo video + chart screenshots for the README."""

from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "docs" / "images"
VIDEO_DIR = ROOT / "docs" / "video_raw"
OUT_MP4 = ROOT / "docs" / "demo.mp4"
BASE = "http://127.0.0.1:8000/"


def wait(page, ms: int = 800) -> None:
    page.wait_for_timeout(ms)


def shot(page, name: str, full: bool = True) -> None:
    IMAGES.mkdir(parents=True, exist_ok=True)
    page.screenshot(path=str(IMAGES / name), full_page=full)


def main() -> int:
    VIDEO_DIR.mkdir(parents=True, exist_ok=True)
    IMAGES.mkdir(parents=True, exist_ok=True)
    for old in VIDEO_DIR.glob("*"):
        old.unlink()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 900},
            device_scale_factor=1,
            record_video_dir=str(VIDEO_DIR),
            record_video_size={"width": 1440, "height": 900},
        )
        page = context.new_page()
        page.goto(BASE, wait_until="networkidle", timeout=60000)
        wait(page, 1500)

        # Markets
        page.locator('[data-desk-tab="markets"]').click()
        wait(page, 1200)
        shot(page, "desk-markets.png", full=False)

        # Trading
        page.locator('[data-desk-tab="trading"]').click()
        wait(page, 1200)
        shot(page, "desk-trading.png", full=False)

        # Chart studio — load AAPL pack (dates required)
        page.locator('[data-desk-tab="charts"]').click()
        wait(page, 1000)
        page.fill("#cs-symbol", "AAPL")
        # Ensure date range even if init defaults lag
        page.evaluate(
            """() => {
              const end = new Date();
              const start = new Date();
              start.setFullYear(end.getFullYear() - 1);
              const fmt = (d) => d.toISOString().slice(0, 10);
              const s = document.getElementById('cs-start');
              const e = document.getElementById('cs-end');
              if (s) s.value = fmt(start);
              if (e) e.value = fmt(end);
            }"""
        )
        with page.expect_response(
            lambda r: "/api/charts/pack" in r.url and r.request.method == "POST",
            timeout=120000,
        ) as resp_info:
            page.click("#btn-chart-pack")
        resp = resp_info.value
        if not resp.ok:
            print(f"chart pack HTTP {resp.status}: {resp.text()[:300]}", file=sys.stderr)
        page.wait_for_function(
            """() => {
              const t = document.getElementById('cs-summary')?.textContent || '';
              return t.includes('AAPL') && t.includes('bars');
            }""",
            timeout=60000,
        )
        wait(page, 1500)
        shot(page, "desk-charts.png", full=False)
        page.locator("#cs-rsi").scroll_into_view_if_needed()
        wait(page, 600)
        shot(page, "desk-charts-indicators.png", full=False)

        # Markets live chart dock if present
        page.locator('[data-desk-tab="markets"]').click()
        wait(page, 800)
        live = page.locator("#live-collapse-chart")
        if live.count():
            live.locator("summary").click()
            wait(page, 500)
            # Try open a symbol from board for live chart
            tile = page.locator(".live-tile, .board-tile, [data-symbol]").first
            if tile.count():
                try:
                    tile.click(timeout=3000)
                    wait(page, 2000)
                    shot(page, "desk-live-chart.png", full=False)
                except Exception:
                    pass

        # Tour a few steps
        page.locator("#btn-tour").click()
        wait(page, 1000)
        shot(page, "desk-tour.png", full=False)
        for _ in range(4):
            nxt = page.locator("#btn-tour-next")
            if nxt.count() and nxt.is_enabled():
                nxt.click()
                wait(page, 700)
        done = page.locator("#btn-tour-done")
        if done.count():
            done.click()
            wait(page, 600)

        # Grapevine sidebar visible on trading
        page.locator('[data-desk-tab="trading"]').click()
        wait(page, 1000)
        shot(page, "desk-grapevine.png", full=False)

        # Brief pause so the last frame holds
        wait(page, 1500)
        context.close()
        browser.close()

    webms = list(VIDEO_DIR.glob("*.webm"))
    if not webms:
        print("No webm recorded", file=sys.stderr)
        return 1
    raw = webms[0]
    print(f"Raw video: {raw} ({raw.stat().st_size} bytes)")

    # Compress to H.264 mp4 suitable for GitHub README
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(raw),
        "-vf",
        "fps=15,scale=1280:-2",
        "-c:v",
        "libx264",
        "-preset",
        "medium",
        "-crf",
        "28",
        "-movflags",
        "+faststart",
        "-an",
        str(OUT_MP4),
    ]
    subprocess.run(cmd, check=True)
    print(f"Wrote {OUT_MP4} ({OUT_MP4.stat().st_size} bytes)")

    # Cleanup raw capture (keep only mp4 in docs/)
    for f in VIDEO_DIR.glob("*"):
        f.unlink()
    try:
        VIDEO_DIR.rmdir()
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
