"""Render pitch/pitch-companion.html to an A4 PDF."""

from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "pitch" / "pitch-companion.html"
OUT = ROOT / "pitch" / "Firebreak-Pitch-Companion.pdf"


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 1400})
        page.goto(SRC.as_uri(), wait_until="networkidle")
        page.emulate_media(media="print")
        page.wait_for_timeout(600)
        page.pdf(
            path=str(OUT),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
        )
        browser.close()
    try:
        from pypdf import PdfReader

        print("pages:", len(PdfReader(str(OUT)).pages))
    except Exception:
        print("pages~", OUT.read_bytes().count(b"/Type /Page"))
    print(OUT, OUT.stat().st_size)


if __name__ == "__main__":
    main()
