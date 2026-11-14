from __future__ import annotations

import argparse
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "artifacts"
CASES = [
    ("dossier-PMMA-ISS.pdf", "PMMA", "iss_internal"),
    ("dossier-Kevlar-PBI-lunar.pdf", "Kevlar/PBI", "lunar_surface"),
    ("dossier-SIBAL-ISS.pdf", "SIBAL", "iss_internal"),
]


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
        page = browser.new_page(viewport={"width": 1440, "height": 900})
        for name, material, atmosphere in CASES:
            page.goto(
                f"{args.base_url}/assess?material={material}&atmosphere={atmosphere}",
                wait_until="networkidle",
            )
            page.evaluate(
                """() => {
                    document.querySelectorAll('.reveal').forEach((el) => {
                        el.style.transition = 'none';
                        el.classList.add('in');
                    });
                }"""
            )
            page.emulate_media(media="print")
            page.pdf(
                path=str(OUT / name),
                format="A4",
                print_background=True,
                margin={"top": "12mm", "bottom": "12mm", "left": "10mm", "right": "10mm"},
            )
            page.emulate_media(media="screen")
            print(f"wrote artifacts/{name}")
        browser.close()


if __name__ == "__main__":
    main()
