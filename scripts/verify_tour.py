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
QA = Path(tempfile.mkdtemp(prefix="firebreak-tour-"))


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
    url = f"http://127.0.0.1:{port}/?tour=1"
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.goto(url, wait_until="domcontentloaded")
        page.wait_for_selector(".gt.on", timeout=20000)
        page.wait_for_timeout(1200)
        print("step:", page.inner_text("#gt-step"), "|", page.inner_text("#gt-kicker"), "|", page.inner_text("#gt-title"))
        print("spot:", page.eval_on_selector("#gt-spot", "e => [e.style.left, e.style.top, e.style.width, e.style.height]"))
        page.screenshot(path=str(QA / "1-corpus.png"))

        page.click("#gt-next")
        page.wait_for_timeout(1900)
        print("step2:", page.inner_text("#gt-step"), "|", page.inner_text("#gt-kicker"),
              "| selected case:", page.eval_on_selector(".case[aria-pressed='true']", "e => e.dataset.key"))
        page.screenshot(path=str(OUT / "demo.png"))

        for _ in range(3):
            page.click("#gt-next")
            page.wait_for_timeout(700)
        print("step5:", page.inner_text("#gt-step"), "|", page.inner_text("#gt-kicker"))
        page.wait_for_timeout(2600)
        print("slider:", page.eval_on_selector("#o2", "e => e.value"),
              "| verdict:", page.inner_text("#ro-verdict"),
              "| p:", page.inner_text("#ml-p"))
        page.screenshot(path=str(OUT / "demo-threshold.png"))

        page.keyboard.press("Escape")
        page.wait_for_timeout(600)
        print("closed:", not page.is_visible(".gt.on"),
              "| case restored:", page.eval_on_selector(".case[aria-pressed='true']", "e => e.dataset.key"),
              "| slider restored:", page.eval_on_selector("#o2", "e => e.value"))

        page.click("nav a[data-demo]")
        page.wait_for_selector(".gt.on")
        print("nav demo reopens:", page.inner_text("#gt-step"))

        page.click("#theme")
        page.wait_for_timeout(400)
        page.screenshot(path=str(QA / "2-light.png"))
        page.click("#theme")
        page.keyboard.press("Escape")

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(url, wait_until="domcontentloaded")
        mobile.wait_for_selector(".gt.on", timeout=20000)
        mobile.wait_for_timeout(1200)
        box = mobile.eval_on_selector("#gt-card", "e => {const r=e.getBoundingClientRect();return [r.left,r.right,r.bottom,innerHeight]}")
        print("mobile card:", box, "| scrollWidth:", mobile.evaluate("document.documentElement.scrollWidth"))
        mobile.screenshot(path=str(QA / "3-mobile.png"))
        browser.close()

    print("console errors:", "; ".join(errors) if errors else "none")
    print("qa screenshots:", QA)
    httpd.shutdown()


if __name__ == "__main__":
    main()
