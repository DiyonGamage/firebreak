"""Capture annotated screenshots for the Singlish pitch companion.

Requires the report on http://127.0.0.1:8021/ and the app on
http://127.0.0.1:8010/. Writes PNGs to pitch/img/.
"""

from __future__ import annotations

import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

APP = "http://127.0.0.1:8010"
REPORT = "http://127.0.0.1:8021/"
OUT = Path(__file__).resolve().parent.parent / "pitch" / "img"
VIEWPORT = {"width": 1280, "height": 900}
SCALE = 2

MARKER_CSS = """
.pshot-marker{position:absolute;width:26px;height:26px;border-radius:50%;
background:#c2410c;color:#fff;font:700 13px/26px Consolas,monospace;text-align:center;
border:2px solid #fff;box-shadow:0 1px 5px rgba(0,0,0,.5);z-index:2147483647;pointer-events:none;}
.js .reveal{opacity:1 !important;transform:none !important;}
"""


def settle(page):
    page.wait_for_load_state("networkidle")
    page.evaluate("document.fonts && document.fonts.ready")
    page.wait_for_timeout(450)


def rect_js(sel):
    return f"""() => {{
        const el = document.querySelector({sel!r});
        if (!el) throw new Error('missing ' + {sel!r});
        const r = el.getBoundingClientRect();
        return {{x: r.left + scrollX, y: r.top + scrollY, w: r.width, h: r.height}};
    }}"""


def union_js(selectors):
    return f"""() => {{
        const sels = {selectors!r};
        const rs = [];
        for (const s of sels) {{
            if (s.startsWith('js:')) {{
                const el = eval(s.slice(3));
                if (el) rs.push(el.getBoundingClientRect());
            }} else {{
                document.querySelectorAll(s).forEach(e => rs.push(e.getBoundingClientRect()));
            }}
        }}
        if (!rs.length) throw new Error('no clip nodes: ' + sels.join(', '));
        const x = Math.min(...rs.map(r => r.left));
        const y = Math.min(...rs.map(r => r.top));
        const right = Math.max(...rs.map(r => r.right));
        const bottom = Math.max(...rs.map(r => r.bottom));
        return {{x, y, w: right - x, h: bottom - y}};
    }}"""


def inject(page):
    page.evaluate(
        """(css) => {
        const style = document.createElement('style');
        style.textContent = css;
        document.head.appendChild(style);
    }""",
        MARKER_CSS,
    )


def marker(page, selector, number, pos="tl", nth=0):
    page.evaluate(
        """([sel, number, pos, nth]) => {
        const els = document.querySelectorAll(sel);
        const el = els[nth];
        if (!el) throw new Error('no node for marker ' + number + ': ' + sel);
        const r = el.getBoundingClientRect();
        const x = r.left + scrollX, y = r.top + scrollY;
        let mx, my;
        if (pos === 'tl') { mx = x - 13; my = y - 13; }
        else if (pos === 'in-tl') { mx = x + 5; my = y + 5; }
        else if (pos === 'left') { mx = x - 40; my = y + r.height / 2 - 13; }
        else if (pos === 'right') { mx = x + r.width + 12; my = y + r.height / 2 - 13; }
        else if (pos === 'top') { mx = x + r.width / 2 - 13; my = y - 34; }
        else if (pos === 'bottom') { mx = x + r.width / 2 - 13; my = y + r.height + 8; }
        mx = Math.max(4, Math.min(mx, innerWidth - 32));
        my = Math.max(4, my);
        const m = document.createElement('span');
        m.className = 'pshot-marker';
        m.textContent = number;
        m.style.left = mx + 'px';
        m.style.top = my + 'px';
        document.body.appendChild(m);
    }""",
        [selector, number, pos, nth],
    )


