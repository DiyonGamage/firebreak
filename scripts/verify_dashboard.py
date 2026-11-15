from __future__ import annotations

import http.server
import socket
import socketserver
import threading
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1] / "docs"
OUT = ROOT / "screenshots"


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
    url = f"http://127.0.0.1:{port}/"
    errors: list[str] = []
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        page.on("console", lambda m: errors.append(f"{m.type}: {m.text}") if m.type == "error" else None)
        page.on("pageerror", lambda e: errors.append(f"pageerror: {e}"))
        page.goto(url, wait_until="networkidle")
        page.wait_for_timeout(1200)
        print("title:", page.title())
        print("stats:", page.eval_on_selector_all(".stat b", "els => els.map(e => e.textContent)"))
        print("grade:", page.inner_text("#grade"), "| verdict:", page.inner_text("#vword"))
        print("nearest rows:", page.eval_on_selector_all("#nearest tr", "els => els.length"))
        print("voices:", page.eval_on_selector_all(".voice", "els => els.length"))
        print("plate nodes:", page.eval_on_selector_all("#plate circle", "els => els.length"))
        print("curve path:", page.eval_on_selector_all("#curve-svg path", "els => els.length"))
        print("change:", page.eval_on_selector_all("#change-list li", "els => els.map(e => e.textContent)"))
        print("matrix cells:", page.eval_on_selector_all(".mx", "els => els.length"),
              "| on:", page.eval_on_selector_all(".mx.on .n", "els => els.map(e => e.textContent)"))
        print("thresholds:", page.inner_text("#thresholds"))
        page.screenshot(path=str(OUT / "dashboard-hero.png"))
        for name, sel in [("console", "#console"), ("change", "#change"), ("sweep", "#sweep"), ("blind", "#blind")]:
            page.locator(sel).scroll_into_view_if_needed()
            page.wait_for_timeout(350)
            page.screenshot(path=str(OUT / f"dashboard-{name}.png"))
        # interaction check
        page.eval_on_selector("#o2", "e => {e.value='18.1'; e.dispatchEvent(new Event('input',{bubbles:true}))}")
        page.wait_for_timeout(250)
        print("at 18.1 ->", page.inner_text("#ro-verdict"), "| p:", page.inner_text("#ml-p"),
              "| abstain visible:", page.is_visible("#abstain"))
        page.eval_on_selector("#o2", "e => {e.value='24.1'; e.dispatchEvent(new Event('input',{bubbles:true}))}")
        page.wait_for_timeout(250)
        print("at 24.1 ->", page.inner_text("#ro-verdict"), "| p:", page.inner_text("#ml-p"),
              "| abstain visible:", page.is_visible("#abstain"))
        page.click(".chip[data-key='kevlar_pbi']")
        page.wait_for_timeout(250)
        print("kevlar case:", page.inner_text("#grade"), page.inner_text("#vword"))

        mobile = browser.new_page(viewport={"width": 390, "height": 844})
        mobile.goto(url, wait_until="networkidle")
        mobile.wait_for_timeout(900)
        mobile.screenshot(path=str(OUT / "dashboard-mobile.png"))
        w = mobile.evaluate("document.documentElement.scrollWidth")
        print("mobile scrollWidth:", w, "viewport 390 -> overflow:", w > 391)
        browser.close()
    httpd.shutdown()
    print("console errors:", errors or "none")


if __name__ == "__main__":
    main()
