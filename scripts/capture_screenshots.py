from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
SHOTS = [
    ("02-assessment.png", ".result-grid"),
    ("03-gap-map.png", "#gaps"),
    ("04-library.png", "#library"),
]


def capture(browser, base_url: str) -> None:
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(base_url + "/", wait_until="networkidle")
    page.wait_for_timeout(800)
    # Reveal below-fold panels; otherwise IntersectionObserver hides them in
    # full-page captures via the .reveal opacity transition.
    page.evaluate(
        """() => {
            document.querySelectorAll('.reveal').forEach((el) => {
                el.style.transition = 'none';
                el.classList.add('in');
            });
        }"""
    )
    page.wait_for_timeout(300)
    page.screenshot(path=str(OUT / "01-overview.png"), full_page=True)
    page.add_style_tag(content=".topbar { display: none !important; }")
    for name, selector in SHOTS:
        page.locator(selector).screenshot(path=str(OUT / name))
        print(f"wrote docs/screenshots/{name}")
    page.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8010")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        try:
            browser = p.chromium.launch()
        except Exception:
            browser = p.chromium.launch(channel="chrome")
        try:
            capture(browser, args.base_url)
        finally:
            browser.close()
    print("wrote docs/screenshots/01-overview.png")


if __name__ == "__main__":
    main()