def marker_at(page, number, fx, fy):
    """Place a marker at a fraction of the document body (0..1)."""
    page.evaluate(
        """([number, fx, fy]) => {
        const m = document.createElement('span');
        m.className = 'pshot-marker';
        m.textContent = number;
        m.style.left = (document.documentElement.scrollWidth * fx - 13) + 'px';
        m.style.top = (document.documentElement.scrollHeight * fy - 13) + 'px';
        document.body.appendChild(m);
    }""",
        [number, fx, fy],
    )


def marker_img(page, img_selector, number, fx, fy):
    """Place a marker at a fraction of an image's box."""
    page.evaluate(
        """([sel, number, fx, fy]) => {
        const el = document.querySelector(sel);
        if (!el) throw new Error('no img ' + sel);
        const r = el.getBoundingClientRect();
        const m = document.createElement('span');
        m.className = 'pshot-marker';
        m.textContent = number;
        m.style.left = (r.left + scrollX + r.width * fx - 13) + 'px';
        m.style.top = (r.top + scrollY + r.height * fy - 13) + 'px';
        document.body.appendChild(m);
    }""",
        [img_selector, number, fx, fy],
    )


def shoot(page, out, clip_js, pad=18, max_h=None, settle_ms=350):
    pad = max(pad, 44)
    viewport = page.viewport_size
    box = page.evaluate(clip_js)
    if box["y"] < 0 or box["y"] + box["h"] > viewport["height"] - 8:
        page.evaluate(
            "(top) => window.scrollTo(0, Math.max(0, top - 48))", box["y"]
        )
        page.wait_for_timeout(settle_ms)
        box = page.evaluate(clip_js)
    x = max(0.0, box["x"] - pad)
    y = max(0.0, box["y"] - pad)
    right = min(float(viewport["width"]), box["x"] + box["w"] + pad)
    bottom = min(float(viewport["height"]), box["y"] + box["h"] + pad)
    if max_h:
        bottom = min(bottom, y + max_h)
    clip = {"x": x, "y": y, "width": right - x, "height": bottom - y}
    page.wait_for_timeout(250)
    path = OUT / out
    page.screenshot(path=str(path), clip=clip, animations="disabled")
    print(f"{out}: {clip['width']:.0f}x{clip['height']:.0f}")


def goto(page, url):
    page.goto(url, wait_until="networkidle")
    settle(page)
    inject(page)
    page.add_style_tag(content=".topbar{position:static !important;} .dossier-actions{display:none !important;}")


