from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "docs" / "screenshots"
DOSSIER = "/assess?material=PMMA&atmosphere=iss_internal"


def reveal(page) -> None:
    page.evaluate(
        """() => {
            document.querySelectorAll('.reveal').forEach((el) => {
                el.style.transition = 'none';
                el.classList.add('in');
            });
        }"""
    )
    page.wait_for_timeout(300)


def hide_topbar(page) -> None:
    page.add_style_tag(content=".topbar { display: none !important; }")


def capture(browser, base_url: str) -> None:
    page = browser.new_page(viewport={"width": 1440, "height": 900})
    page.goto(base_url + "/", wait_until="networkidle")
    reveal(page)
    page.screenshot(path=str(OUT / "01-overview.png"), full_page=True)
    print("wrote docs/screenshots/01-overview.png")

    hide_topbar(page)
    page.locator("#ranked").screenshot(path=str(OUT / "05-ranked-findings.png"))
    page.locator("#matrix").screenshot(path=str(OUT / "06-matrix.png"))
    print("wrote docs/screenshots/05-ranked-findings.png")
    print("wrote docs/screenshots/06-matrix.png")

    page.goto(base_url + DOSSIER, wait_until="networkidle")
    reveal(page)
    hide_topbar(page)
    for name, selector in (
        ("02-assessment.png", ".result-grid"),
        ("03-gap-map.png", "#gaps"),
    ):
        page.locator(selector).screenshot(path=str(OUT / name))
        print(f"wrote docs/screenshots/{name}")

    page.goto(base_url + "/library?q=PMMA%20margin", wait_until="networkidle")
    reveal(page)
    hide_topbar(page)
    page.locator("#library").screenshot(path=str(OUT / "04-library.png"))
    print("wrote docs/screenshots/04-library.png")
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


if __name__ == "__main__":
    main()
