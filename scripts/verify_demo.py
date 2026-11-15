from __future__ import annotations

import http.server
import socket
import socketserver
import tempfile
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1] / "docs"
OUT = ROOT / "screenshots"
QA = Path(tempfile.mkdtemp(prefix="firebreak-demo-"))


def serve() -> tuple[socketserver.TCPServer, int]:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    handler = lambda *a, **kw: http.server.SimpleHTTPRequestHandler(*a, directory=str(ROOT), **kw)
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd, port


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    httpd, port = serve()
    url = f"http://127.0.0.1:{port}/demo.html"
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector(".cond")
        page.click("#play")
        page.wait_for_timeout(200)
        print("title:", page.title())
        print("condition cells:", page.eval_on_selector_all(".cell b", "els => els.map(e => e.textContent)"))
        page.screenshot(path=str(QA / "1-condition.png"))

        page.click("[data-step='1']")
        page.wait_for_selector(".row")
        page.wait_for_timeout(900)
        print("evidence count:", page.inner_text("#n"),
              "| rows:", page.eval_on_selector_all(".row", "els => els.length"),
              "| outcomes:", page.eval_on_selector_all(".tag", "els => els.map(e => e.textContent)"))
        page.screenshot(path=str(QA / "2-evidence.png"))

        page.click("[data-step='2']")
        page.wait_for_selector(".grade-stamp")
        page.wait_for_timeout(1000)
        print("grade:", page.inner_text(".grade-stamp"),
              "| rules:", page.inner_text("#rc"),
              "| reasons:", page.eval_on_selector_all(".reasons li", "els => els.length"))
        page.screenshot(path=str(QA / "3-grade.png"))

        page.click("[data-step='3']")
        page.wait_for_selector(".voice")
        page.wait_for_timeout(900)
        print("voices:", page.eval_on_selector_all(".voice h3", "els => els.map(e => e.textContent)"))
        page.screenshot(path=str(QA / "4-review.png"))

        page.click("[data-step='4']")
        page.wait_for_selector(".vword")
        page.wait_for_timeout(900)
        print("verdict:", page.inner_text(".vword"),
              "| grade:", page.inner_text(".vgrade"),
              "| sens:", page.eval_on_selector_all(".schip", "els => els.length"),
              "| refusal visible:", page.is_visible(".refuse"))
        page.screenshot(path=str(OUT / "demo.png"))

        page.click("[data-case='pmma_lunar']")
        page.wait_for_timeout(400)
        page.click("[data-step='4']")
        page.wait_for_selector(".refuse")
        page.wait_for_timeout(900)
        print("lunar verdict:", page.inner_text(".vword"),
              "| grade:", page.inner_text(".vgrade"),
              "| refuse:", " / ".join(page.eval_on_selector_all(".refuse p, .refuse li", "els => els.map(e => e.textContent)")))
        page.screenshot(path=str(OUT / "demo-refusal.png"))

        page.wait_for_timeout(6200)
        print("bar at finish:", page.eval_on_selector("#progress", "e => e.style.width"),
              "| play label:", page.inner_text("#play"))

        print("theme label:", page.inner_text("#theme"))
        page.click("#theme")
        page.wait_for_timeout(300)
        page.screenshot(path=str(QA / "5-light.png"))
        page.click("#theme")

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(url, wait_until="networkidle")
        mobile.wait_for_selector(".cond")
        print("mobile scrollWidth:", mobile.evaluate("document.documentElement.scrollWidth"))
        mobile.screenshot(path=str(QA / "6-mobile.png"))
        browser.close()

    print("console errors:", "; ".join(errors) if errors else "none")
    print("qa screenshots:", QA)
    httpd.shutdown()


if __name__ == "__main__":
    main()