def run():
    OUT.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", headless=True)

        def new_page():
            return browser.new_page(
                viewport=VIEWPORT, color_scheme="light", device_scale_factor=SCALE
            )

        # ---------- report ----------
        pg = new_page()
        goto(pg, REPORT)
        for sel, n, pos in [
            (".wordmark", 1, "left"),
            (".mastnav", 2, "left"),
            (".themetoggle", 3, "left"),
            (".titlecopy h1", 4, "left"),
            (".byline", 5, "left"),
            (".links", 6, "left"),
            (".coverplate", 7, "tl"),
        ]:
            marker(pg, sel, n, pos)
        shoot(pg, "report-top.png", union_js([".masthead", ".titleblock"]), pad=16)

        pg = new_page()
        goto(pg, REPORT)
        for sel, n, pos in [
            ("#problem h2", 1, "left"),
            ("#problem p:not(.small)", 2, "left"),
            ("#problem blockquote", 3, "tl"),
            ("#problem blockquote cite", 4, "left"),
        ]:
            marker(pg, sel, n, pos)
        shoot(pg, "report-problem.png", union_js(["#problem h2", "#problem blockquote"]), pad=16)

        pg = new_page()
        goto(pg, REPORT)
        shoot(
            pg,
            "report-pipeline.png",
            union_js(['js:document.querySelector(\'img[src*="evidence-pipeline"]\').closest("figure")']),
            pad=16,
        )

        pg = new_page()
        goto(pg, REPORT)
        for sel, n, pos, nth in [
            (".assesshead .assessenv", 1, "left", 0),
            (".assesshead .assessenv", 2, "left", 1),
            (".assesscards .acard", 3, "tl", 0),
            (".assesscards.pair .acard", 4, "tl", 0),
            (".assesscards .acard", 5, "tl", 4),
            ("figure.assessfigure figcaption", 6, "left", 0),
        ]:
            marker(pg, sel, n, pos, nth)
        shoot(pg, "report-cards.png", union_js(["figure.assessfigure"]), pad=16)

        pg = new_page()
        goto(pg, REPORT)
        img = 'img[src*="corpus-units"]'
        for n, fx, fy in [(1, 0.10, 0.30), (2, 0.14, 0.52), (3, 0.10, 0.52), (4, 0.50, 0.93), (5, 0.665, 0.605)]:
            marker_img(pg, img, n, fx, fy)
        shoot(
            pg,
            "report-corpus.png",
            union_js([f'js:document.querySelector(\'{img}\').closest("figure")']),
            pad=16,
        )

        pg = new_page()
        goto(pg, REPORT)
        for sel, n, pos in [
            ("#limits h2", 1, "left"),
            ("#limits ol.limits li:nth-child(1)", 2, "left"),
            ("#limits ol.limits li:nth-child(2)", 3, "left"),
            ("#limits ol.limits li:nth-child(3)", 4, "left"),
        ]:
            marker(pg, sel, n, pos)
        shoot(
            pg,
            "report-limits.png",
            union_js(["#limits h2", "#limits ol.limits li:nth-child(3)"]),
            pad=16,
        )
        pg.close()

        # ---------- app ----------
        pg = new_page()
        goto(pg, APP + "/")
        for sel, n, pos in [
            (".dash-hero h1", 1, "left"),
            (".dash-hero .lede", 2, "left"),
            (".dash-search .card-kicker", 3, "left"),
            (".dash-search button.primary", 4, "right"),
            (".hero-note", 5, "left"),
        ]:
            marker(pg, sel, n, pos)
        shoot(pg, "app-hero.png", union_js([".dash-hero"]), pad=16)

        pg = new_page()
        goto(pg, APP + "/")
        for sel, n, pos in [
            (".verdict-mark", 1, "tl"),
            (".verdict-copy h2", 2, "left"),
            (".verdict-link", 3, "right"),
        ]:
            marker(pg, sel, n, pos)
        shoot(pg, "app-headline.png", union_js([".verdict-band"]), pad=16)

        pg = new_page()
        goto(pg, APP + "/")
        for i in range(5):
            marker(pg, ".kpi-strip .kpi", i + 1, "top", i)
        shoot(pg, "app-kpis.png", union_js([".kpi-strip"]), pad=16)

        pg = new_page()
        goto(pg, APP + "/")
        for sel, n, pos, nth in [
            ("#findings h2", 1, "left", 0),
            ("#findings .finding", 2, "tl", 0),
            ("#findings .finding", 3, "tl", 1),
            ("#findings .finding", 4, "tl", 2),
        ]:
            marker(pg, sel, n, pos, nth)
        shoot(pg, "app-findings.png", union_js(["#findings"]), pad=16)

        pg = new_page()
        goto(pg, APP + "/")
        for sel, n, pos, nth in [
            ("#ranked h2", 1, "left", 0),
            (".insight-card.grade-a", 2, "tl", 0),
            (".insight-card.grade-d", 3, "tl", 0),
            (".insight-card.grade-a .insight-change", 4, "left", 0),
            (".insight-card.grade-a .insight-open", 5, "right", 0),
        ]:
            marker(pg, sel, n, pos, nth)
        shoot(pg, "app-ranked.png", union_js(["#ranked"]), pad=16, max_h=700)

        pg = new_page()
        goto(pg, APP + "/")
        for sel, n, pos in [
            ("#matrix h2", 1, "left"),
            ("#matrix thead th:nth-child(2)", 2, "top"),
            ("#matrix thead th:nth-child(4)", 3, "top"),
            ("#matrix tbody tr:nth-child(1) td:nth-child(2)", 4, "tl"),
            ("#matrix tbody tr:nth-child(8) td:nth-child(4)", 5, "tl"),
            (".matrix-note", 6, "left"),
        ]:
            marker(pg, sel, n, pos)
        shoot(pg, "app-matrix.png", union_js(["#matrix"]), pad=16)

        pg = new_page()
        goto(pg, APP + "/")
        for sel, n, pos, nth in [
            ("#how h2", 1, "left", 0),
            ("#how .read-card", 2, "tl", 0),
            ("#how .read-card", 3, "tl", 1),
            ("#how .read-card", 4, "tl", 2),
            ("#how .read-card", 5, "tl", 3),
            ("#how .step", 6, "left", 0),
            ("#how .step", 7, "left", 1),
            ("#how .step", 8, "left", 2),
        ]:
            marker(pg, sel, n, pos, nth)
        shoot(pg, "app-how.png", union_js(["#how"]), pad=16)

        pg = new_page()
        goto(pg, APP + "/")
        for sel, n, pos, nth in [
            ("#si h2", 1, "left", 0),
            ("#si .pipe-stage", 2, "tl", 0),
            ("#si .pipe-stage", 3, "tl", 1),
            ("#si .pipe-stage", 4, "tl", 2),
            ("#si .pipe-stage", 5, "tl", 3),
            ("#si .pipe-stage", 6, "tl", 4),
        ]:
            marker(pg, sel, n, pos, nth)
        shoot(pg, "app-pipeline.png", union_js(["#si"]), pad=16)
        pg.close()

        # ---------- investigations ----------
        pg = new_page()
        goto(pg, APP + "/investigations")
        for sel, n, pos in [
            (".dash-hero h1", 1, "left"),
            (".dash-hero .lede", 2, "left"),
            (".env-tabs", 3, "left"),
            (".hero-note", 4, "left"),
        ]:
            marker(pg, sel, n, pos)
        shoot(pg, "inv-hero.png", union_js([".dash-hero"]), pad=16)

        pg = new_page()
        goto(pg, APP + "/investigations")
        for sel, n, pos, nth in [
            ("#pillars h2", 1, "left", 0),
            (".pillar-card", 2, "tl", 0),
            (".pillar-card", 3, "tl", 1),
            (".pillar-card", 4, "tl", 2),
        ]:
            marker(pg, sel, n, pos, nth)
        shoot(pg, "inv-pillars.png", union_js(["#pillars"]), pad=16)

        pg = new_page()
        goto(pg, APP + "/investigations")
        for sel, n, pos, nth in [
            ("#ranked h2", 1, "left", 0),
            ("#ranked tbody tr:nth-child(1) td:nth-child(2)", 2, "left", 0),
            ("#ranked tbody tr:nth-child(1) td:nth-child(3)", 3, "top", 0),
            ("#ranked tbody tr:nth-child(1) td:nth-child(5)", 4, "top", 0),
            ("#ranked tbody tr:nth-child(1) td:nth-child(7)", 5, "top", 0),
        ]:
            marker(pg, sel, n, pos, nth)
        shoot(pg, "inv-ranked.png", union_js(["#ranked"]), pad=16, max_h=560)

        pg = new_page()
        goto(pg, APP + "/investigations")
        for sel, n, pos, nth in [
            ("#contradictions h2", 1, "left", 0),
            ("#contradictions .contra-card", 2, "tl", 0),
            ("#contradictions .contra-card", 3, "tl", 1),
        ]:
            marker(pg, sel, n, pos, nth)
        shoot(pg, "inv-contra.png", union_js(["#contradictions"]), pad=16)
        pg.close()

        # ---------- dossier ----------
        dossier = APP + "/assess?material=PMMA&atmosphere=iss_internal"
        pg = new_page()
        goto(pg, dossier)
        for sel, n, pos in [
            (".dossier-title h1", 1, "left"),
            (".dossier-title .subhead", 2, "left"),
            (".dossier-flags", 3, "left"),
            (".back-link", 4, "left"),
        ]:
            try:
                marker(pg, sel, n, pos)
            except Exception as exc:
                print("skip marker", sel, exc)
        shoot(pg, "dossier-head.png", union_js([".dossier-head"]), pad=16)

        pg = new_page()
        goto(pg, dossier)
        for sel, n, pos, nth in [
            (".result-grid .grade-letter", 1, "tl", 0),
            (".result-grid .grade-verdict", 2, "left", 0),
            (".result-grid .grade-meta", 3, "left", 0),
            (".result-grid .grade-flags", 4, "left", 0),
            (".result-grid .panel", 5, "tl", 0),
            (".result-grid .panel", 6, "tl", 1),
        ]:
            try:
                marker(pg, sel, n, pos, nth)
            except Exception as exc:
                print("skip marker", sel, exc)
        shoot(pg, "dossier-grade.png", union_js([".result-grid"]), pad=16, max_h=680)

        pg = new_page()
        goto(pg, dossier)
        for i in range(4):
            marker(pg, ".court-voice", i + 2, "tl", i)
        marker(pg, "#court .panel-kicker", 1, "left")
        marker(pg, "#court .court-note", 6, "left")
        shoot(pg, "dossier-court.png", union_js(["#court"]), pad=16)

        pg = new_page()
        goto(pg, dossier)
        for sel, n, pos in [
            ("#model h2", 1, "left"),
            ("#model .model-badge", 2, "left"),
            ("#model .model-abstain p:first-child", 3, "left"),
            ("#model .model-note", 4, "left"),
            ("#model .model-foot", 5, "left"),
        ]:
            marker(pg, sel, n, pos)
        shoot(pg, "dossier-model.png", union_js(["#model"]), pad=16)

        pg = new_page()
        goto(pg, APP + "/assess?material=PMMA&atmosphere=iss_internal&o2=22.2&pressure=14.7")
        for sel, n, pos in [
            ("#model h2", 1, "left"),
            ("#model .model-number", 2, "tl"),
            ("#model .model-set", 3, "left"),
            ("#model .model-facts", 4, "left"),
            ("#model .model-note", 5, "left"),
        ]:
            marker(pg, sel, n, pos)
        shoot(pg, "dossier-model-resolved.png", union_js(["#model"]), pad=16)

        pg = new_page()
        goto(pg, dossier)
        for sel, n, pos in [
            (".panel.ledger .panel-kicker", 1, "left"),
            (".panel.ledger .legend", 2, "left"),
            (".panel.ledger tbody tr:nth-child(1)", 3, "left"),
            (".panel.ledger tbody tr:nth-child(1) td:nth-child(9)", 4, "right"),
        ]:
            try:
                marker(pg, sel, n, pos)
            except Exception as exc:
                print("skip marker", sel, exc)
        shoot(pg, "dossier-ledger.png", union_js([".panel.ledger"]), pad=16, max_h=600)
        pg.close()

        # ---------- library ----------
        pg = new_page()
        goto(pg, APP + "/library")
        for sel, n, pos in [
            (".library-hero h1", 1, "left"),
            (".library-search input", 2, "tl"),
            (".library-search button", 3, "right"),
            (".library-suggestions", 4, "left"),
        ]:
            marker(pg, sel, n, pos)
        shoot(pg, "library-hero.png", union_js([".library-hero"]), pad=16)

        pg = new_page()
        goto(pg, APP + "/library")
        for sel, n, pos, nth in [
            (".library-corpus-head h2", 5, "left", 0),
            (".doc-grid .doc", 6, "tl", 0),
            (".doc-grid .doc", 7, "tl", 3),
        ]:
            marker(pg, sel, n, pos, nth)
        shoot(pg, "library-docs.png", union_js([".library-corpus-head", ".doc-grid"]), pad=16, max_h=620)
        pg.close()

        browser.close()


if __name__ == "__main__":
    sys.exit(run())
